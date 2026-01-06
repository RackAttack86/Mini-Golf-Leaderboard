"""
Migrate Mini Golf Leaderboard data from JSON files to SQLite database

This script performs a one-time migration of all data from JSON files to SQLite.
It includes backup creation, validation, and rollback capabilities.
"""

import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database import init_database


def backup_json_files(data_dir: Path, backup_dir: Path):
    """
    Create backup of all JSON files

    Args:
        data_dir: Source data directory
        backup_dir: Backup destination directory
    """
    print(f"\nBacking up JSON files to {backup_dir}...")

    backup_dir.mkdir(parents=True, exist_ok=True)

    json_files = [
        'players.json',
        'courses.json',
        'rounds.json',
        'course_ratings.json',
        'tournaments.json'
    ]

    for filename in json_files:
        source = data_dir / filename
        if source.exists():
            dest = backup_dir / filename
            shutil.copy2(source, dest)
            print(f"  [OK] Backed up {filename}")

    print("Backup complete!")


def load_json_file(file_path: Path) -> dict:
    """Load and parse JSON file"""
    if not file_path.exists():
        return {}

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def migrate_players(conn: sqlite3.Connection, data_dir: Path) -> int:
    """
    Migrate players from JSON to SQLite

    Args:
        conn: Database connection
        data_dir: Data directory path

    Returns:
        Number of players migrated
    """
    print("\nMigrating players...")

    data = load_json_file(data_dir / 'players.json')
    players = data.get('players', [])

    for player in players:
        conn.execute("""
            INSERT INTO players (
                id, name, email, profile_picture, favorite_color,
                google_id, role, last_login, created_at, active, meta_quest_username
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            player['id'],
            player['name'],
            player.get('email'),
            player.get('profile_picture'),
            player.get('favorite_color', '#2e7d32'),
            player.get('google_id'),
            player.get('role', 'player'),
            player.get('last_login'),
            player['created_at'],
            1 if player.get('active', True) else 0,
            None  # meta_quest_username will be set manually later
        ))

    print(f"  [OK] Migrated {len(players)} players")
    return len(players)


def migrate_courses(conn: sqlite3.Connection, data_dir: Path) -> int:
    """
    Migrate courses from JSON to SQLite

    Args:
        conn: Database connection
        data_dir: Data directory path

    Returns:
        Number of courses migrated
    """
    print("\nMigrating courses...")

    data = load_json_file(data_dir / 'courses.json')
    courses = data.get('courses', [])

    for course in courses:
        conn.execute("""
            INSERT INTO courses (
                id, name, location, holes, par, image_url, created_at, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            course['id'],
            course['name'],
            course.get('location'),
            course.get('holes'),
            course.get('par'),
            course.get('image_url'),
            course['created_at'],
            1 if course.get('active', True) else 0
        ))

    print(f"  [OK] Migrated {len(courses)} courses")
    return len(courses)


def migrate_rounds(conn: sqlite3.Connection, data_dir: Path) -> tuple[int, int]:
    """
    Migrate rounds from JSON to SQLite

    Args:
        conn: Database connection
        data_dir: Data directory path

    Returns:
        Tuple of (rounds migrated, round_scores migrated)
    """
    print("\nMigrating rounds...")

    data = load_json_file(data_dir / 'rounds.json')
    rounds = data.get('rounds', [])

    round_count = 0
    score_count = 0

    for round_data in rounds:
        # Insert round
        conn.execute("""
            INSERT INTO rounds (
                id, course_id, course_name, date_played, timestamp,
                round_start_time, notes, picture_filename
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            round_data['id'],
            round_data['course_id'],
            round_data['course_name'],
            round_data['date_played'],
            round_data['timestamp'],
            None,  # round_start_time will be from OCR uploads
            round_data.get('notes'),
            None  # picture_filename will be from OCR uploads
        ))
        round_count += 1

        # Insert round scores (previously nested in round object)
        for score_data in round_data.get('scores', []):
            conn.execute("""
                INSERT INTO round_scores (
                    round_id, player_id, player_name, score, hole_scores
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                round_data['id'],
                score_data['player_id'],
                score_data['player_name'],
                score_data['score'],
                None  # hole_scores will be from OCR uploads
            ))
            score_count += 1

    print(f"  [OK] Migrated {round_count} rounds with {score_count} player scores")
    return round_count, score_count


def migrate_course_ratings(conn: sqlite3.Connection, data_dir: Path) -> int:
    """
    Migrate course ratings from JSON to SQLite

    Args:
        conn: Database connection
        data_dir: Data directory path

    Returns:
        Number of ratings migrated
    """
    print("\nMigrating course ratings...")

    data = load_json_file(data_dir / 'course_ratings.json')
    ratings = data.get('ratings', [])

    migrated_count = 0
    skipped_count = 0

    for rating in ratings:
        player_id = rating['player_id']

        # Check if this is a Google ID (not UUID) - lookup player by google_id
        if len(player_id) < 30:  # Google IDs are shorter than UUIDs
            cursor = conn.execute(
                "SELECT id FROM players WHERE google_id = ?",
                (player_id,)
            )
            result = cursor.fetchone()
            if result:
                player_id = result['id']  # Use player's UUID
            else:
                print(f"    [SKIP] Rating for unknown Google user {player_id}")
                skipped_count += 1
                continue

        # Check if course exists
        cursor = conn.execute("SELECT id FROM courses WHERE id = ?", (rating['course_id'],))
        if not cursor.fetchone():
            print(f"    [SKIP] Rating for unknown course {rating['course_id']}")
            skipped_count += 1
            continue

        try:
            conn.execute("""
                INSERT INTO course_ratings (
                    player_id, course_id, rating, date_rated
                ) VALUES (?, ?, ?, ?)
            """, (
                player_id,
                rating['course_id'],
                rating['rating'],
                rating['date_rated']
            ))
            migrated_count += 1
        except Exception as e:
            print(f"    [SKIP] Rating migration error: {e}")
            skipped_count += 1

    print(f"  [OK] Migrated {migrated_count} course ratings ({skipped_count} skipped)")
    return migrated_count


