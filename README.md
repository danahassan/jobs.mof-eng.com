# MOF Jobs Portal — Flask/Python

Job recruitment portal for MOF Engineering Company.
Roles: Admin · Supervisor · Applicant

---

## Project Structure

```
mof_careers/
├── app.py                  # App factory, entry point, shared helpers
├── config.py               # Dev / Production config
├── models.py               # SQLAlchemy models (User, Position, Application, ...)
├── passenger_wsgi.py       # cPanel Python App entry point
├── requirements.txt
├── migrate_from_mysql.py   # One-time migration from old PHP/MySQL portal
├── .env.example            # Copy to .env and fill in secrets
├── routes/
│   ├── auth.py             # Login, logout, register, profile
│   ├── admin.py            # Admin: full CRUD
│   ├── supervisor.py       # Supervisor: assigned apps only
│   └── user.py             # Applicant: browse, apply, track
├── templates/
│   ├── base.html           # Shared layout + sidebar
│   ├── auth/               # Login, register, profile
│   ├── admin/              # Dashboard, positions, applications, users
│   ├── supervisor/         # Dashboard, applications
│   ├── user/               # Browse, apply, my-applications
│   └── emails/             # HTML email templates
├── static/
│   └── uploads/cvs/        # Uploaded CV files
└── instance/
    └── careers.db          # SQLite database (auto-created)
```

---

## Local Development

```bash
cd mof_careers
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # edit .env with your secrets
python app.py                     # runs on http://localhost:5001
```

Default admin account (created on first run):
- Email: admin@mof-eng.com
- Password: Admin@1234  ← change this immediately!

---

## Deploy to cPanel (A2 Hosting — az1-ss27)

Same pattern as your existing ERP at erp.mof-eng.com:

1. Create a new subdomain: jobs.mof-eng.com
   cPanel → Subdomains → careers → document root: /home/mofengco/jobs.mof-eng.com

2. Set up Python App in cPanel:
   cPanel → Setup Python App
   - Python version: 3.11
   - App root: /home/mofengco/jobs.mof-eng.com
   - App startup file: passenger_wsgi.py
   - App Entry point: application

3. Upload files via FTP to /home/mofengco/jobs.mof-eng.com/

4. SSH in and install dependencies:
   cd /home/mofengco/jobs.mof-eng.com
   source venv/bin/activate
   pip install -r requirements.txt --break-system-packages

5. Create .env from .env.example and fill in secrets

6. Restart the app:
   touch /home/mofengco/jobs.mof-eng.com/tmp/restart.txt

---

## Migration from PHP/MySQL

Once deployed, run the migration once:

```bash
# Edit MYSQL_* settings in migrate_from_mysql.py first
python migrate_from_mysql.py
```

All migrated users will have the temporary password: MofMigrated@2026
Notify them to change it via the profile page on first login.

---

## URL Structure

| URL                         | Who sees it            |
|-----------------------------|------------------------|
| /                           | Redirects by role      |
| /login  /register           | Public                 |
| /portal/browse              | Public (job listings)  |
| /portal/apply/<id>          | Logged-in applicants   |
| /portal/my-applications     | Logged-in applicants   |
| /admin/                     | Admin only             |
| /admin/positions            | Admin only             |
| /admin/applications         | Admin only             |
| /admin/users                | Admin only             |
| /supervisor/                | Supervisor + Admin     |
| /supervisor/applications    | Supervisor + Admin     |

---

## Adding Features Later

- **Email notifications**: already wired — just set MAIL_PASSWORD in .env
- **PDF export of applications**: add pdfkit or reportlab
- **Interview calendar**: add a calendar view to the interviews table
- **Bulk status update**: add checkboxes + bulk action to applications table
- **Arabic/Kurdish UI**: wrap templates in `dir="rtl"` and add RTL CSS
