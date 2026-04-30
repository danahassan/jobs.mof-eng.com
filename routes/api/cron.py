"""routes/api/cron.py — scheduled background jobs triggered by external cron.

These endpoints are protected by a shared secret token sent in the
`X-Cron-Token` header (or `?token=` query param). The token is read from
the environment variable `CRON_TOKEN`. If unset, all endpoints return 503
so misconfigured production servers fail loud rather than silent.

Configure cPanel cron jobs (server time):

    # Daily 8AM — supervisor "New applications" reminder
    0 8 * * *   curl -fsS -H "X-Cron-Token: SECRET" https://jobs.mof-eng.com/api/v1/cron/supervisor-daily-reminders >/dev/null

    # Weekly Monday 8AM — student job-match digest (new internships matching profile)
    0 8 * * 1   curl -fsS -H "X-Cron-Token: SECRET" https://jobs.mof-eng.com/api/v1/cron/student-job-match-digest >/dev/null

    # Weekly Monday 9AM — coordinator cohort digest (pending approvals + at-risk students)
    0 9 * * 1   curl -fsS -H "X-Cron-Token: SECRET" https://jobs.mof-eng.com/api/v1/cron/coordinator-weekly-digest >/dev/null

    # Hourly — 24-hour interview reminder for applicants
    0 * * * *   curl -fsS -H "X-Cron-Token: SECRET" https://jobs.mof-eng.com/api/v1/cron/interview-reminders >/dev/null

All endpoints are idempotent within their period (day/week): they track
`*_last_sent` on the user record and skip recipients already processed,
so duplicate cron firings are safe.
"""
from datetime import datetime, date, timedelta
import os

from flask import current_app, jsonify, render_template, request
from models import (db, User, Application, Position, Company, CompanyMember,
                    University, UniversityMember, UniversityDepartment, UserSkill,
                    Interview,
                    ROLE_SUPERVISOR, ROLE_STUDENT, ROLE_UNIVERSITY_COORD,
                    STATUS_NEW, STATUS_UNIV_PENDING, STATUS_INTERVIEW,
                    STATUS_OFFER, STATUS_HIRED)
from sqlalchemy import or_, func
from helpers import send_email
from . import api_bp


def _check_token():
    """Return None if authorised, else a Flask response with the error."""
    expected = os.environ.get('CRON_TOKEN', '').strip()
    if not expected:
        return jsonify({'ok': False, 'error': 'CRON_TOKEN not configured on server'}), 503
    provided = (request.headers.get('X-Cron-Token')
                or request.args.get('token', '')).strip()
    if not provided or provided != expected:
        return jsonify({'ok': False, 'error': 'unauthorised'}), 401
    return None


def _new_apps_for_supervisor(sup):
    """Applications in 'New' status visible to this supervisor.

    Mirrors routes/supervisor.py logic: applications either directly
    assigned to the user OR for positions in companies they manage.
    """
    managed_company_ids = [m.company_id for m in
                            CompanyMember.query.filter_by(user_id=sup.id, role='manager').all()]
    managed_pos_ids = []
    if managed_company_ids:
        managed_pos_ids = [p.id for p in
                            Position.query.filter(Position.company_id.in_(managed_company_ids)).all()]

    q = Application.query.filter(Application.status == STATUS_NEW)
    if managed_pos_ids:
        q = q.filter(or_(
            Application.position_id.in_(managed_pos_ids),
            Application.assigned_to_id == sup.id,
        ))
    else:
        q = q.filter(Application.assigned_to_id == sup.id)
    return q.order_by(Application.applied_at.asc()).all()


