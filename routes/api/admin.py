"""API admin endpoints."""
from flask import jsonify, abort
from flask_login import login_required, current_user
from models import db, User, Position, Application, Company, ROLE_ADMIN, ALL_STATUSES
from sqlalchemy import func
from . import api_bp


@api_bp.route('/admin/stats')
@login_required
def admin_stats():
    if current_user.role != ROLE_ADMIN:
        abort(403)
    return jsonify({
        'users':     User.query.count(),
        'jobs':      Position.query.count(),
        'jobs_active': Position.query.filter_by(is_active=True).count(),
        'apps':      Application.query.count(),
        'companies': Company.query.count(),
        'hired':     Application.query.filter_by(status='Hired').count(),
        'status_dist': {s: Application.query.filter_by(status=s).count() for s in ALL_STATUSES},
        'role_dist': {
            r: User.query.filter_by(role=r).count()
            for r in ('user', 'employer', 'admin', 'supervisor')
        },
    })
