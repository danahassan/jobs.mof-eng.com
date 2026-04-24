import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-in-production-use-random-string')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Web Push (VAPID)
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '').replace('\\n', '\n')
    VAPID_PUBLIC_KEY  = os.environ.get('VAPID_PUBLIC_KEY', '')
    VAPID_SUBJECT     = os.environ.get('VAPID_SUBJECT', 'mailto:admin@mof-eng.com')

    # Canonical public URL — used to build links in emails (never changes based on request host)
    SITE_URL = os.environ.get('SITE_URL', 'https://jobs.mof-eng.com')

    # File uploads
    UPLOAD_FOLDER        = os.path.join(BASE_DIR, 'static', 'uploads', 'cvs')
    AVATAR_FOLDER        = os.path.join(BASE_DIR, 'static', 'uploads', 'avatars')
    PORTFOLIO_FOLDER     = os.path.join(BASE_DIR, 'static', 'uploads', 'portfolio')
    COMPANY_LOGO_FOLDER   = os.path.join(BASE_DIR, 'static', 'uploads', 'company')
    COMPANY_PHOTOS_FOLDER  = os.path.join(BASE_DIR, 'static', 'uploads', 'company_photos')
    REPORTS_FOLDER         = os.path.join(BASE_DIR, 'static', 'uploads', 'reports')
    ADS_FOLDER             = os.path.join(BASE_DIR, 'static', 'uploads', 'ads')
    MAX_CONTENT_LENGTH   = 25 * 1024 * 1024  # 25 MB
    ALLOWED_EXTENSIONS   = {'pdf', 'doc', 'docx'}
    REPORT_ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'odt', 'rtf', 'txt',
                                 'ppt', 'pptx', 'xls', 'xlsx', 'csv',
                                 'jpg', 'jpeg', 'png', 'zip'}
    AD_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}

    # Email (uses your existing no-reply@mof-eng.com setup)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'mail.mof-eng.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'no-reply@mof-eng.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = 'MOF Jobs <no-reply@mof-eng.com>'

    # Pagination
    APPLICATIONS_PER_PAGE = 25
    POSITIONS_PER_PAGE = 20

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'careers.db')
    # Lax is required on HTTP localhost — SameSite=None demands Secure=True which
    # browsers enforce strictly, causing logout cookies to be ignored on plain HTTP.
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE   = False

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'careers.db')
    # OR switch to MySQL on cPanel:
    # SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://user:pass@localhost/mofengco_careers'
    SESSION_COOKIE_SECURE   = True    # HTTPS only
    SESSION_COOKIE_HTTPONLY = True    # no JS access
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
    REMEMBER_COOKIE_SECURE  = True
    REMEMBER_COOKIE_HTTPONLY= True

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
