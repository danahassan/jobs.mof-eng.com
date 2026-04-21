import secrets
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, current_app, abort, jsonify)
from flask_login import current_user
from sqlalchemy import or_
from models import (db, User, Application, Position, University, UniversityMember,
                    ROLE_STUDENT, ROLE_UNIVERSITY_COORD, ROLE_ADMIN,
                    ALL_STATUSES, STATUS_NEW, STATUS_REVIEW, STATUS_INTERVIEW,
                    STATUS_OFFER, STATUS_HIRED, STATUS_REJECTED, SOURCES)
from helpers import university_coordinator_required, log_audit, send_email

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


# ─── Student management ──────────────────────────────────────────────────────

@university_bp.route('/students/add', methods=['GET', 'POST'])
@university_coordinator_required
def student_add():
    univ = _my_university()
    if not univ:
        flash('You are not linked to any university.', 'warning')
        return redirect(url_for('university.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if not email:
            flash('Email is required.', 'danger')
            return render_template('university/student_form.html', univ=univ, student=None)

        # Check if email exists — link existing user or create new one
        existing = User.query.filter_by(email=email).first()
        if existing:
            if existing.role != ROLE_STUDENT:
                flash(f'A non-student account already exists for {email}.', 'danger')
                return render_template('university/student_form.html', univ=univ, student=None)
            existing.university_id   = univ.id
            existing.university_name = univ.name
            existing.university_major = request.form.get('university_major', '').strip() or existing.university_major
            existing.student_gpa      = request.form.get('student_gpa', '').strip() or existing.student_gpa
            existing.graduation_year  = _parse_int(request.form.get('graduation_year', '')) or existing.graduation_year
            existing.student_id_number= request.form.get('student_id_number', '').strip() or existing.student_id_number
            log_audit('university.student_link', f'{existing.full_name} → {univ.name}', user_id=current_user.id)
            db.session.commit()
            flash(f'Existing student {existing.full_name} linked to {univ.name}.', 'success')
            return redirect(url_for('university.students'))

        full_name = request.form.get('full_name', '').strip()
        if not full_name:
            flash('Full name is required.', 'danger')
            return render_template('university/student_form.html', univ=univ, student=None)

        temp_pw = secrets.token_urlsafe(10)
        student = User(
            full_name         = full_name,
            email             = email,
            phone             = request.form.get('phone', '').strip() or None,
            role              = ROLE_STUDENT,
            is_active         = True,
            university_id     = univ.id,
            university_name   = univ.name,
            university_major  = request.form.get('university_major', '').strip() or None,
            student_gpa       = request.form.get('student_gpa', '').strip() or None,
            graduation_year   = _parse_int(request.form.get('graduation_year', '')),
            student_id_number = request.form.get('student_id_number', '').strip() or None,
        )
        student.set_password(temp_pw)
        db.session.add(student)
        log_audit('university.student_add', f'{full_name} → {univ.name}', user_id=current_user.id)
        db.session.commit()

        # Send welcome email with temp password
        try:
            html = render_template('emails/welcome_student.html',
                                   student=student, univ=univ, temp_password=temp_pw)
            send_email(student.email, 'Welcome to MOF Jobs — Your Student Account', html)
        except Exception as e:
            current_app.logger.warning(f'Student welcome email failed: {e}')

        flash(f'Student {full_name} added successfully.', 'success')
        return redirect(url_for('university.students'))

    return render_template('university/student_form.html', univ=univ, student=None)


@university_bp.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
@university_coordinator_required
def student_edit(student_id):
    univ    = _my_university()
    student = db.get_or_404(User, student_id)
    if univ and student.university_id != univ.id:
        abort(403)

    if request.method == 'POST':
        student.full_name         = request.form.get('full_name', student.full_name).strip()
        student.phone             = request.form.get('phone', '').strip() or None
        student.university_major  = request.form.get('university_major', '').strip() or None
        student.student_gpa       = request.form.get('student_gpa', '').strip() or None
        student.graduation_year   = _parse_int(request.form.get('graduation_year', ''))
        student.student_id_number = request.form.get('student_id_number', '').strip() or None
        new_pw = request.form.get('new_password', '').strip()
        if new_pw:
            student.set_password(new_pw)
        log_audit('university.student_edit', student.full_name, user_id=current_user.id)
        db.session.commit()
        flash('Student updated.', 'success')
        return redirect(url_for('university.students'))

    return render_template('university/student_form.html', univ=univ, student=student)


@university_bp.route('/students/<int:student_id>/delete', methods=['POST'])
@university_coordinator_required
def student_delete(student_id):
    univ    = _my_university()
    student = db.get_or_404(User, student_id)
    if univ and student.university_id != univ.id:
        abort(403)
    name = student.full_name
    # Unlink from university instead of hard-deleting the account
    student.university_id = None
    student.university_name = None
    log_audit('university.student_remove', f'{name} ← {univ.name if univ else "university"}', user_id=current_user.id)
    db.session.commit()
    flash(f'Student {name} removed from your university.', 'success')
    return redirect(url_for('university.students'))


# ─── Internship application creation ─────────────────────────────────────────

@university_bp.route('/applications/new', methods=['GET', 'POST'])
@university_coordinator_required
def application_new():
    univ = _my_university()
    if not univ:
        flash('You are not linked to any university.', 'warning')
        return redirect(url_for('university.dashboard'))

    # Only show internship positions
    open_positions = (Position.query
                      .filter_by(is_active=True, type='Internship')
                      .order_by(Position.title).all())
    student_ids = _student_ids(univ)
    students = User.query.filter(User.id.in_(student_ids)).order_by(User.full_name).all() if student_ids else []

    if request.method == 'POST':
        student_id  = request.form.get('student_id', type=int)
        position_id = request.form.get('position_id', type=int)

        if not student_id or not position_id:
            flash('Please select both a student and a position.', 'danger')
            return render_template('university/application_form.html',
                                   univ=univ, students=students, positions=open_positions)

        student  = User.query.get(student_id)
        position = Position.query.get(position_id)
        if not student or not position:
            flash('Invalid student or position.', 'danger')
            return redirect(url_for('university.application_new'))

        # Check student belongs to this university
        if univ and student.university_id != univ.id:
            abort(403)

        # Check not already applied
        existing = Application.query.filter_by(
            applicant_id=student_id, position_id=position_id).first()
        if existing:
            flash(f'{student.full_name} has already applied for {position.title}.', 'warning')
            return redirect(url_for('university.applications'))

        app = Application(
            applicant_id   = student_id,
            position_id    = position_id,
            cover_letter   = request.form.get('cover_letter', '').strip() or None,
            source         = 'University',
            status         = STATUS_NEW,
            internship_duration   = request.form.get('internship_duration', '').strip() or None,
            academic_credit_required = bool(request.form.get('academic_credit_required')),
        )
        db.session.add(app)
        log_audit('university.app_submit',
                  f'{student.full_name} → {position.title}', user_id=current_user.id)
        db.session.commit()
        flash(f'Application for {student.full_name} → {position.title} submitted.', 'success')
        return redirect(url_for('university.applications'))

    return render_template('university/application_form.html',
                           univ=univ, students=students, positions=open_positions)


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


def _parse_int(s):
    try:
        return int(str(s).strip()) if s and str(s).strip() else None
    except (ValueError, TypeError):
        return None
