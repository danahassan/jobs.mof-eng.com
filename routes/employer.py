"""routes/employer.py — Employer dashboard, job management, applicant pipeline."""
from datetime import datetime
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, abort, current_app, jsonify, send_from_directory)
from flask_login import login_required, current_user
from sqlalchemy import func

from models import (db, User, Company, CompanyMember, CompanyFollow, Position,
                    Application, ApplicationHistory, Interview, Notification,
                    UniversityMember,
                    ROLE_EMPLOYER, ROLE_ADMIN, ROLE_STUDENT, ROLE_UNIVERSITY_COORD, ROLE_USER,
                    ALL_STATUSES, STATUS_UNIV_PENDING, EXPERIENCE_LEVELS, JOB_TYPES, COMPANY_SIZES)
from helpers import (admin_required, log_history, save_cv, allowed_file,
                     send_email, push_notification)

employer_bp = Blueprint('employer', __name__)

LOGO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}


# ─── Decorators ───────────────────────────────────────────────────────────────

def employer_required(f):
    from functools import wraps
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role not in (ROLE_EMPLOYER, ROLE_ADMIN):
            abort(403)
        return f(*args, **kwargs)
    return decorated


def get_employer_company():
    """Return the Company the current employer manages, or None."""
    m = CompanyMember.query.filter_by(user_id=current_user.id).first()
    return m.company if m else None


# ─── Dashboard ────────────────────────────────────────────────────────────────

@employer_bp.route('/')
@employer_required
def dashboard():
    company = get_employer_company()
    if not company:
        return redirect(url_for('employer.company_setup'))

    jobs = Position.query.filter_by(company_id=company.id).order_by(
        Position.created_at.desc()).all()

    total_jobs   = len(jobs)
    active_jobs  = sum(1 for j in jobs if j.is_active)
    total_apps   = sum(j.application_count for j in jobs)
    new_apps     = Application.query.join(Position).filter(
        Position.company_id == company.id,
        Application.status == 'New'
    ).count()

    # Status funnel
    funnel = {}
    for s in ALL_STATUSES:
        funnel[s] = Application.query.join(Position).filter(
            Position.company_id == company.id,
            Application.status == s
        ).count()

    # Recent applicants
    recent_apps = (Application.query
                   .join(Position).filter(Position.company_id == company.id)
                   .order_by(Application.applied_at.desc())
                   .limit(10).all())

    return render_template('employer/dashboard.html',
        company=company, jobs=jobs, total_jobs=total_jobs,
        active_jobs=active_jobs, total_apps=total_apps, new_apps=new_apps,
        funnel=funnel, recent_apps=recent_apps)


# ─── Company Setup / Edit ─────────────────────────────────────────────────────

@employer_bp.route('/company/setup', methods=['GET', 'POST'])
@employer_required
def company_setup():
    company = get_employer_company()

    if request.method == 'POST':
        name        = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        industry    = request.form.get('industry', '').strip()
        size        = request.form.get('size', '').strip()
        website     = request.form.get('website', '').strip()
        location    = request.form.get('location', '').strip()
        founded     = request.form.get('founded_year', type=int)

        if not name:
            flash('Company name is required.', 'danger')
            return redirect(request.url)

        if not company:
            company = Company(name=name, created_by=current_user.id)
            company.save_slug()
            db.session.add(company)
            db.session.flush()
            db.session.add(CompanyMember(company_id=company.id,
                                          user_id=current_user.id, role='owner'))
        else:
            company.name = name

        company.description  = description
        company.industry     = industry
        company.size         = size
        company.website      = website
        company.location     = location
        company.founded_year = founded

        # Logo upload
        logo_file = request.files.get('logo')
        if logo_file and logo_file.filename:
            ext = logo_file.filename.rsplit('.', 1)[-1].lower()
            if ext in LOGO_EXTENSIONS:
                import uuid
                logo_dir = current_app.config['COMPANY_LOGO_FOLDER']
                os.makedirs(logo_dir, exist_ok=True)
                fname = f"logo_{uuid.uuid4().hex}.{ext}"
                logo_file.save(os.path.join(logo_dir, fname))
                company.logo_filename = fname

        db.session.commit()
        flash('Company profile saved.', 'success')
        return redirect(url_for('employer.dashboard'))

    return render_template('employer/company_setup.html',
        company=company, sizes=COMPANY_SIZES)


