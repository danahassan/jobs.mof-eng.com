"""routes/company.py — Public company profiles + follow."""
import os
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, abort, jsonify)
from flask_login import login_required, current_user

from models import db, Company, CompanyFollow, CompanyPhoto, Position, ROLE_USER, ROLE_STUDENT
from sqlalchemy import func
from helpers import log_audit

company_bp = Blueprint('companies', __name__)


@company_bp.route('/')
def listing():
    q        = request.args.get('q', '').strip()
    industry = request.args.get('industry', '').strip()
    view     = request.args.get('view', 'card')   # 'card' | 'list'
    page     = request.args.get('page', 1, type=int)

    query = Company.query.filter_by(is_active=True)
    if q:
        query = query.filter(Company.name.ilike(f'%{q}%'))
    if industry:
        query = query.filter(Company.industry == industry)

    pagination = query.order_by(Company.name).paginate(page=page, per_page=24, error_out=False)
    companies  = pagination.items

    # Industries for filter dropdown
    rows = db.session.query(Company.industry)\
             .filter(Company.is_active==True, Company.industry != None)\
             .distinct().order_by(Company.industry).all()
    industries = [r.industry for r in rows]

    # Which companies the current user follows
    followed_ids = set()
    if current_user.is_authenticated:
        followed_ids = {
            f.company_id
            for f in CompanyFollow.query.filter_by(user_id=current_user.id).all()
        }

    total = query.count()

    is_student = current_user.is_authenticated and current_user.role in (ROLE_STUDENT, 'university_coordinator')

    # KPI metrics
    kpi_total     = Company.query.filter_by(is_active=True).count()
    kpi_verified  = Company.query.filter_by(is_active=True, is_verified=True).count()
    kpi_followers = db.session.query(func.count(CompanyFollow.id)).scalar() or 0
    kpi_industries= db.session.query(func.count(func.distinct(Company.industry)))\
                      .filter(Company.is_active==True, Company.industry != None).scalar() or 0

    pos_q = db.session.query(func.count(Position.id))\
                .filter(Position.is_active==True, Position.company_id != None)
    if is_student:
        pos_q = pos_q.filter(Position.type == 'Internship')
    else:
        pos_q = pos_q.filter(Position.type != 'Internship')
    kpi_open_jobs = pos_q.scalar() or 0

    # Per-company internship counts for students (model property counts all types)
    internship_counts = {}
    if is_student:
        rows = db.session.query(Position.company_id, func.count(Position.id))\
                .filter(Position.is_active==True, Position.type=='Internship')\
                .group_by(Position.company_id).all()
        internship_counts = {r[0]: r[1] for r in rows}

    return render_template('companies/listing.html',
        companies=companies, q=q, industry=industry, view=view,
        industries=industries, followed_ids=followed_ids,
        pagination=pagination, total=total,
        kpi_total=kpi_total, kpi_verified=kpi_verified,
        kpi_open_jobs=kpi_open_jobs, kpi_followers=kpi_followers,
        kpi_industries=kpi_industries,
        is_student=is_student, internship_counts=internship_counts)


@company_bp.route('/<slug>')
def profile(slug):
    company = Company.query.filter_by(slug=slug, is_active=True).first_or_404()
    jobs_q = Position.query.filter_by(company_id=company.id, is_active=True)
    if not current_user.is_authenticated or current_user.role == ROLE_USER:
        # Regular/unauthenticated users: hide internships
        jobs_q = jobs_q.filter(Position.type != 'Internship')
    elif current_user.role in (ROLE_STUDENT, 'university_coordinator'):
        # Students and coordinators: show only internships
        jobs_q = jobs_q.filter(Position.type == 'Internship')
    jobs = jobs_q.order_by(Position.created_at.desc()).all()
    photos = company.photos.all()
    following = False
    if current_user.is_authenticated:
        following = CompanyFollow.query.filter_by(
            user_id=current_user.id, company_id=company.id).first() is not None
    return render_template('companies/profile.html',
        company=company, open_jobs=jobs, following=following, photos=photos)


@company_bp.route('/<int:company_id>/follow', methods=['POST'])
@login_required
def toggle_follow(company_id):
    company = Company.query.get_or_404(company_id)
    existing = CompanyFollow.query.filter_by(
        user_id=current_user.id, company_id=company_id).first()
    if existing:
        db.session.delete(existing)
        log_audit('company.unfollow', company.name, user_id=current_user.id)
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'following': False, 'followers': company.follower_count})
        flash(f'Unfollowed {company.name}.', 'info')
        return redirect(request.referrer or url_for('companies.listing'))
    follow = CompanyFollow(user_id=current_user.id, company_id=company_id)
    db.session.add(follow)
    log_audit('company.follow', company.name, user_id=current_user.id)
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'following': True, 'followers': company.follower_count})
    flash(f'Now following {company.name}!', 'success')
    return redirect(request.referrer or url_for('companies.listing'))
