"""routes/api/cron.py — scheduled background jobs triggered by external cron.

These endpoints are protected by a shared secret token sent in the
`X-Cron-Token` header (or `?token=` query param). The token is read from
the environment variable `CRON_TOKEN`. If unset, all endpoints return 503
so misconfigured production servers fail loud rather than silent.

Configure cPanel cron (daily at 08:00 server time):

    0 8 * * *  curl -fsS -H "X-Cron-Token: YOUR_SECRET" https://jobs.mof-eng.com/api/v1/cron/supervisor-daily-reminders >/dev/null

The endpoint is idempotent within a calendar day: it tracks
`User.daily_reminder_last_sent` and skips supervisors who already received
a reminder today, so duplicate cron firings are safe.
"""
from datetime import datetime, date
import os

from flask import current_app, jsonify, render_template, request

from models import (db, User, Application, Position, CompanyMember,
                    ROLE_SUPERVISOR, STATUS_NEW)
from sqlalchemy import or_
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
