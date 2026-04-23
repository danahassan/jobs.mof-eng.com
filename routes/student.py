from flask import Blueprint, render_template, redirect, url_for, request, abort
from flask_login import login_required, current_user
from models import (db, Application, Position, ROLE_STUDENT,
                    ALL_STATUSES, STATUS_NEW, STATUS_REVIEW, STATUS_INTERVIEW,
                    STATUS_OFFER, STATUS_HIRED, STATUS_REJECTED)
from functools import wraps
from datetime import datetime

student_bp = Blueprint('student', __name__)


def student_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != ROLE_STUDENT:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def _profile_coach_actions(user):
    """Return a list of concrete next actions to improve a student profile.

    Each item is a dict: {icon, title, hint, url, points}. Sorted so the
    highest-impact action appears first. Only returns missing items.
    """
    actions = []
    if not user.avatar_filename:
        actions.append({
            'icon': 'bi-person-circle', 'title': 'Add a profile photo',
            'hint': 'Profiles with a photo get 2× more interview invites.',
            'url': url_for('profile.view'), 'points': 10,
        })
    if not user.headline:
        actions.append({
            'icon': 'bi-card-text', 'title': 'Write a one-line headline',
            'hint': 'e.g. "Civil Engineering Student · Slemani · Open to Internships".',
            'url': url_for('profile.view'), 'points': 5,
        })
    if not user.bio:
        actions.append({
            'icon': 'bi-file-text', 'title': 'Add a short bio',
            'hint': '2–3 sentences about your interests, projects, or career goals.',
            'url': url_for('profile.view'), 'points': 10,
        })
    skill_count = user.skills.count()
    if skill_count < 3:
        actions.append({
            'icon': 'bi-stars', 'title': f'Add {3 - skill_count} more skill{"s" if 3-skill_count != 1 else ""}',
            'hint': 'Recruiters search by skill — students with 5+ skills get 3× more views.',
            'url': url_for('profile.view'), 'points': 15,
        })
    if user.experiences.count() == 0:
        actions.append({
            'icon': 'bi-briefcase-fill', 'title': 'Add work or project experience',
            'hint': 'Even a small academic project counts — describe what you built and learned.',
            'url': url_for('profile.view'), 'points': 15,
        })
    if user.educations.count() == 0:
        actions.append({
            'icon': 'bi-mortarboard-fill', 'title': 'Add your education details',
            'hint': 'Make sure your university, degree and graduation year are visible.',
            'url': url_for('profile.view'), 'points': 10,
        })
    if not user.linkedin_url and not user.portfolio_url:
        actions.append({
            'icon': 'bi-link-45deg', 'title': 'Link your LinkedIn or portfolio',
            'hint': 'A live link lets recruiters explore more of your work.',
            'url': url_for('profile.view'), 'points': 5,
        })
    if user.languages.count() == 0:
        actions.append({
            'icon': 'bi-translate', 'title': 'Add the languages you speak',
            'hint': 'Especially helpful for international companies.',
            'url': url_for('profile.view'), 'points': 5,
        })
    if user.certifications.count() == 0:
        actions.append({
            'icon': 'bi-patch-check-fill', 'title': 'List a certification',
            'hint': 'Even online course certificates show initiative.',
            'url': url_for('profile.view'), 'points': 5,
        })
    # Sort by impact (points desc) and cap to 4 visible
    actions.sort(key=lambda a: -a['points'])
    return actions[:4]


def _per_app_hint(app, now):
    """Tiny suggestion for the student about each application."""
    days = (now - app.applied_at).days if app.applied_at else 0
    s = app.status
    if s == 'Pending University Approval':
        return ('bi-building-check', 'Your university coordinator is reviewing this application.')
    if s == 'New':
        if days < 3:
            return ('bi-hourglass-split', f'Submitted {days} day{"s" if days != 1 else ""} ago — companies usually respond within a week.')
        if days < 10:
            return ('bi-eye', f'Pending {days} days. Many recruiters review applications in batches.')
        return ('bi-clock-history', f'Pending {days} days — consider applying to similar positions while you wait.')
    if s == 'Under Review':
        return ('bi-search', 'A recruiter is actively reviewing your profile. Make sure your profile is up to date!')
    if s == 'Interview':
        return ('bi-camera-video', 'Interview stage — research the company and prepare 2–3 questions to ask.')
    if s == 'Offer':
        return ('bi-envelope-open-fill', 'You received an offer! Reply promptly to confirm or negotiate.')
    if s == 'Hired':
        return ('bi-patch-check-fill', 'Congratulations on your placement — best of luck!')
    if s == 'Rejected':
        return ('bi-arrow-clockwise', 'Not the right match this time — keep applying, your next opportunity is close.')
    if s == 'Future Consideration':
        return ('bi-bookmark-fill', 'Saved for future opportunities — keep your profile current.')
    return ('bi-info-circle', 'Check back soon for updates.')


@student_bp.route('/')
@student_required
def dashboard():
    my_apps = (Application.query
               .filter_by(applicant_id=current_user.id)
               .join(Application.position)
               .filter(Position.type == 'Internship')
               .order_by(Application.applied_at.desc())
               .all())

    now = datetime.utcnow()
    total      = len(my_apps)
    active     = sum(1 for a in my_apps
                     if a.status in [STATUS_NEW, STATUS_REVIEW, STATUS_INTERVIEW, STATUS_OFFER])
    placed     = sum(1 for a in my_apps if a.status == STATUS_HIRED)
    rejected   = sum(1 for a in my_apps if a.status == STATUS_REJECTED)

    coach_actions = _profile_coach_actions(current_user)
    profile_strength = current_user.profile_strength

    # Per-application hint dictionary keyed by app.id
    app_hints = {a.id: _per_app_hint(a, now) for a in my_apps}
    # Days waiting per app (visible on card)
    app_days = {a.id: max((now - a.applied_at).days, 0) if a.applied_at else 0 for a in my_apps}

    return render_template('student/dashboard.html',
        my_apps=my_apps,
        kpi_total=total,
        kpi_active=active,
        kpi_placed=placed,
        kpi_rejected=rejected,
        coach_actions=coach_actions,
        profile_strength=profile_strength,
        app_hints=app_hints,
        app_days=app_days,
        ALL_STATUSES=ALL_STATUSES)

