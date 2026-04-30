"""routes/profile.py â€” Extended candidate profile management.

Handles: photo upload, languages, certifications, portfolio items,
CV builder (HTML view + PDF download), job alerts.
"""
import os, uuid
from datetime import datetime
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, abort, jsonify, current_app,
                   send_file, make_response)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from models import (db, User, UserSkill, UserExperience, UserEducation,
                    UserLanguage, UserCertification, UserPortfolioItem,
                    JobAlert, CompanyFollow, LANG_LEVELS, JOB_TYPES,
                    ROLE_STUDENT, ROLE_ADMIN)

profile_bp = Blueprint('profile', __name__)

AVATAR_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
PORTFOLIO_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'zip', 'docx'}
AVATAR_DIR    = os.path.join('static', 'uploads', 'avatars')
PORTFOLIO_DIR = os.path.join('static', 'uploads', 'portfolio')


# â”€â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _check_owner(user_id):
    if current_user.id != user_id:
        abort(403)


def _ensure_dirs():
    os.makedirs(current_app.root_path + '/' + AVATAR_DIR, exist_ok=True)
    os.makedirs(current_app.root_path + '/' + PORTFOLIO_DIR, exist_ok=True)


# â”€â”€â”€ Full Profile View â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@profile_bp.route('/')
@login_required
def view():
    # Keep a single profile UI source: /profile (auth.profile).
    args = dict(request.args)
    tab = args.get('tab')
    if tab and tab not in {'info', 'skills', 'experience', 'security', 'languages', 'certs', 'portfolio'}:
        args['tab'] = 'info'
    return redirect(url_for('auth.profile', **args))


@profile_bp.route('/user/<int:user_id>')
@login_required
def classmate_view(user_id):
    target = db.get_or_404(User, user_id)
    if not target.is_active:
        abort(404)

    # Students can only view classmates from the same university.
    if current_user.role == ROLE_STUDENT:
        if not current_user.university_id or target.role != ROLE_STUDENT or target.university_id != current_user.university_id:
            abort(403)
    # Non-admin non-student users should not access this page.
    elif current_user.role != ROLE_ADMIN:
        abort(403)

    return render_template('profile/classmate_view.html', classmate=target)


# â”€â”€â”€ Photo Upload â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@profile_bp.route('/photo', methods=['POST'])
@login_required
def upload_photo():
    f = request.files.get('photo')
    if not f or not f.filename:
        flash('No file selected.', 'danger')
        return redirect(url_for('profile.view'))
    ext = f.filename.rsplit('.', 1)[-1].lower()
    if ext not in AVATAR_EXTENSIONS:
        flash('Allowed formats: PNG, JPG, WEBP, GIF.', 'danger')
        return redirect(url_for('profile.view'))
    _ensure_dirs()
    fname = f'avatar_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}'
    f.save(os.path.join(current_app.root_path, AVATAR_DIR, fname))
    # Delete old avatar
    if current_user.avatar_filename:
        old = os.path.join(current_app.root_path, AVATAR_DIR, current_user.avatar_filename)
        if os.path.exists(old):
            os.remove(old)
    current_user.avatar_filename = fname
    db.session.commit()
    flash('Profile photo updated.', 'success')
    return redirect(url_for('profile.view'))


# â”€â”€â”€ Basic Info â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@profile_bp.route('/basic', methods=['POST'])
@login_required
def update_basic():
    u = current_user
    u.full_name      = request.form.get('full_name', u.full_name).strip()
    u.headline       = request.form.get('headline', '').strip()
    u.phone          = request.form.get('phone', '').strip()
    u.bio            = request.form.get('bio', '').strip()
    u.location_city  = request.form.get('location_city', '').strip()
    u.nationality    = request.form.get('nationality', '').strip()
    u.gender         = request.form.get('gender', '').strip()
    u.linkedin_url   = request.form.get('linkedin_url', '').strip()
    u.github_url     = request.form.get('github_url', '').strip()
    u.portfolio_url  = request.form.get('portfolio_url', '').strip()
    u.resume_headline= request.form.get('resume_headline', '').strip()
    dob_str = request.form.get('date_of_birth', '').strip()
    if dob_str:
        try:
            from datetime import date
            u.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    db.session.commit()
    flash('Profile updated.', 'success')
    return redirect(url_for('profile.view', mode='edit', tab='info'))


