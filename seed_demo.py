"""
seed_demo.py — Populate the database with realistic demo data.
Run from project root:  python seed_demo.py
Safe to re-run: checks for existing emails/slugs before inserting.
"""
from datetime import datetime, timedelta, date
import random

from app import create_app
from models import (
    db, User, Position, Application, ApplicationHistory,
    Company, CompanyMember, CompanyFollow,
    UserSkill, UserExperience, UserEducation,
    ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_USER,
    STATUS_NEW, STATUS_REVIEW, STATUS_INTERVIEW, STATUS_OFFER, STATUS_HIRED, STATUS_REJECTED,
    ALL_STATUSES, SOURCES,
)

app = create_app()

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def ago(days=0, hours=0):
    return datetime.utcnow() - timedelta(days=days, hours=hours)


def get_or_create_user(full_name, email, role, phone=None, **kwargs):
    u = User.query.filter_by(email=email).first()
    if u:
        return u, False
    u = User(full_name=full_name, email=email, role=role, phone=phone,
             is_active=True, created_at=ago(random.randint(30, 365)), **kwargs)
    u.set_password('Demo@1234')
    db.session.add(u)
    return u, True


# ─────────────────────────────────────────────────────────────────────────────
# DATA DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

COMPANIES_DATA = [
    {
        'name': 'MOF Engineering Co.',
        'industry': 'Engineering',
        'size': '201–500',
        'location': 'Slemani, Iraq',
        'website': 'https://mof-eng.com',
        'contact_email': 'hr@mof-eng.com',
        'contact_phone': '+964 770 100 1000',
        'founded_year': 2005,
        'is_verified': True,
        'description': (
            'MOF Engineering is a leading multidisciplinary engineering firm based in Slemani, Iraq. '
            'We specialise in civil, structural, mechanical, and electrical engineering projects '
            'across the Kurdistan Region and beyond. Our team of 300+ engineers delivers projects '
            'in infrastructure, oil & gas, construction, and sustainable energy.'
        ),
    },
    {
        'name': 'Kurdistan Tech Solutions',
        'industry': 'Information Technology',
        'size': '51–200',
        'location': 'Erbil, Iraq',
        'website': 'https://kts.iq',
        'contact_email': 'careers@kts.iq',
        'contact_phone': '+964 750 200 2000',
        'founded_year': 2013,
        'is_verified': True,
        'description': (
            'Kurdistan Tech Solutions provides cutting-edge software development, IT consulting, '
            'and digital transformation services to businesses across the Middle East. '
            'We build SaaS platforms, mobile apps, and enterprise systems with a team of '
            '150 passionate technologists.'
        ),
    },
    {
        'name': 'Zagros Construction Group',
        'industry': 'Construction',
        'size': '201–500',
        'location': 'Sulaymaniyah, Iraq',
        'website': 'https://zagros-group.com',
        'contact_email': 'jobs@zagros-group.com',
        'contact_phone': '+964 751 300 3000',
        'founded_year': 1998,
        'is_verified': False,
        'description': (
            'Zagros Construction Group is one of the oldest and most trusted construction companies '
            'in Iraqi Kurdistan. With over 25 years of experience, we have delivered residential, '
            'commercial, and government projects worth over $2 billion. Known for quality and '
            'on-time delivery.'
        ),
    },
]

SUPERVISORS_DATA = [
    {
        'full_name': 'Sara Hassan',
        'email': 'sara.hassan@mof-eng.com',
        'phone': '+964 770 111 2233',
        'bio': 'HR Manager with 8 years in talent acquisition and performance management.',
        'headline': 'HR & Recruitment Manager',
        'location_city': 'Slemani',
    },
    {
        'full_name': 'Karim Aziz',
        'email': 'karim.aziz@kts.iq',
        'phone': '+964 750 222 3344',
        'bio': 'Senior Engineering Supervisor overseeing software and infrastructure teams.',
        'headline': 'Engineering Team Lead',
        'location_city': 'Erbil',
    },
    {
        'full_name': 'Nadia Jalal',
        'email': 'nadia.jalal@zagros-group.com',
        'phone': '+964 751 333 4455',
        'bio': 'Operations supervisor with expertise in civil project management.',
        'headline': 'Operations Supervisor',
        'location_city': 'Sulaymaniyah',
    },
]