# ─── Job Management ───────────────────────────────────────────────────────────

@employer_bp.route('/jobs')
@employer_required
def jobs():
    company = get_employer_company()
    if not company:
        return redirect(url_for('employer.company_setup'))
    jobs = Position.query.filter_by(company_id=company.id).order_by(
        Position.created_at.desc()).all()
    return render_template('employer/jobs.html', company=company, jobs=jobs)


@employer_bp.route('/jobs/new', methods=['GET', 'POST'])
@employer_required
def job_new():
    company = get_employer_company()
    if not company:
        flash('Please set up your company profile first.', 'warning')
        return redirect(url_for('employer.company_setup'))

    if request.method == 'POST':
        pos = _build_position_from_form(request.form, company)
        db.session.add(pos)
        db.session.commit()

        # Trigger job alerts
        _dispatch_job_alerts(pos)
        flash('Job posted successfully!', 'success')
        return redirect(url_for('employer.jobs'))

    return render_template('employer/job_form.html', company=company,
        job=None, exp_levels=EXPERIENCE_LEVELS, job_types=JOB_TYPES)


@employer_bp.route('/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
@employer_required
def job_edit(job_id):
    job = _get_employer_job(job_id)
    if request.method == 'POST':
        _build_position_from_form(request.form, job.company, pos=job)
        db.session.commit()
        flash('Job updated.', 'success')
        return redirect(url_for('employer.jobs'))
    return render_template('employer/job_form.html', company=job.company,
        job=job, exp_levels=EXPERIENCE_LEVELS, job_types=JOB_TYPES)


@employer_bp.route('/jobs/<int:job_id>/toggle', methods=['POST'])
@employer_required
def job_toggle(job_id):
    job = _get_employer_job(job_id)
    job.is_active = not job.is_active
    db.session.commit()
    state = 'published' if job.is_active else 'paused'
    flash(f'Job {state}.', 'success')
    return redirect(url_for('employer.jobs'))


@employer_bp.route('/jobs/<int:job_id>/delete', methods=['POST'])
@employer_required
def job_delete(job_id):
    job = _get_employer_job(job_id)
    if job.application_count > 0:
        flash('Cannot delete a job that has received applications. Pause it instead.', 'warning')
        return redirect(url_for('employer.jobs'))
    db.session.delete(job)
    db.session.commit()
    flash('Job deleted.', 'success')
    return redirect(url_for('employer.jobs'))


# ─── Applicant Pipeline ───────────────────────────────────────────────────────

@employer_bp.route('/jobs/<int:job_id>/applicants')
@employer_required
def job_applicants(job_id):
    job = _get_employer_job(job_id)
    status_filter = request.args.get('status', '')
    q = Application.query.filter_by(position_id=job.id)
    if status_filter:
        q = q.filter_by(status=status_filter)
    apps = q.order_by(Application.applied_at.desc()).all()
    return render_template('employer/applicants.html',
        job=job, apps=apps, statuses=ALL_STATUSES, status_filter=status_filter)


@employer_bp.route('/applicants/<int:app_id>')
@employer_required
def applicant_detail(app_id):
    app = _get_employer_application(app_id)
    history = app.history.order_by(ApplicationHistory.created_at.desc()).all()
    interviews = app.interviews.order_by(Interview.scheduled_at.asc()).all()
    available_statuses = ALL_STATUSES if (app.position and app.position.type == 'Internship') else [s for s in ALL_STATUSES if s != STATUS_UNIV_PENDING]
    return render_template('employer/applicant_detail.html',
        app=app, history=history, interviews=interviews, statuses=available_statuses)


@employer_bp.route('/applicants/<int:app_id>/stage', methods=['POST'])
@employer_required
def applicant_stage(app_id):
    application = _get_employer_application(app_id)
    new_status = request.form.get('status')
    note       = request.form.get('note', '').strip()

    if new_status not in ALL_STATUSES:
        abort(400)

    log_history(application, new_status,
                note=note or f'Stage updated to {new_status}',
                actor=current_user)
    application.status = new_status
    db.session.commit()

    push_notification(
        application.applicant_id,
        f'Your application for "{application.position.title}" was updated to <b>{new_status}</b>.',
        url_for('user.my_applications'),
        icon='bi-briefcase-fill'
    )
    flash('Applicant stage updated.', 'success')
    return redirect(url_for('employer.applicant_detail', app_id=app_id))


@employer_bp.route('/applicants/<int:app_id>/interview', methods=['POST'])
@employer_required
def schedule_interview(app_id):
    application = _get_employer_application(app_id)
    scheduled_str = request.form.get('scheduled_at', '')
    location      = request.form.get('location', '').strip()
    notes         = request.form.get('notes', '').strip()

    try:
        scheduled = datetime.strptime(scheduled_str, '%Y-%m-%dT%H:%M')
    except ValueError:
        flash('Invalid date format.', 'danger')
        return redirect(url_for('employer.applicant_detail', app_id=app_id))

    iv = Interview(
        application_id=application.id,
        scheduled_at=scheduled,
        location=location,
        interviewer_id=current_user.id,
        notes=notes,
    )
    db.session.add(iv)
    log_history(application, 'Interview', note=f'Interview scheduled {scheduled_str}', actor=current_user)
    application.status = 'Interview'
    db.session.commit()

    push_notification(
        application.applicant_id,
        f'Interview scheduled for "{application.position.title}" on {scheduled.strftime("%b %d at %H:%M")}.',
        url_for('user.my_applications'),
        icon='bi-calendar-check-fill'
    )
    flash('Interview scheduled.', 'success')
    return redirect(url_for('employer.applicant_detail', app_id=app_id))


# ─── Candidate Search ─────────────────────────────────────────────────────────

@employer_bp.route('/candidates')
@employer_required
def candidate_search():
    q      = request.args.get('q', '').strip()
    skill  = request.args.get('skill', '').strip()
    loc    = request.args.get('location', '').strip()

    query = User.query.filter_by(role='user', is_active=True)
    if q:
        query = query.filter(
            (User.full_name.ilike(f'%{q}%')) | (User.headline.ilike(f'%{q}%'))
        )
    if loc:
        query = query.filter(User.location_city.ilike(f'%{loc}%'))

    candidates = query.limit(50).all()

    if skill:
        from models import UserSkill
        skilled_ids = {s.user_id for s in UserSkill.query.filter(
            UserSkill.name.ilike(f'%{skill}%')).all()}
        candidates = [c for c in candidates if c.id in skilled_ids]

    return render_template('employer/candidates.html',
        candidates=candidates, q=q, skill=skill, loc=loc)


# ─── Analytics ────────────────────────────────────────────────────────────────

@employer_bp.route('/analytics')
@employer_required
def analytics():
    company = get_employer_company()
    if not company:
        return redirect(url_for('employer.company_setup'))

    # Applications per job
    jobs = Position.query.filter_by(company_id=company.id).all()
    job_data = [(j.title, j.application_count) for j in jobs]

    # Monthly applications (last 6 months)
    from datetime import timedelta
    import calendar
    monthly = []
    now = datetime.utcnow()
    for i in range(5, -1, -1):
        d = now.replace(day=1) - timedelta(days=i * 28)
        count = Application.query.join(Position).filter(
            Position.company_id == company.id,
            func.strftime('%Y-%m', Application.applied_at) == d.strftime('%Y-%m')
        ).count()
        monthly.append({'month': d.strftime('%b'), 'count': count})

    funnel = {s: Application.query.join(Position).filter(
        Position.company_id == company.id, Application.status == s
    ).count() for s in ALL_STATUSES}

    total_views = sum((j.views_count or 0) for j in jobs)

    return render_template('employer/analytics.html',
        company=company, job_data=job_data, monthly=monthly,
        funnel=funnel, total_views=total_views,
        total_jobs=len(jobs), active_jobs=sum(1 for j in jobs if j.is_active))


# ─── CV Download ─────────────────────────────────────────────────────────────

@employer_bp.route('/cv/<path:filename>')
@employer_required
def download_cv(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_employer_job(job_id):
    """Return job owned by current employer's company or 404/403."""
    job = Position.query.get_or_404(job_id)
    company = get_employer_company()
    if not company or job.company_id != company.id:
        if current_user.role != ROLE_ADMIN:
            abort(403)
    return job


def _get_employer_application(app_id):
    """Return application for a job managed by current employer or 403."""
    application = Application.query.get_or_404(app_id)
    company = get_employer_company()
    if not company or application.position.company_id != company.id:
        if current_user.role != ROLE_ADMIN:
            abort(403)
    return application


def _build_position_from_form(form, company, pos=None):
    if pos is None:
        pos = Position(company_id=company.id, created_by=current_user.id)
    pos.title           = form.get('title', '').strip()
    pos.department      = form.get('department', '').strip()
    pos.location        = form.get('location', '').strip()
    pos.type            = form.get('job_type', 'Full-time')
    pos.experience_level= form.get('experience_level', '')
    pos.skills_required = form.get('skills_required', '').strip()
    pos.description     = form.get('description', '').strip()
    pos.requirements    = form.get('requirements', '').strip()
    pos.benefits        = form.get('benefits', '').strip()
    pos.salary_range    = form.get('salary_range', '').strip()
    pos.salary_min      = form.get('salary_min', type=int)
    pos.salary_max      = form.get('salary_max', type=int)
    pos.is_remote       = bool(form.get('is_remote'))
    pos.is_active       = bool(form.get('is_active', True))
    closes_str          = form.get('closes_at', '').strip()
    if closes_str:
        try:
            pos.closes_at = datetime.strptime(closes_str, '%Y-%m-%d')
        except ValueError:
            pass
    return pos


def _dispatch_job_alerts(pos):
    """Notify users about a new position.
    - Internships: notify all university coordinators + students who follow the company.
    - Regular jobs: notify users whose saved job alerts match.
    """
    if pos.type == 'Internship':
        _dispatch_internship_alerts(pos)
        return
    from models import JobAlert
    alerts = JobAlert.query.filter_by(is_active=True).all()
    count = 0
    for alert in alerts:
        match = True
        if alert.keywords and alert.keywords.lower() not in pos.title.lower():
            match = False
        if alert.job_type and alert.job_type != pos.type:
            match = False
        if alert.is_remote is not None and alert.is_remote != pos.is_remote:
            match = False
        if match:
            push_notification(
                alert.user_id,
                f'New job matching your alert: <b>{pos.title}</b>',
                url_for('jobs.detail', job_id=pos.id),
                icon='bi-bell-fill'
            )
            count += 1
    if count:
        db.session.commit()


def _dispatch_internship_alerts(pos):
    """Notify all university coordinators + students following the company about a new internship."""
    site_url = current_app.config.get('SITE_URL', '')
    notified_ids = set()

    # 1. All university coordinators
    coord_memberships = UniversityMember.query.filter_by(role='coordinator').all()
    coordinators = User.query.filter(
        User.id.in_([m.user_id for m in coord_memberships]),
        User.is_active == True
    ).all() if coord_memberships else []

    for coord in coordinators:
        push_notification(
            coord.id,
            f'New internship posted: {pos.title}' + (f' at {pos.company.name}' if pos.company else ''),
            url_for('jobs.detail', job_id=pos.id),
            icon='bi-mortarboard-fill'
        )
        try:
            from flask import render_template as _rt
            html = _rt('emails/new_internship_alert.html',
                recipient=coord, position=pos,
                company=pos.company, is_coordinator=True, site_url=site_url)
            send_email(
                coord.email,
                f'New internship: {pos.title}' + (f' at {pos.company.name}' if pos.company else ''),
                html
            )
        except Exception as e:
            current_app.logger.warning(f'Internship coordinator alert email failed for {coord.email}: {e}')
        notified_ids.add(coord.id)

    # 2. Students who follow the company
    if pos.company_id:
        student_follows = (
            CompanyFollow.query
            .join(User, User.id == CompanyFollow.user_id)
            .filter(
                CompanyFollow.company_id == pos.company_id,
                User.role == ROLE_STUDENT,
                User.is_active == True
            ).all()
        )
        for follow in student_follows:
            student = follow.user
            if student.id in notified_ids:
                continue
            push_notification(
                student.id,
                f'New internship at {pos.company.name}: {pos.title}',
                url_for('jobs.detail', job_id=pos.id),
                icon='bi-mortarboard-fill'
            )
            try:
                from flask import render_template as _rt
                html = _rt('emails/new_internship_alert.html',
                    recipient=student, position=pos,
                    company=pos.company, is_coordinator=False, site_url=site_url)
                send_email(
                    student.email,
                    f'New internship at {pos.company.name}: {pos.title}',
                    html
                )
            except Exception as e:
                current_app.logger.warning(f'Internship student alert email failed for {student.email}: {e}')
            notified_ids.add(student.id)

    if notified_ids:
        db.session.commit()