@api_bp.route('/cron/supervisor-daily-reminders', methods=['GET', 'POST'])
def supervisor_daily_reminders():
    """Send a daily 'New applications waiting' reminder to opted-in supervisors.

    Safe to call multiple times per day: each user's last-sent date is
    tracked and processed at most once per UTC day.
    """
    err = _check_token()
    if err:
        return err

    today = date.today()
    now = datetime.utcnow()
    site_url = current_app.config.get('SITE_URL', '').rstrip('/') or request.host_url.rstrip('/')

    sups = (User.query
            .filter_by(role=ROLE_SUPERVISOR, is_active=True, daily_new_apps_reminder=True)
            .all())

    sent = 0
    skipped_already = 0
    skipped_empty = 0
    failed = 0
    details = []

    for sup in sups:
        # Skip if already sent today
        if sup.daily_reminder_last_sent and sup.daily_reminder_last_sent.date() == today:
            skipped_already += 1
            continue

        try:
            apps = _new_apps_for_supervisor(sup)
        except Exception as ex:
            current_app.logger.exception('cron: query failed for supervisor %s: %s', sup.id, ex)
            failed += 1
            details.append({'supervisor': sup.email, 'error': str(ex)})
            continue

        if not apps:
            # No new apps — mark as processed so we don't keep checking
            sup.daily_reminder_last_sent = now
            skipped_empty += 1
            continue

        try:
            html = render_template('emails/supervisor_daily_reminder.html',
                                   supervisor=sup,
                                   apps=apps,
                                   count=len(apps),
                                   now=now,
                                   site_url=site_url)
            subject = f'Reminder: {len(apps)} applicant{"s" if len(apps) != 1 else ""} waiting for your review'
            send_email(sup.email, subject, html)
            sup.daily_reminder_last_sent = now
            sent += 1
            details.append({'supervisor': sup.email, 'count': len(apps), 'sent': True})
        except Exception as ex:
            current_app.logger.exception('cron: email failed for supervisor %s: %s', sup.id, ex)
            failed += 1
            details.append({'supervisor': sup.email, 'count': len(apps), 'error': str(ex)})

    db.session.commit()

    return jsonify({
        'ok': True,
        'date': today.isoformat(),
        'considered': len(sups),
        'sent': sent,
        'skipped_already_sent_today': skipped_already,
        'skipped_no_new_apps': skipped_empty,
        'failed': failed,
        'details': details,
    })


# (appended below)


# ─────────────────────────────────────────────────────────────────────────
#  Helpers (digest)
# ─────────────────────────────────────────────────────────────────────────

def _site_url():
    return (current_app.config.get('SITE_URL') or os.environ.get('SITE_URL')
            or 'https://jobs.mof-eng.com').rstrip('/')


def _due_for_weekly(last_sent, now, min_days=6):
    """Return True if `last_sent` is None or at least `min_days` ago."""
    if not last_sent:
        return True
    return (now - last_sent).days >= min_days


def _student_match_jobs(student, since):
    """Return list of {position, match_reason} for internships posted since `since`
    that match the student's skills/major. Limited to top 12 by recency."""
    q = (Position.query
            .filter(Position.is_active == True)
            .filter(Position.type.ilike('%intern%'))
            .filter(Position.created_at >= since)
            .order_by(Position.created_at.desc())
            .limit(60).all())

    if not q:
        return []

    # Build student keyword set
    skills = [s.name.strip().lower() for s in
              UserSkill.query.filter_by(user_id=student.id).all() if s.name]
    major  = (student.university_major or '').strip().lower()
    keywords = set(filter(None, skills + ([major] if major else [])))

    matches = []
    for p in q:
        reason = None
        haystack = ' '.join(filter(None, [p.title or '', p.skills_required or '',
                                          p.department or ''])).lower()
        # Skill / major hit
        for kw in keywords:
            if len(kw) >= 3 and kw in haystack:
                reason = f"Matches '{kw}'"
                break
        # Fallback: include if no keywords on profile (still worth seeing intern openings)
        if not reason and not keywords:
            reason = 'New internship'
        if reason:
            matches.append({'position': p, 'match_reason': reason})
        if len(matches) >= 12:
            break
    return matches


# ─────────────────────────────────────────────────────────────────────────
#  Weekly job-match digest for STUDENTS
# ─────────────────────────────────────────────────────────────────────────

