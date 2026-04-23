"""routes/reports.py — Internship report submission and evaluation.

Students upload reports (Final / Progress / Research / Affiliation) which are
routed to their University Coordinator. Coordinators can review, grade
(0–100) and leave comments. Admins can see and evaluate any report.
"""
import os
import uuid
from datetime import datetime, date
from functools import wraps

from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, current_app, abort, send_from_directory)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import or_

from models import (db, User, Application, InternshipReport, UniversityMember,
                    REPORT_TYPES, REPORT_TYPE_PROGRESS,
                    REPORT_STATUS_SUBMITTED, REPORT_STATUS_UNDER_REVIEW,
                    REPORT_STATUS_GRADED, REPORT_STATUS_NEEDS_REVISION,
                    ALL_REPORT_STATUSES,
                    ROLE_STUDENT, ROLE_UNIVERSITY_COORD, ROLE_ADMIN)
from helpers import log_audit, send_email, push_notification

reports_bp = Blueprint('reports', __name__)


# ─── Auth helpers ────────────────────────────────────────────────────────────

def student_or_coordinator_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role not in (ROLE_STUDENT, ROLE_UNIVERSITY_COORD, ROLE_ADMIN):
            abort(403)
        return f(*args, **kwargs)
    return decorated


def _coordinator_for_student(student):
    """Pick the university coordinator who owns this student.

    Looks at UniversityMember rows for the student's university. Prefers a
    coordinator scoped to the student's department / class, falls back to a
    full-university coordinator.
    """
    if not student or not student.university_id:
        return None
    members = (UniversityMember.query
               .filter_by(university_id=student.university_id)
               .all())
    if not members:
        return None
    # Department + class match
    for m in members:
        if (m.department_id == student.university_department_id
                and m.class_scope == student.university_class
                and m.department_id is not None):
            return User.query.get(m.user_id)
    # Department match only
    for m in members:
        if m.department_id == student.university_department_id and m.department_id is not None:
            return User.query.get(m.user_id)
    # Full-university scope
    for m in members:
        if not m.department_id:
            return User.query.get(m.user_id)
    return User.query.get(members[0].user_id)


def _coordinator_student_ids(coord):
    """Return list of student IDs in a coordinator's scope."""
    if coord.role == ROLE_ADMIN:
        return [u.id for u in User.query.filter_by(role=ROLE_STUDENT).all()]
    membership = UniversityMember.query.filter_by(
        user_id=coord.id).first()
    if not membership:
        return []
    q = User.query.filter_by(role=ROLE_STUDENT, university_id=membership.university_id)
    if membership.department_id:
        q = q.filter(User.university_department_id == membership.department_id)
    if membership.class_scope:
        q = q.filter(User.university_class == membership.class_scope)
    return [u.id for u in q.all()]


def _can_view(report):
    """Authorisation check for an individual report."""
    if current_user.role == ROLE_ADMIN:
        return True
    if current_user.role == ROLE_STUDENT and report.student_id == current_user.id:
        return True
    if current_user.role == ROLE_UNIVERSITY_COORD:
        return report.student_id in _coordinator_student_ids(current_user)
    return False


def _can_grade(report):
    if current_user.role == ROLE_ADMIN:
        return True
    if current_user.role == ROLE_UNIVERSITY_COORD:
        return report.student_id in _coordinator_student_ids(current_user)
    return False


def _allowed_ext(filename):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[-1].lower()
    return ext in current_app.config['REPORT_ALLOWED_EXTENSIONS']


# ─── Listing ─────────────────────────────────────────────────────────────────

