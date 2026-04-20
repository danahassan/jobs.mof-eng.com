"""API auth endpoints."""
from flask import request, jsonify, session
from flask_login import login_user, logout_user, current_user
from models import db, User, ROLE_EMPLOYER, ROLE_USER
from . import api_bp


@api_bp.route('/auth/me')
def me():
    if not current_user.is_authenticated:
        return jsonify({'authenticated': False}), 401
    return jsonify(_user_dict(current_user))


@api_bp.route('/auth/login', methods=['POST'])
def login():
    data     = request.get_json(force=True)
    email    = (data.get('email') or '').strip().lower()
    password = data.get('password', '')

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401
    if not user.is_active:
        return jsonify({'error': 'Account disabled'}), 403

    if user.totp_enabled:
        return jsonify({'requires_2fa': True, 'user_id': user.id})

    login_user(user)
    return jsonify(_user_dict(user))


@api_bp.route('/auth/logout', methods=['POST'])
def logout():
    logout_user()
    return jsonify({'ok': True})


@api_bp.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json(force=True)
    email    = (data.get('email') or '').strip().lower()
    name     = (data.get('full_name') or '').strip()
    password = data.get('password', '')
    role     = ROLE_EMPLOYER if data.get('is_employer') else ROLE_USER

    if not email or not name or not password:
        return jsonify({'error': 'All fields required'}), 400
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    user = User(full_name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return jsonify(_user_dict(user)), 201


def _user_dict(u):
    return {
        'id':         u.id,
        'full_name':  u.full_name,
        'email':      u.email,
        'role':       u.role,
        'headline':   u.headline,
        'avatar_url': f'/static/uploads/avatars/{u.avatar_filename}' if u.avatar_filename else None,
        'profile_strength': u.profile_strength,
        'authenticated': True,
    }