# â”€â”€â”€ Skills â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@profile_bp.route('/skills', methods=['POST'])
@login_required
def add_skill():
    name = request.form.get('name', '').strip()
    prof = request.form.get('proficiency', 'intermediate')
    if not name:
        return jsonify({'error': 'Name required'}), 400
    s = UserSkill(user_id=current_user.id, name=name, proficiency=prof)
    db.session.add(s)
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'id': s.id, 'name': s.name, 'proficiency': s.proficiency})
    flash('Skill added.', 'success')
    return redirect(url_for('profile.view', mode='edit', tab='skills'))


@profile_bp.route('/skills/<int:skill_id>', methods=['DELETE', 'POST'])
@login_required
def delete_skill(skill_id):
    s = UserSkill.query.get_or_404(skill_id)
    _check_owner(s.user_id)
    db.session.delete(s)
    db.session.commit()
    if request.method == 'DELETE':
        return jsonify({'ok': True})
    flash('Skill removed.', 'success')
    return redirect(url_for('profile.view', mode='edit', tab='skills'))


# â”€â”€â”€ Languages â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@profile_bp.route('/languages', methods=['POST'])
@login_required
def add_language():
    lang  = request.form.get('language', '').strip()
    level = request.form.get('proficiency', 'Intermediate')
    if not lang:
        flash('Language name required.', 'danger')
        return redirect(url_for('profile.view', mode='edit', tab='languages'))
    db.session.add(UserLanguage(user_id=current_user.id, language=lang, proficiency=level))
    db.session.commit()
    flash('Language added.', 'success')
    return redirect(url_for('profile.view', mode='edit', tab='languages'))


@profile_bp.route('/languages/<int:lang_id>/delete', methods=['POST'])
@login_required
def delete_language(lang_id):
    l = UserLanguage.query.get_or_404(lang_id)
    _check_owner(l.user_id)
    db.session.delete(l)
    db.session.commit()
    flash('Language removed.', 'success')
    return redirect(url_for('profile.view', mode='edit', tab='languages'))


# â”€â”€â”€ Certifications â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@profile_bp.route('/certifications', methods=['POST'])
@login_required
def add_cert():
    name   = request.form.get('name', '').strip()
    org    = request.form.get('issuing_org', '').strip()
    cred_id= request.form.get('credential_id', '').strip()
    cred_url=request.form.get('credential_url', '').strip()
    issue  = request.form.get('issue_date', '').strip()
    expiry = request.form.get('expiry_date', '').strip()
    if not name:
        flash('Certification name required.', 'danger')
        return redirect(url_for('profile.view', mode='edit', tab='languages'))
    cert = UserCertification(
        user_id=current_user.id, name=name, issuing_org=org,
        credential_id=cred_id, credential_url=cred_url,
    )
    if issue:
        try: cert.issue_date = datetime.strptime(issue, '%Y-%m-%d').date()
        except ValueError: pass
    if expiry:
        try: cert.expiry_date = datetime.strptime(expiry, '%Y-%m-%d').date()
        except ValueError: pass
    db.session.add(cert)
    db.session.commit()
    flash('Certification added.', 'success')
    return redirect(url_for('profile.view', mode='edit', tab='languages'))


@profile_bp.route('/certifications/<int:cert_id>/delete', methods=['POST'])
@login_required
def delete_cert(cert_id):
    c = UserCertification.query.get_or_404(cert_id)
    _check_owner(c.user_id)
    db.session.delete(c)
    db.session.commit()
    flash('Certification removed.', 'success')
    return redirect(url_for('profile.view', mode='edit', tab='languages'))


# â”€â”€â”€ Portfolio â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@profile_bp.route('/portfolio', methods=['POST'])
@login_required
def add_portfolio():
    title = request.form.get('title', '').strip()
    desc  = request.form.get('description', '').strip()
    url   = request.form.get('url', '').strip()
    if not title:
        flash('Title required.', 'danger')
        return redirect(url_for('profile.view', mode='edit', tab='languages'))
    item = UserPortfolioItem(user_id=current_user.id, title=title, description=desc, url=url)
    f = request.files.get('file')
    if f and f.filename:
        ext = f.filename.rsplit('.', 1)[-1].lower()
        if ext in PORTFOLIO_EXTENSIONS:
            _ensure_dirs()
            fname = f'portfolio_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}'
            f.save(os.path.join(current_app.root_path, PORTFOLIO_DIR, fname))
            item.filename = fname
    db.session.add(item)
    db.session.commit()
    flash('Portfolio item added.', 'success')
    return redirect(url_for('profile.view', mode='edit', tab='languages'))


