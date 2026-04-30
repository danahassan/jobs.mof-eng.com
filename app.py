import os
from datetime import datetime

from flask import (Flask, render_template, redirect, url_for, flash,
                   request, abort, send_from_directory, current_app, make_response)
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)

from config import config

# ─── SENTRY (optional — no-op when SENTRY_DSN is not set) ────────────────────
_sentry_dsn = os.environ.get('SENTRY_DSN', '').strip()
if _sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    sentry_sdk.init(
        dsn=_sentry_dsn,
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.1,   # capture 10 % of requests for performance tracing
        send_default_pii=False,   # do NOT attach user PII to events
    )
from models import (db, User, Message, Notification, Position, Application, ApplicationHistory,
                    Interview, CompanyMember, SupervisorRequest, UniversityRequest,
                    ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_USER, ROLE_EMPLOYER,
                    ROLE_STUDENT, ROLE_UNIVERSITY_COORD,
                    ALL_STATUSES, SOURCES, SALARY_RANGES, STATUS_NEW)

# ─── APP FACTORY ──────────────────────────────────────────────────────────────

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Load persisted site settings (overrides .env defaults at runtime)
    import json as _json
    _settings_path = os.path.join(app.instance_path, 'site_settings.json')
    if os.path.exists(_settings_path):
        with open(_settings_path) as _sf:
            _site = _json.load(_sf)
        for _k, _v in _site.items():
            app.config[_k] = _v
        _name = _site.get('MAIL_FROM_NAME', 'MOF Jobs')
        _addr = _site.get('MAIL_FROM_ADDRESS', app.config.get('MAIL_USERNAME', ''))
        app.config['MAIL_DEFAULT_SENDER'] = f'{_name} <{_addr}>'

    db.init_app(app)

    # Inject SITE_URL into every template so emails never use request.host
    @app.context_processor
    def inject_site_url():
        return {'site_url': app.config['SITE_URL']}

    # Expose full-scope university coordinator status to all templates so the
    # sidebar can show a "Manage University" admin shortcut when applicable.
    @app.context_processor
    def inject_coord_full_scope():
        try:
            from helpers import full_scope_coordinator_university_id
            return {'coord_full_scope_univ_id': full_scope_coordinator_university_id(current_user)}
        except Exception:
            return {'coord_full_scope_univ_id': None}

    # CORS — only allow the React dev server in development
    from flask_cors import CORS
    if app.debug:
        CORS(app, origins=['http://localhost:5173'], supports_credentials=True)

    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from zoneinfo import ZoneInfo
    from datetime import timezone as _utc
    _baghdad = ZoneInfo('Asia/Baghdad')

    @app.template_filter('localdt')
    def localdt_filter(dt):
        """Convert a naive UTC datetime to Asia/Baghdad (GMT+3)."""
        if dt is None:
            return dt
        return dt.replace(tzinfo=_utc.utc).astimezone(_baghdad)

    @app.before_request
    def update_last_seen():
        if current_user.is_authenticated:
            now = datetime.utcnow()
            if (current_user.last_seen is None or
                    (now - current_user.last_seen).total_seconds() > 60):
                current_user.last_seen = now
                db.session.commit()

    # Register blueprints
    from routes.auth              import auth_bp
    from routes.admin             import admin_bp
    from routes.supervisor        import supervisor_bp
    from routes.user              import user_bp
    from routes.messages          import messages_bp
    from routes.notifications     import notifications_bp
    from routes.employer          import employer_bp
    from routes.company           import company_bp
    from routes.jobs              import jobs_bp
    from routes.profile           import profile_bp
    from routes.assessments       import assessments_bp
    from routes.analytics         import analytics_bp
    from routes.api               import api_bp
    from routes.supervisor_apply  import supervisor_apply_bp
    from routes.university_apply  import university_apply_bp
    from routes.university        import university_bp
    from routes.student           import student_bp
    from routes.reports           import reports_bp
    from routes.ads               import ads_bp, get_current_ad

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp,             url_prefix='/admin')
    app.register_blueprint(supervisor_bp,        url_prefix='/supervisor')
    app.register_blueprint(user_bp,              url_prefix='/portal')
    app.register_blueprint(messages_bp,          url_prefix='/messages')
    app.register_blueprint(notifications_bp,     url_prefix='/notifications')
    app.register_blueprint(employer_bp,          url_prefix='/employer')
    app.register_blueprint(company_bp,           url_prefix='/companies')
    app.register_blueprint(jobs_bp,              url_prefix='/jobs')
    app.register_blueprint(profile_bp,           url_prefix='/profile')
    app.register_blueprint(assessments_bp,       url_prefix='/assessments')
    app.register_blueprint(analytics_bp,         url_prefix='/analytics')
    app.register_blueprint(api_bp,               url_prefix='/api/v1')
    app.register_blueprint(supervisor_apply_bp)
    app.register_blueprint(university_apply_bp)
    app.register_blueprint(university_bp,        url_prefix='/university')
    app.register_blueprint(student_bp,           url_prefix='/student')
    app.register_blueprint(reports_bp,           url_prefix='/reports')
    app.register_blueprint(ads_bp,               url_prefix='/ads')

    # Root redirect
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return _role_redirect()
        return redirect(url_for('auth.login'))

    # Serve service worker from root scope (required for PWA)
    @app.route('/sw.js')
    def service_worker():
        response = send_from_directory(app.static_folder, 'sw.js',
                                       mimetype='application/javascript')
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response

    @app.route('/manifest.json')
    def pwa_manifest():
        response = send_from_directory(app.static_folder, 'manifest.json',
                                       mimetype='application/manifest+json')
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response

    @app.route('/pwa-launch')
    def pwa_launch():
        """Stable PWA start URL: always returns 200 then routes client-side."""
        target_url = url_for('dashboard') if current_user.is_authenticated else url_for('auth.login')
        response = make_response(render_template('pwa_launch.html', target_url=target_url))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response

    @app.route('/dashboard')
    @login_required
    def dashboard():
        return _role_redirect()

    def _role_redirect():
        if current_user.role == ROLE_ADMIN:
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == ROLE_SUPERVISOR:
            return redirect(url_for('supervisor.dashboard'))
        elif current_user.role == ROLE_EMPLOYER:
            return redirect(url_for('employer.dashboard'))
        elif current_user.role == ROLE_UNIVERSITY_COORD:
            return redirect(url_for('university.dashboard'))
        elif current_user.role == ROLE_STUDENT:
            return redirect(url_for('student.dashboard'))
        return redirect(url_for('user.dashboard'))

    # Context processor — available in all templates
    def _safe_current_ad():
        try:
            return get_current_ad(current_user if current_user.is_authenticated else None)
        except Exception:
            return None

    @app.context_processor
    def inject_globals():
        unread_messages = 0
        unread_notifications = 0
        managed_companies = []
        pending_sup_requests = 0
        pending_univ_requests = 0
        if current_user.is_authenticated:
            unread_messages = (Message.query
                               .filter_by(receiver_id=current_user.id, is_read=False)
                               .count())
            unread_notifications = (Notification.query
                                    .filter_by(user_id=current_user.id, is_read=False)
                                    .count())
            if current_user.role == ROLE_SUPERVISOR:
                managed_companies = (CompanyMember.query
                                     .filter_by(user_id=current_user.id, role='manager')
                                     .all())
            if current_user.role == ROLE_ADMIN:
                pending_sup_requests = (SupervisorRequest.query
                                        .filter_by(status='pending')
                                        .count())
                pending_univ_requests = (UniversityRequest.query
                                         .filter_by(status='pending')
                                         .count())
        from zoneinfo import ZoneInfo as _ZI
        return dict(
            now=datetime.now(_ZI('Asia/Baghdad')),
            ROLE_ADMIN=ROLE_ADMIN,
            ROLE_SUPERVISOR=ROLE_SUPERVISOR,
            ROLE_USER=ROLE_USER,
            ROLE_EMPLOYER=ROLE_EMPLOYER,
            ROLE_STUDENT=ROLE_STUDENT,
            ROLE_UNIVERSITY_COORD=ROLE_UNIVERSITY_COORD,
            unread_count=unread_messages,
            unread_notifications=unread_notifications,
            managed_companies=managed_companies,
            SALARY_RANGES=SALARY_RANGES,
            pending_sup_requests=pending_sup_requests,
            pending_univ_requests=pending_univ_requests,
            current_ad=_safe_current_ad(),
        )

    # Create DB tables and seed admin on first run
    with app.app_context():
        db.create_all()
        _migrate_db(app)
        _seed_admin(app)
        # Ensure all upload folders exist
        for folder_key in ('UPLOAD_FOLDER', 'AVATAR_FOLDER', 'PORTFOLIO_FOLDER', 'COMPANY_LOGO_FOLDER', 'REPORTS_FOLDER', 'ADS_FOLDER'):
            folder = app.config.get(folder_key)
            if folder:
                os.makedirs(folder, exist_ok=True)

    @app.errorhandler(413)
    def _too_large(e):
        mb = app.config.get('MAX_CONTENT_LENGTH', 0) // (1024 * 1024)
        flash(f'Upload too large. Maximum allowed file size is {mb} MB. Please compress the image and try again.', 'danger')
        return redirect(request.referrer or url_for('index'))

    return app


