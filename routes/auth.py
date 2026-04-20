import os
import uuid
from datetime import datetime, date
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, session, abort, current_app)
from flask_login import login_user, logout_user, login_required, current_user
from models import (db, User, UserSkill, UserExperience, UserEducation,
                    UserLanguage, UserCertification, UserPortfolioItem,
                    Position, ROLE_USER, ROLE_EMPLOYER, LANG_LEVELS)
from sqlalchemy import or_
from helpers import (log_audit, send_email, generate_reset_token,
                     verify_reset_token)
from werkzeug.utils import secure_filename

auth_bp = Blueprint('auth', __name__)

AVATAR_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
AVATAR_DIR = os.path.join('static', 'uploads', 'avatars')


def _safe_next(next_page):
    """Allow only same-site relative redirects."""
    from urllib.parse import urlparse
    if not next_page:
        return None
    parsed = urlparse(next_page)
    if parsed.scheme or parsed.netloc:
        return None
    return next_page


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    next_page = _safe_next(request.values.get('next') or request.args.get('next'))
    if current_user.is_authenticated:
        return redirect(next_page or url_for('dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('email', '').strip()
        password   = request.form.get('password', '')
        remember   = bool(request.form.get('remember'))

        # Allow login by email OR phone number
        user = User.query.filter(
            or_(User.email == identifier.lower(),
                User.phone == identifier)
        ).first()
        if user and user.is_active and user.check_password(password):
            if user.totp_enabled:
                session['2fa_user_id'] = user.id
                session['2fa_next'] = next_page
                return redirect(url_for('auth.verify_2fa'))
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=remember)
            return redirect(next_page or url_for('dashboard'))

        flash('Invalid email/phone or password.', 'danger')

    positions = Position.query.filter_by(is_active=True).order_by(Position.created_at.desc()).all()
    return render_template('auth/login.html', positions=positions)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Public registration — creates applicant accounts only."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email     = request.form.get('email', '').strip().lower()
        phone     = request.form.get('phone', '').strip()
        password  = request.form.get('password', '')
        confirm   = request.form.get('confirm_password', '')

        errors = []
        if not full_name:
            errors.append('Full name is required.')
        if not email or '@' not in email:
            errors.append('Valid email is required.')
        if User.query.filter_by(email=email).first():
            errors.append('An account with this email already exists.')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if password != confirm:
            errors.append('Passwords do not match.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('auth/register.html',
                                   full_name=full_name, email=email, phone=phone)

        is_employer = request.form.get('is_employer') == '1'
        role = ROLE_EMPLOYER if is_employer else ROLE_USER
        user = User(full_name=full_name, email=email, phone=phone, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # get user.id before commit
        log_audit('auth.register', f'{full_name} <{email}>', user_id=user.id)
        db.session.commit()

        # Send welcome email
        try:
            html = render_template('emails/welcome_user.html', user=user)
            send_email(user.email, 'Welcome to MOF Jobs — Your Account is Ready', html)
        except Exception as ex:
            current_app.logger.warning(f'Welcome email failed: {ex}')

        login_user(user)
        flash(f'Welcome, {full_name}! Your account has been created.', 'success')
        if is_employer:
            return redirect(url_for('employer.company_setup'))
        return redirect(url_for('user.browse'))

    return render_template('auth/register.html')


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    tab = request.args.get('tab', 'info')
    mode = request.args.get('mode', 'view')
    if request.method == 'POST':
        current_user.full_name    = request.form.get('full_name', '').strip()
        current_user.headline     = request.form.get('headline', '').strip()
        current_user.phone        = request.form.get('phone', '').strip()
        current_user.bio          = request.form.get('bio', '').strip()
        current_user.location_city= request.form.get('location_city', '').strip()
        current_user.nationality  = request.form.get('nationality', '').strip()
        current_user.gender       = request.form.get('gender', '').strip()
        current_user.resume_headline = request.form.get('resume_headline', '').strip()
        current_user.linkedin_url = request.form.get('linkedin_url', '').strip()
        current_user.github_url   = request.form.get('github_url', '').strip()
        current_user.portfolio_url= request.form.get('portfolio_url', '').strip()
        dob_str = request.form.get('date_of_birth', '').strip()
        if dob_str:
            try:
                current_user.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        else:
            current_user.date_of_birth = None

        f = request.files.get('photo')
        if f and f.filename:
            original = secure_filename(f.filename)
            ext = original.rsplit('.', 1)[-1].lower() if '.' in original else ''
            if ext in AVATAR_EXTENSIONS:
                folder = os.path.join(current_app.root_path, AVATAR_DIR)
                os.makedirs(folder, exist_ok=True)
                fname = f'avatar_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}'
                f.save(os.path.join(folder, fname))
                if current_user.avatar_filename:
                    old_path = os.path.join(folder, current_user.avatar_filename)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                current_user.avatar_filename = fname
            else:
                flash('Photo not updated: allowed formats are PNG, JPG, WEBP, GIF.', 'warning')
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('auth.profile', mode='edit', tab='info'))
    u = current_user
    skills_list = u.skills.order_by(UserSkill.created_at).all()
    exps        = u.experiences.order_by(UserExperience.start_date.desc()).all()
    edus        = u.educations.order_by(UserEducation.start_year.desc()).all()
    langs       = u.languages.order_by(UserLanguage.created_at).all()
    certs       = u.certifications.order_by(UserCertification.created_at).all()
    portfolio   = u.portfolio_items.order_by(UserPortfolioItem.created_at).all()
    return render_template('auth/profile.html', tab=tab, mode=mode,
                           skills_list=skills_list, exps=exps, edus=edus,
                           langs=langs, certs=certs, portfolio=portfolio,
                           lang_levels=LANG_LEVELS)


# ─── SKILLS ───────────────────────────────────────────────────────────────────

@auth_bp.route('/profile/skill/add', methods=['POST'])
@login_required
def skill_add():
    name = request.form.get('name', '').strip()
    proficiency = request.form.get('proficiency', 'intermediate')
    if name:
        db.session.add(UserSkill(user_id=current_user.id, name=name, proficiency=proficiency))
        db.session.commit()
        flash('Skill added.', 'success')
    return redirect(url_for('auth.profile', mode='edit', tab='skills'))


@auth_bp.route('/profile/skill/<int:skill_id>/delete', methods=['POST'])
@login_required
def skill_delete(skill_id):
    s = db.get_or_404(UserSkill, skill_id)
    if s.user_id != current_user.id:
        abort(403)
    db.session.delete(s)
    db.session.commit()
    return redirect(url_for('auth.profile', mode='edit', tab='skills'))


# ─── EXPERIENCE ───────────────────────────────────────────────────────────────

@auth_bp.route('/profile/experience/add', methods=['POST'])
@login_required
def experience_add():
    title = request.form.get('title', '').strip()
    if title:
        start = request.form.get('start_date', '')
        end   = request.form.get('end_date', '')
        db.session.add(UserExperience(
            user_id=current_user.id,
            title=title,
            company=request.form.get('company', '').strip(),
            start_date=date.fromisoformat(start) if start else None,
            end_date=date.fromisoformat(end) if end else None,
            description=request.form.get('description', '').strip(),
        ))
        db.session.commit()
        flash('Experience added.', 'success')
    return redirect(url_for('auth.profile', mode='edit', tab='experience'))


@auth_bp.route('/profile/experience/<int:exp_id>/delete', methods=['POST'])
@login_required
def experience_delete(exp_id):
    exp = db.get_or_404(UserExperience, exp_id)
    if exp.user_id != current_user.id:
        abort(403)
    db.session.delete(exp)
    db.session.commit()
    return redirect(url_for('auth.profile', mode='edit', tab='experience'))


# ─── EDUCATION ────────────────────────────────────────────────────────────────

@auth_bp.route('/profile/education/add', methods=['POST'])
@login_required
def education_add():
    institution = request.form.get('institution', '').strip()
    if institution:
        db.session.add(UserEducation(
            user_id=current_user.id,
            institution=institution,
            degree=request.form.get('degree', '').strip(),
            field=request.form.get('field', '').strip(),
            start_year=request.form.get('start_year', type=int),
            end_year=request.form.get('end_year', type=int),
        ))
        db.session.commit()
        flash('Education added.', 'success')
    return redirect(url_for('auth.profile', mode='edit', tab='experience'))


@auth_bp.route('/profile/education/<int:edu_id>/delete', methods=['POST'])
@login_required
def education_delete(edu_id):
    edu = db.get_or_404(UserEducation, edu_id)
    if edu.user_id != current_user.id:
        abort(403)
    db.session.delete(edu)
    db.session.commit()
    return redirect(url_for('auth.profile', mode='edit', tab='experience'))


# ─── PASSWORD ─────────────────────────────────────────────────────────────────

@auth_bp.route('/profile/password', methods=['POST'])
@login_required
def change_password():
    current_pw  = request.form.get('current_password', '')
    new_pw      = request.form.get('new_password', '')
    confirm_pw  = request.form.get('confirm_new_password', '')
    if not current_user.check_password(current_pw):
        flash('Current password is incorrect.', 'danger')
    elif len(new_pw) < 8:
        flash('New password must be at least 8 characters.', 'danger')
    elif new_pw != confirm_pw:
        flash('Passwords do not match.', 'danger')
    else:
        current_user.set_password(new_pw)
        log_audit('auth.password_change', current_user.email)
        db.session.commit()
        flash('Password changed successfully.', 'success')
    return redirect(url_for('auth.profile', mode='edit', tab='security'))


# ─── TWO-FACTOR AUTH ──────────────────────────────────────────────────────────

@auth_bp.route('/setup-2fa', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    try:
        import pyotp, qrcode, io, base64 as b64
    except ImportError:
        flash('2FA packages not installed. Run: pip install pyotp qrcode[pil]', 'danger')
        return redirect(url_for('auth.profile', mode='edit', tab='security'))

    if request.method == 'POST':
        code   = request.form.get('code', '').strip()
        secret = session.get('totp_setup_secret')
        if not secret:
            flash('Session expired. Please try again.', 'danger')
            return redirect(url_for('auth.setup_2fa'))
        totp = pyotp.TOTP(secret)
        if totp.verify(code, valid_window=1):
            current_user.totp_secret  = secret
            current_user.totp_enabled = True
            db.session.commit()
            session.pop('totp_setup_secret', None)
            flash('Two-factor authentication enabled!', 'success')
            return redirect(url_for('auth.profile', mode='edit', tab='security'))
        flash('Invalid code. Please try again.', 'danger')

    secret = pyotp.random_base32()
    session['totp_setup_secret'] = secret
    totp = pyotp.TOTP(secret)
    uri  = totp.provisioning_uri(name=current_user.email, issuer_name='MOF Jobs')
    qr   = qrcode.QRCode(version=1, box_size=8, border=4)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_b64 = b64.b64encode(buf.getvalue()).decode()
    return render_template('auth/setup_2fa.html', qr_b64=qr_b64, secret=secret)


@auth_bp.route('/disable-2fa', methods=['POST'])
@login_required
def disable_2fa():
    if not current_user.check_password(request.form.get('password', '')):
        flash('Incorrect password.', 'danger')
    else:
        current_user.totp_enabled = False
        current_user.totp_secret  = None
        db.session.commit()
        flash('Two-factor authentication disabled.', 'success')
    return redirect(url_for('auth.profile', mode='edit', tab='security'))


@auth_bp.route('/verify-2fa', methods=['GET', 'POST'])
def verify_2fa():
    user_id = session.get('2fa_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    user = db.session.get(User, user_id)
    if not user:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        try:
            import pyotp
        except ImportError:
            flash('2FA packages not installed.', 'danger')
            return redirect(url_for('auth.login'))
        code = request.form.get('code', '').strip()
        totp = pyotp.TOTP(user.totp_secret)
        if totp.verify(code, valid_window=1):
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user)
            next_page = _safe_next(session.pop('2fa_next', None))
            session.pop('2fa_user_id', None)
            return redirect(next_page or url_for('dashboard'))
        flash('Invalid code. Please try again.', 'danger')

    return render_template('auth/verify_2fa.html', email=user.email)


# ─── FORGOT PASSWORD ──────────────────────────────────────────────────────────

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user  = User.query.filter_by(email=email, is_active=True).first()
        # Always show the same message to prevent email enumeration
        if user:
            token = generate_reset_token(user.email)
            reset_url = current_app.config['SITE_URL'] + url_for('auth.reset_password', token=token)
            try:
                html = render_template('emails/forgot_password.html',
                                       user=user, reset_url=reset_url)
                send_email(user.email, 'Reset Your MOF Jobs Password', html)
            except Exception as ex:
                current_app.logger.warning(f'Forgot-password email failed: {ex}')
            log_audit('auth.forgot_password', email, user_id=user.id)
            db.session.commit()
        flash('If that email is registered, a reset link has been sent.', 'info')
        return redirect(url_for('auth.forgot_password'))
    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    email = verify_reset_token(token)
    if not email:
        flash('This reset link is invalid or has expired. Please request a new one.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    user = User.query.filter_by(email=email, is_active=True).first()
    if not user:
        flash('Account not found.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    if request.method == 'POST':
        new_pw  = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if len(new_pw) < 8:
            flash('Password must be at least 8 characters.', 'danger')
        elif new_pw != confirm:
            flash('Passwords do not match.', 'danger')
        else:
            user.set_password(new_pw)
            log_audit('auth.reset_password', user.email, user_id=user.id)
            db.session.commit()
            try:
                html = render_template('emails/password_reset_done.html', user=user)
                send_email(user.email, 'Your MOF Jobs Password Has Been Reset', html)
            except Exception as ex:
                current_app.logger.warning(f'Reset-done email failed: {ex}')
            flash('Your password has been reset successfully. Please log in.', 'success')
            return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', token=token)
