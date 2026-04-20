"""routes/analytics.py — Candidate, employer, and admin analytics."""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from sqlalchemy import func

from models import (db, User, Position, Application, ApplicationHistory,
                    Company, ROLE_ADMIN, ROLE_EMPLOYER, ALL_STATUSES)

analytics_bp = Blueprint('analytics', __name__)


# ─── Candidate Analytics ─────────────────────────────────────────────────────

@analytics_bp.route('/candidate')
@login_required
def candidate():
    uid = current_user.id

    total_applied  = Application.query.filter_by(applicant_id=uid).count()
    viewed         = Application.query.filter_by(applicant_id=uid, status='Under Review').count()
    shortlisted    = Application.query.filter_by(applicant_id=uid, status='Interview').count()
    hired          = Application.query.filter_by(applicant_id=uid, status='Hired').count()
    rejected       = Application.query.filter_by(applicant_id=uid, status='Rejected').count()

    # Monthly application activity (last 6 months)
    monthly = []
    for i in range(5, -1, -1):
        d = (datetime.utcnow().replace(day=1) - timedelta(days=i * 28))
        count = Application.query.filter(
            Application.applicant_id == uid,
            func.strftime('%Y-%m', Application.applied_at) == d.strftime('%Y-%m')
        ).count()
        monthly.append({'month': d.strftime('%b %Y'), 'count': count})

    # Status breakdown — list of (label, count, color) tuples for chart + legend
    STATUS_COLORS = {
        'New': '#6366f1', 'Under Review': '#f59e0b', 'Interview': '#8b5cf6',
        'Offer': '#3b82f6', 'Hired': '#22c55e', 'Rejected': '#ef4444',
        'Future Consideration': '#94a3b8',
    }
    status_breakdown = [
        (s, Application.query.filter_by(applicant_id=uid, status=s).count(),
         STATUS_COLORS.get(s, '#94a3b8'))
        for s in ALL_STATUSES
    ]

    # Recent applications
    recent = Application.query.filter_by(applicant_id=uid)\
        .order_by(Application.applied_at.desc()).limit(5).all()

    # Profile strength + completion tips
    strength = current_user.profile_strength
    tips = _profile_tips(current_user)

    return render_template('analytics/candidate.html',
        total_applications=total_applied,
        pending_count=viewed,
        interview_count=shortlisted,
        hired_count=hired,
        monthly=monthly,
        monthly_labels=[m['month'] for m in monthly],
        monthly_counts=[m['count'] for m in monthly],
        status_breakdown=status_breakdown,
        recent_applications=recent,
        strength=strength, tips=tips)


# ─── Employer Analytics ──────────────────────────────────────────────────────

@analytics_bp.route('/employer')
@login_required
def employer():
    if current_user.role not in (ROLE_EMPLOYER, ROLE_ADMIN):
        abort(403)

    from routes.employer import get_employer_company
    company = get_employer_company()
    if not company:
        abort(404)

    jobs = Position.query.filter_by(company_id=company.id).all()

    # Counts for KPIs
    total_apps_count = Application.query.join(Position).filter(
        Position.company_id == company.id).count()
    interview_count = Application.query.join(Position).filter(
        Position.company_id == company.id, Application.status == 'Interview').count()
    hired_count = Application.query.join(Position).filter(
        Position.company_id == company.id, Application.status == 'Hired').count()

    # Applicant funnel — list of (stage, count, pct)
    total_for_pct = total_apps_count or 1
    funnel = [
        (s, Application.query.join(Position).filter(
            Position.company_id == company.id, Application.status == s).count(),
         round(Application.query.join(Position).filter(
            Position.company_id == company.id, Application.status == s).count()
         / total_for_pct * 100, 1))
        for s in ALL_STATUSES
    ]

    # Applications over time (last 6 months)
    monthly = []
    for i in range(5, -1, -1):
        d = (datetime.utcnow().replace(day=1) - timedelta(days=i * 28))
        count = Application.query.join(Position).filter(
            Position.company_id == company.id,
            func.strftime('%Y-%m', Application.applied_at) == d.strftime('%Y-%m')
        ).count()
        monthly.append({'month': d.strftime('%b %Y'), 'count': count})

    # Top jobs by applications — expose as app_count for template
    top_jobs_raw = sorted(jobs, key=lambda j: j.application_count, reverse=True)[:5]
    top_jobs = [{'title': j.title, 'views_count': j.views_count or 0,
                 'app_count': j.application_count} for j in top_jobs_raw]

    # Views vs applications ratio
    views_total = sum(j.views_count or 0 for j in jobs)
    apps_total  = sum(j.application_count for j in jobs)
    conversion  = round(apps_total / views_total * 100, 1) if views_total > 0 else 0

    # Time to hire
    hired_apps = Application.query.join(Position).filter(
        Position.company_id == company.id, Application.status == 'Hired').all()
    if hired_apps:
        durations = [(a.updated_at - a.applied_at).days for a in hired_apps]
        avg_hire_days = round(sum(durations) / len(durations))
    else:
        avg_hire_days = None

    return render_template('analytics/employer.html',
        company=company, funnel=funnel, monthly=monthly,
        monthly_labels=[m['month'] for m in monthly],
        monthly_counts=[m['count'] for m in monthly],
        top_jobs=top_jobs,
        total_jobs=sum(1 for j in jobs if j.is_active),
        total_applications=total_apps_count,
        interview_count=interview_count,
        hired_count=hired_count,
        views_total=views_total, apps_total=apps_total,
        conversion=conversion, avg_hire_days=avg_hire_days)


