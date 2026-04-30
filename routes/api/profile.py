"""API profile endpoints."""
import os
from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from models import db, UserSkill, UserExperience, UserEducation

from . import api_bp

# Common tech/soft skills to match against CV text (case-insensitive).
# Extend this list as needed — it drives the suggestion quality.
_SKILL_VOCABULARY = [
    'Python', 'JavaScript', 'TypeScript', 'Java', 'C#', 'C++', 'Go', 'Rust', 'PHP', 'Ruby',
    'Swift', 'Kotlin', 'Dart', 'Flutter', 'React', 'Vue', 'Angular', 'Next.js', 'Node.js',
    'Django', 'Flask', 'FastAPI', 'Spring', 'Laravel', 'Express', 'PostgreSQL', 'MySQL',
    'SQLite', 'MongoDB', 'Redis', 'Elasticsearch', 'Docker', 'Kubernetes', 'AWS', 'Azure',
    'Google Cloud', 'Terraform', 'Ansible', 'CI/CD', 'Git', 'GitHub', 'Linux', 'Bash',
    'REST API', 'GraphQL', 'Microservices', 'Machine Learning', 'Deep Learning', 'PyTorch',
    'TensorFlow', 'Pandas', 'NumPy', 'Scikit-learn', 'Data Analysis', 'Power BI', 'Tableau',
    'Excel', 'SQL', 'HTML', 'CSS', 'Tailwind', 'Bootstrap', 'Figma', 'Photoshop',
    'AutoCAD', 'MATLAB', 'R', 'Scala', 'Hadoop', 'Spark', 'Kafka',
    'Communication', 'Teamwork', 'Leadership', 'Problem Solving', 'Project Management',
    'Agile', 'Scrum', 'Research', 'Writing', 'Presentation', 'Arabic', 'Kurdish', 'English',
]


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


# ─── CV skill extraction ──────────────────────────────────────────────────────

@api_bp.route('/profile/cv-skills')
@login_required
def cv_skills():
    """Extract skill suggestions from the current user's uploaded CV.

    Reads the stored PDF, extracts plain text using pdfminer.six, then
    matches against a vocabulary of known skills.  Returns JSON:
        { "ok": true, "skills": ["Python", "Django", ...], "already_added": ["Python"] }

    Returns {"ok": false, "error": "..."} if no CV is uploaded or pdfminer
    is not available (soft-fail — never crashes the profile page).
    """
    u = current_user
    upload_folder = current_app.config.get('UPLOAD_FOLDER', '')
    if not getattr(u, 'cv_filename', None):
        # Check latest application CV as fallback
        from models import Application
        latest = (Application.query
                  .filter_by(applicant_id=u.id)
                  .filter(Application.cv_filename.isnot(None))
                  .order_by(Application.applied_at.desc())
                  .first())
        cv_path = os.path.join(upload_folder, latest.cv_filename) if latest else None
    else:
        cv_path = os.path.join(upload_folder, u.cv_filename)

    if not cv_path or not os.path.isfile(cv_path):
        return jsonify({'ok': False, 'error': 'No CV found. Upload your CV via My Applications first.'})

    # Extract text — gracefully degrade if pdfminer not installed
    try:
        from pdfminer.high_level import extract_text as _extract
        text = _extract(cv_path)
    except ImportError:
        return jsonify({'ok': False, 'error': 'PDF parsing library not available on this server.'})
    except Exception as ex:
        current_app.logger.warning('cv_skills: pdfminer failed for %s: %s', cv_path, ex)
        return jsonify({'ok': False, 'error': 'Could not read PDF. Ensure it is a valid PDF file.'})

    text_lower = text.lower()
    matched = [s for s in _SKILL_VOCABULARY if s.lower() in text_lower]

    existing = {sk.name.lower() for sk in UserSkill.query.filter_by(user_id=u.id).all()}
    already_added = [s for s in matched if s.lower() in existing]
    new_suggestions = [s for s in matched if s.lower() not in existing]

    return jsonify({
        'ok': True,
        'skills': new_suggestions[:20],
        'already_added': already_added,
    })
