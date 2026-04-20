from flask import Blueprint, render_template, redirect, url_for, request, jsonify, abort
from flask_login import login_required, current_user
from models import db, Notification

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    filter_unread = request.args.get('filter') == 'unread'
    q = Notification.query.filter_by(user_id=current_user.id)
    if filter_unread:
        q = q.filter_by(is_read=False)
    notifs = q.order_by(Notification.created_at.desc()).paginate(page=page, per_page=20)
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template('notifications.html',
                           notifications=notifs,
                           unread_notifications=unread_count,
                           filter_unread=filter_unread)


@notifications_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    (Notification.query
     .filter_by(user_id=current_user.id, is_read=False)
     .update({'is_read': True}))
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(success=True)
    return redirect(url_for('notifications.index'))


@notifications_bp.route('/mark-read/<int:notif_id>', methods=['POST'])
@login_required
def mark_read(notif_id):
    n = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    n.is_read = True
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(success=True)
    return redirect(url_for('notifications.index'))


@notifications_bp.route('/delete/<int:notif_id>', methods=['POST'])
@login_required
def delete(notif_id):
    n = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    db.session.delete(n)
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(success=True)
    return redirect(url_for('notifications.index'))
