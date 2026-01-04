from flask import Blueprint, render_template
from models.player import Player
from models.course import Course
from models.round import Round
from services.achievement_service import AchievementService
import os

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """Dashboard/home page"""
    from datetime import datetime, timedelta

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

    return render_template('index.html',
                           total_players=len(players),
                           total_courses=len(courses),
                           total_rounds=len(rounds),
                           recent_rounds=recent_rounds,  # Last 15 days for activity trends
                           last_10_rounds=last_10_rounds,  # Last 10 non-solo rounds for table
                           top_players=top_players)


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
