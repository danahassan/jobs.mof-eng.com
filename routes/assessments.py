"""routes/assessments.py — Assessment creation, taking, scoring, results."""
import json
from datetime import datetime
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, abort, jsonify)
from flask_login import login_required, current_user

from models import (db, Assessment, AssessmentQuestion, AssessmentSubmission,
                    AssessmentAnswer, Application, ROLE_ADMIN, ROLE_EMPLOYER)
from helpers import admin_required, push_notification

assessments_bp = Blueprint('assessments', __name__)


def _require_staff(f):
    from functools import wraps
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role not in (ROLE_ADMIN, ROLE_EMPLOYER):
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ─── Admin / Employer: Manage Assessments ────────────────────────────────────

@assessments_bp.route('/manage')
@_require_staff
def manage():
    q = Assessment.query
    if current_user.role == ROLE_EMPLOYER:
        q = q.filter_by(created_by=current_user.id)
    assessments = q.order_by(Assessment.created_at.desc()).all()
    return render_template('assessments/manage.html', assessments=assessments)


@assessments_bp.route('/new', methods=['GET', 'POST'])
@_require_staff
def create():
    if request.method == 'POST':
        a = Assessment(
            title=request.form.get('title', '').strip(),
            description=request.form.get('description', '').strip(),
            time_limit_mins=request.form.get('time_limit_mins', 30, type=int),
            pass_score=request.form.get('pass_score', 70, type=int),
            created_by=current_user.id,
        )
        pos_id = request.form.get('position_id', type=int)
        if pos_id:
            a.position_id = pos_id
        db.session.add(a)
        db.session.commit()
        flash('Assessment created. Now add questions.', 'success')
        return redirect(url_for('assessments.edit', assessment_id=a.id))
    from models import Position
    positions = Position.query.filter_by(is_active=True).order_by(Position.title).all()
    return render_template('assessments/form.html', assessment=None, positions=positions)


@assessments_bp.route('/<int:assessment_id>/edit', methods=['GET', 'POST'])
@_require_staff
def edit(assessment_id):
    a = Assessment.query.get_or_404(assessment_id)
    if current_user.role == ROLE_EMPLOYER and a.created_by != current_user.id:
        abort(403)
    if request.method == 'POST':
        a.title           = request.form.get('title', '').strip()
        a.description     = request.form.get('description', '').strip()
        a.time_limit_mins = request.form.get('time_limit_mins', 30, type=int)
        a.pass_score      = request.form.get('pass_score', 70, type=int)
        db.session.commit()
        flash('Assessment updated.', 'success')
    questions = a.questions.order_by(AssessmentQuestion.order).all()
    from models import Position
    positions = Position.query.filter_by(is_active=True).order_by(Position.title).all()
    return render_template('assessments/form.html', assessment=a,
        questions=questions, positions=positions)


@assessments_bp.route('/<int:assessment_id>/questions/add', methods=['POST'])
@_require_staff
def add_question(assessment_id):
    a = Assessment.query.get_or_404(assessment_id)
    q_type    = request.form.get('question_type', 'mcq')
    q_text    = request.form.get('question_text', '').strip()
    correct   = request.form.get('correct_answer', '').strip()
    expl      = request.form.get('explanation', '').strip()
    points    = request.form.get('points', 1, type=int)
    order     = a.questions.count()

    q = AssessmentQuestion(
        assessment_id=assessment_id,
        question_text=q_text,
        question_type=q_type,
        correct_answer=correct,
        explanation=expl,
        points=points,
        order=order,
    )
    if q_type == 'mcq':
        options = request.form.getlist('options[]')
        q.options = [o.strip() for o in options if o.strip()]
    elif q_type == 'true_false':
        q.options = ['True', 'False']

    db.session.add(q)
    db.session.commit()
    flash('Question added.', 'success')
    return redirect(url_for('assessments.edit', assessment_id=assessment_id))


