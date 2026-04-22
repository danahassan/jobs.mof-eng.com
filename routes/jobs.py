"""routes/jobs.py — Public job listing + advanced search (replaces /portal/browse)."""
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, abort
from flask_login import current_user
from sqlalchemy import or_

from models import (db, Position, Company, SavedJob, UserSkill, Application,
                    EXPERIENCE_LEVELS, JOB_TYPES,
                    ROLE_USER)

jobs_bp = Blueprint('jobs', __name__)


@jobs_bp.route('/')
def listing():
    """Public advanced job listing with filters."""
    q          = request.args.get('q', '').strip()
    dept       = request.args.get('dept', '').strip()
    jtype      = request.args.get('type', '').strip()
    exp        = request.args.get('exp', '').strip()
    location   = request.args.get('loc', '').strip()
    remote     = request.args.get('remote', '')
    salary_min = request.args.get('salary_min', type=int)
    company_id = request.args.get('company', type=int)
    sort       = request.args.get('sort', 'newest')
    page       = request.args.get('page', 1, type=int)

    now = datetime.utcnow()
    query = Position.query.filter_by(is_active=True).filter(
        or_(Position.closes_at.is_(None), Position.closes_at >= now))

    # Internships are only visible to authenticated non-ROLE_USER accounts
    if not current_user.is_authenticated or current_user.role == ROLE_USER:
        query = query.filter(Position.type != 'Internship')

    if q:
        query = query.filter(or_(
            Position.title.ilike(f'%{q}%'),
            Position.description.ilike(f'%{q}%'),
            Position.skills_required.ilike(f'%{q}%'),
        ))
    if dept:
        query = query.filter(Position.department.ilike(f'%{dept}%'))
    if jtype:
        query = query.filter_by(type=jtype)
    if exp:
        query = query.filter_by(experience_level=exp)
    if location:
        query = query.filter(Position.location.ilike(f'%{location}%'))
    if remote == '1':
        query = query.filter_by(is_remote=True)
    if salary_min:
        query = query.filter(Position.salary_min >= salary_min)
    if company_id:
        query = query.filter_by(company_id=company_id)

    if sort == 'oldest':
        query = query.order_by(Position.created_at.asc())
    elif sort == 'salary_high':
        query = query.order_by(Position.salary_max.desc().nullslast())
    elif sort == 'salary_low':
        query = query.order_by(Position.salary_min.asc().nullslast())
    else:
        query = query.order_by(Position.created_at.desc())

    positions = query.paginate(page=page, per_page=20)

    # Filter bar options
    depts = [d[0] for d in db.session.query(Position.department)
             .filter_by(is_active=True).distinct().all() if d[0]]
    companies = Company.query.filter_by(is_active=True).order_by(Company.name).all()

    saved_ids = set()
    if current_user.is_authenticated:
        saved_ids = {sj.position_id for sj in
                     SavedJob.query.filter_by(user_id=current_user.id).all()}

    # Smart recommendations (skills match)
    recommended = []
    if current_user.is_authenticated and not q:
        my_skills = {s.name.lower() for s in
                     UserSkill.query.filter_by(user_id=current_user.id).all()}
        if my_skills:
            all_jobs = Position.query.filter_by(is_active=True).limit(100).all()
            def skill_score(pos):
                if not pos.skills_required:
                    return 0
                req = set(s.strip().lower() for s in pos.skills_required.split(','))
                return len(my_skills & req)
            recommended = sorted(
                [p for p in all_jobs if skill_score(p) > 0],
                key=skill_score, reverse=True
            )[:5]

    # KPI counts (always unfiltered)
    kpi_remote   = Position.query.filter_by(is_active=True, is_remote=True).count()
    kpi_apps_7d  = Application.query.filter(
        Application.applied_at >= db.func.date('now', '-7 days')).count()

    return render_template('jobs/listing.html',
        positions=positions, depts=depts, types=JOB_TYPES,
        exp_levels=EXPERIENCE_LEVELS, companies=companies,
        saved_ids=saved_ids, recommended=recommended,
        q=q, dept=dept, jtype=jtype, exp=exp, location=location,
        remote=remote, salary_min=salary_min, sort=sort,
        kpi_remote=kpi_remote, kpi_apps_7d=kpi_apps_7d)


@jobs_bp.route('/<int:job_id>')
def detail(job_id):
    job = Position.query.get_or_404(job_id)
    if not job.is_active:
        abort(404)

    # Internships hidden from unauthenticated visitors and regular users
    if job.type == 'Internship':
        if not current_user.is_authenticated or current_user.role == ROLE_USER:
            abort(404)

    # Track view
    job.views_count = (job.views_count or 0) + 1
    db.session.commit()

    saved = False
    already_applied = False
    if current_user.is_authenticated:
        saved = SavedJob.query.filter_by(
            user_id=current_user.id, position_id=job.id).first() is not None
        from models import Application
        already_applied = Application.query.filter_by(
            applicant_id=current_user.id, position_id=job.id).first() is not None

    # Related / similar jobs
    related = Position.query.filter(
        Position.is_active == True,
        Position.id != job.id,
        or_(
            Position.department == job.department,
            Position.type == job.type,
        )
    ).limit(4).all()

    return render_template('jobs/detail.html',
        job=job, saved=saved, already_applied=already_applied, related=related)


@jobs_bp.route('/api/search')
def api_search():
    """JSON endpoint for live search (used by React frontend)."""
    q      = request.args.get('q', '').strip()
    limit  = min(request.args.get('limit', 10, type=int), 50)
    query  = Position.query.filter_by(is_active=True)
    if q:
        query = query.filter(or_(
            Position.title.ilike(f'%{q}%'),
            Position.department.ilike(f'%{q}%'),
        ))
    jobs = query.order_by(Position.created_at.desc()).limit(limit).all()
    return jsonify([{
        'id': j.id,
        'title': j.title,
        'company': j.company.name if j.company else 'MOF Engineering',
        'location': j.location,
        'type': j.type,
        'is_remote': j.is_remote,
        'created_at': j.created_at.isoformat(),
    } for j in jobs])
