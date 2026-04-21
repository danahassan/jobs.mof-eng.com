from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, current_app, abort)
from flask_login import current_user
from sqlalchemy import or_
from models import (db, User, Application, Position, University, UniversityMember,
                    ROLE_STUDENT, ROLE_UNIVERSITY_COORD, ROLE_ADMIN,
                    ALL_STATUSES, STATUS_NEW, STATUS_REVIEW, STATUS_INTERVIEW,
                    STATUS_OFFER, STATUS_HIRED, STATUS_REJECTED)
from helpers import university_coordinator_required, log_audit

university_bp = Blueprint('university', __name__)


def _my_university():
    """Return the University this coordinator belongs to, or None."""
    if current_user.role == ROLE_ADMIN:
        return None
    member = (UniversityMember.query
              .filter_by(user_id=current_user.id)
              .first())
    return member.university if member else None


@university_bp.route('/')
@university_coordinator_required
def dashboard():
    univ = _my_university()
    if not univ and current_user.role != ROLE_ADMIN:
        flash('You are not linked to any university yet.', 'warning')
        return render_template('university/dashboard.html', univ=None,
                               total_students=0, internship_apps=0,
                               active_apps=0, hired_count=0, recent_apps=[])

    student_ids = _student_ids(univ)
    total_students  = len(student_ids)
    internship_q    = _internship_apps(student_ids)
    internship_apps = internship_q.count()
    active_apps     = internship_q.filter(
        Application.status.in_([STATUS_NEW, STATUS_REVIEW, STATUS_INTERVIEW, STATUS_OFFER])
    ).count()
    hired_count = internship_q.filter_by(status=STATUS_HIRED).count()
    recent_apps = (internship_q
                   .order_by(Application.applied_at.desc())
                   .limit(8).all())

    # Status breakdown
    status_counts = {s: internship_q.filter_by(status=s).count() for s in ALL_STATUSES}

    return render_template('university/dashboard.html',
        univ=univ,
        total_students=total_students,
        internship_apps=internship_apps,
        active_apps=active_apps,
        hired_count=hired_count,
        recent_apps=recent_apps,
        status_counts=status_counts,
        ALL_STATUSES=ALL_STATUSES)


@university_bp.route('/students')
@university_coordinator_required
def students():
    univ = _my_university()
    if not univ and current_user.role != ROLE_ADMIN:
        flash('You are not linked to any university.', 'warning')
        return redirect(url_for('university.dashboard'))

    page   = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()

    if univ:
        q = User.query.filter_by(university_id=univ.id, role=ROLE_STUDENT)
    else:
        q = User.query.filter_by(role=ROLE_STUDENT)

    if search:
        q = q.filter(or_(
            User.full_name.ilike(f'%{search}%'),
            User.email.ilike(f'%{search}%'),
            User.university_major.ilike(f'%{search}%'),
        ))

    students_page = q.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)

    return render_template('university/students.html',
        univ=univ, students=students_page, search=search)


@university_bp.route('/applications')
@university_coordinator_required
def applications():
    univ = _my_university()
    if not univ and current_user.role != ROLE_ADMIN:
        flash('You are not linked to any university.', 'warning')
        return redirect(url_for('university.dashboard'))

    page     = request.args.get('page', 1, type=int)
    search   = request.args.get('q', '').strip()
    status_f = request.args.get('status', '').strip()

    student_ids = _student_ids(univ)
    q = _internship_apps(student_ids)

    if search:
        q = q.join(Application.applicant).filter(or_(
            User.full_name.ilike(f'%{search}%'),
            User.email.ilike(f'%{search}%'),
        ))
    if status_f:
        q = q.filter(Application.status == status_f)

    apps = q.order_by(Application.applied_at.desc()).paginate(
        page=page, per_page=20, error_out=False)

    # KPI counts (unfiltered)
    base_q = _internship_apps(student_ids)
    kpi_total     = base_q.count()
    kpi_active    = base_q.filter(Application.status.in_(
        [STATUS_NEW, STATUS_REVIEW, STATUS_INTERVIEW, STATUS_OFFER])).count()
    kpi_hired     = base_q.filter_by(status=STATUS_HIRED).count()
    kpi_rejected  = base_q.filter_by(status=STATUS_REJECTED).count()

    return render_template('university/applications.html',
        univ=univ, apps=apps, search=search, status_f=status_f,
        ALL_STATUSES=ALL_STATUSES,
        kpi_total=kpi_total, kpi_active=kpi_active,
        kpi_hired=kpi_hired, kpi_rejected=kpi_rejected)


@university_bp.route('/applications/<int:app_id>')
@university_coordinator_required
def application_detail(app_id):
    app = Application.query.get_or_404(app_id)
    univ = _my_university()
    if univ:
        sids = _student_ids(univ)
        if app.applicant_id not in sids:
            abort(403)
    if app.position.type != 'Internship':
        abort(403)
    return render_template('university/application_detail.html', app=app, univ=univ)


# ─── helpers ─────────────────────────────────────────────────────────────────

def _student_ids(univ):
    if univ:
        return [u.id for u in User.query.filter_by(
            university_id=univ.id, role=ROLE_STUDENT).all()]
    return [u.id for u in User.query.filter_by(role=ROLE_STUDENT).all()]


def _internship_apps(student_ids):
    if not student_ids:
        return Application.query.filter(False)
    return (Application.query
            .join(Application.position)
            .filter(
                Application.applicant_id.in_(student_ids),
                Position.type == 'Internship',
            ))
