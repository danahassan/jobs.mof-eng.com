import os
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, current_app, jsonify,
                   send_from_directory, abort)
from flask_login import login_required, current_user
from sqlalchemy import or_, and_, func
from models import (db, Position, Application, ApplicationHistory, Interview,
                    SavedJob, CompanyFollow, Message, User, CompanyMember, ROLE_ADMIN,
                    SOURCES, STATUS_NEW, STATUS_REVIEW, STATUS_INTERVIEW,
                    STATUS_OFFER, STATUS_HIRED, ALL_STATUSES)
from helpers import save_cv, allowed_file, send_email, push_notification, log_audit
from datetime import datetime

user_bp = Blueprint('user', __name__)


@user_bp.route('/')
@login_required
def dashboard():
    my_apps = (Application.query
               .filter_by(applicant_id=current_user.id)
               .order_by(Application.applied_at.desc())
               .all())
    saved_count = SavedJob.query.filter_by(user_id=current_user.id).count()
    followed_companies = (CompanyFollow.query
                          .filter_by(user_id=current_user.id)
                          .all())
    return render_template('user/dashboard.html', my_apps=my_apps,
                           saved_count=saved_count,
                           followed_companies=followed_companies)


@user_bp.route('/browse')
def browse():
    """Public job listing — no login required."""
    dept    = request.args.get('dept', '')
    search  = request.args.get('q', '').strip()
    jtype   = request.args.get('type', '')
    remote  = request.args.get('remote', '')

    now = datetime.utcnow()
    q = Position.query.filter_by(is_active=True).filter(
        or_(Position.closes_at.is_(None), Position.closes_at >= now))
    if dept:
        q = q.filter_by(department=dept)
    if jtype:
        q = q.filter_by(type=jtype)
    if remote == '1':
        q = q.filter_by(is_remote=True)
    if search:
        q = q.filter(Position.title.ilike(f'%{search}%'))

    positions = q.order_by(Position.created_at.desc()).all()
    depts     = db.session.query(Position.department).filter_by(is_active=True).distinct().all()
    depts     = [d[0] for d in depts if d[0]]
    types     = ['Full-time', 'Part-time', 'Contract', 'Internship']

    saved_ids = set()
    if current_user.is_authenticated:
        saved_ids = {sj.position_id for sj in
                     SavedJob.query.filter_by(user_id=current_user.id).all()}

    # KPI metrics
    kpi_total  = Position.query.filter_by(is_active=True).count()
    kpi_remote = Position.query.filter_by(is_active=True, is_remote=True).count()
    kpi_depts  = db.session.query(func.count(func.distinct(Position.department))).filter(
                     Position.is_active == True, Position.department.isnot(None)).scalar() or 0
    kpi_types  = db.session.query(func.count(func.distinct(Position.type))).filter(
                     Position.is_active == True).scalar() or 0
    kpi_apps   = Application.query.join(Position).filter(Position.is_active == True).count()

    return render_template('user/browse.html',
        positions=positions, depts=depts, types=types,
        dept_f=dept, type_f=jtype, remote_f=remote,
        search=search, saved_ids=saved_ids,
        kpi_total=kpi_total, kpi_remote=kpi_remote, kpi_depts=kpi_depts,
        kpi_types=kpi_types, kpi_apps=kpi_apps)


@user_bp.route('/positions/<int:pos_id>')
def position_detail(pos_id):
    pos = db.get_or_404(Position, pos_id)
    already_applied = False
    if current_user.is_authenticated:
        already_applied = Application.query.filter_by(
            applicant_id=current_user.id, position_id=pos_id).first() is not None
    return render_template('user/position_detail.html',
        pos=pos, already_applied=already_applied, SOURCES=SOURCES)