@reports_bp.route('/')
@student_or_coordinator_required
def index():
    """Reports list — student sees own, coordinator sees their cohort."""
    role = current_user.role
    status_f = request.args.get('status', '').strip()
    type_f   = request.args.get('type', '').strip()
    search   = request.args.get('q', '').strip()

    if role == ROLE_STUDENT:
        q = InternshipReport.query.filter_by(student_id=current_user.id)
    else:
        sids = _coordinator_student_ids(current_user)
        if not sids:
            return render_template('reports/index.html', reports=[], role=role,
                                   status_f=status_f, type_f=type_f, search=search,
                                   REPORT_TYPES=REPORT_TYPES,
                                   ALL_REPORT_STATUSES=ALL_REPORT_STATUSES,
                                   stats={'total': 0, 'pending': 0, 'graded': 0, 'avg_grade': None})
        q = InternshipReport.query.filter(InternshipReport.student_id.in_(sids))

    if status_f:
        q = q.filter(InternshipReport.status == status_f)
    if type_f:
        q = q.filter(InternshipReport.report_type == type_f)
    if search:
        q = q.filter(or_(
            InternshipReport.title.ilike(f'%{search}%'),
            InternshipReport.description.ilike(f'%{search}%'),
        ))

    reports = q.order_by(InternshipReport.submitted_at.desc()).all()

    # KPIs (unfiltered)
    if role == ROLE_STUDENT:
        all_q = InternshipReport.query.filter_by(student_id=current_user.id)
    else:
        all_q = InternshipReport.query.filter(InternshipReport.student_id.in_(sids))
    all_reports = all_q.all()
    graded = [r for r in all_reports if r.grade is not None]
    stats = {
        'total':   len(all_reports),
        'pending': sum(1 for r in all_reports if r.status in
                       (REPORT_STATUS_SUBMITTED, REPORT_STATUS_UNDER_REVIEW, REPORT_STATUS_NEEDS_REVISION)),
        'graded':  sum(1 for r in all_reports if r.status == REPORT_STATUS_GRADED),
        'avg_grade': round(sum(r.grade for r in graded) / len(graded), 1) if graded else None,
    }

    return render_template('reports/index.html', reports=reports, role=role,
                           status_f=status_f, type_f=type_f, search=search,
                           REPORT_TYPES=REPORT_TYPES,
                           ALL_REPORT_STATUSES=ALL_REPORT_STATUSES,
                           stats=stats)


# ─── Submission (student) ────────────────────────────────────────────────────

@reports_bp.route('/new', methods=['GET', 'POST'])
@login_required
def submit():
    if current_user.role != ROLE_STUDENT:
        abort(403)

    if request.method == 'POST':
        title       = request.form.get('title', '').strip()
        report_type = request.form.get('report_type', REPORT_TYPE_PROGRESS).strip()
        description = request.form.get('description', '').strip() or None
        period_start_s = request.form.get('period_start', '').strip()
        period_end_s   = request.form.get('period_end', '').strip()
        application_id = request.form.get('application_id', type=int)
        f = request.files.get('file')

        if not title or not f or not f.filename:
            flash('Please provide a title and choose a file to upload.', 'danger')
            return redirect(url_for('reports.submit'))

        if not _allowed_ext(f.filename):
            allowed = ', '.join(sorted(current_app.config['REPORT_ALLOWED_EXTENSIONS']))
            flash(f'Unsupported file type. Allowed: {allowed}', 'danger')
            return redirect(url_for('reports.submit'))

        valid_types = {t for t, _, _ in REPORT_TYPES}
        if report_type not in valid_types:
            report_type = REPORT_TYPE_PROGRESS

        # Save the file
        original = secure_filename(f.filename)
        ext = original.rsplit('.', 1)[-1].lower()
        stored = f"{uuid.uuid4().hex}.{ext}"
        folder = current_app.config['REPORTS_FOLDER']
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, stored)
        f.save(path)
        try:
            file_size = os.path.getsize(path)
        except OSError:
            file_size = 0

        coord = _coordinator_for_student(current_user)

        report = InternshipReport(
            student_id     = current_user.id,
            coordinator_id = coord.id if coord else None,
            application_id = application_id if application_id else None,
            report_type    = report_type,
            title          = title,
            description    = description,
            period_start   = _parse_date(period_start_s),
            period_end     = _parse_date(period_end_s),
            file_path      = stored,
            file_name      = original,
            file_size      = file_size,
            file_mime      = f.mimetype,
            status         = REPORT_STATUS_SUBMITTED,
        )
        db.session.add(report)
        log_audit('report.submit', f'{current_user.full_name}: {title}')
        db.session.commit()

        # Notify coordinator
        if coord:
            try:
                push_notification(
                    coord.id,
                    f'New internship report from {current_user.full_name}: {title}',
                    url_for('reports.detail', report_id=report.id),
                    icon='bi-file-earmark-text-fill',
                )
            except Exception:
                pass
            try:
                site_url = current_app.config['SITE_URL']
                html = render_template('emails/report_submitted.html',
                                       report=report, student=current_user, coordinator=coord,
                                       site_url=site_url)
                send_email(coord.email,
                           f'New internship report submitted: {title}',
                           html)
            except Exception as e:
                current_app.logger.warning(f'Coordinator notification email failed: {e}')

        flash('Report submitted successfully.' +
              ('' if coord else ' (No coordinator linked yet — your report is saved and will be visible once you are assigned.)'),
              'success')
        return redirect(url_for('reports.index'))

    # GET — show form
    apps = (Application.query
            .filter_by(applicant_id=current_user.id)
            .order_by(Application.applied_at.desc()).all())
    coord = _coordinator_for_student(current_user)
    return render_template('reports/submit.html',
                           REPORT_TYPES=REPORT_TYPES,
                           applications=apps,
                           coordinator=coord)


