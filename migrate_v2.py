"""
migrate_v2.py — upgrade existing DB to v2 schema.

Runs ALTER TABLE directly on the SQLite file, then calls db.create_all()
to materialise every new table.  Safe to run multiple times.

Usage:
    python migrate_v2.py
"""
import os, sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'careers.db')

ALTER_STATEMENTS = [
    # users — extended profile
    "ALTER TABLE users ADD COLUMN avatar_filename VARCHAR(200)",
    "ALTER TABLE users ADD COLUMN headline VARCHAR(200)",
    "ALTER TABLE users ADD COLUMN location_city VARCHAR(100)",
    "ALTER TABLE users ADD COLUMN date_of_birth DATE",
    "ALTER TABLE users ADD COLUMN nationality VARCHAR(50)",
    "ALTER TABLE users ADD COLUMN gender VARCHAR(20)",
    "ALTER TABLE users ADD COLUMN resume_headline VARCHAR(300)",

    # positions — extended job fields
    "ALTER TABLE positions ADD COLUMN company_id INTEGER",
    "ALTER TABLE positions ADD COLUMN experience_level VARCHAR(50)",
    "ALTER TABLE positions ADD COLUMN skills_required TEXT",
    "ALTER TABLE positions ADD COLUMN benefits TEXT",
    "ALTER TABLE positions ADD COLUMN salary_min INTEGER",
    "ALTER TABLE positions ADD COLUMN salary_max INTEGER",
    "ALTER TABLE positions ADD COLUMN views_count INTEGER DEFAULT 0",
]

print(f"Migrating: {DB_PATH}")
conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

print("Running ALTER TABLE statements …")
for stmt in ALTER_STATEMENTS:
    col = stmt.split("ADD COLUMN")[1].strip().split()[0]
    try:
        cur.execute(stmt)
        conn.commit()
        print(f"  ✓ {col}")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print(f"  – {col} (already exists, skipped)")
        else:
            print(f"  ✗ ERROR on {col}: {e}")

conn.close()
print("\nALTER TABLE phase done.")

# Now use SQLAlchemy to create new tables
print("\nCreating new tables via SQLAlchemy …")
import sys
sys.path.insert(0, os.path.dirname(__file__))

# Import models directly (avoid running create_app / seed_admin)
from config import config
from models import db
from flask import Flask

mini_app = Flask(__name__)
mini_app.config.from_object(config['default'])

db.init_app(mini_app)

with mini_app.app_context():
    db.create_all()
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"  ✓ {len(tables)} tables in DB:")
    for t in sorted(tables):
        print(f"    • {t}")

print("\nMigration complete.")

