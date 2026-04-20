"""API applications + employer pipeline endpoints."""
from flask import request, jsonify, abort
from flask_login import login_required, current_user
from models import db, Application, Position, ALL_STATUSES, ROLE_ADMIN, ROLE_EMPLOYER
from . import api_bp


@api_bp.route('/applications')
@login_required
def my_applications():
    apps = Application.query.filter_by(applicant_id=current_user.id)\
               .order_by(Application.applied_at.desc()).all()
    return jsonify([_app_dict(a) for a in apps])


@api_bp.route('/applications/<int:app_id>/stage', methods=['PATCH'])
@login_required
def update_stage(app_id):
    if current_user.role not in (ROLE_ADMIN, ROLE_EMPLOYER):
        abort(403)
    data   = request.get_json(force=True)
    status = data.get('status')
    note   = data.get('note', '')
    if status not in ALL_STATUSES:
        return jsonify({'error': 'Invalid status'}), 400
    app = Application.query.get_or_404(app_id)
    from helpers import log_history, push_notification
    from flask import url_for
    log_history(app, status, note=note, actor=current_user)
    app.status = status
    db.session.commit()
    push_notification(app.applicant_id,
        f'Your application for "{app.position.title}" updated to {status}.',
        url_for('user.my_applications'), icon='bi-briefcase-fill')
    return jsonify({'ok': True, 'status': status})


def _app_dict(a):
    return {
        'id':         a.id,
        'status':     a.status,
        'applied_at': a.applied_at.isoformat(),
        'position': {
            'id': a.position_id,
            'title': a.position.title,
            'company': a.position.company.name if a.position.company else 'MOF Engineering',
        } if a.position else None,
    }
