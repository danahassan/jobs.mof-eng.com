import csv
import io
from datetime import datetime, timedelta
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, abort, current_app, send_from_directory,
                   Response, send_file)
from flask_login import current_user

from models import (db, User, Position, Application, ApplicationHistory,
                    Interview, AuditLog, Company, CompanyMember, CompanyFollow,
                    UserSkill, UserExperience, UserEducation,
                    Message,
                    ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_USER, LANG_LEVELS,
                    ALL_STATUSES, SOURCES, STATUS_NEW)
from sqlalchemy import or_, and_
from helpers import (admin_required, log_history, save_cv, allowed_file,
                     send_email, save_company_image, push_notification, log_audit,
                     get_site_settings, save_site_settings)


def _audit(action, target=''):
    """Write a system audit log entry (requires authenticated admin context)."""
    log_audit(action, target)


def _parse_date(s):
    """Return a date object from an ISO string, or None."""
    from datetime import date as _d
    try:
        return _d.fromisoformat(s.strip()) if s and s.strip() else None
    except ValueError:
        return None


def _parse_int(s):
    """Return an int from a string, or None."""
    try:
        return int(str(s).strip()) if s and str(s).strip() else None
    except (ValueError, TypeError):
        return None


admin_bp = Blueprint('admin', __name__)


# ─── DASHBOARD ────────────────────────────────────────────────────────────────

@admin_bp.route('/')
@admin_required
def dashboard():
    from datetime import timedelta
    total_apps      = Application.query.count()
    new_last_7      = Application.query.filter(
        Application.applied_at >= datetime.utcnow() - timedelta(days=7)
    ).count()
    interview_count = Application.query.filter_by(status='Interview').count()
    hired_count     = Application.query.filter_by(status='Hired').count()

    # Status breakdown
    status_counts = {}
    for s in ALL_STATUSES:
        status_counts[s] = Application.query.filter_by(status=s).count()

    # Source breakdown
    source_counts = {}
    for src in SOURCES:
        source_counts[src] = Application.query.filter_by(source=src).count()

    # Latest 10 applications
    latest = (Application.query
              .order_by(Application.applied_at.desc())
              .limit(10).all())

    # Companies & supervisors for new stats
    companies_count   = Company.query.filter_by(is_active=True).count()
    supervisors_count = (User.query
                         .filter_by(role=ROLE_SUPERVISOR, is_active=True)
                         .count())
    total_positions   = Position.query.filter_by(is_active=True).count()
    total_users       = User.query.filter_by(role=ROLE_USER, is_active=True).count()

    recent_companies  = (Company.query
                         .filter_by(is_active=True)
                         .order_by(Company.id.desc())
                         .limit(5).all())
    recent_supervisors = (User.query
                          .filter_by(role=ROLE_SUPERVISOR, is_active=True)
                          .order_by(User.id.desc())
                          .limit(5).all())

    return render_template('admin/dashboard.html',
        total_apps=total_apps, new_last_7=new_last_7,
        interview_count=interview_count, hired_count=hired_count,
        status_counts=status_counts, source_counts=source_counts,
        latest=latest,
        companies_count=companies_count,
        supervisors_count=supervisors_count,
        total_positions=total_positions,
        total_users=total_users,
        recent_companies=recent_companies,
        recent_supervisors=recent_supervisors)


# ─── POSITIONS ────────────────────────────────────────────────────────────────

POSITION_TYPES = ['Full-time', 'Part-time', 'Contract', 'Internship', 'Remote', 'Freelance']

@admin_bp.route('/positions')
@admin_required
def positions():
    page       = request.args.get('page', 1, type=int)
    q_str      = request.args.get('q', '').strip()
    status_f   = request.args.get('status', '')       # 'active'|'inactive'|''
    types_f    = request.args.getlist('type')          # multi
    company_f  = request.args.get('company_id', 0, type=int)
    dept_f     = request.args.get('dept', '').strip()

    q = Position.query
    if q_str:
        q = q.filter(or_(Position.title.ilike(f'%{q_str}%'),
                         Position.department.ilike(f'%{q_str}%')))
    if status_f == 'active':
        q = q.filter_by(is_active=True)
    elif status_f == 'inactive':
        q = q.filter_by(is_active=False)
    if types_f:
        q = q.filter(Position.type.in_(types_f))
    if company_f:
        q = q.filter_by(company_id=company_f)
    if dept_f:
        q = q.filter(Position.department.ilike(f'%{dept_f}%'))

    positions = q.order_by(Position.created_at.desc()).paginate(
        page=page, per_page=current_app.config.get('POSITIONS_PER_PAGE', 25))

    all_companies = Company.query.filter_by(is_active=True).order_by(Company.name).all()

    kpi_active    = Position.query.filter_by(is_active=True).count()
    kpi_inactive  = Position.query.filter_by(is_active=False).count()
    kpi_total_apps = Application.query.count()
    kpi_closing   = Position.query.filter(
        Position.is_active == True,
        Position.closes_at != None,
        Position.closes_at <= datetime.utcnow() + timedelta(days=14)
    ).count()
    kpi_new_30d   = Position.query.filter(
        Position.created_at >= datetime.utcnow() - timedelta(days=30)
    ).count()

    return render_template('admin/positions.html', positions=positions,
                           q_str=q_str, status_f=status_f, types_f=types_f,
                           company_f=company_f, dept_f=dept_f,
                           all_companies=all_companies, POSITION_TYPES=POSITION_TYPES,
                           kpi_active=kpi_active, kpi_inactive=kpi_inactive,
                           kpi_total_apps=kpi_total_apps, kpi_closing=kpi_closing,
                           kpi_new_30d=kpi_new_30d)


@admin_bp.route('/positions/<int:pos_id>')
@admin_required
def position_detail(pos_id):
    pos = db.get_or_404(Position, pos_id)
    recent_apps = pos.applications.order_by(Application.applied_at.desc()).limit(5).all()
    return render_template('admin/position_detail.html', pos=pos, recent_apps=recent_apps)