@user_bp.route('/apply/<int:pos_id>', methods=['GET', 'POST'])
@login_required
def apply(pos_id):
    if current_user.role in ('admin', 'supervisor'):
        flash('Staff accounts cannot submit job applications.', 'warning')
        return redirect(url_for('user.browse'))

    pos = db.get_or_404(Position, pos_id)

    if not pos.is_active:
        flash('This position is no longer accepting applications.', 'warning')
        return redirect(url_for('user.browse'))

    if pos.closes_at and pos.closes_at < datetime.utcnow():
        flash('The application deadline for this position has passed.', 'warning')
        return redirect(url_for('user.browse'))

    existing = Application.query.filter_by(
        applicant_id=current_user.id, position_id=pos_id).first()
    if existing:
        flash('You have already applied for this position.', 'info')
        return redirect(url_for('user.my_applications'))

    if request.method == 'POST':
        cover_letter    = request.form.get('cover_letter', '').strip()
        source          = request.form.get('source', 'Website')
        expected_salary = request.form.get('expected_salary', '').strip()
        cv_file         = request.files.get('cv_file')

        cv_stored = cv_original = None
        if cv_file and cv_file.filename:
            if not allowed_file(cv_file.filename):
                flash('CV must be PDF, DOC, or DOCX.', 'danger')
                return render_template('user/apply.html', pos=pos, SOURCES=SOURCES)
            cv_stored, cv_original = save_cv(cv_file)

        application = Application(
            applicant_id    = current_user.id,
            position_id     = pos_id,
            cover_letter    = cover_letter,
            source          = source,
            expected_salary = expected_salary or None,
            cv_filename     = cv_stored,
            cv_original     = cv_original,
            status          = STATUS_NEW,
        )
        db.session.add(application)
        log_audit('user.apply', f'{current_user.full_name} → {pos.title}',
                  user_id=current_user.id)
        db.session.commit()

        # In-app notification for admin(s)
        from models import User, ROLE_ADMIN, ROLE_SUPERVISOR
        admins = User.query.filter_by(role=ROLE_ADMIN, is_active=True).all()
        for admin in admins:
            push_notification(admin.id,
                f'New application from {current_user.full_name} for {pos.title}',
                url_for('admin.application_detail', app_id=application.id))
        db.session.commit()

        # CV file path for attachment
        cv_path = None
        if application.cv_filename:
            cv_path = os.path.join(current_app.config['UPLOAD_FOLDER'], application.cv_filename)

        # 1. Confirmation email to applicant
        try:
            html = render_template('emails/application_received.html',
                                   app=application, user=current_user, pos=pos)
            send_email(current_user.email,
                       f'Application received — {pos.title}', html)
        except Exception as e:
            current_app.logger.warning(f'Applicant confirmation email failed: {e}')

        # 2. Notification email to supervisors managing this company only
        site_url = current_app.config['SITE_URL']
        review_url = site_url + url_for('admin.application_detail', app_id=application.id)
        if pos.company_id:
            manager_ids = [m.user_id for m in CompanyMember.query.filter_by(
                company_id=pos.company_id, role='manager').all()]
            supervisors = User.query.filter(
                User.id.in_(manager_ids), User.is_active == True).all() if manager_ids else []
        else:
            supervisors = []
        staff_recipients = supervisors
        staff_recipients.extend(supervisors)
        for staff in staff_recipients:
            staff_review_url = review_url
            if staff.role == ROLE_SUPERVISOR:
                staff_review_url = site_url + url_for('supervisor.application_detail', app_id=application.id)
            try:
                html = render_template('emails/application_notify_staff.html',
                                       app=application, pos=pos,
                                       recipient_name=staff.full_name.split()[0],
                                       review_url=staff_review_url)
                send_email(staff.email,
                           f'New Application: {current_user.full_name} → {pos.title}',
                           html,
                           attachment_path=cv_path,
                           attachment_name=application.cv_original)
            except Exception as e:
                current_app.logger.warning(f'Staff notification email to {staff.email} failed: {e}')

        flash(f'Your application for "{pos.title}" has been submitted!', 'success')
        return redirect(url_for('user.my_applications'))

    return render_template('user/apply.html', pos=pos, SOURCES=SOURCES)


@user_bp.route('/save/<int:pos_id>', methods=['POST'])
@login_required
def save_job(pos_id):
    pos = db.get_or_404(Position, pos_id)
    existing = SavedJob.query.filter_by(user_id=current_user.id, position_id=pos_id).first()
    if existing:
        db.session.delete(existing)
        log_audit('user.unsave_job', pos.title, user_id=current_user.id)
        db.session.commit()
        return jsonify({'saved': False})
    db.session.add(SavedJob(user_id=current_user.id, position_id=pos_id))
    log_audit('user.save_job', pos.title, user_id=current_user.id)
    db.session.commit()
    return jsonify({'saved': True})


