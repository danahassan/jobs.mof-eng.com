from flask import Blueprint, render_template, redirect, url_for, request, abort
from flask_login import login_required, current_user
from models import (db, Application, Position, ROLE_STUDENT,
                    ALL_STATUSES, STATUS_NEW, STATUS_REVIEW, STATUS_INTERVIEW,
                    STATUS_OFFER, STATUS_HIRED, STATUS_REJECTED)
from functools import wraps

student_bp = Blueprint('student', __name__)


def student_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != ROLE_STUDENT:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@student_bp.route('/')
@student_required
def dashboard():
    my_apps = (Application.query
               .filter_by(applicant_id=current_user.id)
               .join(Application.position)
               .filter(Position.type == 'Internship')
               .order_by(Application.applied_at.desc())
               .all())

    total      = len(my_apps)
    active     = sum(1 for a in my_apps
                     if a.status in [STATUS_NEW, STATUS_REVIEW, STATUS_INTERVIEW, STATUS_OFFER])
    placed     = sum(1 for a in my_apps if a.status == STATUS_HIRED)
    rejected   = sum(1 for a in my_apps if a.status == STATUS_REJECTED)

    return render_template('student/dashboard.html',
        my_apps=my_apps,
        kpi_total=total,
        kpi_active=active,
        kpi_placed=placed,
        kpi_rejected=rejected,
        ALL_STATUSES=ALL_STATUSES)
