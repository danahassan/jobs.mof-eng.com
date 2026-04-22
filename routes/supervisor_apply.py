"""
Public self-registration portal for prospective supervisors.
No login required. Accessible at /supervisor_apply
"""
import os
from uuid import uuid4
from datetime import datetime

from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, current_app, abort)

from models import db, SupervisorRequest, User, ROLE_ADMIN, COMPANY_SIZES
from helpers import send_email, push_notification, log_audit, save_company_image

supervisor_apply_bp = Blueprint('supervisor_apply', __name__)


def _notify_admins(req, base_url):
    """Send push + email to every active admin about a new/resubmitted request."""
    admins = User.query.filter_by(role=ROLE_ADMIN, is_active=True).all()
    detail_url = base_url + url_for('admin.supervisor_request_detail', req_id=req.id)
    for admin in admins:
        try:
            push_notification(
                admin.id,
                f'New supervisor application from {req.full_name} ({req.company_name})',
                url_for('admin.supervisor_request_detail', req_id=req.id),
            )
            html = render_template(
                'emails/sup_request_admin_notify.html',
                req=req,
                detail_url=detail_url,
            )
            send_email(
                admin.email,
                f'New Supervisor Application — {req.full_name}',
                html,
            )
        except Exception as exc:
            current_app.logger.warning(f'Admin notification failed for admin {admin.id}: {exc}')
    try:
        db.session.commit()
    except Exception:
        pass


def _save_logo(file):
    """Save uploaded company logo via helpers, return filename or None."""
    if not file or not file.filename:
        return None
    try:
        return save_company_image(file)
    except ValueError as exc:
        flash(str(exc), 'warning')
        return None


def _parse_int(s):
    try:
        return int(str(s).strip()) if s and str(s).strip() else None
    except (ValueError, TypeError):
        return None


def _collect_form():
    """Return a dict of all form values (used for both create and update)."""
    f = request.form
    return {
        'full_name':             f.get('full_name', '').strip(),
        'email':                 f.get('email', '').strip().lower(),
        'phone':                 f.get('phone', '').strip(),
        'password':              f.get('password', ''),
        'confirm_password':      f.get('confirm_password', ''),
        'headline':              f.get('headline', '').strip(),
        'bio':                   f.get('bio', '').strip(),
        'nationality':           f.get('nationality', '').strip(),
        'location_city':         f.get('location_city', '').strip(),
        'gender':                f.get('gender', '').strip(),
        'linkedin_url':          f.get('linkedin_url', '').strip(),
        'company_name':          f.get('company_name', '').strip(),
        'company_industry':      f.get('company_industry', '').strip(),
        'company_size':          f.get('company_size', '').strip(),
        'company_website':       f.get('company_website', '').strip(),
        'company_description':   f.get('company_description', '').strip(),
        'company_location':      f.get('company_location', '').strip(),
        'company_founded_year':  _parse_int(f.get('company_founded_year', '')),
        'company_contact_email': f.get('company_contact_email', '').strip().lower(),
        'company_contact_phone': f.get('company_contact_phone', '').strip(),
    }