@profile_bp.route('/portfolio/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_portfolio(item_id):
    item = UserPortfolioItem.query.get_or_404(item_id)
    _check_owner(item.user_id)
    if item.filename:
        path = os.path.join(current_app.root_path, PORTFOLIO_DIR, item.filename)
        if os.path.exists(path):
            os.remove(path)
    db.session.delete(item)
    db.session.commit()
    flash('Portfolio item removed.', 'success')
    return redirect(url_for('profile.view', mode='edit', tab='languages'))


# â”€â”€â”€ Job Alerts â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@profile_bp.route('/alerts', methods=['POST'])
@login_required
def add_alert():
    keywords = request.form.get('keywords', '').strip()
    location = request.form.get('location', '').strip()
    job_type = request.form.get('job_type', '').strip()
    is_remote = bool(request.form.get('is_remote'))

    # Prevent identical duplicates for the same user
    existing = JobAlert.query.filter_by(
        user_id=current_user.id,
        keywords=keywords or None,
        location=location or None,
        job_type=job_type or None,
    ).first()
    if existing:
        flash('You already have an identical job alert.', 'info')
        return redirect(url_for('profile.view', mode='edit', tab='alerts'))

    alert = JobAlert(
        user_id=current_user.id,
        keywords=keywords or None,
        location=location or None,
        job_type=job_type or None,
        is_remote=is_remote,
    )
    db.session.add(alert)
    db.session.commit()
    flash('Job alert saved. You\'ll be notified when matching jobs are posted.', 'success')
    return redirect(url_for('profile.view', mode='edit', tab='alerts'))

# --- Experience ----------------------------------------------------------

@profile_bp.route('/experience', methods=['POST'])
@login_required
def add_experience():
    title = request.form.get('title', '').strip()
    if not title:
        flash('Job title required.', 'danger')
        return redirect(url_for('profile.view', mode='edit', tab='experience'))
    exp = UserExperience(
        user_id=current_user.id,
        title=title,
        company=request.form.get('company', '').strip(),
    )
    start = request.form.get('start_date', '').strip()
    end   = request.form.get('end_date', '').strip()
    if start:
        try:
            exp.start_date = datetime.strptime(start, '%Y-%m-%d').date()
        except ValueError:
            pass
    if end:
        try:
            exp.end_date = datetime.strptime(end, '%Y-%m-%d').date()
        except ValueError:
            pass
    db.session.add(exp)
    db.session.commit()
    flash('Experience added.', 'success')
    return redirect(url_for('profile.view', mode='edit', tab='experience'))


@profile_bp.route('/experience/<int:exp_id>/delete', methods=['POST'])
@login_required
def delete_experience(exp_id):
    exp = UserExperience.query.get_or_404(exp_id)
    _check_owner(exp.user_id)
    db.session.delete(exp)
    db.session.commit()
    flash('Experience removed.', 'success')
    return redirect(url_for('profile.view', mode='edit', tab='experience'))


# --- Education -----------------------------------------------------------

@profile_bp.route('/education', methods=['POST'])
@login_required
def add_education():
    institution = request.form.get('institution', '').strip()
    if not institution:
        flash('Institution required.', 'danger')
        return redirect(url_for('profile.view', mode='edit', tab='education'))
    edu = UserEducation(
        user_id=current_user.id,
        institution=institution,
        degree=request.form.get('degree', '').strip(),
        field=request.form.get('field_of_study', '').strip(),
    )
    start_yr = request.form.get('start_year', '').strip()
    end_yr   = request.form.get('end_year', '').strip()
    if start_yr:
        try:
            edu.start_year = int(start_yr)
        except ValueError:
            pass
    if end_yr:
        try:
            edu.end_year = int(end_yr)
        except ValueError:
            pass
    db.session.add(edu)
    db.session.commit()
    flash('Education added.', 'success')
    return redirect(url_for('profile.view', mode='edit', tab='education'))


@profile_bp.route('/education/<int:edu_id>/delete', methods=['POST'])
@login_required
def delete_education(edu_id):
    edu = UserEducation.query.get_or_404(edu_id)
    _check_owner(edu.user_id)
    db.session.delete(edu)
    db.session.commit()
    flash('Education removed.', 'success')
    return redirect(url_for('profile.view', mode='edit', tab='education'))



@profile_bp.route('/alerts/<int:alert_id>/delete', methods=['POST'])
@login_required
def delete_alert(alert_id):
    a = JobAlert.query.get_or_404(alert_id)
    _check_owner(a.user_id)
    db.session.delete(a)
    db.session.commit()
    flash('Alert removed.', 'success')
    return redirect(url_for('profile.view', mode='edit', tab='alerts'))

# â”€â”€â”€ CV Builder + PDF â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@profile_bp.route('/cv')
@login_required
def cv_builder():
    """HTML preview of the candidate's CV."""
    u = current_user
    skills   = u.skills.order_by(UserSkill.created_at).all()
    exps     = u.experiences.order_by(UserExperience.start_date.desc()).all()
    edus     = u.educations.order_by(UserEducation.start_year.desc()).all()
    langs    = u.languages.order_by(UserLanguage.created_at).all()
    certs    = u.certifications.order_by(UserCertification.created_at).all()
    portfolio= u.portfolio_items.order_by(UserPortfolioItem.created_at).all()
    return render_template('profile/cv_preview.html',
        u=u, user=u, skills=skills, exps=exps, edus=edus,
        langs=langs, certs=certs, portfolio=portfolio)


@profile_bp.route('/cv/download')
@login_required
def cv_download():
    """Generate and return a PDF CV using ReportLab."""
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

    u      = current_user
    skills = u.skills.all()
    exps   = u.experiences.order_by(UserExperience.start_date.desc()).all()
    edus   = u.educations.order_by(UserEducation.start_year.desc()).all()
    langs  = u.languages.order_by(UserLanguage.created_at).all()
    certs  = u.certifications.order_by(UserCertification.created_at).all()

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             rightMargin=2*cm, leftMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    name_style = ParagraphStyle('Name', parent=styles['Title'], fontSize=22,
                                 textColor=colors.HexColor('#1a56db'), spaceAfter=4)
    h2_style   = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=13,
                                  textColor=colors.HexColor('#1a56db'), spaceBefore=12, spaceAfter=4)
    body       = styles['Normal']
    body.fontSize = 10

    story = []

    # Name + headline
    story.append(Paragraph(u.full_name, name_style))
    if u.headline:
        story.append(Paragraph(u.headline, styles['Italic']))
    story.append(Spacer(1, 4))

    # Contact line
    contact_parts = []
    if u.email:        contact_parts.append(u.email)
    if u.phone:        contact_parts.append(u.phone)
    if u.location_city: contact_parts.append(u.location_city)
    if contact_parts:
        story.append(Paragraph(' | '.join(contact_parts), body))

    links = []
    if u.linkedin_url:   links.append(f'LinkedIn: {u.linkedin_url}')
    if u.github_url:     links.append(f'GitHub: {u.github_url}')
    if u.portfolio_url:  links.append(f'Portfolio: {u.portfolio_url}')
    if links:
        story.append(Paragraph(' | '.join(links), body))

    story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#1a56db'), spaceAfter=6))

    # Summary
    if u.bio:
        story.append(Paragraph('Summary', h2_style))
        story.append(Paragraph(u.bio.replace('\n', '<br/>'), body))

    # Experience
    if exps:
        story.append(Paragraph('Experience', h2_style))
        for e in exps:
            start = e.start_date.strftime('%b %Y') if e.start_date else ''
            end   = e.end_date.strftime('%b %Y') if e.end_date else 'Present'
            story.append(Paragraph(f'<b>{e.title}</b> â€” {e.company or ""} &nbsp;&nbsp;<i>{start} â€“ {end}</i>', body))
            if e.description:
                story.append(Paragraph(e.description.replace('\n', '<br/>'), body))
            story.append(Spacer(1, 4))

    # Education
    if edus:
        story.append(Paragraph('Education', h2_style))
        for e in edus:
            yrs = f'{e.start_year or ""} â€“ {e.end_year or "Present"}'
            story.append(Paragraph(f'<b>{e.degree or ""} {e.field or ""}</b> â€” {e.institution} &nbsp;<i>{yrs}</i>', body))
        story.append(Spacer(1, 4))

    # Skills
    if skills:
        story.append(Paragraph('Skills', h2_style))
        skill_text = ', '.join(s.name for s in skills)
        story.append(Paragraph(skill_text, body))

    # Languages
    if langs:
        story.append(Paragraph('Languages', h2_style))
        lang_text = ', '.join(f'{l.language} ({l.proficiency})' for l in langs)
        story.append(Paragraph(lang_text, body))

    # Certifications
    if certs:
        story.append(Paragraph('Certifications', h2_style))
        for c in certs:
            issued = c.issue_date.strftime('%b %Y') if c.issue_date else ''
            story.append(Paragraph(f'<b>{c.name}</b>{" â€” " + c.issuing_org if c.issuing_org else ""}{" (" + issued + ")" if issued else ""}', body))

    doc.build(story)
    buf.seek(0)
    safe_name = u.full_name.replace(' ', '_')
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True,
                     download_name=f'CV_{safe_name}.pdf')