POSITIONS_DATA = [
    # MOF Engineering (company index 0)
    {
        'title': 'Senior Civil Engineer',
        'department': 'Civil Engineering',
        'location': 'Slemani, Iraq',
        'type': 'Full-time',
        'description': (
            'We are looking for an experienced Senior Civil Engineer to lead design and '
            'construction supervision of infrastructure projects. You will manage a team '
            'of junior engineers, liaise with government clients, and ensure compliance '
            'with international standards (AASHTO, ACI, AISC).'
        ),
        'requirements': (
            '• BSc or MSc in Civil Engineering\n'
            '• 7+ years of relevant experience\n'
            '• Proficiency in AutoCAD, Civil 3D, and SAP2000\n'
            '• Strong project management skills\n'
            '• PMP or PE certification preferred'
        ),
        'salary_range': '$2,000–$3,500/mo',
        'experience_level': 'Senior',
        'is_active': True,
        'company_idx': 0,
        'closes_days': 45,
    },
    {
        'title': 'Structural Engineer',
        'department': 'Structural Engineering',
        'location': 'Slemani, Iraq',
        'type': 'Full-time',
        'description': (
            'Design and analyse structural systems for commercial and residential buildings. '
            'Work closely with architects and MEP teams to deliver integrated structural solutions.'
        ),
        'requirements': (
            '• BSc in Civil / Structural Engineering\n'
            '• 4+ years in structural design\n'
            '• ETABS, SAP2000, SAFE proficiency required\n'
            '• Knowledge of ACI 318 and AISC standards'
        ),
        'salary_range': '$1,500–$2,500/mo',
        'experience_level': 'Mid-Level',
        'is_active': True,
        'company_idx': 0,
        'closes_days': 30,
    },
    {
        'title': 'Mechanical Engineer — HVAC',
        'department': 'Mechanical Engineering',
        'location': 'Slemani, Iraq',
        'type': 'Full-time',
        'description': (
            'Design and oversee HVAC, plumbing, and fire protection systems for '
            'large commercial and industrial facilities.'
        ),
        'requirements': (
            '• BSc in Mechanical Engineering\n'
            '• 3+ years in HVAC / MEP design\n'
            '• AutoCAD MEP and Revit MEP experience\n'
            '• Knowledge of ASHRAE standards'
        ),
        'salary_range': '$1,400–$2,200/mo',
        'experience_level': 'Mid-Level',
        'is_active': True,
        'company_idx': 0,
        'closes_days': 20,
    },
    # Kurdistan Tech Solutions (company index 1)
    {
        'title': 'Full-Stack Web Developer',
        'department': 'Software Development',
        'location': 'Erbil, Iraq',
        'type': 'Full-time',
        'description': (
            'Build and maintain scalable web applications using modern stacks. '
            'You will work in agile sprints, collaborate with product managers and designers, '
            'and take ownership of features from design to production.'
        ),
        'requirements': (
            '• 3+ years in full-stack development\n'
            '• Proficiency in React / Vue.js + Node.js or Python/Django\n'
            '• Experience with PostgreSQL or MySQL\n'
            '• RESTful API design, Git workflow\n'
            '• Docker / CI-CD knowledge is a plus'
        ),
        'salary_range': '$1,800–$2,800/mo',
        'experience_level': 'Mid-Level',
        'is_active': True,
        'company_idx': 1,
        'closes_days': 25,
    },
    {
        'title': 'Data Analyst',
        'department': 'Business Intelligence',
        'location': 'Erbil, Iraq',
        'type': 'Full-time',
        'description': (
            'Analyse business data, build dashboards, and deliver actionable insights '
            'to product and executive teams. Work with large datasets across multiple '
            'client verticals.'
        ),
        'requirements': (
            '• BSc in Statistics, Computer Science, or related field\n'
            '• 2+ years in data analysis\n'
            '• Power BI or Tableau expertise\n'
            '• SQL proficiency required\n'
            '• Python (pandas, numpy) is a strong plus'
        ),
        'salary_range': '$1,200–$1,800/mo',
        'experience_level': 'Junior',
        'is_active': True,
        'company_idx': 1,
        'closes_days': 15,
    },
    {
        'title': 'DevOps Engineer',
        'department': 'Infrastructure',
        'location': 'Erbil, Iraq',
        'type': 'Full-time',
        'description': (
            'Own our cloud infrastructure, build CI/CD pipelines, and ensure 99.9% uptime '
            'for our SaaS platform. Partner with development teams to improve deployment '
            'speed and reliability.'
        ),
        'requirements': (
            '• 3+ years in DevOps / SRE\n'
            '• AWS or Azure experience required\n'
            '• Strong Kubernetes + Docker skills\n'
            '• Terraform / Ansible for IaC\n'
            '• Linux systems administration'
        ),
        'salary_range': '$2,000–$3,000/mo',
        'experience_level': 'Senior',
        'is_active': True,
        'company_idx': 1,
        'closes_days': 40,
    },
    # Zagros Construction (company index 2)
    {
        'title': 'Site Project Manager',
        'department': 'Project Management',
        'location': 'Sulaymaniyah, Iraq',
        'type': 'Full-time',
        'description': (
            'Lead on-site construction operations for a major residential complex project. '
            'Manage subcontractors, budgets, schedules, and safety compliance. '
            'Report directly to the CEO and client representatives.'
        ),
        'requirements': (
            '• BSc in Civil Engineering or Construction Management\n'
            '• 8+ years in construction project management\n'
            '• PMP certification required\n'
            '• Experience managing projects > $10M\n'
            '• Strong knowledge of FIDIC contracts'
        ),
        'salary_range': '$2,500–$4,000/mo',
        'experience_level': 'Manager',
        'is_active': True,
        'company_idx': 2,
        'closes_days': 60,
    },
    {
        'title': 'Quantity Surveyor',
        'department': 'Cost & Commercial',
        'location': 'Sulaymaniyah, Iraq',
        'type': 'Full-time',
        'description': (
            'Prepare Bills of Quantities, manage cost control, valuations, and '
            'final accounts for construction projects.'
        ),
        'requirements': (
            '• BSc in Quantity Surveying or Civil Engineering\n'
            '• 4+ years in QS roles\n'
            '• Proficiency in CostX or MS Excel for estimation\n'
            '• Knowledge of RICS standards and BOQ preparation'
        ),
        'salary_range': '$1,400–$2,200/mo',
        'experience_level': 'Mid-Level',
        'is_active': True,
        'company_idx': 2,
        'closes_days': 35,
    },
    {
        'title': 'Electrical Engineer — Site',
        'department': 'Electrical Engineering',
        'location': 'Sulaymaniyah, Iraq',
        'type': 'Full-time',
        'description': (
            'Supervise electrical installation works, review shop drawings, and coordinate '
            'with MEP contractor on large building projects.'
        ),
        'requirements': (
            '• BSc in Electrical Engineering\n'
            '• 3+ years on construction sites\n'
            '• AutoCAD Electrical proficiency\n'
            '• IEC and local code compliance knowledge'
        ),
        'salary_range': '$1,200–$1,900/mo',
        'experience_level': 'Mid-Level',
        'is_active': True,
        'company_idx': 2,
        'closes_days': 28,
    },
]

