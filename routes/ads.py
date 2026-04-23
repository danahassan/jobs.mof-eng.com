"""routes/ads.py — Admin-managed top banner ads.

Admins can upload an image, schedule a date window, set priority and a
click URL. The system shows the highest-priority *live* ad on every page.
Views are tracked via a 1×1 pixel beacon, clicks via a redirect endpoint.
"""
import os
import uuid
from datetime import datetime
from functools import wraps

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, abort, current_app, send_from_directory, Response)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from models import db, Ad, ROLE_ADMIN
from helpers import log_audit

ads_bp = Blueprint('ads', __name__)

# Transparent 1×1 GIF
_PIXEL = (b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00'
          b'!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01'
          b'\x00\x00\x02\x02D\x01\x00;')


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != ROLE_ADMIN:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def _allowed(filename):
    if '.' not in filename:
        return False
    return filename.rsplit('.', 1)[-1].lower() in current_app.config['AD_ALLOWED_EXTENSIONS']


def _parse_dt(s, default=None):
    if not s:
        return default
    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return default


def get_current_ad():
    """Return the single highest-priority *live* ad to show right now."""
    now = datetime.utcnow()
    return (Ad.query
            .filter(Ad.is_active == True)
            .filter((Ad.start_at == None) | (Ad.start_at <= now))   # noqa: E711
            .filter((Ad.end_at == None) | (Ad.end_at >= now))
            .order_by(Ad.priority.desc(), Ad.created_at.desc())
            .first())


# ─── Public tracking endpoints ───────────────────────────────────────────────

@ads_bp.route('/v/<int:ad_id>.gif')
def view_pixel(ad_id):
    """1×1 GIF beacon — increments the view count then returns transparent pixel."""
    ad = db.session.get(Ad, ad_id)
    if ad:
        try:
            ad.view_count = (ad.view_count or 0) + 1
            db.session.commit()
        except Exception:
            db.session.rollback()
    resp = Response(_PIXEL, mimetype='image/gif')
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return resp


@ads_bp.route('/c/<int:ad_id>')
def click(ad_id):
    """Click tracker — increments click count then redirects to the ad target."""
    ad = Ad.query.get_or_404(ad_id)
    try:
        ad.click_count = (ad.click_count or 0) + 1
        db.session.commit()
    except Exception:
        db.session.rollback()
    return redirect(ad.link_url or url_for('index'))


@ads_bp.route('/img/<path:filename>')
def serve_image(filename):
    """Serve uploaded ad images directly from the ads folder."""
    return send_from_directory(current_app.config['ADS_FOLDER'], filename)


# ─── Admin UI ────────────────────────────────────────────────────────────────

@ads_bp.route('/admin')
@admin_required
def admin_list():
    ads = Ad.query.order_by(Ad.is_active.desc(), Ad.priority.desc(),
                            Ad.created_at.desc()).all()
    now = datetime.utcnow()
    stats = {
        'total':   len(ads),
        'live':    sum(1 for a in ads if a.is_live),
        'views':   sum((a.view_count or 0) for a in ads),
        'clicks':  sum((a.click_count or 0) for a in ads),
    }
    return render_template('ads/admin_list.html', ads=ads, stats=stats, now=now)


@ads_bp.route('/admin/new', methods=['GET', 'POST'])
@admin_required
def admin_new():
    if request.method == 'POST':
        return _save_ad(None)
    return render_template('ads/admin_form.html', ad=None)


