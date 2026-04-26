from flask import Blueprint, render_template, url_for
from flask_login import current_user

supervisor_apply_bp = Blueprint('supervisor_apply', __name__)


def _chat_link(channel):
    target = url_for('messages.compose', channel=channel)
    if current_user.is_authenticated:
        return target
    return url_for('auth.login', next=target)


@supervisor_apply_bp.route('/supervisor_apply')
def index():
    return render_template(
        'public/apply_portal.html',
        page_title='Supervisor and Company Portal Application',
        page_kicker='OUR SOLUTION',
        page_headline='One platform. Every stakeholder. Real-time.',
        page_subtitle='Supervisors and companies run placement operations with live alerts, structured tasks, and auditable outcomes.',
        cta_primary_text='Apply as Supervisor',
        cta_primary_link=url_for('auth.register'),
        cta_secondary_text='Company-Coordinator Chat',
        cta_secondary_link=_chat_link('company_coordinator'),
        section_label='Company Operations View',
        section_copy='Built for fast company onboarding, task tracking, and reporting across internship cycles.',
        channel_one_title='Company <> Coordinator Chat',
        channel_one_copy='Collaborate on openings, candidate alignment, approvals, and status updates in one place.',
        channel_one_link=_chat_link('company_coordinator'),
        channel_two_title='Coordinator <> Student Chat',
        channel_two_copy='Support students from assignment to submission, with centralized communication history.',
        channel_two_link=_chat_link('coordinator_student'),
    )
