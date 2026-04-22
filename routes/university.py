import secrets
import io
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, current_app, abort, jsonify, send_file)
from flask_login import current_user
from sqlalchemy import or_, false as sql_false
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


# ─── Student export / import ─────────────────────────────────────────────────

_STUDENT_COLS = [
    ('student_id_number', 'Student ID'),
    ('full_name',         'Full Name'),
    ('email',             'Email'),
    ('phone',             'Phone'),
    ('university_major',  'Major'),
    ('student_gpa',       'GPA'),
    ('graduation_year',   'Graduation Year'),
]


@university_bp.route('/students/export')
@university_coordinator_required
def students_export():
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    univ = _my_university()
    if univ:
        rows = User.query.filter_by(university_id=univ.id, role=ROLE_STUDENT).order_by(User.full_name).all()
    else:
        rows = User.query.filter_by(role=ROLE_STUDENT).order_by(User.full_name).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Students'

    header_fill = PatternFill('solid', fgColor='1a5c38')
    header_font = Font(color='FFFFFF', bold=True)
    headers = [col[1] for col in _STUDENT_COLS]
    for ci, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=ci, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        ws.column_dimensions[cell.column_letter].width = max(len(h) + 4, 16)

    for ri, s in enumerate(rows, 2):
        for ci, (attr, _) in enumerate(_STUDENT_COLS, 1):
            ws.cell(row=ri, column=ci, value=getattr(s, attr, None))

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    name = f"{univ.name.replace(' ','_')}_students.xlsx" if univ else 'students.xlsx'
    return send_file(buf, as_attachment=True, download_name=name,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@university_bp.route('/students/import-template')
@university_coordinator_required
def students_import_template():
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Students'

    header_fill = PatternFill('solid', fgColor='1a5c38')
    header_font = Font(color='FFFFFF', bold=True)
    example_data = {
        'student_id_number': '20231001',
        'full_name':         'Ahmed Al-Rashidi',
        'email':             'ahmed@example.com',
        'phone':             '+96894123456',
        'university_major':  'Computer Science',
        'student_gpa':       '3.75',
        'graduation_year':   '2025',
    }
    for ci, (attr, label) in enumerate(_STUDENT_COLS, 1):
        cell = ws.cell(row=1, column=ci, value=label)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        ws.column_dimensions[cell.column_letter].width = max(len(label) + 4, 18)
        ws.cell(row=2, column=ci, value=example_data.get(attr, ''))

    # Mark example row in light gray
    from openpyxl.styles import PatternFill as PF
    ex_fill = PF('solid', fgColor='F3F4F6')
    for ci in range(1, len(_STUDENT_COLS) + 1):
        ws.cell(row=2, column=ci).fill = ex_fill

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name='students_import_template.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@university_bp.route('/students/import', methods=['POST'])
@university_coordinator_required
def students_import():
    import openpyxl
    univ = _my_university()
    if not univ:
        flash('You are not linked to any university.', 'warning')
        return redirect(url_for('university.students'))

    f = request.files.get('file')
    if not f or not f.filename:
        flash('No file selected.', 'danger')
        return redirect(url_for('university.students'))
    if not f.filename.lower().endswith(('.xlsx', '.xls')):
        flash('Please upload an Excel file (.xlsx or .xls).', 'danger')
        return redirect(url_for('university.students'))

    try:
        wb = openpyxl.load_workbook(io.BytesIO(f.read()), data_only=True)
        ws = wb.active
    except Exception:
        flash('Could not read the uploaded file. Make sure it is a valid Excel workbook.', 'danger')
        return redirect(url_for('university.students'))

    headers = [str(cell.value or '').strip() for cell in ws[1]]
    label_to_attr = {col[1]: col[0] for col in _STUDENT_COLS}
    col_map = {}  # column index → attribute name
    for ci, h in enumerate(headers):
        if h in label_to_attr:
            col_map[ci] = label_to_attr[h]

    if 'email' not in col_map.values() or 'full_name' not in col_map.values():
        flash('Import failed: the file must have "Email" and "Full Name" columns.', 'danger')
        return redirect(url_for('university.students'))

    created = linked = skipped = 0
    errors = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue  # skip blank rows
        data = {}
        for ci, attr in col_map.items():
            val = row[ci] if ci < len(row) else None
            data[attr] = str(val).strip() if val is not None else ''

        email = data.get('email', '').lower()
        full_name = data.get('full_name', '').strip()
        if not email or not full_name:
            errors.append(f'Row skipped — missing email or name: {data}')
            skipped += 1
            continue

        existing = User.query.filter_by(email=email).first()
        if existing:
            if existing.role == ROLE_STUDENT:
                existing.university_id   = univ.id
                existing.university_name = univ.name
                for attr in ('university_major', 'student_gpa', 'student_id_number', 'phone'):
                    if data.get(attr):
                        setattr(existing, attr, data[attr])
                if data.get('graduation_year'):
                    existing.graduation_year = _parse_int(data['graduation_year'])
                linked += 1
            else:
                errors.append(f'Non-student account exists for {email} — skipped')
                skipped += 1
            continue

        temp_pw = secrets.token_urlsafe(10)
        student = User(
            full_name         = full_name,
            email             = email,
            phone             = data.get('phone') or None,
            role              = ROLE_STUDENT,
            is_active         = True,
            university_id     = univ.id,
            university_name   = univ.name,
            university_major  = data.get('university_major') or None,
            student_gpa       = data.get('student_gpa') or None,
            graduation_year   = _parse_int(data.get('graduation_year', '')),
            student_id_number = data.get('student_id_number') or None,
        )
        student.set_password(temp_pw)
        db.session.add(student)
        db.session.flush()  # get student.id before commit

        try:
            html = render_template('emails/welcome_student.html',
                                   student=student, univ=univ, temp_password=temp_pw)
            send_email(student.email, 'Welcome to MOF Jobs — Your Student Account', html)
        except Exception as e:
            current_app.logger.warning(f'Welcome email failed for {email}: {e}')

        log_audit('university.student_import', f'{full_name} → {univ.name}', user_id=current_user.id)
        created += 1

    db.session.commit()

    parts = []
    if created:  parts.append(f'{created} created')
    if linked:   parts.append(f'{linked} linked')
    if skipped:  parts.append(f'{skipped} skipped')
    msg = 'Import complete: ' + ', '.join(parts) + '.' if parts else 'No rows processed.'
    flash(msg, 'success' if not errors else 'warning')
    for err in errors[:5]:
        flash(err, 'warning')
    return redirect(url_for('university.students'))


# ─── helpers ─────────────────────────────────────────────────────────────────

def _student_ids(univ):
    if univ:
        return [u.id for u in User.query.filter_by(
            university_id=univ.id, role=ROLE_STUDENT).all()]
    return [u.id for u in User.query.filter_by(role=ROLE_STUDENT).all()]


def _internship_pos_ids():
    """Return all internship position IDs (avoids JOIN in paginated queries)."""
    return [p.id for p in Position.query.filter_by(type='Internship').all()]


def _internship_apps(student_ids):
    if not student_ids:
        return Application.query.filter(sql_false())
    pos_ids = _internship_pos_ids()
    if not pos_ids:
        return Application.query.filter(sql_false())
    return Application.query.filter(
        Application.applicant_id.in_(student_ids),
        Application.position_id.in_(pos_ids),
    )


def _parse_int(s):
    try:
        return int(str(s).strip()) if s and str(s).strip() else None
    except (ValueError, TypeError):
        return None