# ─── Detail / review ─────────────────────────────────────────────────────────

@reports_bp.route('/<int:report_id>')
@login_required
def detail(report_id):
    report = InternshipReport.query.get_or_404(report_id)
    if not _can_view(report):
        abort(403)
    return render_template('reports/detail.html',
                           report=report,
                           can_grade=_can_grade(report),
                           is_student=(current_user.role == ROLE_STUDENT))


@reports_bp.route('/<int:report_id>/file')
@login_required
def download(report_id):
    report = InternshipReport.query.get_or_404(report_id)
    if not _can_view(report):
        abort(403)
    folder = current_app.config['REPORTS_FOLDER']
    return send_from_directory(folder, report.file_path,
                               as_attachment=True,
                               download_name=report.file_name)


@reports_bp.route('/<int:report_id>/review', methods=['POST'])
@login_required
def review(report_id):
    report = InternshipReport.query.get_or_404(report_id)
    if not _can_grade(report):
        abort(403)

    new_status = request.form.get('status', '').strip()
    grade_s    = request.form.get('grade', '').strip()
    comment    = request.form.get('comment', '').strip() or None

    if new_status and new_status not in ALL_REPORT_STATUSES:
        flash('Invalid status value.', 'danger')
        return redirect(url_for('reports.detail', report_id=report.id))

    grade_val = None
    if grade_s:
        try:
            grade_val = int(grade_s)
            if grade_val < 0 or grade_val > 100:
                raise ValueError
        except ValueError:
            flash('Grade must be an integer between 0 and 100.', 'danger')
            return redirect(url_for('reports.detail', report_id=report.id))

    if new_status:
        report.status = new_status
    elif grade_val is not None:
        report.status = REPORT_STATUS_GRADED

    if grade_val is not None:
        report.grade = grade_val
    if comment is not None:
        report.coordinator_comment = comment

    report.reviewed_by_id = current_user.id
    report.reviewed_at    = datetime.utcnow()
    if not report.coordinator_id:
        report.coordinator_id = current_user.id

    log_audit('report.review',
              f'{report.student.full_name}: {report.title} → {report.status}'
              + (f' ({report.grade}/100)' if report.grade is not None else ''))
    db.session.commit()

    # Notify student
    try:
        push_notification(
            report.student_id,
            f'Your report "{report.title}" was {report.status.lower()}'
            + (f' ({report.grade}/100)' if report.grade is not None else ''),
            url_for('reports.detail', report_id=report.id),
            icon='bi-clipboard-check-fill',
        )
    except Exception:
        pass
    try:
        site_url = current_app.config['SITE_URL']
        html = render_template('emails/report_reviewed.html',
                               report=report, student=report.student,
                               coordinator=current_user, site_url=site_url)
        send_email(report.student.email,
                   f'Your internship report was reviewed: {report.title}',
                   html)
    except Exception as e:
        current_app.logger.warning(f'Student review email failed: {e}')

    flash('Report review saved and the student has been notified.', 'success')
    return redirect(url_for('reports.detail', report_id=report.id))


@reports_bp.route('/<int:report_id>/delete', methods=['POST'])
@login_required
def delete(report_id):
    report = InternshipReport.query.get_or_404(report_id)
    # Only the owning student (and only while not yet graded) or admin can delete
    is_owner = (current_user.role == ROLE_STUDENT and report.student_id == current_user.id)
    if not (current_user.role == ROLE_ADMIN or
            (is_owner and report.status != REPORT_STATUS_GRADED)):
        abort(403)

    # Remove the stored file (best-effort)
    try:
        path = os.path.join(current_app.config['REPORTS_FOLDER'], report.file_path)
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass

    log_audit('report.delete', f'{report.student.full_name}: {report.title}')
    db.session.delete(report)
    db.session.commit()
    flash('Report deleted.', 'success')
    return redirect(url_for('reports.index'))


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except ValueError:
        return None
