from datetime import datetime, date
import json
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from slugify import slugify

db = SQLAlchemy()

# ─── ROLES ────────────────────────────────────────────────────────────────────
ROLE_ADMIN      = 'admin'
ROLE_SUPERVISOR = 'supervisor'
ROLE_EMPLOYER   = 'employer'
ROLE_USER       = 'user'

EXPERIENCE_LEVELS = ['Entry Level', 'Junior', 'Mid-Level', 'Senior', 'Lead', 'Manager', 'Director']
JOB_TYPES         = ['Full-time', 'Part-time', 'Contract', 'Freelance', 'Internship', 'Temporary']
COMPANY_SIZES     = ['1–10', '11–50', '51–200', '201–500', '501–1000', '1000+']
LANG_LEVELS       = ['Native', 'Fluent', 'Advanced', 'Intermediate', 'Basic']

# ─── APPLICATION STATUSES ─────────────────────────────────────────────────────
STATUS_NEW         = 'New'
STATUS_REVIEW      = 'Under Review'
STATUS_INTERVIEW   = 'Interview'
STATUS_OFFER       = 'Offer'
STATUS_HIRED       = 'Hired'
STATUS_REJECTED    = 'Rejected'
STATUS_FUTURE      = 'Future Consideration'

ALL_STATUSES = [STATUS_NEW, STATUS_REVIEW, STATUS_INTERVIEW,
                STATUS_OFFER, STATUS_HIRED, STATUS_REJECTED, STATUS_FUTURE]

# ─── SOURCES ──────────────────────────────────────────────────────────────────
SOURCES = ['Website', 'LinkedIn', 'Referral', 'Walk-in', 'Other']

