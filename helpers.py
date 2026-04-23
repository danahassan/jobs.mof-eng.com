import os
import json
import ssl
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from functools import wraps

from flask import current_app, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from models import (ApplicationHistory, ROLE_ADMIN, ROLE_SUPERVISOR,
                    ROLE_UNIVERSITY_COORD)


def allowed_file(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in current_app.config['ALLOWED_EXTENSIONS']


def save_cv(file):
    """Save uploaded CV, return (stored_filename, original_filename)."""
    original = secure_filename(file.filename)
    ext = original.rsplit('.', 1)[-1].lower()
    stored = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(current_app.config['UPLOAD_FOLDER'], stored)
    file.save(path)
    return stored, original


def allowed_image(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in {'jpg', 'jpeg', 'png', 'gif', 'webp'}


def save_company_image(file, folder_key='COMPANY_LOGO_FOLDER'):
    """Save uploaded company logo or cover image, return stored filename."""
    original = secure_filename(file.filename)
    if not allowed_image(original):
        raise ValueError('Invalid image type. Use JPG, PNG, GIF, or WebP.')
    ext = original.rsplit('.', 1)[-1].lower()
    stored = f"{uuid.uuid4().hex}.{ext}"
    folder = current_app.config[folder_key]
    os.makedirs(folder, exist_ok=True)
    file.save(os.path.join(folder, stored))
    return stored


def log_audit(action, target='', user_id=None):
    """Write an audit log entry — works with or without an authenticated session."""
    from models import db, AuditLog
    from flask import request, has_request_context
    try:
        from flask_login import current_user as _cu
        uid = user_id
        if uid is None and _cu.is_authenticated:
            uid = _cu.id
    except Exception:
        uid = user_id
    entry = AuditLog(
        user_id=uid,
        action=action,
        target=target,
        ip_address=request.remote_addr if has_request_context() else None,
    )
    db.session.add(entry)


def generate_reset_token(email):
    """Create a time-limited signed token for password reset."""
    from itsdangerous import URLSafeTimedSerializer
    from flask import current_app
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps(email, salt='pwd-reset-salt')


def verify_reset_token(token, expiration=3600):
    """Return the email address if token is valid, else None."""
    from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
    from flask import current_app
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = s.loads(token, salt='pwd-reset-salt', max_age=expiration)
    except (SignatureExpired, BadSignature):
        return None
    return email


def _site_settings_path():
    app = current_app._get_current_object()
    return os.path.join(app.instance_path, 'site_settings.json')


def get_site_settings():
    """Return the persisted site settings dict (empty dict if none saved yet)."""
    path = _site_settings_path()
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def save_site_settings(new_vals):
    """Persist new values into site_settings.json and update live app.config."""
    app = current_app._get_current_object()
    path = _site_settings_path()
    data = get_site_settings()
    data.update(new_vals)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    # Propagate to running app.config so effect is immediate
    for k, v in data.items():
        app.config[k] = v
    name = data.get('MAIL_FROM_NAME', 'MOF Jobs')
    addr = data.get('MAIL_FROM_ADDRESS', app.config.get('MAIL_USERNAME', ''))
    app.config['MAIL_DEFAULT_SENDER'] = f'{name} <{addr}>'


def send_email(to, subject, html_body, attachment_path=None, attachment_name=None):
    """Send HTML email via configured SMTP. Optionally attach a file."""
    cfg = current_app.config
    msg = MIMEMultipart('mixed')
    msg['Subject'] = subject
    msg['From']    = cfg['MAIL_DEFAULT_SENDER']
    msg['To']      = to
    msg.attach(MIMEText(html_body, 'html'))
    if attachment_path and os.path.isfile(attachment_path):
        with open(attachment_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        encoders.encode_base64(part)
        fname = attachment_name or os.path.basename(attachment_path)
        part.add_header('Content-Disposition', f'attachment; filename="{fname}"')
        msg.attach(part)
    context = ssl.create_default_context()
    with smtplib.SMTP(cfg['MAIL_SERVER'], cfg['MAIL_PORT']) as s:
        s.starttls(context=context)
        s.login(cfg['MAIL_USERNAME'], cfg['MAIL_PASSWORD'])
        s.sendmail(cfg['MAIL_USERNAME'], to, msg.as_string())
    try:
        from models import db as _db
        log_audit('email.send', f'{subject} → {to}')
        _db.session.commit()
    except Exception:
        pass


def log_history(application, changed_by, new_status=None, note=None, is_internal=False):
    """Record a status change or note in the audit trail."""
    from models import db
    entry = ApplicationHistory(
        application_id=application.id,
        changed_by_id=changed_by.id,
        old_status=application.status if new_status else None,
        new_status=new_status,
        note=note,
        is_internal=is_internal,
    )
    db.session.add(entry)


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != ROLE_ADMIN:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def supervisor_or_admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role not in (ROLE_ADMIN, ROLE_SUPERVISOR):
            abort(403)
        return f(*args, **kwargs)
    return decorated


def university_coordinator_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role not in (ROLE_ADMIN, ROLE_UNIVERSITY_COORD):
            abort(403)
        return f(*args, **kwargs)
    return decorated


def push_notification(user_id, message, link=None, icon='bi-bell-fill'):
    """Create an in-app notification and send Web Push if subscriptions exist."""
    from models import Notification, db
    n = Notification(user_id=user_id, message=message, link=link, icon=icon)
    db.session.add(n)
    _send_web_push(user_id, message, link)


def _send_web_push(user_id, message, link=None):
    """Fire-and-forget Web Push to all subscriptions for a user.
    Returns a list of per-subscription result dicts so callers (the test endpoint)
    can surface failures directly to the admin UI without relying on log files.
    """
    results = []
    try:
        from models import PushSubscription, db as _db
        try:
            from pywebpush import webpush, WebPushException
        except ImportError:
            current_app.logger.warning('[push] pywebpush not installed — pip install pywebpush')
            return [{'ok': False, 'error': 'pywebpush not installed on server'}]
        import json as _json
        cfg = current_app.config
        private_key = cfg.get('VAPID_PRIVATE_KEY', '')
        public_key  = cfg.get('VAPID_PUBLIC_KEY', '')
        if not private_key or not public_key:
            current_app.logger.warning(
                '[push] VAPID keys not configured (VAPID_PRIVATE_KEY / VAPID_PUBLIC_KEY env vars missing) — push disabled'
            )
            return [{'ok': False, 'error': 'VAPID keys missing on server'}]
        subs = PushSubscription.query.filter_by(user_id=user_id).all()
        if not subs:
            current_app.logger.info('[push] user %s has no push subscriptions', user_id)
            return [{'ok': False, 'error': 'no subscriptions stored for user'}]
        payload = _json.dumps({
            'title': 'MOF Jobs',
            'body':  message,
            'url':   link or '/notifications',
        })
        dead = []
        for sub in subs:
            try:
                webpush(
                    subscription_info={
                        'endpoint': sub.endpoint,
                        'keys': {'p256dh': sub.p256dh, 'auth': sub.auth},
                    },
                    data=payload,
                    vapid_private_key=private_key,
                    vapid_claims={'sub': cfg.get('VAPID_SUBJECT', 'mailto:admin@mof-eng.com')},
                    ttl=86400,
                )
                results.append({
                    'sub_id': sub.id,
                    'endpoint_host': (sub.endpoint or '').split('/')[2] if sub.endpoint else '',
                    'ok': True,
                })
            except WebPushException as exc:
                code = exc.response.status_code if exc.response is not None else None
                body = exc.response.text if exc.response is not None else str(exc)
                if code in (404, 410):
                    dead.append(sub.id)
                results.append({
                    'sub_id': sub.id,
                    'endpoint_host': (sub.endpoint or '').split('/')[2] if sub.endpoint else '',
                    'ok': False,
                    'http': code,
                    'error': body[:300],
                })
                current_app.logger.warning('[push] webpush failed sub=%s code=%s body=%s',
                                           sub.id, code, body)
            except Exception as e:
                results.append({
                    'sub_id': sub.id,
                    'endpoint_host': (sub.endpoint or '').split('/')[2] if sub.endpoint else '',
                    'ok': False,
                    'error': str(e)[:300],
                })
                current_app.logger.warning('[push] unexpected error sub=%s: %s', sub.id, e)
        if dead:
            PushSubscription.query.filter(PushSubscription.id.in_(dead)).delete(
                synchronize_session=False)
            _db.session.commit()
    except Exception as e:
        try:
            current_app.logger.exception('[push] fatal: %s', e)
        except Exception:
            pass
        results.append({'ok': False, 'error': 'fatal: ' + str(e)[:300]})
    return results
