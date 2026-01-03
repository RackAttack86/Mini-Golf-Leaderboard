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
    # Get summary statistics
    players = Player.get_all()
    courses = Course.get_all()
    rounds = Round.get_all()

    # Get recent rounds (last 10) and add winner player data
    recent_rounds = rounds[:10] if len(rounds) > 10 else rounds

    # Add winner player data and course image to each round
    for round_data in recent_rounds:
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
                           recent_rounds=recent_rounds,
                           top_players=top_players)


@bp.route('/trophies')
def trophies():
    """Display all course trophies"""
    # Get all courses
    courses = Course.get_all()

    # Remove duplicates (HARD versions) and sort
    unique_courses = {}
    for course in courses:
        base_name = course['name'].replace(' (HARD)', '')
        if base_name not in unique_courses:
            unique_courses[base_name] = course

    # Convert course names to Linux-friendly trophy filenames
    def course_to_trophy_name(course_name):
        return course_name.replace("'", "").replace(",", "").replace(" ", "_")

    # Check which courses have trophy images
    trophy_dir = os.path.join('static', 'uploads', 'trophies')
    trophy_files = set(os.listdir(trophy_dir)) if os.path.exists(trophy_dir) else set()

    # Build list of courses with trophy info
    course_trophies = []
    for base_name, course in sorted(unique_courses.items()):
        trophy_filename = course_to_trophy_name(base_name) + '.png'
        has_trophy = trophy_filename in trophy_files

        course_trophies.append({
            'course_id': course['id'],
            'course_name': base_name,
            'trophy_filename': trophy_filename,
            'has_trophy': has_trophy
        })

    # Sort by course name
    course_trophies.sort(key=lambda x: x['course_name'])

    return render_template('trophies.html', course_trophies=course_trophies)
