"""routes/api/push.py — Web Push subscription management."""
from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from models import db, PushSubscription
from . import api_bp


@api_bp.route('/push/vapid-public-key')
@login_required
def vapid_public_key():
    return jsonify({'publicKey': current_app.config.get('VAPID_PUBLIC_KEY', '')})


@api_bp.route('/push/status')
@login_required
def push_status():
    """Quick diagnostic so admins can see why push isn't reaching them."""
    cfg = current_app.config
    has_keys = bool(cfg.get('VAPID_PUBLIC_KEY')) and bool(cfg.get('VAPID_PRIVATE_KEY'))
    try:
        import pywebpush  # noqa: F401
        lib_ok = True
    except ImportError:
        lib_ok = False
    # Try loading the private key the same way the sender does
    private_key_loadable = False
    private_key_error    = None
    if has_keys:
        try:
            raw = (cfg.get('VAPID_PRIVATE_KEY', '') or '').strip()
            if '-----BEGIN' in raw:
                from py_vapid import Vapid01
                Vapid01.from_string(private_key=raw.replace('\\n', '\n'))
            else:
                import base64 as _b64
                from cryptography.hazmat.primitives.asymmetric import ec
                b = raw + '=' * ((4 - len(raw) % 4) % 4)
                priv_bytes = _b64.urlsafe_b64decode(b.encode('ascii'))
                if len(priv_bytes) != 32:
                    raise ValueError('expected 32-byte EC scalar, got %d' % len(priv_bytes))
                ec.derive_private_key(int.from_bytes(priv_bytes, 'big'), ec.SECP256R1())
            private_key_loadable = True
        except Exception as e:
            private_key_error = str(e)[:200]
    subs = PushSubscription.query.filter_by(user_id=current_user.id).all()
    return jsonify({
        'vapid_configured':       has_keys,
        'vapid_private_loadable': private_key_loadable,
        'vapid_private_error':    private_key_error,
        'pywebpush_installed':    lib_ok,
        'subscriptions':          len(subs),
        'subject':                cfg.get('VAPID_SUBJECT', ''),
        'public_key_preview':     (cfg.get('VAPID_PUBLIC_KEY', '') or '')[:16] + '…' if has_keys else '',
    })


@api_bp.route('/push/clear-mine', methods=['POST'])
@login_required
def push_clear_mine():
    """Delete all of my stored push subscriptions (after rotating VAPID keys)."""
    n = PushSubscription.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({'ok': True, 'deleted': n})


@api_bp.route('/push/test', methods=['POST'])
@login_required
def push_test():
    """Send a test push to the current user's subscriptions and return per-sub results."""
    from helpers import _send_web_push
    results = _send_web_push(current_user.id, 'Test notification from MOF Jobs ✓',
                             link='/notifications')
    ok_count = sum(1 for r in (results or []) if r.get('ok'))
    return jsonify({
        'ok': ok_count > 0,
        'sent_to': ok_count,
        'results': results or [],
    })


@api_bp.route('/push/subscribe', methods=['POST'])
@login_required
def push_subscribe():
    data   = request.get_json(force=True) or {}
    endpoint = data.get('endpoint')
    keys     = data.get('keys', {})
    p256dh   = keys.get('p256dh')
    auth     = keys.get('auth')
    if not (endpoint and p256dh and auth):
        return jsonify({'error': 'Missing fields'}), 400

    sub = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if sub:
        sub.user_id = current_user.id
        sub.p256dh  = p256dh
        sub.auth    = auth
    else:
        sub = PushSubscription(
            user_id=current_user.id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
        )
        db.session.add(sub)
    db.session.commit()
    return jsonify({'ok': True}), 201


@api_bp.route('/push/unsubscribe', methods=['POST'])
@login_required
def push_unsubscribe():
    data     = request.get_json(force=True) or {}
    endpoint = data.get('endpoint')
    if endpoint:
        PushSubscription.query.filter_by(
            endpoint=endpoint, user_id=current_user.id).delete()
        db.session.commit()
    return jsonify({'ok': True})
