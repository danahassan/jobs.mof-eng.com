# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
fix_syntax.py  —  fixes all syntax errors caused by incomplete rollback.
Run from the app root:  python fix_syntax.py
"""
import os, sys, py_compile, glob as _glob

BASE = os.path.dirname(os.path.abspath(__file__))
_applied = 0
_skipped = 0

def fix(rel_path, old, new, desc):
    global _applied, _skipped
    full = os.path.join(BASE, rel_path)
    with open(full, 'r', encoding='utf-8') as f:
        src = f.read()
    if old not in src:
        print(f'  [SKIP] {desc}')
        _skipped += 1
        return
    with open(full, 'w', encoding='utf-8') as f:
        f.write(src.replace(old, new, 1))
    print(f'  [OK]   {desc}')
    _applied += 1


print('=== Applying fixes ===\n')

# FIX 1 — models.py: restore the deleted Position class
fix(
    'models.py',
    "    def __repr__(self):\n"
    "        return f'<User {self.email} [{self.role}]>'\n"
    "\n\n\n"
    "            delta = self.closes_at - datetime.utcnow()\n"
    "            return 0 <= delta.days <= 14\n"
    "        return False\n"
    "\n"
    "    def __repr__(self):\n"
    "        return f'<Position {self.title}>'\n"
    "\n\nclass Application(db.Model):",
    "    def __repr__(self):\n"
    "        return f'<User {self.email} [{self.role}]>'\n"
    "\n\n"
    "class Position(db.Model):\n"
    "    __tablename__ = 'positions'\n"
    "\n"
    "    id               = db.Column(db.Integer, primary_key=True)\n"
    "    title            = db.Column(db.String(200), nullable=False)\n"
    "    company_id       = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True, index=True)\n"
    "    department       = db.Column(db.String(100))\n"
    "    location         = db.Column(db.String(200), default='Slemani, Iraq')\n"
    "    type             = db.Column(db.String(50), default='Full-time')\n"
    "    description      = db.Column(db.Text)\n"
    "    requirements     = db.Column(db.Text)\n"
    "    benefits         = db.Column(db.Text)\n"
    "    skills_required  = db.Column(db.Text)\n"
    "    salary_range     = db.Column(db.String(100))\n"
    "    salary_min       = db.Column(db.Integer)\n"
    "    salary_max       = db.Column(db.Integer)\n"
    "    experience_level = db.Column(db.String(50))\n"
    "    is_active        = db.Column(db.Boolean, default=True)\n"
    "    is_remote        = db.Column(db.Boolean, default=False)\n"
    "    views_count      = db.Column(db.Integer, default=0)\n"
    "    closes_at        = db.Column(db.DateTime)\n"
    "    created_at       = db.Column(db.DateTime, default=datetime.utcnow)\n"
    "    created_by       = db.Column(db.Integer, db.ForeignKey('users.id'))\n"
    "\n"
    "    company      = db.relationship('Company', back_populates='positions',\n"
    "                                   foreign_keys=[company_id])\n"
    "    applications = db.relationship('Application', back_populates='position',\n"
    "                                   lazy='dynamic', cascade='all,delete-orphan')\n"
    "\n"
    "    @property\n"
    "    def application_count(self):\n"
    "        return self.applications.count()\n"
    "\n"
    "    @property\n"
    "    def is_closing_soon(self):\n"
    "        if self.closes_at:\n"
    "            delta = self.closes_at - datetime.utcnow()\n"
    "            return 0 <= delta.days <= 14\n"
    "        return False\n"
    "\n"
    "    def __repr__(self):\n"
    "        return f'<Position {self.title}>'\n"
    "\n\nclass Application(db.Model):",
    'models.py — restore Position class',
)

# FIX 2 — routes/admin.py: orphan UserLanguage add line
fix(
    'routes/admin.py',
    "            if lname:\n"
    "                # Removed UserLanguage add (rollback)\n"
    "                                            proficiency=lprof or 'Intermediate'))",
    "            if lname:\n"
    "                pass  # Removed UserLanguage add (rollback)",
    'admin.py — remove orphan UserLanguage add line',
)

# FIX 3 — routes/admin.py: orphan UserCertification add block
fix(
    'routes/admin.py',
    "            if cname:\n"
    "                # Removed UserCertification add (rollback)\n"
    "                    user_id=user.id, name=cname,\n"
    "                    issuing_org=corg.strip() or None,\n"
    "                    issue_date=_parse_date(cissued),\n"
    "                    credential_id=ccid.strip() or None,\n"
    "                    credential_url=curl.strip() or None))",
    "            if cname:\n"
    "                pass  # Removed UserCertification add (rollback)",
    'admin.py — remove orphan UserCertification add block',
)

# FIX 4 — routes/admin.py: broken langs_str / certs_str joins
fix(
    'routes/admin.py',
    "        # Languages\n"
    "        langs_str = ', '.join(\n"
    "            f'{l.language} ({l.proficiency})' for l in\n"
    "            # Removed UserLanguage (rollback)\n"
    "        )\n"
    "\n"
    "        # Certifications\n"
    "        certs_str = ', '.join(\n"
    "            f'{c.name}' + (f' \u2014 {c.issuing_org}' if c.issuing_org else '')\n"
    "            # Removed UserCertification (rollback)\n"
    "        )",
    "        # Languages removed (rollback)\n"
    "        langs_str = ''\n"
    "\n"
    "        # Certifications removed (rollback)\n"
    "        certs_str = ''",
    'admin.py — fix broken langs_str/certs_str joins',
)

# FIX 5 — routes/profile.py: orphan cert add block
fix(
    'routes/profile.py',
    "    # Removed UserCertification add (rollback)\n"
    "        user_id=current_user.id, name=name,\n"
    "        issuing_org=org, credential_id=cred_id, credential_url=cred_url\n"
    "    )\n"
    "    if issue:\n"
    "        try:\n"
    "            cert.issue_date = datetime.strptime(issue, '%Y-%m-%d').date()\n"
    "        except ValueError:\n"
    "            pass\n"
    "    if expiry:\n"
    "        try:\n"
    "            cert.expiry_date = datetime.strptime(expiry, '%Y-%m-%d').date()\n"
    "        except ValueError:\n"
    "            pass\n"
    "    db.session.add(cert)\n"
    "    db.session.commit()\n"
    "    flash('Certification added.', 'success')\n"
    "    return redirect(url_for('profile.view', mode='edit', tab='certs'))",
    "    # Removed UserCertification add (rollback)\n"
    "    flash('Certification added.', 'success')\n"
    "    return redirect(url_for('profile.view', mode='edit', tab='certs'))",
    'profile.py — remove orphan cert add block',
)

# FIX 6 — routes/profile.py: duplicate doc.build / return block
fix(
    'routes/profile.py',
    "    doc.build(story)\n"
    "    buf.seek(0)\n"
    "    safe_name = u.full_name.replace(' ', '_')\n"
    "    return send_file(buf, mimetype='application/pdf',\n"
    "                     as_attachment=True,\n"
    "                     download_name=f'CV_{safe_name}.pdf')\n"
    "        story.append(Paragraph('Certifications', h2_style))\n"
    "        for c in certs:\n"
    "            issued = c.issue_date.strftime('%b %Y') if c.issue_date else ''\n"
    "            story.append(Paragraph(f'<b>{c.name}</b>'"
    r"""{" — " + c.issuing_org if c.issuing_org else ""}{" (" + issued + ")" if issued else ""}"""
    "', body))\n"
    "\n"
    "    doc.build(story)\n"
    "    buf.seek(0)\n"
    "    safe_name = u.full_name.replace(' ', '_')\n"
    "    return send_file(buf, mimetype='application/pdf',\n"
    "                     as_attachment=True,\n"
    "                     download_name=f'CV_{safe_name}.pdf')",
    "    doc.build(story)\n"
    "    buf.seek(0)\n"
    "    safe_name = u.full_name.replace(' ', '_')\n"
    "    return send_file(buf, mimetype='application/pdf',\n"
    "                     as_attachment=True,\n"
    "                     download_name=f'CV_{safe_name}.pdf')",
    'profile.py — remove duplicate doc.build/return block',
)

# FIX 7 — routes/api/profile.py: unclosed import parenthesis
fix(
    'routes/api/profile.py',
    'from models import (db, UserSkill, UserExperience, UserEducation,\n'
    '\n'
    'from . import api_bp',
    'from models import db, UserSkill, UserExperience, UserEducation\n'
    '\n'
    'from . import api_bp',
    'api/profile.py — close unclosed import parenthesis',
)

# Verify
print(f'\n=== Applied {_applied}, skipped {_skipped} ===\n')
print('=== Verifying syntax ===\n')

files = sorted(
    _glob.glob(os.path.join(BASE, 'routes', '*.py')) +
    _glob.glob(os.path.join(BASE, 'routes', 'api', '*.py')) +
    [os.path.join(BASE, f) for f in
     ('models.py', 'helpers.py', 'config.py', 'passenger_wsgi.py', 'app.py')]
)

all_ok = True
for f in files:
    rel = os.path.relpath(f, BASE)
    try:
        py_compile.compile(f, doraise=True)
        print(f'  OK   {rel}')
    except py_compile.PyCompileError as e:
        print(f'  FAIL {rel}\n       {e}')
        all_ok = False

print()
if all_ok:
    restart = os.path.join(BASE, 'tmp', 'restart.txt')
    open(restart, 'a').close()
    os.utime(restart, None)
    print('All files OK.')
    print('tmp/restart.txt touched — Passenger will reload on next request.')
else:
    print('Some files still have errors — check output above.')
    sys.exit(1)
