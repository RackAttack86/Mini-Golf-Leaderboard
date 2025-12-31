#!/usr/bin/env python3
"""Migration script to add course_notes table"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database import init_database
from config import Config

def run_migration():
    """Run course notes table migration"""
    print("Starting course_notes table migration...")

    # Initialize database
    db = init_database(Config.DATABASE_PATH)
    conn = db.get_connection()

    # Read migration SQL
    migration_file = Path(__file__).parent / 'add_course_notes_table.sql'
    with open(migration_file, 'r') as f:
        migration_sql = f.read()

    # Execute migration
    try:
        conn.executescript(migration_sql)
        print("[OK] course_notes table created successfully")

        # Verify table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='course_notes'"
        )
        if cursor.fetchone():
            print("[OK] Table verification passed")
        else:
            print("[FAIL] Table not found after migration")
            return False

        return True

    except Exception as e:
        print(f"[FAIL] Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
