#!/usr/bin/env python3
"""
Cleanup test data from production database

Removes all players with test/example email addresses and their associated data:
- Round scores
- Course ratings
- Course notes
- Course trophies
- Rounds (if only test players participated)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database import init_database, get_db
from config import Config

def cleanup_test_data():
    """Remove all test data from the database"""

    print("=== Cleaning up test data from database ===\n")

    # Initialize database
    init_database(Config.DATABASE_PATH)
    db = get_db()
    conn = db.get_connection()

    # Patterns for test emails
    test_patterns = ['%test%', '%example%', '%dummy%']

    # Find all test players
    print("Finding test players...")
    test_player_ids = []
    for pattern in test_patterns:
        cursor = conn.execute(
            "SELECT id, name, email FROM players WHERE email LIKE ?",
            (pattern,)
        )
        for row in cursor.fetchall():
            test_player_ids.append(row['id'])
            print(f"  - {row['name']} ({row['email']})")

    if not test_player_ids:
        print("\nNo test players found!")
        return

    print(f"\nFound {len(test_player_ids)} test players")

    # Create placeholders for SQL IN clause
    placeholders = ','.join('?' * len(test_player_ids))

    # Delete round scores for test players
    print("\nDeleting round scores...")
    cursor = conn.execute(
        f"DELETE FROM round_scores WHERE player_id IN ({placeholders})",
        test_player_ids
    )
    print(f"  Deleted {cursor.rowcount} round scores")

    # Delete course ratings by test players
    print("Deleting course ratings...")
    cursor = conn.execute(
        f"DELETE FROM course_ratings WHERE player_id IN ({placeholders})",
        test_player_ids
    )
    print(f"  Deleted {cursor.rowcount} course ratings")

    # Delete course notes by test players
    print("Deleting course notes...")
    cursor = conn.execute(
        f"DELETE FROM course_notes WHERE player_id IN ({placeholders})",
        test_player_ids
    )
    print(f"  Deleted {cursor.rowcount} course notes")

    # Delete course trophies owned by test players
    print("Deleting course trophies...")
    cursor = conn.execute(
        f"DELETE FROM course_trophies WHERE player_id IN ({placeholders})",
        test_player_ids
    )
    print(f"  Deleted {cursor.rowcount} course trophies")

    # Find rounds with no remaining scores (orphaned rounds)
    print("Finding orphaned rounds...")
    cursor = conn.execute("""
        SELECT r.id
        FROM rounds r
        LEFT JOIN round_scores rs ON r.id = rs.round_id
        WHERE rs.round_id IS NULL
    """)
    orphaned_round_ids = [row['id'] for row in cursor.fetchall()]

    if orphaned_round_ids:
        print(f"  Found {len(orphaned_round_ids)} orphaned rounds")
        orphan_placeholders = ','.join('?' * len(orphaned_round_ids))
        cursor = conn.execute(
            f"DELETE FROM rounds WHERE id IN ({orphan_placeholders})",
            orphaned_round_ids
        )
        print(f"  Deleted {cursor.rowcount} orphaned rounds")
    else:
        print("  No orphaned rounds found")

    # Delete test players
    print("\nDeleting test players...")
    cursor = conn.execute(
        f"DELETE FROM players WHERE id IN ({placeholders})",
        test_player_ids
    )
    print(f"  Deleted {cursor.rowcount} test players")

    # Commit all changes
    conn.commit()

    print("\n=== Cleanup complete! ===")
    print(f"\nSummary:")
    print(f"  - Removed {len(test_player_ids)} test players")
    print(f"  - Cleaned up associated scores, ratings, notes, and trophies")
    if orphaned_round_ids:
        print(f"  - Removed {len(orphaned_round_ids)} orphaned rounds")

if __name__ == '__main__':
    try:
        cleanup_test_data()
    except Exception as e:
        print(f"\nError during cleanup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
