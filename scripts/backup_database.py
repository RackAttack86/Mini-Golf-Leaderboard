#!/usr/bin/env python3
"""Backup SQLite database with timestamp"""

import shutil
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config

def backup_database():
    """Create a timestamped backup of the database"""

    # Source database
    db_path = Config.DATABASE_PATH

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return False

    # Create backups directory
    backup_dir = Config.DATA_DIR / 'backups'
    backup_dir.mkdir(exist_ok=True)

    # Generate timestamped filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = backup_dir / f'minigolf_backup_{timestamp}.db'

    # Copy database file
    try:
        shutil.copy2(db_path, backup_path)

        # Get file size
        size_kb = backup_path.stat().st_size / 1024

        print(f"[OK] Backup created successfully!")
        print(f"  Location: {backup_path}")
        print(f"  Size: {size_kb:.1f} KB")
        print(f"  Timestamp: {timestamp}")

        # Keep only last 10 backups
        cleanup_old_backups(backup_dir, keep=10)

        return True

    except Exception as e:
        print(f"[ERROR] Backup failed: {e}")
        return False

def cleanup_old_backups(backup_dir, keep=10):
    """Keep only the most recent N backups"""
    backups = sorted(backup_dir.glob('minigolf_backup_*.db'),
                     key=lambda p: p.stat().st_mtime,
                     reverse=True)

    if len(backups) > keep:
        for old_backup in backups[keep:]:
            old_backup.unlink()
            print(f"  Removed old backup: {old_backup.name}")

if __name__ == '__main__':
    backup_database()