@user_bp.route('/saved')
@login_required
def saved_jobs():
    saved = (SavedJob.query
             .filter_by(user_id=current_user.id)
             .order_by(SavedJob.saved_at.desc()).all())
    # Filter out saved jobs whose position has been deleted
    saved = [s for s in saved if s.position is not None]
    saved_remote   = sum(1 for s in saved if s.position.is_remote)
    saved_companies = len({s.position.company_id for s in saved
                           if s.position.company_id})
    saved_types    = len({s.position.type for s in saved
                          if s.position.type})
    return render_template('user/saved_jobs.html', saved=saved,
                           saved_remote=saved_remote,
                           saved_companies=saved_companies,
                           saved_types=saved_types)


@user_bp.route('/my-applications')
@login_required
def my_applications():
    page     = request.args.get('page', 1, type=int)
    q        = request.args.get('q', '').strip()
    status_f = request.args.get('status', '').strip()

    query = Application.query.filter_by(applicant_id=current_user.id)
    if q:
        query = query.join(Application.position).filter(
            Position.title.ilike(f'%{q}%'))
    if status_f:
        query = query.filter(Application.status == status_f)

    apps = (query.order_by(Application.applied_at.desc())
            .paginate(page=page, per_page=20, error_out=False))

    # KPI counts — always unfiltered
    all_q = Application.query.filter_by(applicant_id=current_user.id)
    total_all = all_q.count()
    status_counts = {s: all_q.filter_by(status=s).count() for s in ALL_STATUSES}
    active_count = sum(status_counts.get(s, 0)
                       for s in [STATUS_REVIEW, STATUS_INTERVIEW, STATUS_OFFER])
    interview_count = status_counts.get(STATUS_INTERVIEW, 0)
    success_count   = status_counts.get(STATUS_OFFER, 0) + status_counts.get(STATUS_HIRED, 0)

    return render_template('user/my_applications.html',
                           apps=apps, q=q, status_f=status_f,
                           ALL_STATUSES=ALL_STATUSES,
                           status_counts=status_counts,
                           total_all=total_all,
                           active_count=active_count,
                           interview_count=interview_count,
                           success_count=success_count)


@user_bp.route('/my-applications/<int:app_id>/cv')
@login_required
def application_cv(app_id):
    """Let the applicant view/download the CV they uploaded with this application."""
    record = Application.query.filter_by(
        id=app_id, applicant_id=current_user.id).first_or_404()
    if not record.cv_filename:
        abort(404)
    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        record.cv_filename,
        download_name=record.cv_original or record.cv_filename,
        as_attachment=False)   # inline so PDF opens in browser; user can save manually


@user_bp.route('/my-applications/<int:app_id>')
@login_required
def application_detail(app_id):
    app = Application.query.filter_by(
        id=app_id, applicant_id=current_user.id).first_or_404()
    history    = app.history.filter(ApplicationHistory.new_status.isnot(None)).order_by(ApplicationHistory.created_at.asc()).all()
    interviews = app.interviews.order_by(Interview.scheduled_at).all()

    # Determine the best conversation partner: assigned supervisor > any admin
    partner = app.assigned_to
    if not partner:
        partner = User.query.filter_by(role=ROLE_ADMIN, is_active=True)\
                            .order_by(User.id).first()

    thread_messages = []
    if partner:
        thread_messages = (Message.query
                           .filter(or_(
                               and_(Message.sender_id == current_user.id,
                                    Message.receiver_id == partner.id,
                                    Message.deleted_by_sender == False),
                               and_(Message.sender_id == partner.id,
                                    Message.receiver_id == current_user.id,
                                    Message.deleted_by_receiver == False)
                           ))
                           .order_by(Message.created_at.asc())
                           .all())
        # Mark received messages as read
        Message.query.filter_by(sender_id=partner.id, receiver_id=current_user.id,
                                is_read=False).update({'is_read': True})
        db.session.commit()

    return render_template('user/application_detail.html',
        app=app, history=history, interviews=interviews,
        thread_messages=thread_messages, partner=partner)