def migrate_tournaments(conn: sqlite3.Connection, data_dir: Path) -> tuple[int, int]:
    """
    Migrate tournaments from JSON to SQLite

    Args:
        conn: Database connection
        data_dir: Data directory path

    Returns:
        Tuple of (tournaments migrated, tournament_rounds migrated)
    """
    print("\nMigrating tournaments...")

    data = load_json_file(data_dir / 'tournaments.json')
    tournaments = data.get('tournaments', [])

    tournament_count = 0
    tournament_round_count = 0

    for tournament in tournaments:
        # Insert tournament
        conn.execute("""
            INSERT INTO tournaments (
                id, name, description, start_date, end_date, created_at, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            tournament['id'],
            tournament['name'],
            tournament.get('description'),
            tournament.get('start_date'),
            tournament.get('end_date'),
            tournament['created_at'],
            1 if tournament.get('active', True) else 0
        ))
        tournament_count += 1

        # Insert tournament rounds if they exist
        for round_id in tournament.get('round_ids', []):
            conn.execute("""
                INSERT INTO tournament_rounds (tournament_id, round_id)
                VALUES (?, ?)
            """, (tournament['id'], round_id))
            tournament_round_count += 1

    print(f"  [OK] Migrated {tournament_count} tournaments with {tournament_round_count} tournament rounds")
    return tournament_count, tournament_round_count


def validate_migration(conn: sqlite3.Connection, stats: dict):
    """
    Validate migrated data counts

    Args:
        conn: Database connection
        stats: Dictionary of expected counts
    """
    print("\nValidating migration...")

    validations = [
        ("players", "SELECT COUNT(*) FROM players"),
        ("courses", "SELECT COUNT(*) FROM courses"),
        ("rounds", "SELECT COUNT(*) FROM rounds"),
        ("round_scores", "SELECT COUNT(*) FROM round_scores"),
        ("course_ratings", "SELECT COUNT(*) FROM course_ratings"),
        ("tournaments", "SELECT COUNT(*) FROM tournaments"),
        ("tournament_rounds", "SELECT COUNT(*) FROM tournament_rounds")
    ]

    all_valid = True
    for table_name, query in validations:
        actual_count = conn.execute(query).fetchone()[0]
        expected_count = stats.get(table_name, 0)

        status = "[OK]" if actual_count == expected_count else "[FAIL]"
        print(f"  {status} {table_name}: {actual_count} (expected {expected_count})")

        if actual_count != expected_count:
            all_valid = False

    if all_valid:
        print("\n[OK] All validations passed!")
    else:
        print("\n[FAIL] Validation failed! Some counts don't match.")
        return False

    return True


def migrate_all(data_dir: Path = None, db_path: Path = None):
    """
    Run complete migration from JSON to SQLite

    Args:
        data_dir: Data directory (defaults to ../data)
        db_path: Database file path (defaults to data/minigolf.db)
    """
    if data_dir is None:
        data_dir = Path(__file__).parent.parent / 'data'

    if db_path is None:
        db_path = data_dir / 'minigolf.db'

    print("=" * 70)
    print("Mini Golf Leaderboard - JSON to SQLite Migration")
    print("=" * 70)

    # Create backup
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = data_dir / f'backup_{timestamp}'
    backup_json_files(data_dir, backup_dir)

    # Initialize database
    print(f"\nInitializing SQLite database at {db_path}...")
    db = init_database(db_path)
    conn = db.get_connection()

    try:
        # Migrate all data
        stats = {}

        stats['players'] = migrate_players(conn, data_dir)
        stats['courses'] = migrate_courses(conn, data_dir)

        round_count, score_count = migrate_rounds(conn, data_dir)
        stats['rounds'] = round_count
        stats['round_scores'] = score_count

        stats['course_ratings'] = migrate_course_ratings(conn, data_dir)

        tournament_count, tournament_round_count = migrate_tournaments(conn, data_dir)
        stats['tournaments'] = tournament_count
        stats['tournament_rounds'] = tournament_round_count

        # Validate
        if not validate_migration(conn, stats):
            print("\n⚠ Warning: Validation failed. Check the counts above.")
            print(f"Backup saved at: {backup_dir}")
            return False

        print("\n" + "=" * 70)
        print("[SUCCESS] Migration completed successfully!")
        print("=" * 70)
        print(f"\nBackup location: {backup_dir}")
        print(f"Database location: {db_path}")
        print("\nNext steps:")
        print("1. Test the application with the new database")
        print("2. If issues occur, restore from backup")
        print("3. After 2+ weeks of validation, backup can be deleted")

        return True

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        print(f"Backup saved at: {backup_dir}")
        print("You can restore from backup if needed.")
        raise


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migrate Mini Golf data from JSON to SQLite')
    parser.add_argument('--data-dir', type=Path, help='Data directory path')
    parser.add_argument('--db-path', type=Path, help='Database file path')

    args = parser.parse_args()

    migrate_all(data_dir=args.data_dir, db_path=args.db_path)