@admin_bp.route('/positions/export')
@admin_required
def positions_export():
    fmt = request.args.get('fmt', 'csv')
    rows = Position.query.order_by(Position.created_at.desc()).all()
    headers = ['ID', 'Title', 'Department', 'Type', 'Location', 'Company',
               'Status', 'Applications', 'Views', 'Created', 'Closes']
    data = [[
        p.id, p.title, p.department or '', p.type, p.location or '',
        p.company.name if p.company else '',
        'Active' if p.is_active else 'Inactive',
        p.application_count, p.views_count,
        p.created_at.strftime('%Y-%m-%d'),
        p.closes_at.strftime('%Y-%m-%d') if p.closes_at else ''
    ] for p in rows]
    return _export(headers, data, 'positions', fmt)


@admin_bp.route('/positions/new', methods=['GET', 'POST'])
@admin_required
def position_new():
    if request.method == 'POST':
        company_id = request.form.get('company_id', type=int) or None
        pos = Position(
            title        = request.form['title'].strip(),
            department   = request.form.get('department', '').strip(),
            location     = request.form.get('location', 'Slemani, Iraq').strip(),
            type         = request.form.get('type', 'Full-time'),
            description  = request.form.get('description', '').strip(),
            requirements = request.form.get('requirements', '').strip(),
            salary_range = request.form.get('salary_range', '').strip(),
            is_active    = bool(request.form.get('is_active')),
            company_id   = company_id,
            created_by   = current_user.id,
        )
        closes = request.form.get('closes_at', '').strip()
        if closes:
            pos.closes_at = datetime.strptime(closes, '%Y-%m-%d')
        db.session.add(pos)
        _audit('position.create', pos.title)
        db.session.commit()
        notify = request.form.get('notify_users') == '1'
        if pos.is_active and company_id and notify:
            _send_company_job_alerts(pos)
        flash(f'Position "{pos.title}" created.', 'success')
        return redirect(url_for('admin.positions'))
    companies = Company.query.filter_by(is_active=True).order_by(Company.name).all()
    return render_template('admin/position_form.html', pos=None, companies=companies)


@admin_bp.route('/positions/<int:pos_id>/edit', methods=['GET', 'POST'])
@admin_required
def position_edit(pos_id):
    pos = db.get_or_404(Position, pos_id)
    if request.method == 'POST':
        was_active   = pos.is_active
        old_company  = pos.company_id
        company_id   = request.form.get('company_id', type=int) or None
        pos.title        = request.form['title'].strip()
        pos.department   = request.form.get('department', '').strip()
        pos.location     = request.form.get('location', '').strip()
        pos.type         = request.form.get('type', 'Full-time')
        pos.description  = request.form.get('description', '').strip()
        pos.requirements = request.form.get('requirements', '').strip()
        pos.salary_range = request.form.get('salary_range', '').strip()
        pos.is_active    = bool(request.form.get('is_active'))
        pos.company_id   = company_id
        closes = request.form.get('closes_at', '').strip()
        pos.closes_at    = datetime.strptime(closes, '%Y-%m-%d') if closes else None
        _audit('position.edit', pos.title)
        db.session.commit()
        # Send alerts only if admin explicitly checks notify
        notify = request.form.get('notify_users') == '1'
        if pos.is_active and company_id and notify:
            _send_company_job_alerts(pos)
        flash('Position updated.', 'success')
        return redirect(url_for('admin.positions'))
    companies = Company.query.filter_by(is_active=True).order_by(Company.name).all()
    return render_template('admin/position_form.html', pos=pos, companies=companies)


@admin_bp.route('/positions/<int:pos_id>/toggle', methods=['POST'])
@admin_required
def position_toggle(pos_id):
    pos = db.get_or_404(Position, pos_id)
    pos.is_active = not pos.is_active
    db.session.commit()
    state = 'activated' if pos.is_active else 'deactivated'
    flash(f'"{pos.title}" {state}.', 'success')
    return redirect(request.referrer or url_for('admin.positions'))


@admin_bp.route('/positions/<int:pos_id>/delete', methods=['POST'])
@admin_required
def position_delete(pos_id):
    pos = db.get_or_404(Position, pos_id)
    title = pos.title
    app_count = pos.application_count
    for app in pos.applications.all():
        app.history.delete(synchronize_session=False)
        app.interviews.delete(synchronize_session=False)
        db.session.delete(app)
    db.session.delete(pos)
    _audit('position.delete', f'{title} ({app_count} apps deleted)')
    db.session.commit()
    flash(f'Position "{title}" and {app_count} application(s) permanently deleted.', 'success')
    return redirect(url_for('admin.positions'))


# ─── APPLICATIONS ─────────────────────────────────────────────────────────────

@admin_bp.route('/applications')
@admin_required
def applications():
    page       = request.args.get('page', 1, type=int)
    status_f   = request.args.getlist('status')        # multi-select list
    position_f = request.args.get('position_id', 0, type=int)
    source_f   = request.args.getlist('source')        # multi-select list
    assigned_f = request.args.get('assigned_to', 0, type=int)
    search     = request.args.get('q', '').strip()

    q = Application.query.join(User, Application.applicant_id == User.id)

    if status_f:
        q = q.filter(Application.status.in_(status_f))
    if position_f:
        q = q.filter(Application.position_id == position_f)
    if source_f:
        q = q.filter(Application.source.in_(source_f))
    if assigned_f:
        q = q.filter(Application.assigned_to_id == assigned_f)
    if search:
        q = q.filter(or_(User.full_name.ilike(f'%{search}%'),
                         User.email.ilike(f'%{search}%')))

    apps = q.order_by(Application.applied_at.desc()).paginate(
        page=page, per_page=current_app.config.get('APPLICATIONS_PER_PAGE', 25))

    all_positions  = Position.query.order_by(Position.title).all()
    supervisors    = User.query.filter_by(role=ROLE_SUPERVISOR, is_active=True).order_by(User.full_name).all()

    kpi_total      = Application.query.count()
    kpi_new_7d     = Application.query.filter(
        Application.applied_at >= datetime.utcnow() - timedelta(days=7)).count()
    kpi_interview  = Application.query.filter_by(status='Interview').count()
    kpi_hired      = Application.query.filter_by(status='Hired').count()
    kpi_rejected   = Application.query.filter_by(status='Rejected').count()
    kpi_pending    = Application.query.filter_by(status='New').count()

    return render_template('admin/applications.html',
        apps=apps, all_positions=all_positions, supervisors=supervisors,
        ALL_STATUSES=ALL_STATUSES, SOURCES=SOURCES,
        status_f=status_f, position_f=position_f, source_f=source_f,
        assigned_f=assigned_f, search=search,
        kpi_total=kpi_total, kpi_new_7d=kpi_new_7d, kpi_interview=kpi_interview,
        kpi_hired=kpi_hired, kpi_rejected=kpi_rejected, kpi_pending=kpi_pending)