# ─── SALARY RANGES (IQD) ─────────────────────────────────────────────────────
SALARY_RANGES = [
    'Less than 500,000 IQD',
    '500,000 – 1,000,000 IQD',
    '1,000,000 – 1,500,000 IQD',
    '1,500,000 – 2,000,000 IQD',
    '2,000,000 – 3,000,000 IQD',
    '3,000,000 – 3,500,000 IQD',
    '3,500,000 – 4,000,000 IQD',
    '4,000,000 – 5,000,000 IQD',
    '5,000,000 – 6,000,000 IQD',
    '6,000,000 – 7,000,000 IQD',
    '7,000,000 – 8,000,000 IQD',
    '8,000,000 – 9,000,000 IQD',
    '9,000,000 – 10,000,000 IQD',
    'Above 10,000,000 IQD',
]


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    full_name     = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20), nullable=False, default=ROLE_USER)
    phone         = db.Column(db.String(30))
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    last_login    = db.Column(db.DateTime)
    last_seen     = db.Column(db.DateTime)
    bio           = db.Column(db.Text)
    linkedin_url  = db.Column(db.String(200))
    github_url    = db.Column(db.String(200))
    portfolio_url = db.Column(db.String(200))
    totp_secret   = db.Column(db.String(64))
    totp_enabled  = db.Column(db.Boolean, default=False)

    # Extended profile
    avatar_filename = db.Column(db.String(200))
    headline        = db.Column(db.String(200))   # e.g. "Senior Software Engineer"
    location_city   = db.Column(db.String(100))
    date_of_birth   = db.Column(db.Date)
    nationality     = db.Column(db.String(50))
    gender          = db.Column(db.String(20))
    resume_headline = db.Column(db.String(300))   # one-line resume summary

    # Relationships
    applications      = db.relationship('Application', foreign_keys='Application.applicant_id',
                                        back_populates='applicant', lazy='dynamic')
    supervised_apps   = db.relationship('Application', foreign_keys='Application.assigned_to_id',
                                        back_populates='assigned_to', lazy='dynamic')
    skills            = db.relationship('UserSkill',      back_populates='user', lazy='dynamic',
                                        cascade='all,delete-orphan')
    experiences       = db.relationship('UserExperience', back_populates='user', lazy='dynamic',
                                        cascade='all,delete-orphan')
    educations        = db.relationship('UserEducation',  back_populates='user', lazy='dynamic',
                                        cascade='all,delete-orphan')
    notifications_rel = db.relationship('Notification',   back_populates='user', lazy='dynamic',
                                        cascade='all,delete-orphan')
    saved_jobs_rel    = db.relationship('SavedJob',       back_populates='user', lazy='dynamic',
                                        cascade='all,delete-orphan')
    languages         = db.relationship('UserLanguage',      back_populates='user', lazy='dynamic',
                                        cascade='all,delete-orphan')
    certifications    = db.relationship('UserCertification', back_populates='user', lazy='dynamic',
                                        cascade='all,delete-orphan')
    portfolio_items   = db.relationship('UserPortfolioItem', back_populates='user', lazy='dynamic',
                                        cascade='all,delete-orphan')
    job_alerts        = db.relationship('JobAlert',          back_populates='user', lazy='dynamic',
                                        cascade='all,delete-orphan')
    connections_sent  = db.relationship('UserConnection',
                                        foreign_keys='UserConnection.requester_id',
                                        back_populates='requester', lazy='dynamic')
    connections_rcvd  = db.relationship('UserConnection',
                                        foreign_keys='UserConnection.recipient_id',
                                        back_populates='recipient', lazy='dynamic')
    assessment_submissions = db.relationship('AssessmentSubmission', back_populates='user',
                                             lazy='dynamic', cascade='all,delete-orphan')
    company_memberships    = db.relationship('CompanyMember', back_populates='user',
                                             lazy='dynamic', cascade='all,delete-orphan')
    company_follows        = db.relationship('CompanyFollow', back_populates='user',
                                             lazy='dynamic', cascade='all,delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        # Handle PHP bcrypt hashes ($2y$) — swap prefix to Python-compatible $2b$
        if self.password_hash and self.password_hash.startswith('$2y$'):
            try:
                import bcrypt as _bcrypt
                compat = self.password_hash.replace('$2y$', '$2b$', 1).encode('utf-8')
                matched = _bcrypt.checkpw(password.encode('utf-8'), compat)
                if matched:
                    # Silently upgrade to werkzeug hash so future logins skip bcrypt
                    self.password_hash = generate_password_hash(password)
                return matched
            except Exception:
                pass
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN

    @property
    def is_supervisor(self):
        return self.role == ROLE_SUPERVISOR

    @property
    def initials(self):
        parts = self.full_name.split()
        return (parts[0][0] + parts[-1][0]).upper() if len(parts) > 1 else parts[0][:2].upper()

    @property
    def is_employer(self):
        return self.role == ROLE_EMPLOYER

    @property
    def profile_strength(self):
        score = 0
        if self.full_name:                       score += 10
        if self.headline:                         score += 5
        if self.phone:                            score += 5
        if self.bio:                              score += 10
        if self.avatar_filename:                  score += 10
        if self.location_city:                    score += 5
        if self.linkedin_url or self.portfolio_url: score += 5
        if self.skills.count() >= 3:             score += 15
        if self.experiences.count() > 0:         score += 15
        if self.educations.count() > 0:          score += 10
        if self.languages.count() > 0:           score += 5
        if self.certifications.count() > 0:      score += 5
        return min(score, 100)

    def __repr__(self):
        return f'<User {self.email} [{self.role}]>'


class Position(db.Model):
    __tablename__ = 'positions'

    id               = db.Column(db.Integer, primary_key=True)
    title            = db.Column(db.String(200), nullable=False)
    company_id       = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True, index=True)
    department       = db.Column(db.String(100))
    location         = db.Column(db.String(200), default='Slemani, Iraq')
    type             = db.Column(db.String(50), default='Full-time')
    description      = db.Column(db.Text)
    requirements     = db.Column(db.Text)
    benefits         = db.Column(db.Text)
    skills_required  = db.Column(db.Text)
    salary_range     = db.Column(db.String(100))
    salary_min       = db.Column(db.Integer)
    salary_max       = db.Column(db.Integer)
    experience_level = db.Column(db.String(50))
    is_active        = db.Column(db.Boolean, default=True)
    is_remote        = db.Column(db.Boolean, default=False)
    views_count      = db.Column(db.Integer, default=0)
    closes_at        = db.Column(db.DateTime)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    created_by       = db.Column(db.Integer, db.ForeignKey('users.id'))

    company      = db.relationship('Company', back_populates='positions',
                                   foreign_keys=[company_id])
    applications = db.relationship('Application', back_populates='position',
                                   lazy='dynamic', cascade='all,delete-orphan')

    @property
    def application_count(self):
        return self.applications.count()

    @property
    def is_closing_soon(self):
        if self.closes_at:
            delta = self.closes_at - datetime.utcnow()
            return 0 <= delta.days <= 14
        return False

    def __repr__(self):
        return f'<Position {self.title}>'


