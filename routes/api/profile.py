"""API profile endpoints."""
from flask import request, jsonify
from flask_login import login_required, current_user
from models import db, UserSkill, UserExperience, UserEducation

from . import api_bp


@api_bp.route('/profile')
@login_required
def profile():
    u = current_user
    return jsonify({
        'id':             u.id,
        'full_name':      u.full_name,
        'email':          u.email,
        'headline':       u.headline,
        'bio':            u.bio,
        'phone':          u.phone,
        'location_city':  u.location_city,
        'nationality':    u.nationality,
        'gender':         u.gender,
        'linkedin_url':   u.linkedin_url,
        'github_url':     u.github_url,
        'portfolio_url':  u.portfolio_url,
        'resume_headline':u.resume_headline,
        'avatar_url':     f'/static/uploads/avatars/{u.avatar_filename}' if u.avatar_filename else None,
        'profile_strength': u.profile_strength,
        'skills':         [{'id': s.id, 'name': s.name, 'proficiency': s.proficiency}
                            for s in u.skills.all()],
        'experiences':    [_exp_dict(e) for e in u.experiences.order_by(UserExperience.start_date.desc()).all()],
        'educations':     [_edu_dict(e) for e in u.educations.order_by(UserEducation.start_year.desc()).all()],
        'languages':      [{'id': l.id, 'language': l.language, 'proficiency': l.proficiency}
                            for l in u.languages.all()],
        'certifications': [_cert_dict(c) for c in u.certifications.all()],
        'portfolio':      [_portfolio_dict(p) for p in u.portfolio_items.all()],
    })


@api_bp.route('/profile', methods=['PATCH'])
@login_required
def update_profile():
    data = request.get_json(force=True)
    u = current_user
    fields = ['full_name', 'headline', 'bio', 'phone', 'location_city',
              'nationality', 'gender', 'linkedin_url', 'github_url',
              'portfolio_url', 'resume_headline']
    for f in fields:
        if f in data:
            setattr(u, f, (data[f] or '').strip())
    db.session.commit()
    return jsonify({'ok': True, 'profile_strength': u.profile_strength})


def _exp_dict(e):
    return {
        'id': e.id, 'title': e.title, 'company': e.company,
        'start_date': e.start_date.isoformat() if e.start_date else None,
        'end_date':   e.end_date.isoformat()   if e.end_date   else None,
        'description': e.description,
    }


def _edu_dict(e):
    return {
        'id': e.id, 'institution': e.institution,
        'degree': e.degree, 'field': e.field,
        'start_year': e.start_year, 'end_year': e.end_year,
    }


def _cert_dict(c):
    return {
        'id': c.id, 'name': c.name, 'issuing_org': c.issuing_org,
        'issue_date':  c.issue_date.isoformat()  if c.issue_date  else None,
        'expiry_date': c.expiry_date.isoformat() if c.expiry_date else None,
        'credential_url': c.credential_url,
        'is_expired': c.is_expired,
    }


def _portfolio_dict(p):
    return {
        'id': p.id, 'title': p.title, 'description': p.description,
        'url': p.url,
        'file_url': f'/static/uploads/portfolio/{p.filename}' if p.filename else None,
    }
