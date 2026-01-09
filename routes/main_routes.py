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


@bp.route('/debug-trophies')
@csrf.exempt
@limiter.exempt
def debug_trophies():
    """Debug endpoint to check trophy directory contents"""
    from flask import jsonify
    import os

    normal_trophy_dir = os.path.join('static', 'uploads', 'trophies', 'normal')
    hard_trophy_dir = os.path.join('static', 'uploads', 'trophies', 'hard')

    # Get courses and trophy matching info
    courses = Course.get_all()

    def course_to_trophy_name(course_name):
        return course_name.replace("'", "").replace(",", "").replace(" ", "_")

    course_matches = []
    for course in courses[:10]:  # First 10 courses
        is_hard = '(HARD)' in course['name']
        base_name = course['name'].replace(' (HARD)', '')
        trophy_filename = course_to_trophy_name(base_name) + '.png'
        course_matches.append({
            'course_name': course['name'],
            'base_name': base_name,
            'trophy_filename': trophy_filename,
            'is_hard': is_hard
        })

    result = {
        'cwd': os.getcwd(),
        'total_courses': len(courses),
        'first_10_course_matches': course_matches,
        'normal_dir': {
            'path': normal_trophy_dir,
            'absolute_path': os.path.abspath(normal_trophy_dir),
            'exists': os.path.exists(normal_trophy_dir),
            'files': sorted(list(os.listdir(normal_trophy_dir))) if os.path.exists(normal_trophy_dir) else []
        },
        'hard_dir': {
            'path': hard_trophy_dir,
            'absolute_path': os.path.abspath(hard_trophy_dir),
            'exists': os.path.exists(hard_trophy_dir),
            'files': sorted(list(os.listdir(hard_trophy_dir))) if os.path.exists(hard_trophy_dir) else []
        },
        'static_dir_exists': os.path.exists('static'),
        'static_uploads_exists': os.path.exists('static/uploads'),
        'static_uploads_trophies_exists': os.path.exists('static/uploads/trophies')
    }

    return jsonify(result), 200


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

    # Debug logging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Trophy directories - Normal exists: {os.path.exists(normal_trophy_dir)}, Hard exists: {os.path.exists(hard_trophy_dir)}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Normal trophy dir absolute: {os.path.abspath(normal_trophy_dir)}")

    normal_trophy_files = set(os.listdir(normal_trophy_dir)) if os.path.exists(normal_trophy_dir) else set()
    hard_trophy_files = set(os.listdir(hard_trophy_dir)) if os.path.exists(hard_trophy_dir) else set()

    logger.info(f"Found {len(normal_trophy_files)} normal trophies, {len(hard_trophy_files)} hard trophies")

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
