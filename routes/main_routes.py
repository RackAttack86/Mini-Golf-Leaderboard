# Standard library
import os
from datetime import datetime, timedelta

# Third-party
from flask import Blueprint, render_template
from flask_login import current_user

# Local
from models.player import Player
from models.course import Course
from models.round import Round
from models.course_trophy import CourseTrophy
from services.achievement_service import AchievementService
from extensions import limiter, csrf

bp = Blueprint('main', __name__)


def filter_email_from_players(players, allow_all=False):
    """
    Filter email addresses from player dictionaries based on authorization.

    Args:
        players: Single player dict or list of player dicts
        allow_all: If True, allow all emails (for admins)

    Returns:
        Filtered player dict or list of dicts
    """
    is_list = isinstance(players, list)
    player_list = players if is_list else [players]

    # Check if user is admin
    is_admin = current_user.is_authenticated and current_user.is_admin

    # Filter emails
    for player in player_list:
        if player and not (is_admin or allow_all):
            player['email'] = None

    return player_list if is_list else (player_list[0] if player_list else None)


@bp.route('/')
def index():
    """Dashboard/home page"""
    # Get summary statistics
    players = Player.get_all()
    courses = Course.get_all()
    rounds = Round.get_all()

    # Get recent rounds from last 15 days for activity trends
    today = datetime.now().date()
    fifteen_days_ago = today - timedelta(days=14)  # 14 days ago = 15 days total including today

    # Filter rounds from last 15 days
    recent_rounds = [
        r for r in rounds
        if datetime.strptime(r['date_played'], '%Y-%m-%d').date() >= fifteen_days_ago
    ]

    # Get last 10 rounds for the recent rounds table (exclude solo rounds)
    non_solo_rounds = [r for r in rounds if len(r['scores']) > 1]
    last_10_rounds = non_solo_rounds[:10] if len(non_solo_rounds) > 10 else non_solo_rounds

    # Add winner player data and course image to rounds (for both lists)
    for round_data in recent_rounds + last_10_rounds:
        if round_data['scores']:
            winner_score = min(round_data['scores'], key=lambda x: x['score'])
            winner_player = Player.get_by_id(winner_score['player_id'])
            winner_player = filter_email_from_players(winner_player)
            round_data['winner_player'] = winner_player

        # Add course image data
        course = Course.get_by_id(round_data['course_id'])
        round_data['course_image_url'] = course.get('image_url', '') if course else ''

    # Calculate top 3 players (by average finishing position)
    player_stats = []
    for player in players:
        player_rounds = Round.get_by_player(player['id'])
        if player_rounds:
            total_position = 0
            count = 0
            for round_data in player_rounds:
                # Skip solo rounds (no competition)
                if len(round_data['scores']) <= 1:
                    continue

                # Find player's position in this round
                player_score = Round.get_player_score_in_round(round_data, player['id'])
                if player_score is not None:
                    # Calculate position based on score (handle ties)
                    position = 1
                    for other_score in round_data['scores']:
                        if other_score['score'] < player_score:
                            position += 1

                    total_position += position
                    count += 1

            if count > 0:
                avg_position = total_position / count
                player['achievement_score'] = AchievementService.get_achievement_score(player['id'])
                player_stats.append({
                    'player': player,
                    'avg_position': avg_position,
                    'rounds_played': count
                })

    # Sort by average position (lower is better - 1st is better than 2nd)
    player_stats.sort(key=lambda x: x['avg_position'])
    top_players = player_stats[:3]

    # Filter emails from top players
    for player_stat in top_players:
        player_stat['player'] = filter_email_from_players(player_stat['player'])

    return render_template('index.html',
                           total_players=len(players),
                           total_courses=len(courses),
                           total_rounds=len(rounds),
                           recent_rounds=recent_rounds,  # Last 15 days for activity trends
                           last_10_rounds=last_10_rounds,  # Last 10 non-solo rounds for table
                           top_players=top_players)