@api_bp.route('/cron/student-job-match-digest', methods=['GET', 'POST'])
def student_job_match_digest():
    err = _check_token()
    if err: return err

    now = datetime.utcnow()
    since = now - timedelta(days=14)
    site_url = _site_url()

    students = (User.query
                .filter(User.role == ROLE_STUDENT)
                .filter(User.is_active == True)
                .filter(User.weekly_job_match_digest == True)
                .all())

    sent = skipped_recent = skipped_empty = failed = 0
    details = []

    for s in students:
        if not _due_for_weekly(s.job_match_digest_last_sent, now):
            skipped_recent += 1
            continue

        try:
            jobs = _student_match_jobs(s, since)
        except Exception as ex:
            current_app.logger.exception('cron: match query failed for student %s: %s', s.id, ex)
            failed += 1
            details.append({'student': s.email, 'error': str(ex)})
            continue

        if not jobs:
            # Mark processed even with nothing to send, so we don't recheck constantly
            s.job_match_digest_last_sent = now
            skipped_empty += 1
            continue

        try:
            html = render_template('emails/student_job_match_digest.html',
                                   student=s,
                                   jobs=jobs,
                                   count=len(jobs),
                                   now=now,
                                   site_url=site_url)
            subject = f'{len(jobs)} new internship{"s" if len(jobs) != 1 else ""} matching your profile'
            send_email(s.email, subject, html)
            s.job_match_digest_last_sent = now
            sent += 1
            details.append({'student': s.email, 'count': len(jobs), 'sent': True})
        except Exception as ex:
            current_app.logger.exception('cron: digest email failed for student %s: %s', s.id, ex)
            failed += 1
            details.append({'student': s.email, 'count': len(jobs), 'error': str(ex)})

    db.session.commit()
    return jsonify({
        'ok': True,
        'date': now.date().isoformat(),
        'considered': len(students),
        'sent': sent,
        'skipped_recent': skipped_recent,
        'skipped_no_matches': skipped_empty,
        'failed': failed,
        'details': details,
    })


# ─────────────────────────────────────────────────────────────────────────
#  Weekly cohort digest for UNIVERSITY COORDINATORS
# ─────────────────────────────────────────────────────────────────────────

def _coordinator_digest_payload(coord, now):
    """Build (univ, stats, pending_apps, at_risk, recent_progress) for the
    given coordinator. Returns None if coordinator has no university scope."""
    membership = (UniversityMember.query
                    .filter_by(user_id=coord.id, is_active=True)
                    .first())
    if not membership:
        return None
    univ = University.query.get(membership.university_id)
    if not univ:
        return None

    # Student scope
    student_q = (User.query
                    .filter(User.role == ROLE_STUDENT)
                    .filter(User.university_id == univ.id))
    if membership.department_id:
        student_q = student_q.filter(User.university_department_id == membership.department_id)
    students = student_q.all()
    student_ids = [s.id for s in students]

    if not student_ids:
        return univ, {
            'total_students': 0, 'apps_last_7': 0, 'pending_approvals': 0,
            'hired_total': 0, 'placement_rate': 0, 'inactive_students': 0,
        }, [], [], []

    apps_q = Application.query.filter(Application.applicant_id.in_(student_ids))
    week_ago = now - timedelta(days=7)
    apps_last_7 = apps_q.filter(Application.applied_at >= week_ago).count()

    pending_apps = (apps_q.filter(Application.status == STATUS_UNIV_PENDING)
                       .order_by(Application.applied_at.asc()).all())
    pending_count = len(pending_apps)

    hired_set = {a.applicant_id for a in
                 apps_q.filter(Application.status == STATUS_HIRED).all()}
    hired_total = len(hired_set)
    placement_rate = round(hired_total * 100 / len(students)) if students else 0

    applied_set = {a.applicant_id for a in apps_q.all()}
    inactive_students = len(students) - len(applied_set)

    # At-risk = no apps at all
    at_risk = [s for s in students if s.id not in applied_set][:10]

    # Recent progress = apps that moved to Interview/Offer/Hired in last 7 days
    recent_progress = []
    progress_apps = (apps_q
        .filter(Application.status.in_([STATUS_INTERVIEW, STATUS_OFFER, STATUS_HIRED]))
        .filter(Application.last_status_at >= week_ago if hasattr(Application, 'last_status_at') else Application.applied_at >= week_ago)
        .order_by(Application.applied_at.desc())
        .limit(8).all())
    for a in progress_apps:
        recent_progress.append({
            'name': a.applicant.full_name if a.applicant else '—',
            'detail': f"{a.position.title}{(' · ' + a.position.company.name) if a.position and a.position.company else ''}",
            'status': a.status,
        })

    stats = {
        'total_students': len(students),
        'apps_last_7': apps_last_7,
        'pending_approvals': pending_count,
        'hired_total': hired_total,
        'placement_rate': placement_rate,
        'inactive_students': inactive_students,
    }
    return univ, stats, pending_apps, at_risk, recent_progress


