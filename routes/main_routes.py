# Standard library
import os
from datetime import datetime, timedelta

# Third-party
from flask import Blueprint, render_template, send_from_directory, session
from flask_login import current_user

# Local
from models.player import Player
from models.course import Course
from models.round import Round
from models.course_trophy import CourseTrophy
from models.friendship import Friendship
from services.achievement_service import AchievementService
from extensions import limiter, csrf
from config import Config

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


@bp.route('/uploads/profiles/<path:filename>')
def serve_profile_picture(filename):
    """Serve profile pictures from data directory"""
    return send_from_directory(Config.PROFILE_PICTURES_DIR, filename)


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



@bp.route('/trophies')
def trophies():
    """Display all course trophies"""
    # Get all courses
    courses = Course.get_all()

    # Convert course names to Linux-friendly trophy filenames
    def course_to_trophy_name(course_name):
        return course_name.replace("'", "").replace(",", "").replace(" ", "_")

    # Trophy background gradients based on course themes
    trophy_backgrounds = {
        "20,000 Leagues Under the Sea": "linear-gradient(135deg, #0c2340 0%, #1a5276 50%, #21618c 100%)",
        "8-bit Lair": "linear-gradient(135deg, #2d1b4e 0%, #6b2d5b 50%, #9b4dca 100%)",
        "Alfheim": "linear-gradient(135deg, #1e3c2f 0%, #2d5a3f 50%, #4a7c59 100%)",
        "Alice's Adventures in Wonderland": "linear-gradient(135deg, #4a1259 0%, #7b2d8e 50%, #d4a5d9 100%)",
        "Arizona Modern": "linear-gradient(135deg, #8b4513 0%, #cd5c5c 50%, #f4a460 100%)",
        "Around the World in 80 Days": "linear-gradient(135deg, #1a365d 0%, #2c5282 50%, #d4af37 100%)",
        "Atlantis": "linear-gradient(135deg, #005577 0%, #008b8b 50%, #40e0d0 100%)",
        "Bogey's Bonanza": "linear-gradient(135deg, #1e4d2b 0%, #2e7d32 50%, #4caf50 100%)",
        "Cherry Blossom": "linear-gradient(135deg, #8b4557 0%, #d87093 50%, #ffb7c5 100%)",
        "Crystal Lair": "linear-gradient(135deg, #1a1a2e 0%, #4a69bd 50%, #a8d8ea 100%)",
        "El Dorado": "linear-gradient(135deg, #8b6914 0%, #d4af37 50%, #ffd700 100%)",
        "Forgotten Fairyland": "linear-gradient(135deg, #2d4a3e 0%, #6b4984 50%, #9370db 100%)",
        "Gardens of Babylon": "linear-gradient(135deg, #2e4a1e 0%, #4a7023 50%, #8fbc8f 100%)",
        "Holiday Hideaway": "linear-gradient(135deg, #8b0000 0%, #228b22 50%, #ff6347 100%)",
        "Ice Lair": "linear-gradient(135deg, #1c3f5f 0%, #5dade2 50%, #e8f4f8 100%)",
        "Journey to the Center of the Earth": "linear-gradient(135deg, #4a2511 0%, #8b4513 50%, #cd5c5c 100%)",
        "Labyrinth": "linear-gradient(135deg, #3d3d3d 0%, #6b6b6b 50%, #d4af37 100%)",
        "Laser Lair": "linear-gradient(135deg, #1a0a2e 0%, #00ff00 50%, #ff00ff 100%)",
        "Mars Garden": "linear-gradient(135deg, #4a1a0a 0%, #8b3a2f 50%, #cd5c5c 100%)",
        "Meow Wolf": "linear-gradient(135deg, #ff006e 0%, #8338ec 50%, #3a86ff 100%)",
        "Mount Olympus": "linear-gradient(135deg, #2c3e50 0%, #f5f5dc 50%, #d4af37 100%)",
        "Myst": "linear-gradient(135deg, #1a2a3a 0%, #34495e 50%, #5d6d7e 100%)",
        "Original Gothic": "linear-gradient(135deg, #1a1a2e 0%, #2d2d44 50%, #4a3f5c 100%)",
        "Quixote Valley": "linear-gradient(135deg, #8b4513 0%, #d2691e 50%, #f4a460 100%)",
        "Raptor Cliff's": "linear-gradient(135deg, #3d2914 0%, #5d4e37 50%, #8fbc8f 100%)",
        "Seagull Stacks": "linear-gradient(135deg, #1e3a5f 0%, #4682b4 50%, #f5deb3 100%)",
        "Shangri-La": "linear-gradient(135deg, #4a0e0e 0%, #8b0000 50%, #d4af37 100%)",
        "Sweetopia": "linear-gradient(135deg, #ff69b4 0%, #da70d6 50%, #ffb6c1 100%)",
        "Temple at Zerzura": "linear-gradient(135deg, #8b7355 0%, #d4a574 50%, #f4e4c1 100%)",
        "Tethys Station": "linear-gradient(135deg, #0a0a1a 0%, #1a1a4a 50%, #4169e1 100%)",
        "Tiki a Coco": "linear-gradient(135deg, #d2691e 0%, #ff8c00 50%, #20b2aa 100%)",
        "Tokyo": "linear-gradient(135deg, #1a1a2e 0%, #ff1493 50%, #ff6b6b 100%)",
        "Tourist Trap": "linear-gradient(135deg, #006400 0%, #228b22 50%, #00ced1 100%)",
        "Upside Town": "linear-gradient(135deg, #4a0080 0%, #8000ff 50%, #00ffff 100%)",
        "Venice": "linear-gradient(135deg, #1e3d59 0%, #4682b4 50%, #d2691e 100%)",
        "Viva Las Elvis": "linear-gradient(135deg, #4a0e0e 0%, #d4af37 50%, #ff4500 100%)",
        "Wallace & Gromit": "linear-gradient(135deg, #3d2b1f 0%, #228b22 50%, #daa520 100%)",
        "Widow's Walkabout": "linear-gradient(135deg, #1a0a1a 0%, #4a0e4a 50%, #800080 100%)",
    }
    default_background = "linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)"

    # Check which courses have trophy images (normal and hard)
    normal_trophy_dir = os.path.join('static', 'uploads', 'trophies', 'normal')
    hard_trophy_dir = os.path.join('static', 'uploads', 'trophies', 'hard')
    normal_trophy_files = set(os.listdir(normal_trophy_dir)) if os.path.exists(normal_trophy_dir) else set()
    hard_trophy_files = set(os.listdir(hard_trophy_dir)) if os.path.exists(hard_trophy_dir) else set()

    # Group trophies by base course name (normal + hard together)
    trophy_groups = {}
    for course in courses:
        is_hard = '(HARD)' in course['name']
        base_name = course['name'].replace(' (HARD)', '')
        trophy_filename = course_to_trophy_name(base_name) + '.png'

        # Initialize group if not exists
        if base_name not in trophy_groups:
            trophy_groups[base_name] = {
                'base_name': base_name,
                'background': trophy_backgrounds.get(base_name, default_background),
                'normal': None,
                'hard': None
            }

        # Check if trophy exists and add to appropriate slot
        if is_hard:
            has_trophy = trophy_filename in hard_trophy_files
            if has_trophy:
                trophy_groups[base_name]['hard'] = {
                    'filename': trophy_filename,
                    'subdir': 'hard'
                }
        else:
            has_trophy = trophy_filename in normal_trophy_files
            if has_trophy:
                trophy_groups[base_name]['normal'] = {
                    'filename': trophy_filename,
                    'subdir': 'normal'
                }

    # Convert to sorted list, only include groups with at least one trophy
    course_trophies = [
        group for group in sorted(trophy_groups.values(), key=lambda x: x['base_name'])
        if group['normal'] or group['hard']
    ]

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

    # Get friend IDs for filtering if needed
    view_mode = 'everyone'
    friend_ids = None
    if current_user.is_authenticated:
        view_mode = session.get('view_mode', 'everyone')
        if view_mode == 'friends':
            friend_ids = Friendship.get_friends_and_self(current_user.id)

    for row in cursor.fetchall():
        player_id = row['player_id']

        # Filter by friends if view mode is 'friends'
        if friend_ids and player_id not in friend_ids:
            continue

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
