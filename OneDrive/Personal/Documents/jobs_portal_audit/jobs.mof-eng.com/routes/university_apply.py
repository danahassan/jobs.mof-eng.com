from flask import Blueprint, render_template, url_for
from flask_login import current_user

university_apply_bp = Blueprint('university_apply', __name__)


def _chat_link(channel):
    target = url_for('messages.compose', channel=channel)
    if current_user.is_authenticated:
        return target
    return url_for('auth.login', next=target)


@university_apply_bp.route('/university_apply')
def index():
    return render_template(
        'public/apply_portal.html',
        page_title='University Portal Application',
        page_kicker='OUR SOLUTION',
        page_headline='One platform. Every stakeholder. Real-time.',
        page_subtitle='Universities onboard quickly, coordinate with companies, and track student progress from one modern workspace.',
        cta_primary_text='Apply as University Coordinator',
        cta_primary_link=url_for('auth.register'),
        cta_secondary_text='Coordinator Chat',
        cta_secondary_link=_chat_link('coordinator_student'),
        section_label='University Web View',
        section_copy='Designed for coordinators managing student placement, grading, and communication.',
        channel_one_title='Company <> Coordinator Chat',
        channel_one_copy='Open direct conversations with companies to align internships, expectations, and approvals.',
        channel_one_link=_chat_link('company_coordinator'),
        channel_two_title='Coordinator <> Student Chat',
        channel_two_copy='Keep students informed with one-to-one support, reminders, and task clarifications.',
        channel_two_link=_chat_link('coordinator_student'),
    )