@admin_bp.route('/applications/export')
@admin_required
def applications_export():
    from models import UserSkill, UserExperience, UserEducation
    fmt = request.args.get('fmt', 'csv')
    rows = Application.query.order_by(Application.applied_at.desc()).all()

    headers = [
        # ── Application submission info ──────────────────────────────────
        'App ID', 'Applied At', 'Updated At', 'Status', 'Source',
        'Position', 'Department', 'Position Type', 'Company',
        'Assigned To',
        'Cover Letter', 'CV Filename (Original)',
        'Internal Notes',
        # ── Applicant identity ───────────────────────────────────────────
        'Full Name', 'Email', 'Phone',
        'Headline', 'Resume Summary',
        'Location', 'Nationality', 'Gender', 'Date of Birth',
        # ── Online presence ──────────────────────────────────────────────
        'LinkedIn', 'Portfolio', 'GitHub',
        # ── Profile sections ─────────────────────────────────────────────
        'Skills',
        'Latest Experience (Title @ Company)',
        'All Experience',
        'Education',
        'Languages',
        'Certifications',
        # ── Misc ─────────────────────────────────────────────────────────
        'Profile Strength (%)', 'Bio',
    ]

    data = []
    for a in rows:
        u = a.applicant

        # Skills
        skills_str = ', '.join(
            f'{s.name} ({s.proficiency})' for s in
            UserSkill.query.filter_by(user_id=u.id).order_by(UserSkill.name).all()
        )

        # Experiences
        exps = UserExperience.query.filter_by(user_id=u.id).order_by(
            UserExperience.start_date.desc().nullslast()).all()
        latest_exp = ''
        if exps:
            e = exps[0]
            latest_exp = f'{e.title}' + (f' @ {e.company}' if e.company else '')
        all_exps = ' | '.join(
            f'{e.title}' + (f' @ {e.company}' if e.company else '') +
            (f' ({e.start_date.year}–{e.end_date.year if e.end_date else "present"})' if e.start_date else '')
            for e in exps
        )

        # Education
        edus = UserEducation.query.filter_by(user_id=u.id).order_by(
            UserEducation.end_year.desc().nullslast()).all()
        edu_str = ' | '.join(
            f'{e.degree or ""}{"," if e.degree and e.field else ""}{e.field or ""} — {e.institution}'
            + (f' ({e.end_year})' if e.end_year else '')
            for e in edus
        )

        # Languages removed (rollback)
        langs_str = ''

        # Certifications removed (rollback)
        certs_str = ''

        dob = u.date_of_birth.strftime('%Y-%m-%d') if u.date_of_birth else ''

        data.append([
            a.id,
            a.applied_at.strftime('%Y-%m-%d %H:%M'),
            a.updated_at.strftime('%Y-%m-%d %H:%M') if a.updated_at else '',
            a.status,
            a.source,
            a.position.title,
            a.position.department or '',
            a.position.type,
            a.position.company.name if a.position.company else '',
            a.assigned_to.full_name if a.assigned_to else '',
            a.cover_letter or '',
            a.cv_original or '',
            a.notes or '',
            u.full_name,
            u.email,
            u.phone or '',
            u.headline or '',
            u.resume_headline or '',
            u.location_city or '',
            u.nationality or '',
            u.gender or '',
            dob,
            u.linkedin_url or '',
            u.portfolio_url or '',
            u.github_url or '',
            skills_str,
            latest_exp,
            all_exps,
            edu_str,
            langs_str,
            certs_str,
            u.profile_strength,
            (u.bio or '').replace('\n', ' '),
        ])

    return _export(headers, data, 'applications', fmt)


@admin_bp.route('/applications/<int:app_id>')
@admin_required
def application_detail(app_id):
    app = db.get_or_404(Application, app_id)
    supervisors = User.query.filter_by(role=ROLE_SUPERVISOR, is_active=True).all()
    # Admins see all status changes + admin-authored entries (notes without status change)
    admin_ids = [u.id for u in User.query.filter_by(role=ROLE_ADMIN).with_entities(User.id).all()]
    history   = app.history.filter(
        db.or_(
            ApplicationHistory.new_status.isnot(None),
            ApplicationHistory.changed_by_id.in_(admin_ids)
        )
    ).order_by(ApplicationHistory.created_at.desc()).all()
    interviews  = app.interviews.order_by(Interview.scheduled_at).all()

    # Applicant profile
    u = app.applicant
    skills         = UserSkill.query.filter_by(user_id=u.id).order_by(UserSkill.name).all()
    experiences    = UserExperience.query.filter_by(user_id=u.id).order_by(
                        UserExperience.start_date.desc().nullslast()).all()
    educations     = UserEducation.query.filter_by(user_id=u.id).order_by(
                        UserEducation.end_year.desc().nullslast()).all()
# Removed languages and certifications (rollback)
    languages = []
    certifications = []
    # Message thread between current admin and the applicant
    thread_messages = (Message.query
                       .filter(or_(
                           and_(Message.sender_id == current_user.id,
                                Message.receiver_id == u.id),
                           and_(Message.sender_id == u.id,
                                Message.receiver_id == current_user.id)
                       ))
                       .order_by(Message.created_at.asc())
                       .all())
    # Mark received as read
    Message.query.filter_by(sender_id=u.id, receiver_id=current_user.id,
                            is_read=False).update({'is_read': True})

    # Message thread between ANY admin and the assigned supervisor (if any)
    supervisor_thread = []
    if app.assigned_to_id:
        admin_ids = [u.id for u in User.query.filter_by(role=ROLE_ADMIN, is_active=True).all()]
        supervisor_thread = (Message.query
                             .filter(or_(
                                 and_(Message.sender_id == app.assigned_to_id,
                                      Message.receiver_id.in_(admin_ids)),
                                 and_(Message.sender_id.in_(admin_ids),
                                      Message.receiver_id == app.assigned_to_id)
                             ))
                             .order_by(Message.created_at.asc())
                             .all())
        Message.query.filter(
            Message.sender_id == app.assigned_to_id,
            Message.receiver_id.in_(admin_ids),
            Message.is_read == False
        ).update({'is_read': True}, synchronize_session=False)

    db.session.commit()

    return render_template('admin/application_detail.html',
        app=app, supervisors=supervisors, ALL_STATUSES=ALL_STATUSES,
        history=history, interviews=interviews,
        skills=skills, experiences=experiences, educations=educations,
        languages=languages, certifications=certifications,
        thread_messages=thread_messages, supervisor_thread=supervisor_thread)


