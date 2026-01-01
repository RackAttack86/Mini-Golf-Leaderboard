#!/usr/bin/env python3
"""Restore SQLite database from backup"""

import shutil
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config

def list_backups():
    """List available backups"""
    backup_dir = Config.DATA_DIR / 'backups'

    if not backup_dir.exists():
        print("No backups directory found.")
        return []

    backups = sorted(backup_dir.glob('minigolf_backup_*.db'),
                     key=lambda p: p.stat().st_mtime,
                     reverse=True)

    if not backups:
        print("No backups found.")
        return []

    print("\nAvailable backups:")
    print("-" * 60)
    for i, backup in enumerate(backups, 1):
        size_kb = backup.stat().st_size / 1024
        mtime = backup.stat().st_mtime
        from datetime import datetime
        timestamp = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        print(f"{i}. {backup.name}")
        print(f"   Size: {size_kb:.1f} KB | Created: {timestamp}")

    return backups

def restore_database(backup_path):
    """Restore database from backup"""

    db_path = Config.DATABASE_PATH

    # Create backup of current database first
    if db_path.exists():
        current_backup = db_path.parent / f'minigolf_before_restore_{int(time.time())}.db'
        import time
        shutil.copy2(db_path, current_backup)
        print(f"[OK] Current database backed up to: {current_backup.name}")

    # Restore from backup
    try:
        shutil.copy2(backup_path, db_path)
        print(f"[OK] Database restored successfully from: {backup_path.name}")
        return True
    except Exception as e:
        print(f"[ERROR] Restore failed: {e}")
        return False

if __name__ == '__main__':
    backups = list_backups()

    if backups:
        print("\nEnter backup number to restore (or 'q' to quit): ", end='')
        choice = input().strip()

        if choice.lower() == 'q':
            print("Cancelled.")
            sys.exit(0)

        try:
            index = int(choice) - 1
            if 0 <= index < len(backups):
                print(f"\n[WARNING] This will overwrite your current database!")
                print(f"Are you sure you want to restore from {backups[index].name}? (yes/no): ", end='')
                confirm = input().strip().lower()

                if confirm == 'yes':
                    restore_database(backups[index])
                else:
                    print("Cancelled.")
            else:
                print("Invalid backup number.")
        except ValueError:
            print("Invalid input.")
