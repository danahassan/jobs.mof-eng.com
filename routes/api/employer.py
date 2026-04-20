"""API employer endpoints."""
from flask import request, jsonify, abort
from flask_login import login_required, current_user
from models import db, Position, Application, Company, ROLE_EMPLOYER, ROLE_ADMIN, ALL_STATUSES
from . import api_bp


def _require_employer():
    if not current_user.is_authenticated or current_user.role not in (ROLE_EMPLOYER, ROLE_ADMIN):
        abort(403)


@api_bp.route('/employer/jobs')
@login_required
def employer_jobs():
    _require_employer()
    from routes.employer import get_employer_company
    company = get_employer_company()
    if not company:
        return jsonify([])
    jobs = Position.query.filter_by(company_id=company.id)\
               .order_by(Position.created_at.desc()).all()
    return jsonify([{
        'id': j.id, 'title': j.title, 'type': j.type,
        'is_active': j.is_active, 'views_count': j.views_count or 0,
        'application_count': j.application_count,
        'created_at': j.created_at.isoformat(),
    } for j in jobs])


@api_bp.route('/employer/pipeline')
@login_required
def employer_pipeline():
    _require_employer()
    from routes.employer import get_employer_company
    company = get_employer_company()
    if not company:
        return jsonify({})
    funnel = {s: Application.query.join(Position).filter(
        Position.company_id == company.id, Application.status == s
    ).count() for s in ALL_STATUSES}
    return jsonify(funnel)