class Application(db.Model):
    __tablename__ = 'applications'

    id             = db.Column(db.Integer, primary_key=True)
    applicant_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    position_id    = db.Column(db.Integer, db.ForeignKey('positions.id'), nullable=False, index=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    status         = db.Column(db.String(30), default=STATUS_NEW, index=True)
    source         = db.Column(db.String(50), default='Website')
    cover_letter   = db.Column(db.Text)
    cv_filename    = db.Column(db.String(200))    # stored filename in uploads/cvs/
    cv_original    = db.Column(db.String(200))    # original uploaded filename
    notes             = db.Column(db.Text)           # internal admin/supervisor notes
    expected_salary   = db.Column(db.String(100))    # applicant's expected salary range

    applied_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    applicant    = db.relationship('User', foreign_keys=[applicant_id], back_populates='applications')
    position     = db.relationship('Position', back_populates='applications')
    assigned_to  = db.relationship('User', foreign_keys=[assigned_to_id], back_populates='supervised_apps')
    history      = db.relationship('ApplicationHistory', back_populates='application',
                                   order_by='ApplicationHistory.created_at', lazy='dynamic')
    interviews   = db.relationship('Interview', back_populates='application', lazy='dynamic')

    def __repr__(self):
        return f'<Application #{self.id} {self.status}>'


class ApplicationHistory(db.Model):
    """Audit trail — every status change or note is logged here."""
    __tablename__ = 'application_history'

    id             = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False, index=True)
    changed_by_id  = db.Column(db.Integer, db.ForeignKey('users.id'))
    old_status     = db.Column(db.String(30))
    new_status     = db.Column(db.String(30))
    note           = db.Column(db.Text)
    is_internal    = db.Column(db.Boolean, default=False)   # True = admin-only, hidden from supervisors & users
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    application = db.relationship('Application', back_populates='history')
    changed_by  = db.relationship('User')


class Interview(db.Model):
    __tablename__ = 'interviews'

    id             = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)
    scheduled_at   = db.Column(db.DateTime, nullable=False)
    location       = db.Column(db.String(200))     # room, address, or "Online - Zoom"
    interviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    notes          = db.Column(db.Text)
    result         = db.Column(db.String(30))       # Pass / Fail / No-show
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    application = db.relationship('Application', back_populates='interviews')
    interviewer = db.relationship('User')


class Message(db.Model):
    """Direct messages between users with role-based privilege."""
    __tablename__ = 'messages'

    id          = db.Column(db.Integer, primary_key=True)
    sender_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    subject     = db.Column(db.String(200))
    body        = db.Column(db.Text, nullable=False)
    is_read     = db.Column(db.Boolean, default=False)
    deleted_by_sender   = db.Column(db.Boolean, default=False)
    deleted_by_receiver = db.Column(db.Boolean, default=False)
    # thread_id = ID of the first message; replies share this ID
    thread_id   = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    sender   = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')
    replies  = db.relationship('Message', foreign_keys='Message.thread_id',
                               backref=db.backref('thread_parent', remote_side='Message.id'),
                               lazy='dynamic')

    def __repr__(self):
        return f'<Message #{self.id} from {self.sender_id} to {self.receiver_id}>'


class AuditLog(db.Model):
    """System-wide audit trail for admin actions beyond application history."""
    __tablename__ = 'audit_log'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'))
    action     = db.Column(db.String(100), nullable=False)   # e.g. 'user.create', 'position.edit'
    target     = db.Column(db.String(200))                   # human-readable description
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')

    def __repr__(self):
        return f'<AuditLog {self.action} by {self.user_id}>'


class UserSkill(db.Model):
    __tablename__ = 'user_skills'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name        = db.Column(db.String(100), nullable=False)
    proficiency = db.Column(db.String(20), default='intermediate')
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', back_populates='skills')


class UserExperience(db.Model):
    __tablename__ = 'user_experiences'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title       = db.Column(db.String(150), nullable=False)
    company     = db.Column(db.String(150))
    start_date  = db.Column(db.Date)
    end_date    = db.Column(db.Date)
    description = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', back_populates='experiences')


class UserEducation(db.Model):
    __tablename__ = 'user_educations'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    institution = db.Column(db.String(200), nullable=False)
    degree      = db.Column(db.String(100))
    field       = db.Column(db.String(150))
    start_year  = db.Column(db.Integer)
    end_year    = db.Column(db.Integer)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', back_populates='educations')



class UserLanguage(db.Model):
    __tablename__ = 'user_languages'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    language    = db.Column(db.String(100), nullable=False)
    proficiency = db.Column(db.String(30), default='Intermediate')
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', back_populates='languages')