def _seed_admin(app):
    """Create default admin account if no users exist."""
    with app.app_context():
        if User.query.count() == 0:
            admin = User(
                full_name='Admin',
                email='admin@mof-eng.com',
                role=ROLE_ADMIN,
                is_active=True,
            )
            admin.set_password('Admin@1234')   # ← change on first login
            db.session.add(admin)
            db.session.commit()
            print('✓ Default admin created: admin@mof-eng.com / Admin@1234')


def _migrate_db(app):
    """Add new columns to existing tables (safe, idempotent)."""
    with app.app_context():
        with db.engine.connect() as conn:
            _safe_add_column(conn, 'companies', 'contact_email', 'VARCHAR(200)')
            _safe_add_column(conn, 'companies', 'contact_phone', 'VARCHAR(100)')
            _safe_add_column(conn, 'users', 'last_seen', 'DATETIME')
            # Student fields
            _safe_add_column(conn, 'users', 'university_id', 'INTEGER')
            _safe_add_column(conn, 'users', 'university_department_id', 'INTEGER')
            _safe_add_column(conn, 'users', 'university_name', 'VARCHAR(200)')
            _safe_add_column(conn, 'users', 'university_class', 'VARCHAR(100)')
            _safe_add_column(conn, 'users', 'university_major', 'VARCHAR(200)')
            _safe_add_column(conn, 'users', 'graduation_year', 'INTEGER')
            _safe_add_column(conn, 'users', 'student_id_number', 'VARCHAR(50)')
            _safe_add_column(conn, 'universities', 'banner_filename', 'VARCHAR(200)')
            # University coordinator scope fields
            _safe_add_column(conn, 'university_members', 'department_id', 'INTEGER')
            _safe_add_column(conn, 'university_members', 'class_scope', 'VARCHAR(100)')
            # Internship fields on applications
            _safe_add_column(conn, 'applications', 'internship_duration', 'VARCHAR(50)')
            _safe_add_column(conn, 'applications', 'internship_start_date', 'DATE')
            _safe_add_column(conn, 'applications', 'academic_credit_required', 'BOOLEAN')
            _safe_add_column(conn, 'applications', 'supervisor_evaluation', 'TEXT')
            _safe_add_column(conn, 'applications', 'evaluation_score', 'INTEGER')
            _safe_add_column(conn, 'applications', 'completion_confirmed', 'BOOLEAN')
            # Supervisor daily reminder preferences
            _safe_add_column(conn, 'users', 'daily_new_apps_reminder', 'BOOLEAN')
            _safe_add_column(conn, 'users', 'daily_reminder_last_sent', 'DATETIME')
            # Student weekly job-match digest preferences
            _safe_add_column(conn, 'users', 'weekly_job_match_digest', 'BOOLEAN')
            _safe_add_column(conn, 'users', 'job_match_digest_last_sent', 'DATETIME')
            # University coordinator weekly digest preferences
            _safe_add_column(conn, 'users', 'weekly_coord_digest', 'BOOLEAN')
            _safe_add_column(conn, 'users', 'coord_digest_last_sent', 'DATETIME')
            # Ads — separate mobile image
            _safe_add_column(conn, 'ads', 'mobile_image_path', 'VARCHAR(255)')
            _safe_add_column(conn, 'ads', 'mobile_image_name', 'VARCHAR(255)')
            _safe_add_column(conn, 'ads', 'mobile_image_mime', 'VARCHAR(80)')
            # Ads — audience targeting (CSV of roles or 'all')
            _safe_add_column(conn, 'ads', 'audience', "VARCHAR(255) DEFAULT 'all'")
            # Interview 24-hour reminder tracking
            _safe_add_column(conn, 'interviews', 'reminder_sent_at', 'DATETIME')
            # University verification (admin lock-down). After adding the
            # column, backfill all existing rows to verified=1 so admin-only
            # behavior is preserved for them; only newly-approved universities
            # will start unverified.
            added_verified = _safe_add_column(conn, 'universities', 'is_verified', 'BOOLEAN DEFAULT 0')
            _safe_add_column(conn, 'universities', 'verified_at', 'DATETIME')
            _safe_add_column(conn, 'universities', 'verified_by_id', 'INTEGER')
            if added_verified:
                from sqlalchemy import text as _text
                conn.execute(_text("UPDATE universities SET is_verified = 1 WHERE is_verified IS NULL OR is_verified = 0"))
                conn.commit()
                print('✓ Backfilled: existing universities marked verified')

            # Department uniqueness now spans (university_id, name, college).
            # The original CREATE TABLE baked a (university_id, name)-only
            # UNIQUE constraint into the table definition; in SQLite that
            # cannot be dropped with DROP INDEX/CONSTRAINT — the table must
            # be rebuilt. Detect and rebuild idempotently.
            try:
                from sqlalchemy import text as _text, inspect as _inspect
                # Drop any leftover legacy index name (no-op if absent).
                conn.execute(_text('DROP INDEX IF EXISTS uq_university_department_name'))
                conn.commit()

                inspector = _inspect(conn)
                tables = inspector.get_table_names()
                if 'university_departments' in tables:
                    # Read CREATE TABLE SQL to detect the legacy 2-column UNIQUE.
                    res = conn.execute(_text(
                        "SELECT sql FROM sqlite_master "
                        "WHERE type='table' AND name='university_departments'"
                    )).fetchone()
                    create_sql = (res[0] or '') if res else ''
                    needs_rebuild = (
                        'uq_university_department_name' in create_sql
                        and 'uq_university_department_name_college' not in create_sql
                    )
                    if needs_rebuild:
                        print('• Rebuilding university_departments to relax UNIQUE constraint …')
                        conn.execute(_text('PRAGMA foreign_keys=OFF'))
                        conn.execute(_text('BEGIN'))
                        try:
                            conn.execute(_text('''
                                CREATE TABLE university_departments__new (
                                    id INTEGER PRIMARY KEY,
                                    university_id INTEGER NOT NULL,
                                    name VARCHAR(200) NOT NULL,
                                    college VARCHAR(200),
                                    is_active BOOLEAN,
                                    created_at DATETIME,
                                    FOREIGN KEY(university_id) REFERENCES universities(id),
                                    CONSTRAINT uq_university_department_name_college
                                        UNIQUE (university_id, name, college)
                                )
                            '''))
                            conn.execute(_text('''
                                INSERT INTO university_departments__new
                                    (id, university_id, name, college, is_active, created_at)
                                SELECT id, university_id, name, college, is_active, created_at
                                FROM university_departments
                            '''))
                            conn.execute(_text('DROP TABLE university_departments'))
                            conn.execute(_text(
                                'ALTER TABLE university_departments__new '
                                'RENAME TO university_departments'
                            ))
                            conn.execute(_text('COMMIT'))
                            print('  ✓ university_departments rebuilt')
                        except Exception as rebuild_err:
                            conn.execute(_text('ROLLBACK'))
                            raise rebuild_err
                        finally:
                            conn.execute(_text('PRAGMA foreign_keys=ON'))
                            conn.commit()

                # Make sure the new composite unique index exists either way.
                conn.execute(_text(
                    'CREATE UNIQUE INDEX IF NOT EXISTS uq_university_department_name_college '
                    'ON university_departments(university_id, name, college)'
                ))
                conn.commit()
            except Exception as ex:
                print(f'  ! department index migration skipped: {ex}')

            # Deduplicate job_alerts — prevent the same search being saved twice.
            try:
                from sqlalchemy import text as _text
                conn.execute(_text(
                    'CREATE UNIQUE INDEX IF NOT EXISTS uq_job_alert_user_keywords_type_location '
                    'ON job_alerts(user_id, COALESCE(keywords,""), COALESCE(job_type,""), COALESCE(location,""))'
                ))
                conn.commit()
            except Exception as ex:
                print(f'  ! job_alerts dedup index skipped: {ex}')


def _safe_add_column(conn, table, column, col_type):
    """Add a column to a table if it doesn't already exist (SQLite safe)."""
    from sqlalchemy import text, inspect
    inspector = inspect(conn)
    existing = [c['name'] for c in inspector.get_columns(table)]
    if column not in existing:
        conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}'))
        conn.commit()
        print(f'✓ Migrated: added {table}.{column}')
        return True
    return False


# ─── HELPERS & DECORATORS (shared across routes) ──────────────────────────────
from helpers import (allowed_file, save_cv, send_email, log_history,
                     admin_required, supervisor_or_admin_required)


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5001)
