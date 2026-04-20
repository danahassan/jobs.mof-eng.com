"""routes/api/push.py — Web Push subscription management."""
from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from models import db, PushSubscription
from . import api_bp


@api_bp.route('/push/vapid-public-key')
@login_required
def vapid_public_key():
    return jsonify({'publicKey': current_app.config.get('VAPID_PUBLIC_KEY', '')})


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