class UserCertification(db.Model):
    __tablename__ = 'user_certifications'
    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name           = db.Column(db.String(200), nullable=False)
    issuing_org    = db.Column(db.String(200))
    credential_id  = db.Column(db.String(100))
    credential_url = db.Column(db.String(300))
    issue_date     = db.Column(db.Date)
    expiry_date    = db.Column(db.Date)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', back_populates='certifications')


class UserPortfolioItem(db.Model):
    __tablename__ = 'user_portfolio_items'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    url         = db.Column(db.String(300))
    filename    = db.Column(db.String(200))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', back_populates='portfolio_items')


class Notification(db.Model):
    __tablename__ = 'notifications'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    message    = db.Column(db.String(300), nullable=False)
    link       = db.Column(db.String(300))
    icon       = db.Column(db.String(50), default='bi-bell-fill')
    is_read    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', back_populates='notifications_rel')


class SavedJob(db.Model):
    __tablename__ = 'saved_jobs'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'), nullable=False)
    saved_at    = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'position_id', name='uq_saved_job'),)
    user     = db.relationship('User', back_populates='saved_jobs_rel')
    position = db.relationship('Position')


# ─────────────────────────────────────────────────────────────────────────────
# COMPANY & EMPLOYER
# ─────────────────────────────────────────────────────────────────────────────

class Company(db.Model):
    __tablename__ = 'companies'

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(200), nullable=False)
    slug          = db.Column(db.String(200), unique=True, nullable=False, index=True)
    description   = db.Column(db.Text)
    industry      = db.Column(db.String(100))
    size          = db.Column(db.String(30))           # '1–10', '11–50' …
    website       = db.Column(db.String(300))
    logo_filename = db.Column(db.String(200))
    cover_filename= db.Column(db.String(200))
    location      = db.Column(db.String(200))
    founded_year  = db.Column(db.Integer)
    contact_email = db.Column(db.String(200))
    contact_phone = db.Column(db.String(100))
    is_verified   = db.Column(db.Boolean, default=False)
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    created_by    = db.Column(db.Integer, db.ForeignKey('users.id'))

    positions  = db.relationship('Position', back_populates='company',
                                  foreign_keys='Position.company_id', lazy='dynamic')
    members    = db.relationship('CompanyMember', back_populates='company',
                                  lazy='dynamic', cascade='all,delete-orphan')
    followers  = db.relationship('CompanyFollow', back_populates='company',
                                  lazy='dynamic', cascade='all,delete-orphan')
    photos     = db.relationship('CompanyPhoto', back_populates='company',
                                  lazy='dynamic', cascade='all,delete-orphan',
                                  order_by='CompanyPhoto.uploaded_at')
    creator    = db.relationship('User', foreign_keys=[created_by])

    def save_slug(self):
        base = slugify(self.name)
        slug = base
        i = 2
        while Company.query.filter_by(slug=slug).first():
            slug = f'{base}-{i}'; i += 1
        self.slug = slug

    @property
    def follower_count(self):
        return self.followers.count()

    @property
    def open_jobs_count(self):
        return self.positions.filter_by(is_active=True).count()

    def __repr__(self):
        return f'<Company {self.name}>'


class CompanyPhoto(db.Model):
    __tablename__ = 'company_photos'

    id          = db.Column(db.Integer, primary_key=True)
    company_id  = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    filename    = db.Column(db.String(200), nullable=False)
    caption     = db.Column(db.String(200))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    company  = db.relationship('Company', back_populates='photos')
    uploader = db.relationship('User', foreign_keys=[uploaded_by])


class CompanyMember(db.Model):
    """Links employer users or supervisors to a company."""
    __tablename__ = 'company_members'

    id         = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role       = db.Column(db.String(30), default='owner')  # owner | recruiter | manager
    joined_at  = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('company_id', 'user_id'),)

    company = db.relationship('Company', back_populates='members')
    user    = db.relationship('User', back_populates='company_memberships')


class CompanyFollow(db.Model):
    __tablename__ = 'company_follows'

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    company_id  = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    followed_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'company_id'),)

    user    = db.relationship('User', back_populates='company_follows')
    company = db.relationship('Company', back_populates='followers')


# ─────────────────────────────────────────────────────────────────────────────
# EXTENDED CANDIDATE PROFILE
# ─────────────────────────────────────────────────────────────────────────────




