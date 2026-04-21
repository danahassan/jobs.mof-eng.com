import secrets
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, current_app)
from models import db, UniversityRequest, User, ROLE_ADMIN
from helpers import send_email, log_audit, push_notification, save_company_image

university_apply_bp = Blueprint('university_apply', __name__)


def _save_logo(file):
    if not file or not file.filename:
        return None
    try:
        return save_company_image(file)
    except ValueError:
        return None


def _handle_form(req=None):
    """Shared logic for new application and resubmit."""
    data = request.form.to_dict()
    errors = []

    required = ['full_name', 'email', 'phone', 'headline', 'bio',
                'nationality', 'location_city', 'gender',
                'university_name', 'university_location',
                'university_contact_email', 'university_description']
    for field in required:
        if not data.get(field, '').strip():
            errors.append(f'{field.replace("_", " ").title()} is required.')

    pw  = data.get('password', '').strip()
    cpw = data.get('confirm_password', '').strip()
    if not req:
        if not pw:
            errors.append('Password is required.')
        elif len(pw) < 8:
            errors.append('Password must be at least 8 characters.')
        elif pw != cpw:
            errors.append('Passwords do not match.')
    elif pw:
        if len(pw) < 8:
            errors.append('Password must be at least 8 characters.')
        elif pw != cpw:
            errors.append('Passwords do not match.')

    email = data.get('email', '').strip().lower()
    if not req:
        if User.query.filter_by(email=email).first():
            errors.append('An account with this email already exists.')
        if UniversityRequest.query.filter_by(email=email, status='pending').first():
            errors.append('A pending application with this email already exists.')

    if errors:
        for e in errors:
            flash(e, 'danger')
        return None, data

    logo_fn = _save_logo(request.files.get('university_logo'))

    if req:
        req.full_name             = data['full_name'].strip()
        req.email                 = email
        req.phone                 = data['phone'].strip()
        req.headline              = data.get('headline', '').strip()
        req.bio                   = data.get('bio', '').strip()
        req.nationality           = data.get('nationality', '').strip()
        req.location_city         = data.get('location_city', '').strip()
        req.gender                = data.get('gender', '').strip()
        req.linkedin_url          = data.get('linkedin_url', '').strip() or None
        req.university_name          = data['university_name'].strip()
        req.university_location      = data.get('university_location', '').strip()
        req.university_website       = data.get('university_website', '').strip() or None
        req.university_description   = data.get('university_description', '').strip()
        req.university_contact_email = data.get('university_contact_email', '').strip()
        req.university_contact_phone = data.get('university_contact_phone', '').strip() or None
        if logo_fn:
            req.university_logo_filename = logo_fn
        if pw:
            req.set_password(pw)
        if req.status == 'rejected':
            req.status = 'pending'
        db.session.commit()
        log_audit('university_request.resubmit', f'{req.full_name} resubmitted')
        db.session.commit()
        return req, {}

    token = secrets.token_urlsafe(32)
    new_req = UniversityRequest(
        token=token,
        full_name             = data['full_name'].strip(),
        email                 = email,
        phone                 = data['phone'].strip(),
        headline              = data.get('headline', '').strip(),
        bio                   = data.get('bio', '').strip(),
        nationality           = data.get('nationality', '').strip(),
        location_city         = data.get('location_city', '').strip(),
        gender                = data.get('gender', '').strip(),
        linkedin_url          = data.get('linkedin_url', '').strip() or None,
        university_name          = data['university_name'].strip(),
        university_location      = data.get('university_location', '').strip(),
        university_website       = data.get('university_website', '').strip() or None,
        university_description   = data.get('university_description', '').strip(),
        university_contact_email = data.get('university_contact_email', '').strip(),
        university_contact_phone = data.get('university_contact_phone', '').strip() or None,
        university_logo_filename = logo_fn,
    )
    new_req.set_password(pw)
    db.session.add(new_req)
    db.session.commit()
    log_audit('university_request.submit', f'{new_req.full_name} applied')
    db.session.commit()

    # Notify admins
    admins = User.query.filter_by(role=ROLE_ADMIN, is_active=True).all()
    site_url = current_app.config.get('SITE_URL', '')
    review_url = site_url + url_for('admin.university_request_detail', req_id=new_req.id)
    for admin in admins:
        push_notification(admin.id,
            f'New university request from {new_req.full_name} ({new_req.university_name})',
            url_for('admin.university_request_detail', req_id=new_req.id),
            'bi-mortarboard-fill')
    db.session.commit()
    for admin in admins:
        try:
            html = render_template('emails/univ_request_admin_notify.html',
                                   req=new_req, review_url=review_url,
                                   admin_name=admin.full_name.split()[0])
            send_email(admin.email,
                       f'New University Coordinator Request — {new_req.university_name}', html)
        except Exception as e:
            current_app.logger.warning(f'Admin notify email failed: {e}')

    return new_req, {}


@university_apply_bp.route('/university_apply', methods=['GET', 'POST'])
def apply():
    if request.method == 'POST':
        saved, data = _handle_form(req=None)
        if saved:
            return render_template('university_apply.html', data={}, req=None, submitted=True)
        return render_template('university_apply.html', data=data, req=None, submitted=False)
    return render_template('university_apply.html', data={}, req=None, submitted=False)


@university_apply_bp.route('/university_apply/<token>', methods=['GET', 'POST'])
def apply_edit(token):
    req = UniversityRequest.query.filter_by(token=token).first_or_404()
    if req.status == 'approved':
        flash('This application has already been approved. Please log in.', 'info')
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        saved, data = _handle_form(req=req)
        if saved:
            flash('Your application has been resubmitted!', 'success')
            return render_template('university_apply.html', data={}, req=req, submitted=True)
        return render_template('university_apply.html', data=data, req=req, submitted=False)
    data = {
        'full_name': req.full_name, 'email': req.email, 'phone': req.phone,
        'headline': req.headline, 'bio': req.bio, 'nationality': req.nationality,
        'location_city': req.location_city, 'gender': req.gender,
        'linkedin_url': req.linkedin_url or '',
        'university_name': req.university_name,
        'university_location': req.university_location or '',
        'university_website': req.university_website or '',
        'university_description': req.university_description or '',
        'university_contact_email': req.university_contact_email or '',
        'university_contact_phone': req.university_contact_phone or '',
    }
    return render_template('university_apply.html', data=data, req=req, submitted=False)