@api_bp.route('/cron/coordinator-weekly-digest', methods=['GET', 'POST'])
def coordinator_weekly_digest():
    err = _check_token()
    if err: return err

    now = datetime.utcnow()
    site_url = _site_url()

    coords = (User.query
                .filter(User.role == ROLE_UNIVERSITY_COORD)
                .filter(User.is_active == True)
                .filter(User.weekly_coord_digest == True)
                .all())

    sent = skipped_recent = skipped_no_scope = failed = 0
    details = []

    for c in coords:
        if not _due_for_weekly(c.coord_digest_last_sent, now):
            skipped_recent += 1
            continue

        try:
            payload = _coordinator_digest_payload(c, now)
        except Exception as ex:
            current_app.logger.exception('cron: payload failed for coord %s: %s', c.id, ex)
            failed += 1
            details.append({'coord': c.email, 'error': str(ex)})
            continue

        if payload is None:
            skipped_no_scope += 1
            continue

        univ, stats, pending_apps, at_risk, recent_progress = payload
        try:
            html = render_template('emails/coordinator_weekly_digest.html',
                                   coordinator=c,
                                   univ=univ,
                                   stats=stats,
                                   pending_apps=pending_apps,
                                   at_risk=at_risk,
                                   recent_progress=recent_progress,
                                   now=now,
                                   site_url=site_url)
            badge = []
            if stats['pending_approvals']:
                badge.append(f"{stats['pending_approvals']} pending")
            if stats['inactive_students']:
                badge.append(f"{stats['inactive_students']} inactive")
            subject_tail = ' — ' + ', '.join(badge) if badge else ''
            subject = f'Weekly cohort digest{subject_tail}'
            send_email(c.email, subject, html)
            c.coord_digest_last_sent = now
            sent += 1
            details.append({'coord': c.email, 'sent': True,
                            'pending': stats['pending_approvals'],
                            'inactive': stats['inactive_students']})
        except Exception as ex:
            current_app.logger.exception('cron: digest email failed for coord %s: %s', c.id, ex)
            failed += 1
            details.append({'coord': c.email, 'error': str(ex)})

    db.session.commit()
    return jsonify({
        'ok': True,
        'date': now.date().isoformat(),
        'considered': len(coords),
        'sent': sent,
        'skipped_recent': skipped_recent,
        'skipped_no_scope': skipped_no_scope,
        'failed': failed,
        'details': details,
    })


# ─────────────────────────────────────────────────────────────────────────────
#  24-hour interview reminders for APPLICANTS
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route('/cron/interview-reminders', methods=['GET', 'POST'])
def interview_reminders():
    """Send a reminder email to applicants whose interview is in the next 24–26 hours.

    Run this cron every hour:
        0 * * * *  curl -fsS -H "X-Cron-Token: SECRET" https://jobs.mof-eng.com/api/v1/cron/interview-reminders >/dev/null

    Idempotent: `reminder_sent_at` is stamped on the Interview row so
    duplicate cron firings within the window send nothing twice.
    """
    err = _check_token()
    if err:
        return err

    now = datetime.utcnow()
    site_url = _site_url()

    # Window: interviews scheduled between now+24h and now+26h
    window_start = now + timedelta(hours=24)
    window_end   = now + timedelta(hours=26)

    upcoming = (Interview.query
                .filter(Interview.scheduled_at >= window_start)
                .filter(Interview.scheduled_at <= window_end)
                .filter(Interview.reminder_sent_at.is_(None))
                .filter(Interview.result.is_(None))   # skip already-concluded interviews
                .all())

    sent = skipped = failed = 0
    details = []

    for iv in upcoming:
        app = iv.application
        if not app or not app.applicant:
            skipped += 1
            continue
        applicant = app.applicant
        pos = app.position
        try:
            html = render_template(
                'emails/interview_reminder.html',
                applicant=applicant,
                interview=iv,
                position=pos,
                company=pos.company if pos else None,
                site_url=site_url,
            )
            subject = f'Interview Reminder: {pos.title if pos else "Your Interview"} — Tomorrow'
            send_email(applicant.email, subject, html)
            iv.reminder_sent_at = now
            sent += 1
            details.append({'applicant': applicant.email, 'scheduled_at': iv.scheduled_at.isoformat(), 'sent': True})
        except Exception as ex:
            current_app.logger.exception('cron: interview reminder failed for iv %s: %s', iv.id, ex)
            failed += 1
            details.append({'applicant': applicant.email, 'error': str(ex)})

    db.session.commit()
    return jsonify({
        'ok': True,
        'date': now.isoformat(),
        'window': f'{window_start.isoformat()} – {window_end.isoformat()}',
        'considered': len(upcoming),
        'sent': sent,
        'skipped': skipped,
        'failed': failed,
        'details': details,
    })