# ─── Admin Analytics ─────────────────────────────────────────────────────────

@analytics_bp.route('/admin')
@login_required
def admin():
    if current_user.role != ROLE_ADMIN:
        abort(403)

    # Platform totals
    total_users   = User.query.count()
    total_jobs    = Position.query.count()
    total_apps    = Application.query.count()
    total_companies= Company.query.count()
    active_jobs   = Position.query.filter_by(is_active=True).count()
    hired_total   = Application.query.filter_by(status='Hired').count()

    # New users per month (last 6)
    monthly_users = []
    monthly_apps_list = []
    month_labels = []
    for i in range(5, -1, -1):
        d = (datetime.utcnow().replace(day=1) - timedelta(days=i * 28))
        month_str = d.strftime('%Y-%m')
        uc = User.query.filter(
            func.strftime('%Y-%m', User.created_at) == month_str).count()
        ac = Application.query.filter(
            func.strftime('%Y-%m', Application.applied_at) == month_str).count()
        month_labels.append(d.strftime('%b'))
        monthly_users.append(uc)
        monthly_apps_list.append(ac)

    # Status breakdown — list of (label, count, color) tuples
    STATUS_COLORS = {
        'New': '#6366f1', 'Under Review': '#f59e0b', 'Interview': '#8b5cf6',
        'Offer': '#3b82f6', 'Hired': '#22c55e', 'Rejected': '#ef4444',
        'Future Consideration': '#94a3b8',
    }
    status_breakdown = [
        (s, Application.query.filter_by(status=s).count(), STATUS_COLORS.get(s, '#94a3b8'))
        for s in ALL_STATUSES
    ]

    # Role breakdown — list of (role, count, pct) tuples
    role_dist_raw = {
        'Candidates': User.query.filter_by(role='user').count(),
        'Employers':  User.query.filter_by(role='employer').count(),
        'Admins':     User.query.filter_by(role='admin').count(),
        'Supervisors':User.query.filter_by(role='supervisor').count(),
    }
    role_total = total_users or 1
    role_breakdown = [
        (role, count, round(count / role_total * 100, 1))
        for role, count in role_dist_raw.items()
    ]

    # Top hiring companies
    top_companies_raw = db.session.query(
        Company.name,
        func.count(Application.id).label('app_count')
    ).join(Position, Position.company_id == Company.id)\
     .join(Application, Application.position_id == Position.id)\
     .group_by(Company.id)\
     .order_by(func.count(Application.id).desc())\
     .limit(5).all()

    top_companies = []
    for row in top_companies_raw:
        company_row = Company.query.filter_by(name=row.name).first()
        open_jobs = Position.query.filter_by(company_id=company_row.id, is_active=True).count() if company_row else 0
        top_companies.append({'name': row.name, 'app_count': row.app_count, 'open_jobs': open_jobs})

    return render_template('analytics/admin.html',
        total_users=total_users, total_jobs=total_jobs,
        total_applications=total_apps, total_companies=total_companies,
        active_jobs=active_jobs, hired_total=hired_total,
        monthly_labels=month_labels,
        monthly_users=monthly_users,
        monthly_apps=monthly_apps_list,
        status_breakdown=status_breakdown,
        role_breakdown=role_breakdown,
        top_companies=top_companies)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _profile_tips(user):
    tips = []
    if not user.avatar_filename:
        tips.append({'icon': 'bi-camera', 'text': 'Add a profile photo to stand out.'})
    if not user.headline:
        tips.append({'icon': 'bi-pencil', 'text': 'Add a professional headline.'})
    if not user.bio:
        tips.append({'icon': 'bi-file-text', 'text': 'Write a summary/bio.'})
    if user.skills.count() < 3:
        tips.append({'icon': 'bi-tools', 'text': 'Add at least 3 skills.'})
    if user.experiences.count() == 0:
        tips.append({'icon': 'bi-briefcase', 'text': 'Add your work experience.'})
    if user.educations.count() == 0:
        tips.append({'icon': 'bi-mortarboard', 'text': 'Add your education.'})
    if not user.linkedin_url:
        tips.append({'icon': 'bi-linkedin', 'text': 'Link your LinkedIn profile.'})
    return tips
