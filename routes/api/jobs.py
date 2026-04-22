"""API jobs endpoints."""
from flask import request, jsonify
from flask_login import current_user
from sqlalchemy import or_
from models import db, Position, Company, SavedJob, EXPERIENCE_LEVELS, JOB_TYPES, ROLE_USER
from . import api_bp


def _job_dict(j, saved_ids=None):
    return {
        'id':              j.id,
        'title':           j.title,
        'department':      j.department,
        'location':        j.location,
        'type':            j.type,
        'experience_level':j.experience_level,
        'is_remote':       j.is_remote,
        'salary_min':      j.salary_min,
        'salary_max':      j.salary_max,
        'salary_range':    j.salary_range,
        'skills_required': j.skills_required,
        'description':     j.description,
        'requirements':    j.requirements,
        'benefits':        j.benefits,
        'views_count':     j.views_count,
        'closes_at':       j.closes_at.isoformat() if j.closes_at else None,
        'created_at':      j.created_at.isoformat(),
        'company': {
            'id':   j.company.id,
            'name': j.company.name,
            'slug': j.company.slug,
            'logo': f'/static/uploads/company/{j.company.logo_filename}' if j.company and j.company.logo_filename else None,
        } if j.company else None,
        'is_saved':        (j.id in saved_ids) if saved_ids is not None else False,
    }


@api_bp.route('/jobs')
def jobs_list():
    q          = request.args.get('q', '').strip()
    dept       = request.args.get('dept', '').strip()
    jtype      = request.args.get('type', '').strip()
    location   = request.args.get('loc', '').strip()
    remote     = request.args.get('remote', '')
    salary_min = request.args.get('salary_min', type=int)
    exp        = request.args.get('exp', '').strip()
    page       = request.args.get('page', 1, type=int)
    per_page   = min(request.args.get('per_page', 20, type=int), 50)

    query = Position.query.filter_by(is_active=True)
    # Internships only visible to authenticated non-ROLE_USER accounts
    if not current_user.is_authenticated or current_user.role == ROLE_USER:
        query = query.filter(Position.type != 'Internship')
    if q:
        query = query.filter(or_(
            Position.title.ilike(f'%{q}%'),
            Position.description.ilike(f'%{q}%'),
            Position.skills_required.ilike(f'%{q}%'),
        ))
    if dept:    query = query.filter(Position.department.ilike(f'%{dept}%'))
    if jtype:   query = query.filter_by(type=jtype)
    if location:query = query.filter(Position.location.ilike(f'%{location}%'))
    if remote == '1': query = query.filter_by(is_remote=True)
    if salary_min: query = query.filter(Position.salary_min >= salary_min)
    if exp:     query = query.filter_by(experience_level=exp)

    paginated = query.order_by(Position.created_at.desc()).paginate(
        page=page, per_page=per_page)

    saved_ids = set()
    if current_user.is_authenticated:
        saved_ids = {sj.position_id for sj in
                     SavedJob.query.filter_by(user_id=current_user.id).all()}

    return jsonify({
        'jobs':    [_job_dict(j, saved_ids) for j in paginated.items],
        'total':   paginated.total,
        'pages':   paginated.pages,
        'page':    page,
        'filters': {'types': JOB_TYPES, 'exp_levels': EXPERIENCE_LEVELS},
    })


@api_bp.route('/jobs/<int:job_id>')
def job_detail(job_id):
    j = Position.query.get_or_404(job_id)
    if not j.is_active:
        return jsonify({'error': 'Not found'}), 404
    if j.type == 'Internship' and (not current_user.is_authenticated or current_user.role == ROLE_USER):
        return jsonify({'error': 'Not found'}), 404
    j.views_count = (j.views_count or 0) + 1
    db.session.commit()
    saved_ids = set()
    if current_user.is_authenticated:
        from models import Application
        applied = Application.query.filter_by(
            applicant_id=current_user.id, position_id=j.id).first() is not None
        saved = SavedJob.query.filter_by(
            user_id=current_user.id, position_id=j.id).first() is not None
        return jsonify({**_job_dict(j), 'already_applied': applied, 'is_saved': saved})
    return jsonify(_job_dict(j))


@api_bp.route('/jobs/<int:job_id>/save', methods=['POST'])
def save_job(job_id):
    if not current_user.is_authenticated:
        return jsonify({'error': 'Login required'}), 401
    Position.query.get_or_404(job_id)
    existing = SavedJob.query.filter_by(
        user_id=current_user.id, position_id=job_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'saved': False})
    db.session.add(SavedJob(user_id=current_user.id, position_id=job_id))
    db.session.commit()
    return jsonify({'saved': True})