@ads_bp.route('/admin/<int:ad_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    if request.method == 'POST':
        return _save_ad(ad)
    return render_template('ads/admin_form.html', ad=ad)


def _save_ad(ad):
    title    = request.form.get('title', '').strip()
    link_url = request.form.get('link_url', '').strip() or None
    days_s   = request.form.get('days', '').strip()
    start_s  = request.form.get('start_at', '').strip()
    end_s    = request.form.get('end_at', '').strip()
    priority = request.form.get('priority', '0').strip()
    is_active = bool(request.form.get('is_active'))

    if not title:
        flash('Please give the ad a title.', 'danger')
        return redirect(request.url)

    try:
        priority = int(priority)
    except ValueError:
        priority = 0

    start_at = _parse_dt(start_s) or datetime.utcnow()
    end_at   = _parse_dt(end_s)
    # If "days" supplied, it overrides end_at
    if days_s:
        try:
            days = int(days_s)
            if days > 0:
                from datetime import timedelta
                end_at = start_at + timedelta(days=days)
        except ValueError:
            pass

    f = request.files.get('image')
    image_path = ad.image_path if ad else None
    image_name = ad.image_name if ad else None
    image_mime = ad.image_mime if ad else None

    if f and f.filename:
        if not _allowed(f.filename):
            flash('Unsupported image type. Allowed: PNG, JPG, GIF, WebP, SVG.', 'danger')
            return redirect(request.url)
        original = secure_filename(f.filename)
        ext = original.rsplit('.', 1)[-1].lower()
        stored = f"{uuid.uuid4().hex}.{ext}"
        folder = current_app.config['ADS_FOLDER']
        os.makedirs(folder, exist_ok=True)
        f.save(os.path.join(folder, stored))
        # Remove old file if replacing
        if ad and ad.image_path:
            try:
                old = os.path.join(folder, ad.image_path)
                if os.path.isfile(old):
                    os.remove(old)
            except OSError:
                pass
        image_path = stored
        image_name = original
        image_mime = f.mimetype

    # Mobile image (optional)
    mf = request.files.get('mobile_image')
    mobile_image_path = ad.mobile_image_path if ad else None
    mobile_image_name = ad.mobile_image_name if ad else None
    mobile_image_mime = ad.mobile_image_mime if ad else None

    if mf and mf.filename:
        if not _allowed(mf.filename):
            flash('Unsupported mobile image type. Allowed: PNG, JPG, GIF, WebP, SVG.', 'danger')
            return redirect(request.url)
        original = secure_filename(mf.filename)
        ext = original.rsplit('.', 1)[-1].lower()
        stored = f"{uuid.uuid4().hex}.{ext}"
        folder = current_app.config['ADS_FOLDER']
        os.makedirs(folder, exist_ok=True)
        mf.save(os.path.join(folder, stored))
        if ad and ad.mobile_image_path:
            try:
                old = os.path.join(folder, ad.mobile_image_path)
                if os.path.isfile(old):
                    os.remove(old)
            except OSError:
                pass
        mobile_image_path = stored
        mobile_image_name = original
        mobile_image_mime = mf.mimetype

    # Allow clearing the mobile image explicitly
    if request.form.get('remove_mobile') and ad and ad.mobile_image_path:
        try:
            old = os.path.join(current_app.config['ADS_FOLDER'], ad.mobile_image_path)
            if os.path.isfile(old):
                os.remove(old)
        except OSError:
            pass
        mobile_image_path = None
        mobile_image_name = None
        mobile_image_mime = None

    if ad is None:
        if not image_path:
            flash('Please upload an image for the ad.', 'danger')
            return redirect(request.url)
        ad = Ad(
            title         = title,
            image_path    = image_path,
            image_name    = image_name,
            image_mime    = image_mime,
            mobile_image_path = mobile_image_path,
            mobile_image_name = mobile_image_name,
            mobile_image_mime = mobile_image_mime,
            link_url      = link_url,
            start_at      = start_at,
            end_at        = end_at,
            priority      = priority,
            is_active     = is_active,
            created_by_id = current_user.id,
        )
        db.session.add(ad)
        log_audit('ad.create', f'#{title}')
    else:
        ad.title      = title
        ad.image_path = image_path
        ad.image_name = image_name
        ad.image_mime = image_mime
        ad.mobile_image_path = mobile_image_path
        ad.mobile_image_name = mobile_image_name
        ad.mobile_image_mime = mobile_image_mime
        ad.link_url   = link_url
        ad.start_at   = start_at
        ad.end_at     = end_at
        ad.priority   = priority
        ad.is_active  = is_active
        log_audit('ad.update', f'#{ad.id} {title}')

    db.session.commit()
    flash('Ad saved.', 'success')
    return redirect(url_for('ads.admin_list'))


@ads_bp.route('/admin/<int:ad_id>/toggle', methods=['POST'])
@admin_required
def admin_toggle(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    ad.is_active = not ad.is_active
    log_audit('ad.toggle', f'#{ad.id} → {"on" if ad.is_active else "off"}')
    db.session.commit()
    flash(f'Ad "{ad.title}" is now {"active" if ad.is_active else "disabled"}.', 'success')
    return redirect(url_for('ads.admin_list'))


@ads_bp.route('/admin/<int:ad_id>/delete', methods=['POST'])
@admin_required
def admin_delete(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    folder = current_app.config['ADS_FOLDER']
    for fname in (ad.image_path, ad.mobile_image_path):
        if not fname:
            continue
        try:
            path = os.path.join(folder, fname)
            if os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass
    log_audit('ad.delete', f'#{ad.id} {ad.title}')
    db.session.delete(ad)
    db.session.commit()
    flash('Ad deleted.', 'success')
    return redirect(url_for('ads.admin_list'))


@ads_bp.route('/admin/<int:ad_id>/reset-stats', methods=['POST'])
@admin_required
def admin_reset_stats(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    ad.view_count = 0
    ad.click_count = 0
    log_audit('ad.reset_stats', f'#{ad.id} {ad.title}')
    db.session.commit()
    flash('Stats reset.', 'success')
    return redirect(url_for('ads.admin_list'))