def _validate(data, require_password=True):
    """Return list of error strings (empty == valid)."""
    errors = []
    required_fields = [
        ('full_name', 'Full name'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('headline', 'Headline'),
        ('location_city', 'City / Location'),
        ('bio', 'Bio'),
        ('company_name', 'Company name'),
        ('company_industry', 'Company industry'),
        ('company_size', 'Company size'),
        ('company_location', 'Company location'),
        ('company_contact_email', 'Company contact email'),
    ]
    for field, label in required_fields:
        if not data.get(field):
            errors.append(f'{label} is required.')
    if require_password:
        if not data.get('password'):
            errors.append('Password is required.')
        elif len(data['password']) < 8:
            errors.append('Password must be at least 8 characters.')
        elif data['password'] != data['confirm_password']:
            errors.append('Passwords do not match.')
    return errors


# ─── NEW APPLICATION ──────────────────────────────────────────────────────────

@supervisor_apply_bp.route('/supervisor_apply', methods=['GET', 'POST'])
def apply():
    if request.method == 'POST':
        data = _collect_form()
        errors = _validate(data, require_password=True)
        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('supervisor_apply.html',
                                   data=data, COMPANY_SIZES=COMPANY_SIZES)

        req = SupervisorRequest(
            token=uuid4().hex,
            status='pending',
            full_name=data['full_name'],
            email=data['email'],
            phone=data['phone'],
            headline=data['headline'],
            bio=data['bio'],
            nationality=data['nationality'],
            location_city=data['location_city'],
            gender=data['gender'],
            linkedin_url=data['linkedin_url'],
            company_name=data['company_name'],
            company_industry=data['company_industry'],
            company_size=data['company_size'],
            company_website=data['company_website'],
            company_description=data['company_description'],
            company_location=data['company_location'],
            company_founded_year=data['company_founded_year'],
            company_contact_email=data['company_contact_email'],
            company_contact_phone=data['company_contact_phone'],
        )
        req.set_password(data['password'])

        logo = request.files.get('company_logo')
        req.company_logo_filename = _save_logo(logo)

        db.session.add(req)
        db.session.commit()

        log_audit('supervisor_request.create', f'{req.full_name} <{req.email}>')
        db.session.commit()

        # Build absolute base URL for email links
        site_url = current_app.config.get('SITE_URL', request.host_url.rstrip('/'))
        _notify_admins(req, site_url)

        return redirect(url_for('supervisor_apply.apply', submitted=1))

    submitted = request.args.get('submitted') == '1'
    return render_template('supervisor_apply.html',
                           data={}, COMPANY_SIZES=COMPANY_SIZES,
                           submitted=submitted)


# ─── EDIT / RESUBMIT ─────────────────────────────────────────────────────────

@supervisor_apply_bp.route('/supervisor_apply/<token>', methods=['GET', 'POST'])
def apply_edit(token):
    req = SupervisorRequest.query.filter_by(token=token).first_or_404()
    if req.status != 'rejected':
        abort(403)

    if request.method == 'POST':
        data = _collect_form()
        # Password is optional on resubmit — only validate if provided
        require_pw = bool(data.get('password'))
        errors = _validate(data, require_password=require_pw)
        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('supervisor_apply.html',
                                   data=data, req=req,
                                   COMPANY_SIZES=COMPANY_SIZES)

        req.full_name             = data['full_name']
        req.email                 = data['email']
        req.phone                 = data['phone']
        req.headline              = data['headline']
        req.bio                   = data['bio']
        req.nationality           = data['nationality']
        req.location_city         = data['location_city']
        req.gender                = data['gender']
        req.linkedin_url          = data['linkedin_url']
        req.company_name          = data['company_name']
        req.company_industry      = data['company_industry']
        req.company_size          = data['company_size']
        req.company_website       = data['company_website']
        req.company_description   = data['company_description']
        req.company_location      = data['company_location']
        req.company_founded_year  = data['company_founded_year']
        req.company_contact_email = data['company_contact_email']
        req.company_contact_phone = data['company_contact_phone']
        req.updated_at            = datetime.utcnow()
        req.status                = 'pending'
        req.rejection_reason      = None

        if require_pw:
            req.set_password(data['password'])

        logo = request.files.get('company_logo')
        new_logo = _save_logo(logo)
        if new_logo:
            req.company_logo_filename = new_logo

        db.session.commit()

        log_audit('supervisor_request.resubmit', f'{req.full_name} <{req.email}>')
        db.session.commit()

        site_url = current_app.config.get('SITE_URL', request.host_url.rstrip('/'))
        _notify_admins(req, site_url)

        flash('Your application has been resubmitted! We will review it shortly.', 'success')
        return redirect(url_for('supervisor_apply.apply_edit', token=token))

    # Pre-fill form data from existing record
    data = {
        'full_name':             req.full_name,
        'email':                 req.email,
        'phone':                 req.phone,
        'headline':              req.headline or '',
        'bio':                   req.bio or '',
        'nationality':           req.nationality or '',
        'location_city':         req.location_city or '',
        'gender':                req.gender or '',
        'linkedin_url':          req.linkedin_url or '',
        'company_name':          req.company_name,
        'company_industry':      req.company_industry or '',
        'company_size':          req.company_size or '',
        'company_website':       req.company_website or '',
        'company_description':   req.company_description or '',
        'company_location':      req.company_location or '',
        'company_founded_year':  req.company_founded_year or '',
        'company_contact_email': req.company_contact_email or '',
        'company_contact_phone': req.company_contact_phone or '',
    }
    return render_template('supervisor_apply.html',
                           data=data, req=req,
                           COMPANY_SIZES=COMPANY_SIZES)