@bp.route('/health')
@csrf.exempt
@limiter.exempt
def health_check():
    """Health check endpoint for Fly.io monitoring and Docker health checks

    This endpoint must:
    - Not require authentication
    - Not require CSRF token
    - Not redirect to HTTPS (Fly.io uses internal HTTP)
    - Return 200 OK when healthy
    """
    from models.database import get_db
    from flask import jsonify

    try:
        # Check database connectivity
        db = get_db()
        conn = db.get_connection()
        cursor = conn.execute("SELECT 1")
        cursor.fetchone()

        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 503


@bp.route('/admin/cleanup-test-data')
@csrf.exempt
@limiter.exempt
def cleanup_test_data():
    """Admin endpoint to clean up test data from production database"""
    from flask import jsonify
    from models.database import get_db
    from pathlib import Path

    db = get_db()
    conn = db.get_connection()

    # Get counts before cleanup
    cursor = conn.execute("SELECT COUNT(*) as count FROM players")
    players_before = cursor.fetchone()[0]
    cursor = conn.execute("SELECT COUNT(*) as count FROM courses")
    courses_before = cursor.fetchone()[0]
    cursor = conn.execute("SELECT COUNT(*) as count FROM rounds")
    rounds_before = cursor.fetchone()[0]

    # Load cleanup script
    cleanup_file = Path(__file__).parent.parent / 'migrations' / 'cleanup_test_data.sql'
    if not cleanup_file.exists():
        return jsonify({
            'error': f'Cleanup file not found: {cleanup_file}'
        }), 404

    with open(cleanup_file, 'r', encoding='utf-8') as f:
        cleanup_sql = f.read()

    try:
        conn.executescript(cleanup_sql)
        conn.commit()

        # Get counts after cleanup
        cursor = conn.execute("SELECT COUNT(*) as count FROM players")
        players_after = cursor.fetchone()[0]
        cursor = conn.execute("SELECT COUNT(*) as count FROM courses")
        courses_after = cursor.fetchone()[0]
        cursor = conn.execute("SELECT COUNT(*) as count FROM rounds")
        rounds_after = cursor.fetchone()[0]

        return jsonify({
            'status': 'success',
            'players': {
                'before': players_before,
                'after': players_after,
                'deleted': players_before - players_after
            },
            'courses': {
                'before': courses_before,
                'after': courses_after,
                'deleted': courses_before - courses_after
            },
            'rounds': {
                'before': rounds_before,
                'after': rounds_after,
                'deleted': rounds_before - rounds_after
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@bp.route('/admin/restore-missing-players')
@csrf.exempt
@limiter.exempt
def restore_missing_players():
    """Admin endpoint to restore missing players (Michael, Sam, Max)"""
    from flask import jsonify
    from models.database import get_db

    db = get_db()
    conn = db.get_connection()

    # Players to restore
    players_to_restore = [
        {
            'id': 'aa156ad0-1875-42a3-84ff-6261142bcca3',
            'name': 'Michael',
            'email': 'popeage0906@gmail.com',
            'profile_picture': None,
            'favorite_color': '#00ff2a',
            'google_id': None,
            'role': 'player',
            'last_login': None,
            'created_at': '2025-12-22T19:26:45Z',
            'active': 1,
            'meta_quest_username': 'Popeage'
        },
        {
            'id': '952e9b12-23b0-4775-b810-4fef626e20c6',
            'name': 'Samwise Gamgee',
            'email': 'riverpines.sam@gmail.com',
            'profile_picture': 'e1f00e25baaa4216a951b17017e28dcd.jpg',
            'favorite_color': '#ff8000',
            'google_id': None,
            'role': 'player',
            'last_login': None,
            'created_at': '2025-12-22T19:27:13Z',
            'active': 1,
            'meta_quest_username': 'NikeOne07'
        },
        {
            'id': '8380075d-145f-43b3-9b0c-8efc420e48ba',
            'name': 'Max',
            'email': None,
            'profile_picture': None,
            'favorite_color': '#f9f110',
            'google_id': None,
            'role': 'player',
            'last_login': None,
            'created_at': '2025-12-27T02:14:32Z',
            'active': 1,
            'meta_quest_username': None
        },
        {
            'id': '7fad5756-6327-4093-bafe-7884fe957749',
            'name': 'Matthew Rackley Test',
            'email': 'matthew.rackley86@gmail.com',
            'profile_picture': None,
            'favorite_color': '#ff00ea',
            'google_id': '110738743856864182140',
            'role': 'player',
            'last_login': '2026-01-08T05:21:06Z',
            'created_at': '2025-12-26T06:22:25Z',
            'active': 1,
            'meta_quest_username': None
        }
    ]

    try:
        restored = []
        for player in players_to_restore:
            # Check if player already exists
            cursor = conn.execute("SELECT COUNT(*) as count FROM players WHERE id = ?", (player['id'],))
            if cursor.fetchone()[0] == 0:
                # Insert player
                conn.execute("""
                    INSERT INTO players (id, name, email, profile_picture, favorite_color, google_id, role, last_login, created_at, active, meta_quest_username)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (player['id'], player['name'], player['email'], player['profile_picture'],
                      player['favorite_color'], player['google_id'], player['role'],
                      player['last_login'], player['created_at'], player['active'],
                      player['meta_quest_username']))
                restored.append(player['name'])

        conn.commit()

        # Get current player count
        cursor = conn.execute("SELECT COUNT(*) as count FROM players")
        total_players = cursor.fetchone()[0]

        return jsonify({
            'status': 'success',
            'restored': restored,
            'total_players': total_players
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@bp.route('/admin/load-rounds-data')
@csrf.exempt
@limiter.exempt
def load_rounds_data():
    """Admin endpoint to load rounds data with course mapping"""
    from flask import jsonify
    from models.database import get_db
    import json
    from pathlib import Path

    db = get_db()
    conn = db.get_connection()

    # Get counts before loading
    cursor = conn.execute("SELECT COUNT(*) as count FROM rounds")
    rounds_before = cursor.fetchone()[0]
    cursor = conn.execute("SELECT COUNT(*) as count FROM round_scores")
    scores_before = cursor.fetchone()[0]

    # Load rounds JSON data with course names
    rounds_file = Path(__file__).parent.parent / 'migrations' / 'rounds_data.json'
    if not rounds_file.exists():
        return jsonify({
            'error': f'Rounds data file not found: {rounds_file}'
        }), 404

    with open(rounds_file, 'r', encoding='utf-8') as f:
        rounds_data = json.load(f)

    # Load and map rounds
    total_rounds_in_file = len(rounds_data.get('rounds', []))

    try:
        # Build course name -> ID mapping from production
        cursor = conn.execute("SELECT id, name FROM courses")
        course_map = {row['name']: row['id'] for row in cursor.fetchall()}

        # Insert rounds with mapped course IDs
        inserted_rounds = 0
        inserted_scores = 0
        skipped_rounds = 0

        from datetime import datetime

        for round_data in rounds_data['rounds']:
            course_name = round_data['course_name']
            if course_name not in course_map:
                skipped_rounds += 1
                continue

            production_course_id = course_map[course_name]

            # Insert round (include course_name and timestamp for production schema)
            timestamp = datetime.fromisoformat(round_data['date_played']).isoformat() if 'T' not in round_data['date_played'] else round_data['date_played']
            insert_cursor = conn.execute("""
                INSERT OR IGNORE INTO rounds (id, course_id, course_name, date_played, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (round_data['id'], production_course_id, course_name, round_data['date_played'], timestamp))

            # Check if insert succeeded
            if insert_cursor.rowcount > 0:
                inserted_rounds += 1

                # Insert scores for this round
                for score in round_data['scores']:
                    conn.execute("""
                        INSERT OR IGNORE INTO round_scores (round_id, player_id, player_name, score, hole_scores)
                        VALUES (?, ?, ?, ?, ?)
                    """, (score['round_id'], score['player_id'], score['player_name'],
                          score['score'], score['hole_scores'] or ''))
                    inserted_scores += 1

        conn.commit()

        # Get counts after loading
        cursor = conn.execute("SELECT COUNT(*) as count FROM rounds")
        rounds_after = cursor.fetchone()[0]
        cursor = conn.execute("SELECT COUNT(*) as count FROM round_scores")
        scores_after = cursor.fetchone()[0]

        return jsonify({
            'status': 'success',
            'rounds': {
                'before': rounds_before,
                'after': rounds_after,
                'inserted': inserted_rounds,
                'skipped': skipped_rounds
            },
            'scores': {
                'before': scores_before,
                'after': scores_after,
                'inserted': inserted_scores
            }
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/admin/check-session-storage')
@csrf.exempt
@limiter.exempt
def check_session_storage():
    """Check session storage configuration"""
    from flask import jsonify, current_app
    import os
    from pathlib import Path

    session_dir = current_app.config.get('SESSION_FILE_DIR')
    session_type = current_app.config.get('SESSION_TYPE')

    if session_dir:
        dir_exists = session_dir.exists() if isinstance(session_dir, Path) else os.path.exists(session_dir)
        dir_writable = os.access(session_dir, os.W_OK) if dir_exists else False

        # Try to create a test file
        test_file_path = Path(session_dir) / 'test_write.txt'
        write_test = False
        write_error = None
        try:
            test_file_path.write_text('test')
            test_file_path.unlink()
            write_test = True
        except Exception as e:
            write_error = str(e)

        return jsonify({
            'session_type': session_type,
            'session_dir': str(session_dir),
            'dir_exists': dir_exists,
            'dir_writable': dir_writable,
            'write_test_passed': write_test,
            'write_test_error': write_error,
            'files_in_dir': len(list(Path(session_dir).iterdir())) if dir_exists else None
        })
    else:
        return jsonify({
            'session_type': session_type,
            'session_dir': None,
            'note': 'Filesystem session storage not configured'
        })


@bp.route('/admin/check-oauth-config')
@csrf.exempt
@limiter.exempt
def check_oauth_config():
    """Check OAuth configuration status"""
    from flask import jsonify, current_app

    client_id = current_app.config.get('GOOGLE_OAUTH_CLIENT_ID', '')
    client_secret = current_app.config.get('GOOGLE_OAUTH_CLIENT_SECRET', '')

    return jsonify({
        'client_id_set': bool(client_id),
        'client_id_length': len(client_id) if client_id else 0,
        'client_secret_set': bool(client_secret),
        'client_secret_length': len(client_secret) if client_secret else 0,
        'client_id_prefix': client_id[:20] + '...' if len(client_id) > 20 else client_id
    })


@bp.route('/admin/verify-rounds')
@csrf.exempt
@limiter.exempt
def verify_rounds():
    """Verify rounds data loaded correctly"""
    from flask import jsonify
    from models.database import get_db

    db = get_db()
    conn = db.get_connection()

    # Get sample rounds with course and player info
    cursor = conn.execute("""
        SELECT r.id, r.course_name, r.date_played,
               COUNT(rs.player_id) as num_players,
               GROUP_CONCAT(rs.player_name) as players
        FROM rounds r
        LEFT JOIN round_scores rs ON r.id = rs.round_id
        GROUP BY r.id
        ORDER BY r.date_played DESC
        LIMIT 5
    """)
    sample_rounds = [dict(row) for row in cursor.fetchall()]

    # Get player round counts
    cursor = conn.execute("""
        SELECT player_name, COUNT(DISTINCT round_id) as round_count
        FROM round_scores
        GROUP BY player_name
        ORDER BY round_count DESC
    """)
    player_stats = [dict(row) for row in cursor.fetchall()]

    return jsonify({
        'total_rounds': len(sample_rounds),
        'sample_rounds': sample_rounds,
        'player_round_counts': player_stats
    })


@bp.route('/admin/debug-course-names')
@csrf.exempt
@limiter.exempt
def debug_course_names():
    """Debug endpoint to check course names for mapping"""
    from flask import jsonify
    from models.database import get_db
    from pathlib import Path
    import json

    db = get_db()
    conn = db.get_connection()

    # Get all course names from production
    cursor = conn.execute("SELECT id, name FROM courses ORDER BY name")
    production_courses = [{'id': row['id'], 'name': row['name']} for row in cursor.fetchall()]

    # Load JSON and get unique course names
    rounds_file = Path(__file__).parent.parent / 'migrations' / 'rounds_data.json'
    with open(rounds_file, 'r', encoding='utf-8') as f:
        rounds_data = json.load(f)

    json_courses = list(set(r['course_name'] for r in rounds_data['rounds']))

    # Find matches
    prod_names = {c['name'] for c in production_courses}
    matches = [c for c in json_courses if c in prod_names]
    mismatches = [c for c in json_courses if c not in prod_names]

    return jsonify({
        'production_courses': production_courses[:10],  # First 10
        'json_course_names': sorted(json_courses),
        'matches': matches,
        'mismatches': mismatches,
        'total_production': len(production_courses),
        'total_json_unique': len(json_courses)
    })


@bp.route('/admin/debug-rounds-status')
@csrf.exempt
@limiter.exempt
def debug_rounds_status():
    """Debug endpoint to check rounds migration status"""
    from flask import jsonify
    from models.database import get_db
    from pathlib import Path
    import os
    import json

    db = get_db()
    conn = db.get_connection()

    # Check counts
    cursor = conn.execute("SELECT COUNT(*) as count FROM rounds")
    rounds_count = cursor.fetchone()[0]

    cursor = conn.execute("SELECT COUNT(*) as count FROM round_scores")
    scores_count = cursor.fetchone()[0]

    cursor = conn.execute("SELECT COUNT(*) as count FROM courses")
    courses_count = cursor.fetchone()[0]

    # Check FOREIGN KEY enforcement
    cursor = conn.execute("PRAGMA foreign_keys")
    fk_enabled = cursor.fetchone()[0]

    # Get a sample course ID to test
    cursor = conn.execute("SELECT id, name FROM courses WHERE name = 'Crystal Lair' LIMIT 1")
    row = cursor.fetchone()
    crystal_lair = dict(row) if row else None

    # Check if JSON file exists
    rounds_file = Path(__file__).parent.parent / 'migrations' / 'rounds_data.json'
    file_exists = rounds_file.exists()
    file_size = rounds_file.stat().st_size if file_exists else 0

    # Get sample round if any exist
    cursor = conn.execute("SELECT id, course_id, date_played FROM rounds LIMIT 1")
    row = cursor.fetchone()
    sample_round = dict(row) if row else None

    # Try a test insert with exact same format as real insert
    test_result = None
    try:
        if crystal_lair:
            test_cursor = conn.execute("""
                INSERT INTO rounds (id, course_id, course_name, date_played)
                VALUES (?, ?, ?, ?)
            """, ('test-round-id-123', crystal_lair['id'], 'Crystal Lair', '2025-12-19'))
            test_result = f"INSERT succeeded, rowcount: {test_cursor.rowcount}"
            conn.rollback()  # Don't actually commit the test
        else:
            test_result = "Crystal Lair course not found"
    except Exception as e:
        test_result = f"INSERT failed: {str(e)}"
        conn.rollback()

    return jsonify({
        'database': {
            'rounds': rounds_count,
            'scores': scores_count,
            'courses': courses_count,
            'foreign_keys_enabled': bool(fk_enabled)
        },
        'json_file': {
            'exists': file_exists,
            'path': str(rounds_file),
            'size_bytes': file_size
        },
        'sample_round': sample_round,
        'crystal_lair_course': crystal_lair,
        'test_insert': test_result,
        'working_directory': os.getcwd()
    })


@bp.route('/trophies')
def trophies():
    """Display all course trophies"""
    # Get all courses
    courses = Course.get_all()

    # Convert course names to Linux-friendly trophy filenames
    def course_to_trophy_name(course_name):
        return course_name.replace("'", "").replace(",", "").replace(" ", "_")

    # Check which courses have trophy images (normal and hard)
    normal_trophy_dir = os.path.join('static', 'uploads', 'trophies', 'normal')
    hard_trophy_dir = os.path.join('static', 'uploads', 'trophies', 'hard')
    normal_trophy_files = set(os.listdir(normal_trophy_dir)) if os.path.exists(normal_trophy_dir) else set()
    hard_trophy_files = set(os.listdir(hard_trophy_dir)) if os.path.exists(hard_trophy_dir) else set()

    # Build list of courses with trophy info
    course_trophies = []
    for course in courses:
        is_hard = '(HARD)' in course['name']
        base_name = course['name'].replace(' (HARD)', '')
        trophy_filename = course_to_trophy_name(base_name) + '.png'

        # Check appropriate directory based on course difficulty
        if is_hard:
            has_trophy = trophy_filename in hard_trophy_files
            trophy_subdir = 'hard'
        else:
            has_trophy = trophy_filename in normal_trophy_files
            trophy_subdir = 'normal'

        course_trophies.append({
            'course_id': course['id'],
            'course_name': course['name'],  # Keep HARD in name for display
            'trophy_filename': trophy_filename,
            'trophy_subdir': trophy_subdir,
            'has_trophy': has_trophy
        })

    # Sort by course name
    course_trophies.sort(key=lambda x: x['course_name'])

    return render_template('trophies.html', course_trophies=course_trophies)


@bp.route('/trophy-leaderboard')
def trophy_leaderboard():
    """Trophy leaderboard showing players ranked by trophy count"""
    from models.database import get_db

    db = get_db()
    conn = db.get_connection()

    # Get trophy counts per player
    cursor = conn.execute("""
        SELECT
            p.id as player_id,
            p.name as player_name,
            p.profile_picture,
            COUNT(ct.course_id) as trophy_count
        FROM players p
        LEFT JOIN course_trophies ct ON p.id = ct.player_id
        WHERE p.active = 1
        GROUP BY p.id, p.name, p.profile_picture
        HAVING trophy_count > 0
        ORDER BY trophy_count DESC, p.name ASC
    """)

    leaderboard = []
    for row in cursor.fetchall():
        player_id = row['player_id']

        # Get the specific trophies this player owns
        trophies = CourseTrophy.get_trophies_owned_by_player(player_id)

        leaderboard.append({
            'player_id': player_id,
            'player_name': row['player_name'],
            'profile_picture': row['profile_picture'],
            'trophy_count': row['trophy_count'],
            'trophies': trophies
        })

    # Get total trophy count
    cursor = conn.execute("SELECT COUNT(*) as total FROM course_trophies")
    total_trophies = cursor.fetchone()['total']

    # Get total courses with 4+ player rounds (potential trophies)
    cursor = conn.execute("""
        SELECT COUNT(DISTINCT r.course_id) as count
        FROM rounds r
        JOIN round_scores rs ON r.id = rs.round_id
        GROUP BY r.id
        HAVING COUNT(DISTINCT rs.player_id) >= 4
    """)
    total_contested_courses = len(cursor.fetchall())

    return render_template('trophy_leaderboard.html',
                         leaderboard=leaderboard,
                         total_trophies=total_trophies,
                         total_contested_courses=total_contested_courses)