@admin_bp.route('/applications/<int:app_id>/update', methods=['POST'])
@admin_required
def application_update(app_id):
    application = db.get_or_404(Application, app_id)
    new_status  = request.form.get('status')
    note        = request.form.get('note', '').strip()
    assign_to   = request.form.get('assigned_to_id', type=int)

    status_changed = new_status and new_status != application.status

    if status_changed:
        log_history(application, current_user, new_status=new_status, note=note or None, is_internal=True)
        application.status = new_status
        application.updated_at = datetime.utcnow()
        _audit('application.status_change', f'#{application.id} → {new_status}')
    elif note:
        log_history(application, current_user, note=note, is_internal=True)

    if assign_to is not None:
        old_assignee = application.assigned_to_id
        application.assigned_to_id = assign_to or None
        if assign_to and assign_to != old_assignee:
            supervisor = db.session.get(User, assign_to)
            if supervisor:
                _audit('application.assign', f'#{application.id} → {supervisor.full_name}')
                _send_assignment_email(application, supervisor)
                push_notification(
                    supervisor.id,
                    f'Application #{application.id} ({application.position.title}) assigned to you',
                    url_for('supervisor.application_detail', app_id=application.id)
                )

    db.session.commit()

    # Send email + push notification AFTER commit so new status is fully persisted
    if status_changed:
        _send_status_email(application)
        push_notification(
            application.applicant_id,
            f'Your application for "{application.position.title}" is now: {new_status}',
            url_for('user.my_applications')
        )

    flash('Application updated.', 'success')
    return redirect(url_for('admin.application_detail', app_id=app_id))


@admin_bp.route('/applications/<int:app_id>/delete', methods=['POST'])
@admin_required
def application_delete(app_id):
    application = db.get_or_404(Application, app_id)
    application.history.order_by(None).delete(synchronize_session=False)
    application.interviews.delete(synchronize_session=False)
    db.session.delete(application)
    _audit('application.delete', f'#{app_id} {application.position.title}')
    db.session.commit()
    flash('Application permanently deleted.', 'success')
    return redirect(url_for('admin.applications'))


@admin_bp.route('/applications/<int:app_id>/history/<int:history_id>/delete', methods=['POST'])
@admin_required
def history_delete(app_id, history_id):
    entry = db.get_or_404(ApplicationHistory, history_id)
    if entry.application_id != app_id:
        abort(404)
    db.session.delete(entry)
    _audit('application.history_delete', f'app #{app_id} history #{history_id}')
    db.session.commit()
    flash('Timeline entry deleted.', 'success')
    return redirect(url_for('admin.application_detail', app_id=app_id))


@admin_bp.route('/applications/<int:app_id>/interview', methods=['POST'])
@admin_required
def schedule_interview(app_id):
    application = db.get_or_404(Application, app_id)
    scheduled   = request.form.get('scheduled_at', '')
    location    = request.form.get('location', '').strip()
    notes       = request.form.get('notes', '').strip()

    if not scheduled:
        flash('Please provide a date/time for the interview.', 'danger')
        return redirect(url_for('admin.application_detail', app_id=app_id))

    interview = Interview(
        application_id  = application.id,
        scheduled_at    = datetime.strptime(scheduled, '%Y-%m-%dT%H:%M'),
        location        = location,
        interviewer_id  = current_user.id,
        notes           = notes,
    )
    db.session.add(interview)

    if application.status != 'Interview':
        log_history(application, current_user, new_status='Interview',
                    note=f'Interview scheduled for {scheduled}')
        application.status = 'Interview'

    db.session.commit()
    flash('Interview scheduled.', 'success')
    return redirect(url_for('admin.application_detail', app_id=app_id))


# ─── USERS ────────────────────────────────────────────────────────────────────

@admin_bp.route('/users')
@admin_required
def users():
    page     = request.args.get('page', 1, type=int)
    q_str    = request.args.get('q', '').strip()
    roles_f  = request.args.getlist('role')
    status_f = request.args.get('status', '')

    q = User.query
    if q_str:
        q = q.filter(or_(User.full_name.ilike(f'%{q_str}%'),
                         User.email.ilike(f'%{q_str}%')))
    if roles_f:
        q = q.filter(User.role.in_(roles_f))
    if status_f == 'active':
        q = q.filter_by(is_active=True)
    elif status_f == 'inactive':
        q = q.filter_by(is_active=False)

    users_paged = q.order_by(User.role, User.full_name).paginate(
        page=page, per_page=30, error_out=False)

    kpi_total      = User.query.count()
    kpi_admins     = User.query.filter_by(role=ROLE_ADMIN).count()
    kpi_supervisors= User.query.filter_by(role=ROLE_SUPERVISOR).count()
    kpi_users      = User.query.filter_by(role=ROLE_USER).count()
    kpi_active     = User.query.filter_by(is_active=True).count()
    kpi_inactive   = User.query.filter_by(is_active=False).count()

    return render_template('admin/users.html', users=users_paged,
                           q_str=q_str, roles_f=roles_f, status_f=status_f,
                           ROLES=[ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_USER],
                           kpi_total=kpi_total, kpi_admins=kpi_admins,
                           kpi_supervisors=kpi_supervisors, kpi_users=kpi_users,
                           kpi_active=kpi_active, kpi_inactive=kpi_inactive)