CANDIDATES_DATA = [
    {
        'full_name': 'Ahmed Al-Rashid',
        'email': 'ahmed.rashid@gmail.com',
        'phone': '+964 770 501 1111',
        'headline': 'Senior Civil Engineer | 9 Years Experience',
        'location_city': 'Slemani',
        'bio': 'Experienced civil engineer with a proven track record in highway design, bridge engineering, and large-scale infrastructure. Passionate about sustainable construction practice.',
        'nationality': 'Iraqi',
        'gender': 'Male',
        'skills': ['AutoCAD', 'Civil 3D', 'SAP2000', 'Project Management', 'AASHTO', 'ACI 318'],
        'exp': [
            ('Senior Engineer', 'Municipality of Slemani', 2020, None, 'Led design of 4 major road projects totalling 120km. Managed team of 12 engineers.'),
            ('Civil Engineer', 'Al-Badr Consulting', 2015, 2020, 'Designed drainage systems, retaining walls, and road cross-sections for residential developments.'),
        ],
        'edu': [('MSc Civil Engineering', 'University of Slemani', 2014, 2016), ('BSc Civil Engineering', 'University of Slemani', 2009, 2013)],
        'languages': [('Arabic', 'Native'), ('Kurdish', 'Fluent'), ('English', 'Advanced')],
        'certs': [('PMP – Project Management Professional', 'PMI', '2021-03-15'), ('AutoCAD Certified Professional', 'Autodesk', '2019-07-10')],
        'apply_positions': [0, 1],   # position indices
    },
    {
        'full_name': 'Lana Karim',
        'email': 'lana.karim@outlook.com',
        'phone': '+964 750 502 2222',
        'headline': 'Full-Stack Developer | React & Django',
        'location_city': 'Erbil',
        'bio': 'Passionate web developer building clean, fast applications. 4 years professional experience in both frontend (React) and backend (Django, Node). Active open-source contributor.',
        'nationality': 'Iraqi',
        'gender': 'Female',
        'skills': ['React', 'Django', 'Python', 'JavaScript', 'PostgreSQL', 'Docker', 'Git'],
        'exp': [
            ('Full-Stack Developer', 'Kurdistan Tech Solutions', 2022, None, 'Built customer portal SaaS product with React/Django. 10,000+ active users.'),
            ('Junior Developer', 'Byte Systems', 2020, 2022, 'Maintained Laravel PHP applications and developed Vue.js components.'),
        ],
        'edu': [('BSc Computer Science', 'Salahaddin University', 2016, 2020)],
        'languages': [('Kurdish', 'Native'), ('Arabic', 'Fluent'), ('English', 'Fluent')],
        'certs': [('AWS Certified Cloud Practitioner', 'Amazon', '2023-01-20'), ('Meta Front-End Developer', 'Meta / Coursera', '2022-05-01')],
        'apply_positions': [3, 4],
    },
    {
        'full_name': 'Omar Farouk',
        'email': 'omar.farouk@email.com',
        'phone': '+964 751 503 3333',
        'headline': 'Structural Engineer | ETABS & SAP2000 Specialist',
        'location_city': 'Sulaymaniyah',
        'bio': 'Structural engineer with 5 years of experience designing high-rise and industrial buildings. Expert in tall structures and seismic analysis.',
        'nationality': 'Iraqi',
        'gender': 'Male',
        'skills': ['ETABS', 'SAP2000', 'SAFE', 'AutoCAD', 'ACI 318', 'Seismic Analysis'],
        'exp': [
            ('Structural Design Engineer', 'Zagros Construction Group', 2021, None, 'Designed structural systems for 6 commercial towers, 15–32 floors each.'),
            ('Junior Structural Engineer', 'Sardem Engineering', 2019, 2021, 'Assisted in RCC and steel structure design.'),
        ],
        'edu': [('BSc Civil Engineering', 'Sulaimani Polytechnic University', 2015, 2019)],
        'languages': [('Arabic', 'Native'), ('Kurdish', 'Fluent'), ('English', 'Intermediate')],
        'certs': [('ETABS Advanced Training', 'CSI', '2022-06-01')],
        'apply_positions': [1, 0],
    },
    {
        'full_name': 'Roya Salam',
        'email': 'roya.salam@proton.me',
        'phone': '+964 770 504 4444',
        'headline': 'Data Analyst | Power BI & SQL',
        'location_city': 'Erbil',
        'bio': 'Data-driven analyst with a knack for turning complex datasets into clear business insights. Built dashboards that reduced reporting time by 60% at previous employer.',
        'nationality': 'Iraqi',
        'gender': 'Female',
        'skills': ['SQL', 'Python', 'Power BI', 'Tableau', 'Pandas', 'Excel', 'DAX'],
        'exp': [
            ('Business Analyst', 'Korek Telecom', 2022, None, 'Created executive KPI dashboards in Power BI with live SQL Server feeds.'),
            ('Data Intern', 'Erbil Analytics', 2021, 2022, 'Cleaned datasets and built ad-hoc reports using Excel and Python.'),
        ],
        'edu': [('BSc Statistics', 'University of Kurdistan Hewlêr', 2017, 2021)],
        'languages': [('Kurdish', 'Native'), ('English', 'Advanced'), ('Arabic', 'Intermediate')],
        'certs': [('Microsoft PL-300: Power BI Data Analyst', 'Microsoft', '2023-04-10'), ('Google Data Analytics Certificate', 'Google / Coursera', '2022-09-15')],
        'apply_positions': [4, 3],
    },
    {
        'full_name': 'Hassan Mirza',
        'email': 'hassan.mirza@yahoo.com',
        'phone': '+964 751 505 5555',
        'headline': 'Construction Project Manager | PMP Certified',
        'location_city': 'Sulaymaniyah',
        'bio': 'Senior construction manager with 12 years leading large infrastructure and building projects in Iraq and the GCC. Expert in FIDIC contracts, claims management, and stakeholder relations.',
        'nationality': 'Iraqi',
        'gender': 'Male',
        'skills': ['Project Management', 'FIDIC Contracts', 'Primavera P6', 'Cost Control', 'Risk Management', 'AutoCAD'],
        'exp': [
            ('Project Director', 'Kirkuk Construction Co.', 2018, None, 'Directed a $45M hospital construction project. Delivered 2 weeks ahead of schedule.'),
            ('Senior Project Manager', 'Gulf Build LLC (Dubai)', 2013, 2018, 'Managed 3 concurrent commercial tower projects in Dubai totalling AED 380M.'),
        ],
        'edu': [('BSc Civil Engineering', 'University of Technology, Baghdad', 2006, 2010), ('MBA', 'University of Kurdistan Hewlêr', 2011, 2013)],
        'languages': [('Arabic', 'Native'), ('Kurdish', 'Fluent'), ('English', 'Fluent')],
        'certs': [('PMP – Project Management Professional', 'PMI', '2015-08-20'), ('FIDIC Contracts Training', 'NEC / FIDIC', '2020-11-05')],
        'apply_positions': [6, 7],
    },
    {
        'full_name': 'Shirin Baban',
        'email': 'shirin.baban@gmail.com',
        'phone': '+964 770 506 6666',
        'headline': 'HVAC & MEP Engineer | 5 Years Experience',
        'location_city': 'Slemani',
        'bio': 'Mechanical engineer specialising in HVAC system design for commercial and industrial facilities. Strong background in energy efficiency and ASHRAE compliance.',
        'nationality': 'Iraqi',
        'gender': 'Female',
        'skills': ['HVAC Design', 'AutoCAD MEP', 'Revit MEP', 'ASHRAE Standards', 'Energy Modelling', 'HAP Software'],
        'exp': [
            ('MEP Engineer', 'MOF Engineering Co.', 2021, None, 'Designed HVAC for 3 large hospital projects and 2 commercial complexes.'),
            ('HVAC Designer', 'Al-Noor MEP', 2019, 2021, 'Drafted ductwork layouts and performed load calculations for residential buildings.'),
        ],
        'edu': [('BSc Mechanical Engineering', 'University of Slemani', 2015, 2019)],
        'languages': [('Kurdish', 'Native'), ('Arabic', 'Fluent'), ('English', 'Intermediate')],
        'certs': [('ASHRAE Certified HVAC Designer', 'ASHRAE', '2022-04-12')],
        'apply_positions': [2, 8],
    },
    {
        'full_name': 'Dilan Nouri',
        'email': 'dilan.nouri@gmail.com',
        'phone': '+964 750 507 7777',
        'headline': 'DevOps Engineer | AWS & Kubernetes',
        'location_city': 'Erbil',
        'bio': 'Cloud-native engineer with a passion for automation. Built and maintained Kubernetes clusters serving 5M+ requests/day. Strong advocate for GitOps practices.',
        'nationality': 'Iraqi',
        'gender': 'Male',
        'skills': ['Kubernetes', 'AWS', 'Docker', 'Terraform', 'CI/CD', 'Ansible', 'Linux', 'Python'],
        'exp': [
            ('DevOps Engineer', 'Newroz Telecom', 2021, None, 'Migrated legacy bare-metal infrastructure to AWS EKS. Reduced deployment time from 2h to 8 minutes.'),
            ('Systems Administrator', 'Tech Erbil', 2019, 2021, 'Managed on-premise Linux servers, backups, and networking for 200+ user organisation.'),
        ],
        'edu': [('BSc Software Engineering', 'Salahaddin University', 2015, 2019)],
        'languages': [('Kurdish', 'Native'), ('English', 'Advanced'), ('Arabic', 'Intermediate')],
        'certs': [('AWS Solutions Architect – Associate', 'Amazon', '2022-07-18'), ('Certified Kubernetes Administrator (CKA)', 'CNCF', '2023-02-14')],
        'apply_positions': [5, 3],
    },
    {
        'full_name': 'Tara Jamal',
        'email': 'tara.jamal@outlook.com',
        'phone': '+964 751 508 8888',
        'headline': 'Quantity Surveyor | Cost Control Specialist',
        'location_city': 'Sulaymaniyah',
        'bio': 'Detail-oriented QS professional experienced in pre and post-contract cost management for high-value building projects.',
        'nationality': 'Iraqi',
        'gender': 'Female',
        'skills': ['Quantity Surveying', 'CostX', 'BOQ Preparation', 'RICS Standards', 'Contract Management', 'MS Excel'],
        'exp': [
            ('Quantity Surveyor', 'Kurd Build Co.', 2020, None, 'Managed BOQs for 5 mixed-use developments totalling $30M.'),
            ('Assistant QS', 'Apex Consulting', 2018, 2020, 'Assisted with site measurement, valuation, and subcontractor accounts.'),
        ],
        'edu': [('BSc Quantity Surveying', 'Sulaimani Polytechnic University', 2014, 2018)],
        'languages': [('Kurdish', 'Native'), ('Arabic', 'Fluent'), ('English', 'Intermediate')],
        'certs': [('RICS APC – AssocRICS', 'Royal Institution of Chartered Surveyors', '2021-09-30')],
        'apply_positions': [7, 6],
    },
]