class JobAlert(db.Model):
    """Saved search that triggers email alerts when matching jobs are posted."""
    __tablename__ = 'job_alerts'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    keywords   = db.Column(db.String(200))
    location   = db.Column(db.String(100))
    job_type   = db.Column(db.String(50))
    is_remote  = db.Column(db.Boolean)
    is_active  = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_sent  = db.Column(db.DateTime)

    user = db.relationship('User', back_populates='job_alerts')


# ─────────────────────────────────────────────────────────────────────────────
# PROFESSIONAL CONNECTIONS
# ─────────────────────────────────────────────────────────────────────────────

class UserConnection(db.Model):
    __tablename__ = 'user_connections'

    id           = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status       = db.Column(db.String(20), default='pending')  # pending|accepted|rejected
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('requester_id', 'recipient_id'),)

    requester = db.relationship('User', foreign_keys=[requester_id], back_populates='connections_sent')
    recipient = db.relationship('User', foreign_keys=[recipient_id], back_populates='connections_rcvd')


# ─────────────────────────────────────────────────────────────────────────────
# ASSESSMENTS
# ─────────────────────────────────────────────────────────────────────────────

class Assessment(db.Model):
    __tablename__ = 'assessments'

    id              = db.Column(db.Integer, primary_key=True)
    title           = db.Column(db.String(200), nullable=False)
    description     = db.Column(db.Text)
    position_id     = db.Column(db.Integer, db.ForeignKey('positions.id'))  # optional job link
    time_limit_mins = db.Column(db.Integer, default=30)
    pass_score      = db.Column(db.Integer, default=70)   # percentage
    is_active       = db.Column(db.Boolean, default=True)
    created_by      = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    questions   = db.relationship('AssessmentQuestion', back_populates='assessment',
                                   order_by='AssessmentQuestion.order', lazy='dynamic',
                                   cascade='all,delete-orphan')
    submissions = db.relationship('AssessmentSubmission', back_populates='assessment',
                                   lazy='dynamic', cascade='all,delete-orphan')
    position    = db.relationship('Position')
    creator     = db.relationship('User', foreign_keys=[created_by])

    @property
    def question_count(self):
        return self.questions.count()

    @property
    def total_points(self):
        return db.session.query(db.func.sum(AssessmentQuestion.points)).filter_by(
            assessment_id=self.id).scalar() or 0


class AssessmentQuestion(db.Model):
    __tablename__ = 'assessment_questions'

    id            = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), default='mcq')  # mcq | text | true_false
    options_json  = db.Column(db.Text)    # JSON array of strings (MCQ options)
    correct_answer= db.Column(db.Text)    # MCQ: "0" (index) | text: exact answer | tf: "true"/"false"
    explanation   = db.Column(db.Text)
    points        = db.Column(db.Integer, default=1)
    order         = db.Column(db.Integer, default=0)

    assessment = db.relationship('Assessment', back_populates='questions')

    @property
    def options(self):
        try:
            return json.loads(self.options_json) if self.options_json else []
        except Exception:
            return []

    @options.setter
    def options(self, value):
        self.options_json = json.dumps(value, ensure_ascii=False)


class AssessmentSubmission(db.Model):
    __tablename__ = 'assessment_submissions'

    id             = db.Column(db.Integer, primary_key=True)
    assessment_id  = db.Column(db.Integer, db.ForeignKey('assessments.id'), nullable=False)
    user_id        = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'))
    score          = db.Column(db.Float)
    max_score      = db.Column(db.Float)
    percentage     = db.Column(db.Float)
    passed         = db.Column(db.Boolean)
    started_at     = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at   = db.Column(db.DateTime)

    assessment  = db.relationship('Assessment', back_populates='submissions')
    user        = db.relationship('User', back_populates='assessment_submissions')
    answers     = db.relationship('AssessmentAnswer', back_populates='submission',
                                   lazy='dynamic', cascade='all,delete-orphan')
    application = db.relationship('Application')


class AssessmentAnswer(db.Model):
    __tablename__ = 'assessment_answers'

    id            = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('assessment_submissions.id'), nullable=False)
    question_id   = db.Column(db.Integer, db.ForeignKey('assessment_questions.id'), nullable=False)
    answer_text   = db.Column(db.Text)
    is_correct    = db.Column(db.Boolean)
    points_earned = db.Column(db.Float, default=0)

    submission = db.relationship('AssessmentSubmission', back_populates='answers')
    question   = db.relationship('AssessmentQuestion')


# Ensure all string-based relationship references resolve after every class is defined.
# This prevents SQLAlchemy mapper errors during Flask hot-reload.
from sqlalchemy.orm import configure_mappers  # noqa: E402
configure_mappers()

