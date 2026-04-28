"""One-shot migration: add is_verified / verified_at / verified_by_id columns
to the universities table, and mark all existing universities as verified
(so admin-only edit behavior is preserved for them).

Idempotent: safely re-runnable; checks for existing columns first.
Run on the live server:
    python migrate_university_verified.py
"""
from datetime import datetime
from sqlalchemy import inspect, text

from app import app
from models import db


def column_exists(conn, table, column):
    insp = inspect(conn)
    return any(c['name'] == column for c in insp.get_columns(table))


def main():
    with app.app_context():
        conn = db.engine.connect()
        added = []
        with conn.begin():
            if not column_exists(conn, 'universities', 'is_verified'):
                conn.execute(text(
                    "ALTER TABLE universities ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT 0"
                ))
                added.append('is_verified')
            if not column_exists(conn, 'universities', 'verified_at'):
                conn.execute(text(
                    "ALTER TABLE universities ADD COLUMN verified_at DATETIME"
                ))
                added.append('verified_at')
            if not column_exists(conn, 'universities', 'verified_by_id'):
                conn.execute(text(
                    "ALTER TABLE universities ADD COLUMN verified_by_id INTEGER"
                ))
                added.append('verified_by_id')

            # Backfill: mark every existing university as verified so admin
            # remains the only editor by default. Coordinator-edit access is
            # only granted for newly-created (unverified) universities going
            # forward.
            result = conn.execute(text(
                "UPDATE universities "
                "SET is_verified = 1, verified_at = :now "
                "WHERE is_verified = 0 OR is_verified IS NULL"
            ), {'now': datetime.utcnow()})
            updated_rows = result.rowcount

        print(f"Added columns: {added or 'none (all present)'}")
        print(f"Backfilled rows (set is_verified=1): {updated_rows}")
        print("Done.")


if __name__ == '__main__':
    main()