# Application statuses per (candidate, position) — deterministic so re-runs are stable
APP_STATUS_SEQUENCE = [
    STATUS_HIRED,
    STATUS_INTERVIEW,
    STATUS_REVIEW,
    STATUS_NEW,
    STATUS_REJECTED,
    STATUS_REVIEW,
    STATUS_INTERVIEW,
    STATUS_OFFER,
    STATUS_NEW,
    STATUS_REVIEW,
    STATUS_HIRED,
    STATUS_REJECTED,
    STATUS_INTERVIEW,
    STATUS_NEW,
    STATUS_REVIEW,
    STATUS_REVIEW,
]


# ─────────────────────────────────────────────────────────────────────────────
# SEED
# ─────────────────────────────────────────────────────────────────────────────

def run():
    with app.app_context():
        print('\n🌱  Seeding demo data...\n')

        # ── 1. Companies ──────────────────────────────────────────────────────
        print('  Companies...')
        admin = User.query.filter_by(email='admin@mof-eng.com').first()
        companies = []
        for cd in COMPANIES_DATA:
            existing = Company.query.filter_by(name=cd['name']).first()
            if existing:
                companies.append(existing)
                print(f'    skip (exists): {cd["name"]}')
                continue
            c = Company(
                name          = cd['name'],
                industry      = cd['industry'],
                size          = cd['size'],
                location      = cd['location'],
                website       = cd['website'],
                contact_email = cd['contact_email'],
                contact_phone = cd['contact_phone'],
                founded_year  = cd['founded_year'],
                is_verified   = cd['is_verified'],
                is_active     = True,
                description   = cd['description'],
                created_by    = admin.id if admin else None,
            )
            c.save_slug()
            db.session.add(c)
            db.session.flush()
            companies.append(c)
            print(f'    ✓ {c.name}')
        db.session.commit()

        # ── 2. Supervisors ────────────────────────────────────────────────────
        print('\n  Supervisors...')
        supervisors = []
        for i, sd in enumerate(SUPERVISORS_DATA):
            sup, created = get_or_create_user(
                full_name     = sd['full_name'],
                email         = sd['email'],
                role          = ROLE_SUPERVISOR,
                phone         = sd['phone'],
                bio           = sd['bio'],
                headline      = sd['headline'],
                location_city = sd['location_city'],
            )
            if created:
                db.session.flush()
                print(f'    ✓ {sup.full_name}')
            else:
                print(f'    skip (exists): {sup.full_name}')
            supervisors.append(sup)
        db.session.commit()

        # ── 3. Assign supervisors as company managers ─────────────────────────
        print('\n  Assigning managers...')
        for i, (sup, company) in enumerate(zip(supervisors, companies)):
            existing = CompanyMember.query.filter_by(
                company_id=company.id, user_id=sup.id).first()
            if not existing:
                db.session.add(CompanyMember(
                    company_id=company.id, user_id=sup.id, role='manager'))
                print(f'    ✓ {sup.full_name} → {company.name}')
            else:
                print(f'    skip (exists): {sup.full_name} → {company.name}')
        db.session.commit()

        # ── 4. Positions ──────────────────────────────────────────────────────
        print('\n  Positions...')
        positions = []
        admin_id = admin.id if admin else None
        for pd in POSITIONS_DATA:
            existing = Position.query.filter_by(title=pd['title']).first()
            if existing:
                positions.append(existing)
                print(f'    skip (exists): {pd["title"]}')
                continue
            p = Position(
                title            = pd['title'],
                department       = pd['department'],
                location         = pd['location'],
                type             = pd['type'],
                description      = pd['description'],
                requirements     = pd['requirements'],
                salary_range     = pd['salary_range'],
                experience_level = pd['experience_level'],
                is_active        = pd['is_active'],
                company_id       = companies[pd['company_idx']].id,
                created_by       = admin_id,
                created_at       = ago(random.randint(5, 60)),
                closes_at        = datetime.utcnow() + timedelta(days=pd['closes_days']),
            )
            db.session.add(p)
            db.session.flush()
            positions.append(p)
            print(f'    ✓ {p.title}')
        db.session.commit()

        # ── 5. Candidates with full profiles ─────────────────────────────────
        print('\n  Candidates + profiles...')
        candidates = []
        app_counter = 0

        for cd in CANDIDATES_DATA:
            candidate, created = get_or_create_user(
                full_name     = cd['full_name'],
                email         = cd['email'],
                role          = ROLE_USER,
                phone         = cd['phone'],
                bio           = cd['bio'],
                headline      = cd['headline'],
                location_city = cd['location_city'],
                nationality   = cd.get('nationality', ''),
                gender        = cd.get('gender', ''),
            )
            db.session.flush()
            candidates.append(candidate)

            if created:
                print(f'    ✓ {candidate.full_name}')
                # Skills
                for skill_name in cd.get('skills', []):
                    db.session.add(UserSkill(user_id=candidate.id, name=skill_name,
                                             proficiency='advanced'))
                # Experience
                for (exp_title, company_name, yr_start, yr_end, desc) in cd.get('exp', []):
                    end_date = date(yr_end, 6, 1) if yr_end else None
                    db.session.add(UserExperience(
                        user_id     = candidate.id,
                        title       = exp_title,
                        company     = company_name,
                        start_date  = date(yr_start, 1, 1),
                        end_date    = end_date,
                        description = desc,
                    ))
                # Education
                for (deg, institution, yr_start, yr_end) in cd.get('edu', []):
                    db.session.add(UserEducation(
                        user_id     = candidate.id,
                        degree      = deg,
                        institution = institution,
                        start_year  = yr_start,
                        end_year    = yr_end,
                    ))
                # Languages
                for (lang, level) in cd.get('languages', []):
                    # Removed UserLanguage add (rollback)
                        user_id     = candidate.id,
                        language    = lang,
                        proficiency = level,
                    ))
                # Certifications
                for (cert_name, issuer, issued_str) in cd.get('certs', []):
                    # Removed UserCertification add (rollback)
                        user_id     = candidate.id,
                        name        = cert_name,
                        issuing_org = issuer,
                        issue_date  = datetime.strptime(issued_str, '%Y-%m-%d').date(),
                    ))
            else:
                print(f'    skip (exists): {candidate.full_name}')

        db.session.commit()

        # ── 6. Applications ────────────────────────────────────────────────────
        print('\n  Applications...')
        for cd_data, candidate in zip(CANDIDATES_DATA, candidates):
            # Assign to supervisor based on company
            for pos_idx in cd_data.get('apply_positions', []):
                if pos_idx >= len(positions):
                    continue
                pos = positions[pos_idx]
                existing_app = Application.query.filter_by(
                    applicant_id=candidate.id, position_id=pos.id).first()
                if existing_app:
                    print(f'    skip app (exists): {candidate.full_name} → {pos.title}')
                    continue

                status = APP_STATUS_SEQUENCE[app_counter % len(APP_STATUS_SEQUENCE)]
                app_counter += 1
                applied_days_ago = random.randint(1, 45)

                # Find supervisor for this company
                company_id = pos.company_id
                mgr = CompanyMember.query.filter_by(
                    company_id=company_id, role='manager').first()
                assigned_to_id = mgr.user_id if mgr else None

                application = Application(
                    applicant_id   = candidate.id,
                    position_id    = pos.id,
                    status         = status,
                    source         = random.choice(SOURCES),
                    cover_letter   = (
                        f"Dear Hiring Manager,\n\nI am writing to express my strong interest "
                        f"in the {pos.title} position at {pos.company.name}. With my background "
                        f"in {cd_data['headline']}, I am confident I would make an immediate "
                        f"contribution to your team.\n\nBest regards,\n{candidate.full_name}"
                    ),
                    applied_at     = ago(applied_days_ago),
                    updated_at     = ago(applied_days_ago - random.randint(0, applied_days_ago)),
                    assigned_to_id = assigned_to_id,
                )
                db.session.add(application)
                db.session.flush()

                # History entries
                db.session.add(ApplicationHistory(
                    application_id = application.id,
                    changed_by_id  = admin.id if admin else candidate.id,
                    old_status     = None,
                    new_status     = STATUS_NEW,
                    note           = 'Application received.',
                    created_at     = ago(applied_days_ago),
                ))
                if status != STATUS_NEW:
                    db.session.add(ApplicationHistory(
                        application_id = application.id,
                        changed_by_id  = assigned_to_id or (admin.id if admin else candidate.id),
                        old_status     = STATUS_NEW,
                        new_status     = STATUS_REVIEW,
                        note           = 'CV reviewed — moving to next stage.',
                        created_at     = ago(applied_days_ago - 2),
                    ))
                if status in (STATUS_INTERVIEW, STATUS_OFFER, STATUS_HIRED):
                    db.session.add(ApplicationHistory(
                        application_id = application.id,
                        changed_by_id  = assigned_to_id or (admin.id if admin else candidate.id),
                        old_status     = STATUS_REVIEW,
                        new_status     = STATUS_INTERVIEW,
                        note           = 'Strong candidate — interview scheduled.',
                        created_at     = ago(max(applied_days_ago - 7, 1)),
                    ))
                if status in (STATUS_OFFER, STATUS_HIRED):
                    db.session.add(ApplicationHistory(
                        application_id = application.id,
                        changed_by_id  = admin.id if admin else candidate.id,
                        old_status     = STATUS_INTERVIEW,
                        new_status     = STATUS_OFFER,
                        note           = 'Excellent interview performance. Offer extended.',
                        created_at     = ago(max(applied_days_ago - 12, 1)),
                    ))
                if status == STATUS_HIRED:
                    db.session.add(ApplicationHistory(
                        application_id = application.id,
                        changed_by_id  = admin.id if admin else candidate.id,
                        old_status     = STATUS_OFFER,
                        new_status     = STATUS_HIRED,
                        note           = 'Offer accepted. Start date confirmed.',
                        created_at     = ago(max(applied_days_ago - 18, 1)),
                    ))

                print(f'    ✓ {candidate.full_name} → {pos.title} [{status}]')

        db.session.commit()

        # ── 7. Company follows ─────────────────────────────────────────────────
        print('\n  Company follows...')
        for i, candidate in enumerate(candidates):
            # Each candidate follows 1-2 companies
            for company in random.sample(companies, k=min(2, len(companies))):
                from models import CompanyFollow
                existing_follow = CompanyFollow.query.filter_by(
                    user_id=candidate.id, company_id=company.id).first()
                if not existing_follow:
                    db.session.add(CompanyFollow(
                        user_id    = candidate.id,
                        company_id = company.id,
                    ))
        db.session.commit()
        print('    ✓ Follows added')

        # ─── Summary ──────────────────────────────────────────────────────────
        print('\n' + '─' * 50)
        print(f'  Companies  : {Company.query.count()}')
        print(f'  Supervisors: {len(supervisors)}')
        print(f'  Positions  : {Position.query.count()}')
        print(f'  Candidates : {len(candidates)}')
        print(f'  Applications: {Application.query.count()}')
        print('─' * 50)
        print('\n✅  Demo data loaded! Login with any of these accounts:')
        print('   Admin      : admin@mof-eng.com       / Admin@1234')
        print('   Supervisors: sara.hassan@mof-eng.com / Demo@1234')
        print('               karim.aziz@kts.iq        / Demo@1234')
        print('               nadia.jalal@zagros-group.com / Demo@1234')
        print('   Candidates : ahmed.rashid@gmail.com  / Demo@1234')
        print('                lana.karim@outlook.com  / Demo@1234')
        print('                (all candidates use Demo@1234)\n')


if __name__ == '__main__':
    run()