@assessments_bp.route('/questions/<int:q_id>/delete', methods=['POST'])
@_require_staff
def delete_question(q_id):
    q = AssessmentQuestion.query.get_or_404(q_id)
    assessment_id = q.assessment_id
    db.session.delete(q)
    db.session.commit()
    flash('Question deleted.', 'success')
    return redirect(url_for('assessments.edit', assessment_id=assessment_id))


# ─── Candidate: Take Assessment ───────────────────────────────────────────────

@assessments_bp.route('/<int:assessment_id>/take')
@login_required
def take(assessment_id):
    a = Assessment.query.get_or_404(assessment_id)
    if not a.is_active:
        abort(404)

    # Prevent retake
    existing = AssessmentSubmission.query.filter_by(
        assessment_id=assessment_id,
        user_id=current_user.id,
    ).filter(AssessmentSubmission.completed_at.isnot(None)).first()
    if existing:
        return redirect(url_for('assessments.result', submission_id=existing.id))

    questions = a.questions.order_by(AssessmentQuestion.order).all()
    # Create a pending submission
    sub = AssessmentSubmission(
        assessment_id=assessment_id,
        user_id=current_user.id,
    )
    db.session.add(sub)
    db.session.commit()
    return render_template('assessments/take.html', assessment=a,
        questions=questions, submission_id=sub.id)


@assessments_bp.route('/<int:assessment_id>/submit/<int:submission_id>', methods=['POST'])
@login_required
def submit(assessment_id, submission_id):
    sub = AssessmentSubmission.query.get_or_404(submission_id)
    if sub.user_id != current_user.id:
        abort(403)
    if sub.completed_at:
        return redirect(url_for('assessments.result', submission_id=sub.id))

    a = sub.assessment
    questions = a.questions.order_by(AssessmentQuestion.order).all()

    total_points = 0
    earned       = 0

    for q in questions:
        answer_key = f'q_{q.id}'
        answer_val = request.form.get(answer_key, '').strip()
        total_points += q.points

        if q.question_type in ('mcq', 'true_false'):
            correct = str(q.correct_answer).strip().lower() == answer_val.lower()
        else:
            # text: exact match (case-insensitive)
            correct = q.correct_answer and q.correct_answer.strip().lower() == answer_val.lower()

        pts = q.points if correct else 0
        earned += pts

        ans = AssessmentAnswer(
            submission_id=sub.id,
            question_id=q.id,
            answer_text=answer_val,
            is_correct=correct,
            points_earned=pts,
        )
        db.session.add(ans)

    sub.completed_at = datetime.utcnow()
    sub.score        = earned
    sub.max_score    = total_points
    sub.percentage   = round(earned / total_points * 100, 1) if total_points > 0 else 0
    sub.passed       = sub.percentage >= a.pass_score
    db.session.commit()

    push_notification(
        current_user.id,
        f'You scored <b>{sub.percentage}%</b> on "{a.title}" — {"Passed ✓" if sub.passed else "Not passed"}.',
        url_for('assessments.result', submission_id=sub.id),
        icon='bi-clipboard-check-fill'
    )
    return redirect(url_for('assessments.result', submission_id=sub.id))


@assessments_bp.route('/result/<int:submission_id>')
@login_required
def result(submission_id):
    sub = AssessmentSubmission.query.get_or_404(submission_id)
    if sub.user_id != current_user.id and current_user.role not in (ROLE_ADMIN, ROLE_EMPLOYER):
        abort(403)
    answers  = sub.answers.all()
    questions= {q.id: q for q in sub.assessment.questions.all()}
    return render_template('assessments/result.html',
        sub=sub, answers=answers, questions=questions)


# ─── Staff: View Submissions ──────────────────────────────────────────────────

@assessments_bp.route('/<int:assessment_id>/submissions')
@_require_staff
def submissions(assessment_id):
    a = Assessment.query.get_or_404(assessment_id)
    subs = a.submissions.order_by(AssessmentSubmission.completed_at.desc()).all()
    return render_template('assessments/submissions.html', assessment=a, subs=subs)