@admin_bp.route('/users/export')
@admin_required
def users_export():
    fmt = request.args.get('fmt', 'csv')
    rows = User.query.order_by(User.role, User.full_name).all()
    headers = ['ID', 'Full Name', 'Email', 'Phone', 'Role', 'Status',
               'Created At', 'Last Login']
    data = [[
        u.id, u.full_name, u.email, u.phone or '',
        u.role, 'Active' if u.is_active else 'Inactive',
        u.created_at.strftime('%Y-%m-%d') if hasattr(u, 'created_at') and u.created_at else '',
        u.last_login.strftime('%Y-%m-%d %H:%M') if u.last_login else 'Never'
    ] for u in rows]
    return _export(headers, data, 'users', fmt)


@admin_bp.route('/users/<int:user_id>')
@admin_required
def user_detail(user_id):
    user = db.get_or_404(User, user_id)
    recent_apps = user.applications.order_by(Application.applied_at.desc()).limit(5).all()
    return render_template('admin/user_detail.html', user=user, recent_apps=recent_apps)


@admin_bp.route('/users/new', methods=['GET', 'POST'])
@admin_required
def user_new():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('admin.user_new'))

        user = User(
            full_name = request.form.get('full_name', '').strip(),
            email     = email,
            phone     = request.form.get('phone', '').strip(),
            role      = request.form.get('role', ROLE_USER),
            is_active = bool(request.form.get('is_active', True)),
        )
        user.set_password(request.form.get('password', 'ChangeMe@123'))
        db.session.add(user)
        _audit('user.create', f'{user.full_name} <{user.email}>')
        db.session.commit()
        # Send welcome email based on role
        try:
            temp_pw = request.form.get('password', 'ChangeMe@123')
            if user.role in (ROLE_SUPERVISOR, ROLE_ADMIN):
                html = render_template('emails/welcome_supervisor.html',
                                       user=user,
                                       temp_password=temp_pw,
                                       is_admin=(user.role == ROLE_ADMIN))
                subject = 'Your MOF Jobs Admin Account is Ready' if user.role == ROLE_ADMIN else 'Your MOF Jobs Supervisor Account is Ready'
                send_email(user.email, subject, html)
            else:
                html = render_template('emails/welcome_user.html', user=user)
                send_email(user.email, 'Welcome to MOF Jobs — Your Account is Ready', html)
        except Exception as ex:
            current_app.logger.warning(f'User-create welcome email failed: {ex}')
        flash(f'User {user.full_name} created.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', user=None,
                           ROLES=[ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_USER])


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def user_edit(user_id):
    user = db.get_or_404(User, user_id)
    if request.method == 'POST':
        # ── Account ──────────────────────────────────────────────────────────
        user.full_name = request.form.get('full_name', '').strip()
        new_email = request.form.get('email', '').strip().lower()
        if new_email and new_email != user.email:
            existing = User.query.filter(User.email == new_email, User.id != user.id).first()
            if existing:
                flash('That email is already in use by another account.', 'danger')
                return redirect(url_for('admin.user_edit', user_id=user.id))
            user.email = new_email
        user.phone     = request.form.get('phone', '').strip() or None
        user.role      = request.form.get('role', user.role)
        user.is_active = bool(request.form.get('is_active'))
        new_pw = request.form.get('new_password', '').strip()
        if new_pw:
            user.set_password(new_pw)

        # ── Profile ───────────────────────────────────────────────────────────
        user.gender          = request.form.get('gender') or None
        user.location_city   = request.form.get('location_city', '').strip() or None
        user.headline        = request.form.get('headline', '').strip() or None
        user.bio             = request.form.get('bio', '').strip() or None
        user.resume_headline = request.form.get('resume_headline', '').strip() or None
        user.nationality     = request.form.get('nationality', '').strip() or None
        user.linkedin_url    = request.form.get('linkedin_url', '').strip() or None
        user.github_url      = request.form.get('github_url', '').strip() or None
        user.portfolio_url   = request.form.get('portfolio_url', '').strip() or None
        dob_str = request.form.get('date_of_birth', '').strip()
        user.date_of_birth = _parse_date(dob_str)

        # ── Skills ────────────────────────────────────────────────────────────
        UserSkill.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        for sname, sprof in zip(request.form.getlist('skill_name[]'),
                                request.form.getlist('skill_prof[]')):
            sname = sname.strip()
            if sname:
                db.session.add(UserSkill(user_id=user.id, name=sname,
                                         proficiency=sprof or 'intermediate'))

        # ── Work Experience ───────────────────────────────────────────────────
        UserExperience.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        for title, co, start, end, desc in zip(
                request.form.getlist('exp_title[]'),
                request.form.getlist('exp_company[]'),
                request.form.getlist('exp_start[]'),
                request.form.getlist('exp_end[]'),
                request.form.getlist('exp_desc[]')):
            title = title.strip()
            if title:
                db.session.add(UserExperience(
                    user_id=user.id, title=title,
                    company=co.strip() or None,
                    start_date=_parse_date(start),
                    end_date=_parse_date(end),
                    description=desc.strip() or None))

        # ── Education ────────────────────────────────────────────────────────
        UserEducation.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        for inst, deg, fld, sy, ey in zip(
                request.form.getlist('edu_inst[]'),
                request.form.getlist('edu_degree[]'),
                request.form.getlist('edu_field[]'),
                request.form.getlist('edu_start_year[]'),
                request.form.getlist('edu_end_year[]')):
            inst = inst.strip()
            if inst:
                db.session.add(UserEducation(
                    user_id=user.id, institution=inst,
                    degree=deg.strip() or None,
                    field=fld.strip() or None,
                    start_year=_parse_int(sy),
                    end_year=_parse_int(ey)))

        # ── Languages ────────────────────────────────────────────────────────
        # Removed UserLanguage delete (rollback)
        for lname, lprof in zip(request.form.getlist('lang_name[]'),
                                request.form.getlist('lang_prof[]')):
            lname = lname.strip()
            if lname:
                pass  # Removed UserLanguage add (rollback)

        # ── Certifications ───────────────────────────────────────────────────
        # Removed UserCertification delete (rollback)
        for cname, corg, cissued, ccid, curl in zip(
                request.form.getlist('cert_name[]'),
                request.form.getlist('cert_org[]'),
                request.form.getlist('cert_issued[]'),
                request.form.getlist('cert_cid[]'),
                request.form.getlist('cert_url[]')):
            cname = cname.strip()
            if cname:
                pass  # Removed UserCertification add (rollback)

        _audit('user.edit', f'{user.full_name} <{user.email}>')
        db.session.commit()
        flash('User updated.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', user=user,
                           ROLES=[ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_USER],
                           LANG_LEVELS=LANG_LEVELS)


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@admin_required
def user_toggle(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
    else:
        user.is_active = not user.is_active
        db.session.commit()
        flash(f'{user.full_name} {"activated" if user.is_active else "deactivated"}.', 'success')
    return redirect(request.referrer or url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def user_delete(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.users'))
    name = user.full_name
    for app in user.applications.all():
        app.history.order_by(None).delete(synchronize_session=False)
        app.interviews.delete(synchronize_session=False)
        db.session.delete(app)
    # Delete messages where user is sender or receiver (both cols are NOT NULL)
    Message.query.filter(
        (Message.sender_id == user.id) | (Message.receiver_id == user.id)
    ).delete(synchronize_session=False)
    db.session.delete(user)
    _audit('user.delete', f'{name}')
    db.session.commit()
    flash(f'User "{name}" permanently deleted.', 'success')
    return redirect(url_for('admin.users'))


# ─── CV DOWNLOAD ──────────────────────────────────────────────────────────────

@admin_bp.route('/cv/<filename>')
@admin_required
def download_cv(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _send_status_email(application):
    """Send applicant a status update email."""
    try:
        html = render_template('emails/status_update.html', app=application)
        send_email(application.applicant.email,
                   f'Your application update — {application.position.title}',
                   html)
        current_app.logger.info(f'Status email sent for app #{application.id} to {application.applicant.email}')
    except Exception as e:
        import traceback
        current_app.logger.error(f'Status email FAILED for app #{application.id}: {e}\n{traceback.format_exc()}')
        flash(f'Status updated, but email to {application.applicant.email} failed: {e}', 'warning')


def _send_assignment_email(application, supervisor):
    """Notify supervisor that an application has been assigned to them."""
    try:
        html = render_template('emails/assignment_notification.html',
                               app=application, supervisor=supervisor)
        send_email(supervisor.email,
                   f'New application assigned to you — {application.position.title}',
                   html)
    except Exception as e:
        current_app.logger.warning(f'Assignment email failed: {e}')


# ─── AUDIT TRAIL ──────────────────────────────────────────────────────────────

@admin_bp.route('/audit')
@admin_required
def audit_trail():
    page = request.args.get('page', 1, type=int)
    user_f = request.args.get('user_id', 0, type=int)
    action_f = request.args.get('action', '')

    # System audit log
    q_audit = AuditLog.query.order_by(AuditLog.created_at.desc())
    if user_f:
        q_audit = q_audit.filter_by(user_id=user_f)
    if action_f:
        q_audit = q_audit.filter(AuditLog.action.ilike(f'%{action_f}%'))

    audit_entries = q_audit.paginate(page=page, per_page=40)
    all_users = User.query.order_by(User.full_name).all()

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    kpi_total      = AuditLog.query.count()
    kpi_today      = AuditLog.query.filter(AuditLog.created_at >= today_start).count()
    kpi_this_week  = AuditLog.query.filter(
        AuditLog.created_at >= datetime.utcnow() - timedelta(days=7)).count()
    kpi_users_active = db.session.query(
        db.func.count(db.func.distinct(AuditLog.user_id))
    ).filter(AuditLog.created_at >= datetime.utcnow() - timedelta(days=7)).scalar() or 0

    return render_template('admin/audit.html',
                           audit_entries=audit_entries,
                           all_users=all_users,
                           user_f=user_f,
                           action_f=action_f,
                           kpi_total=kpi_total, kpi_today=kpi_today,
                           kpi_this_week=kpi_this_week,
                           kpi_users_active=kpi_users_active)


@admin_bp.route('/audit/export')
@admin_required
def audit_export():
    fmt = request.args.get('fmt', 'csv')
    rows = AuditLog.query.order_by(AuditLog.created_at.desc()).all()
    headers = ['ID', 'Timestamp', 'User', 'Role', 'Action', 'Target', 'IP Address']
    data = [[
        e.id,
        e.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        e.user.full_name if e.user else 'System',
        e.user.role if e.user else '',
        e.action, e.target or '', e.ip_address or ''
    ] for e in rows]
    return _export(headers, data, 'audit_trail', fmt)


@admin_bp.route('/audit/<int:entry_id>/delete', methods=['POST'])
@admin_required
def audit_delete(entry_id):
    entry = db.get_or_404(AuditLog, entry_id)
    db.session.delete(entry)
    _audit('audit.delete', f'Removed entry #{entry_id}')
    db.session.commit()
    flash(f'Audit entry #{entry_id} deleted.', 'success')
    return redirect(request.referrer or url_for('admin.audit_trail'))


@admin_bp.route('/audit/clear', methods=['POST'])
@admin_required
def audit_clear():
    """Delete all audit log entries (irreversible)."""
    count = AuditLog.query.count()
    AuditLog.query.delete()
    _audit('audit.clear', f'Cleared {count} entries')
    db.session.commit()
    flash(f'All {count} audit entries cleared.', 'success')
    return redirect(url_for('admin.audit_trail'))


# ─── SETTINGS ────────────────────────────────────────────────────────────────

@admin_bp.route('/settings')
@admin_required
def settings():
    site = get_site_settings()
    cfg  = current_app.config
    ctx = {
        'mail_from_name':    site.get('MAIL_FROM_NAME',    'MOF Jobs'),
        'mail_from_address': site.get('MAIL_FROM_ADDRESS', cfg.get('MAIL_USERNAME', '')),
        'mail_server':       cfg.get('MAIL_SERVER', ''),
        'mail_port':         cfg.get('MAIL_PORT', 587),
        'mail_username':     cfg.get('MAIL_USERNAME', ''),
    }
    return render_template('admin/settings.html', **ctx)


@admin_bp.route('/settings/save', methods=['POST'])
@admin_required
def settings_save():
    from_name    = request.form.get('mail_from_name', '').strip()
    from_address = request.form.get('mail_from_address', '').strip()
    if not from_name or not from_address:
        flash('From Name and From Address cannot be empty.', 'danger')
        return redirect(url_for('admin.settings'))
    save_site_settings({'MAIL_FROM_NAME': from_name, 'MAIL_FROM_ADDRESS': from_address})
    _audit('settings.email', f'Sender set to {from_name} <{from_address}>')
    db.session.commit()
    flash('Email sender settings saved.', 'success')
    return redirect(url_for('admin.settings'))


@admin_bp.route('/settings/test-email', methods=['POST'])
@admin_required
def test_email():
    """Send a test email to verify SMTP configuration."""
    recipient = request.form.get('recipient', current_user.email).strip()
    try:
        html = render_template('emails/test_email.html', admin=current_user)
        send_email(recipient, '✅ MOF Jobs — Email Configuration Test', html)
        flash(f'Test email sent to {recipient}. Check your inbox.', 'success')
        _audit('email.test', f'To: {recipient}')
        db.session.commit()
    except Exception as ex:
        flash(f'Email failed: {ex}', 'danger')
    return redirect(url_for('admin.settings'))


# ─── COMPANIES ────────────────────────────────────────────────────────────────

INDUSTRY_CHOICES = [
    'Engineering', 'Construction', 'Oil & Gas', 'Manufacturing',
    'Information Technology', 'Finance', 'Healthcare', 'Education',
    'Consulting', 'Government', 'Logistics', 'Real Estate', 'Other',
]
SIZE_CHOICES = ['1–10', '11–50', '51–200', '201–500', '500+']


@admin_bp.route('/companies')
@admin_required
def companies():
    q_str        = request.args.get('q', '').strip()
    industries_f = request.args.getlist('industry')
    status_f     = request.args.get('status', '')
    verified_f   = request.args.get('verified', '')

    q = Company.query
    if q_str:
        q = q.filter(Company.name.ilike(f'%{q_str}%'))
    if industries_f:
        q = q.filter(Company.industry.in_(industries_f))
    if status_f == 'active':
        q = q.filter_by(is_active=True)
    elif status_f == 'inactive':
        q = q.filter_by(is_active=False)
    if verified_f == 'yes':
        q = q.filter_by(is_verified=True)
    elif verified_f == 'no':
        q = q.filter_by(is_verified=False)

    all_companies = q.order_by(Company.name).all()

    kpi_total    = Company.query.count()
    kpi_active   = Company.query.filter_by(is_active=True).count()
    kpi_verified = Company.query.filter_by(is_verified=True).count()
    kpi_open_jobs = Position.query.filter_by(is_active=True).count()
    kpi_followers = db.session.query(db.func.count(CompanyFollow.id)).scalar() or 0
    kpi_new_30d  = Company.query.filter(
        Company.created_at >= datetime.utcnow() - timedelta(days=30)
    ).count() if hasattr(Company, 'created_at') else 0

    return render_template('admin/companies.html', companies=all_companies,
                           q_str=q_str, industries_f=industries_f,
                           status_f=status_f, verified_f=verified_f,
                           INDUSTRY_CHOICES=INDUSTRY_CHOICES,
                           kpi_total=kpi_total, kpi_active=kpi_active,
                           kpi_verified=kpi_verified, kpi_open_jobs=kpi_open_jobs,
                           kpi_followers=kpi_followers, kpi_new_30d=kpi_new_30d)


@admin_bp.route('/companies/export')
@admin_required
def companies_export():
    fmt = request.args.get('fmt', 'csv')
    rows = Company.query.order_by(Company.name).all()
    headers = ['ID', 'Name', 'Industry', 'Size', 'Location', 'Website',
               'Contact Email', 'Status', 'Verified', 'Open Jobs', 'Followers']
    data = [[
        c.id, c.name, c.industry or '', c.size or '', c.location or '',
        c.website or '', c.contact_email or '',
        'Active' if c.is_active else 'Inactive',
        'Yes' if c.is_verified else 'No',
        c.open_jobs_count, c.follower_count
    ] for c in rows]
    return _export(headers, data, 'companies', fmt)


@admin_bp.route('/companies/new', methods=['GET', 'POST'])
@admin_required
def company_new():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Company name is required.', 'danger')
            return redirect(url_for('admin.company_new'))

        company = Company(
            name          = name,
            description   = request.form.get('description', '').strip(),
            industry      = request.form.get('industry', ''),
            size          = request.form.get('size', ''),
            website       = request.form.get('website', '').strip(),
            location      = request.form.get('location', '').strip(),
            contact_email = request.form.get('contact_email', '').strip(),
            contact_phone = request.form.get('contact_phone', '').strip(),
            is_verified   = bool(request.form.get('is_verified')),
            is_active     = bool(request.form.get('is_active', 'on')),
            created_by    = current_user.id,
        )
        yr = request.form.get('founded_year', '').strip()
        if yr.isdigit():
            company.founded_year = int(yr)
        company.save_slug()

        logo = request.files.get('logo')
        if logo and logo.filename:
            try:
                company.logo_filename = save_company_image(logo)
            except ValueError as e:
                flash(str(e), 'danger')
        cover = request.files.get('cover')
        if cover and cover.filename:
            try:
                company.cover_filename = save_company_image(cover)
            except ValueError as e:
                flash(str(e), 'danger')

        db.session.add(company)
        _audit('company.create', company.name)
        db.session.commit()
        flash(f'Company "{company.name}" created.', 'success')
        return redirect(url_for('admin.company_detail', company_id=company.id))

    return render_template('admin/company_form.html', company=None,
                           industries=INDUSTRY_CHOICES, sizes=SIZE_CHOICES)


@admin_bp.route('/companies/<int:company_id>')
@admin_required
def company_detail(company_id):
    company    = db.get_or_404(Company, company_id)
    managers   = (CompanyMember.query
                  .filter_by(company_id=company_id, role='manager')
                  .all())
    supervisors = User.query.filter_by(role=ROLE_SUPERVISOR, is_active=True).all()
    assigned_ids = {m.user_id for m in managers}
    available_supervisors = [s for s in supervisors if s.id not in assigned_ids]
    positions = company.positions.order_by(Position.created_at.desc()).all()
    return render_template('admin/company_detail.html',
                           company=company,
                           managers=managers,
                           available_supervisors=available_supervisors,
                           positions=positions)


@admin_bp.route('/companies/<int:company_id>/edit', methods=['GET', 'POST'])
@admin_required
def company_edit(company_id):
    company = db.get_or_404(Company, company_id)
    if request.method == 'POST':
        company.name          = request.form.get('name', company.name).strip()
        company.description   = request.form.get('description', '').strip()
        company.industry      = request.form.get('industry', '')
        company.size          = request.form.get('size', '')
        company.website       = request.form.get('website', '').strip()
        company.location      = request.form.get('location', '').strip()
        company.contact_email = request.form.get('contact_email', '').strip()
        company.contact_phone = request.form.get('contact_phone', '').strip()
        company.is_verified   = bool(request.form.get('is_verified'))
        company.is_active     = bool(request.form.get('is_active'))
        yr = request.form.get('founded_year', '').strip()
        company.founded_year  = int(yr) if yr.isdigit() else None

        logo = request.files.get('logo')
        if logo and logo.filename:
            try:
                company.logo_filename = save_company_image(logo)
            except ValueError as e:
                flash(str(e), 'danger')
        cover = request.files.get('cover')
        if cover and cover.filename:
            try:
                company.cover_filename = save_company_image(cover)
            except ValueError as e:
                flash(str(e), 'danger')

        _audit('company.edit', company.name)
        db.session.commit()
        flash('Company updated.', 'success')
        return redirect(url_for('admin.company_detail', company_id=company_id))

    return render_template('admin/company_form.html', company=company,
                           industries=INDUSTRY_CHOICES, sizes=SIZE_CHOICES)


@admin_bp.route('/companies/<int:company_id>/delete', methods=['POST'])
@admin_required
def company_delete(company_id):
    company = db.get_or_404(Company, company_id)
    name = company.name
    db.session.delete(company)
    _audit('company.delete', name)
    db.session.commit()
    flash(f'Company "{name}" deleted.', 'success')
    return redirect(url_for('admin.companies'))


@admin_bp.route('/companies/<int:company_id>/managers/add', methods=['POST'])
@admin_required
def company_manager_add(company_id):
    company = db.get_or_404(Company, company_id)
    user_id = request.form.get('user_id', type=int)
    if not user_id:
        flash('Select a supervisor.', 'danger')
        return redirect(url_for('admin.company_detail', company_id=company_id))
    supervisor = db.get_or_404(User, user_id)
    if supervisor.role != ROLE_SUPERVISOR:
        flash('Selected user is not a supervisor.', 'danger')
        return redirect(url_for('admin.company_detail', company_id=company_id))

    existing = CompanyMember.query.filter_by(
        company_id=company_id, user_id=user_id).first()
    if existing:
        existing.role = 'manager'
    else:
        db.session.add(CompanyMember(
            company_id=company_id, user_id=user_id, role='manager'))

    _audit('company.manager_add', f'{supervisor.full_name} → {company.name}')
    db.session.commit()
    push_notification(
        user_id,
        f'You have been assigned as manager of {company.name}',
        url_for('supervisor.company_dashboard', company_id=company_id),
    )
    db.session.commit()
    try:
        dashboard_url = url_for('supervisor.company_dashboard', company_id=company_id)
        html = render_template(
            'emails/company_manager_assigned.html',
            supervisor=supervisor,
            company=company,
            dashboard_url=dashboard_url,
        )
        send_email(
            supervisor.email,
            f'You have been assigned as manager of {company.name}',
            html,
        )
    except Exception as e:
        current_app.logger.warning(f'Company manager assignment email failed: {e}')
    flash(f'{supervisor.full_name} added as manager of {company.name}.', 'success')
    return redirect(url_for('admin.company_detail', company_id=company_id))


@admin_bp.route('/companies/<int:company_id>/managers/<int:user_id>/remove',
                methods=['POST'])
@admin_required
def company_manager_remove(company_id, user_id):
    company = db.get_or_404(Company, company_id)
    member = CompanyMember.query.filter_by(
        company_id=company_id, user_id=user_id, role='manager').first_or_404()
    db.session.delete(member)
    _audit('company.manager_remove', f'user#{user_id} ← {company.name}')
    db.session.commit()
    flash('Manager removed.', 'success')
    return redirect(url_for('admin.company_detail', company_id=company_id))


# ─── COMPANY JOB ALERTS ───────────────────────────────────────────────────────

def _send_company_job_alerts(position):
    """Email & notify all followers of a company when a new job is posted."""
    if not position.company_id:
        return
    followers = CompanyFollow.query.filter_by(company_id=position.company_id).all()
    for follow in followers:
        user = follow.user
        try:
            html = render_template(
                'emails/new_job_alert.html',
                user=user, position=position, company=position.company,
            )
            send_email(
                user.email,
                f'New job at {position.company.name}: {position.title}',
                html,
            )
        except Exception as e:
            current_app.logger.warning(
                f'Job alert email failed for {user.email}: {e}')
        push_notification(
            user.id,
            f'New job at {position.company.name}: {position.title}',
            url_for('jobs.detail', position_id=position.id),
            'bi-briefcase-fill',
        )
    if followers:
        db.session.commit()


# ─── EXPORT HELPER ────────────────────────────────────────────────────────────

def _export(headers, data, filename_base, fmt='csv'):
    """Return a CSV or Excel response for the given data."""
    if fmt == 'xlsx':
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = filename_base.replace('_', ' ').title()
            # Header row styling
            header_fill = PatternFill('solid', fgColor='0F1923')
            header_font = Font(bold=True, color='FFFFFF', size=11)
            ws.append(headers)
            for col_idx, _ in enumerate(headers, start=1):
                cell = ws.cell(row=1, column=col_idx)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center')
            for row in data:
                ws.append([str(v) if v is not None else '' for v in row])
            # Auto column width
            for col in ws.columns:
                max_len = max((len(str(c.value or '')) for c in col), default=10)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)
            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            return send_file(buf,
                             mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                             as_attachment=True,
                             download_name=f'{filename_base}.xlsx')
        except ImportError:
            flash('openpyxl is required for Excel export. Install it with: pip install openpyxl', 'warning')
            return redirect(request.referrer or url_for('admin.dashboard'))

    # Default: CSV
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(headers)
    for row in data:
        writer.writerow([str(v) if v is not None else '' for v in row])
    return Response(
        si.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename_base}.csv'}
    )
