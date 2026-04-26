import os
from datetime import datetime

from flask import (Flask, render_template, redirect, url_for, flash,
                   request, abort, send_from_directory, current_app, make_response)
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)

from config import config
from models import (db, User, Message, Notification, Position, Application, ApplicationHistory,
                    Interview, CompanyMember, ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_USER, ROLE_EMPLOYER,
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

    # Register blueprints
    from routes.auth          import auth_bp
    from routes.admin         import admin_bp
    from routes.supervisor    import supervisor_bp
    from routes.user          import user_bp
    from routes.messages      import messages_bp
    from routes.notifications import notifications_bp
    from routes.employer      import employer_bp
    from routes.company       import company_bp
    from routes.jobs          import jobs_bp
    from routes.profile       import profile_bp
    from routes.assessments   import assessments_bp
    from routes.analytics     import analytics_bp
    from routes.api           import api_bp
    from routes.supervisor_apply import supervisor_apply_bp
    from routes.university_apply import university_apply_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp,          url_prefix='/admin')
    app.register_blueprint(supervisor_bp,     url_prefix='/supervisor')
    app.register_blueprint(user_bp,           url_prefix='/portal')
    app.register_blueprint(messages_bp,       url_prefix='/messages')
    app.register_blueprint(notifications_bp,  url_prefix='/notifications')
    app.register_blueprint(employer_bp,       url_prefix='/employer')
    app.register_blueprint(company_bp,        url_prefix='/companies')
    app.register_blueprint(jobs_bp,           url_prefix='/jobs')
    app.register_blueprint(profile_bp,        url_prefix='/profile')
    app.register_blueprint(assessments_bp,    url_prefix='/assessments')
    app.register_blueprint(analytics_bp,      url_prefix='/analytics')
    app.register_blueprint(api_bp,            url_prefix='/api/v1')
    app.register_blueprint(supervisor_apply_bp)
    app.register_blueprint(university_apply_bp)

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
        return redirect(url_for('user.dashboard'))

    # Context processor — available in all templates
    @app.context_processor
    def inject_globals():
        unread_messages = 0
        unread_notifications = 0
        managed_companies = []
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
        return dict(
            now=datetime.utcnow(),
            ROLE_ADMIN=ROLE_ADMIN,
            ROLE_SUPERVISOR=ROLE_SUPERVISOR,
            ROLE_USER=ROLE_USER,
            ROLE_EMPLOYER=ROLE_EMPLOYER,
            unread_count=unread_messages,
            unread_notifications=unread_notifications,
            managed_companies=managed_companies,
            SALARY_RANGES=SALARY_RANGES,
        )

    # Create DB tables and seed admin on first run
    with app.app_context():
        db.create_all()
        _seed_admin(app)
        _migrate_db(app)
        # Ensure all upload folders exist
        for folder_key in ('UPLOAD_FOLDER', 'AVATAR_FOLDER', 'PORTFOLIO_FOLDER', 'COMPANY_LOGO_FOLDER'):
            folder = app.config.get(folder_key)
            if folder:
                os.makedirs(folder, exist_ok=True)

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


def _safe_add_column(conn, table, column, col_type):
    """Add a column to a table if it doesn't already exist (SQLite safe)."""
    from sqlalchemy import text, inspect
    inspector = inspect(conn)
    existing = [c['name'] for c in inspector.get_columns(table)]
    if column not in existing:
        conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}'))
        conn.commit()
        print(f'✓ Migrated: added {table}.{column}')


# ─── HELPERS & DECORATORS (shared across routes) ──────────────────────────────
from helpers import (allowed_file, save_cv, send_email, log_history,
                     admin_required, supervisor_or_admin_required)


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5001)
