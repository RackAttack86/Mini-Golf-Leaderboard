#!/usr/bin/env python3
"""
Migration script for course trophy ownership feature.

This script:
1. Checks if migration is needed
2. Applies schema changes
3. Retroactively assigns trophies from historical data
4. Reports results
"""

from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database import init_database, get_db
from models.course_trophy import CourseTrophy
from config import Config


def check_migration_needed():
    """Check if migration has already been applied"""
    db = get_db()
    conn = db.get_connection()

    # Check if course_trophies table exists
    cursor = conn.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='course_trophies'
    """)

    row = cursor.fetchone()

    if row:
        print("Migration already applied. Skipping.")
        return False

    return True


def apply_migration():
    """Apply schema migration"""
    db = get_db()
    conn = db.get_connection()

    migration_file = Path(__file__).parent.parent / 'migrations' / 'add_course_trophy_ownership.sql'

    if not migration_file.exists():
        print(f"Error: Migration file not found at {migration_file}")
        return False

    with open(migration_file, 'r') as f:
        migration_sql = f.read()

    try:
        conn.executescript(migration_sql)
        print("[OK] Schema migration applied successfully")
        return True
    except Exception as e:
        print(f"[ERROR] Error applying migration: {e}")
        return False


def initialize_trophies():
    """Initialize trophies from historical data"""
    print("\nInitializing trophies from historical data...")

    assigned_count, warnings = CourseTrophy.initialize_trophies_from_history()

    print(f"[OK] Assigned {assigned_count} trophies")

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  - {warning}")

    return True


def main():
    """Main migration function"""
    print("=== Course Trophy Ownership Migration ===\n")

    # Initialize database
    init_database(Config.DATABASE_PATH)

    # Check if migration needed
    if not check_migration_needed():
        return

    # Apply migration
    print("Applying schema migration...")
    if not apply_migration():
        print("\nMigration failed!")
        sys.exit(1)

    # Initialize trophies
    if not initialize_trophies():
        print("\nTrophy initialization failed!")
        sys.exit(1)

    print("\n=== Migration completed successfully! ===")


if __name__ == '__main__':
    main()
