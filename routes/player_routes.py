from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import current_user
import os
import uuid
from models.player import Player
from models.round import Round
from models.course_trophy import CourseTrophy
from services.achievement_service import AchievementService
from utils.auth_decorators import admin_required, player_or_admin_required
from utils.file_validators import validate_image_file, sanitize_filename
from extensions import limiter

bp = Blueprint('players', __name__)


def filter_email_from_players(players, allow_all=False, allowed_player_id=None):
    """
    Filter email addresses from player dictionaries based on authorization.

    Args:
        players: Single player dict or list of player dicts
        allow_all: If True, allow all emails (for admins)
        allowed_player_id: Specific player ID whose email is allowed (for viewing own profile)

    Returns:
        Filtered player dict or list of dicts
    """
    is_list = isinstance(players, list)
    player_list = players if is_list else [players]

    # Check if user is admin
    is_admin = current_user.is_authenticated and current_user.is_admin

    # Filter emails
    for player in player_list:
        # Allow email if: admin, allow_all flag, or viewing own profile
        if not (is_admin or allow_all or (allowed_player_id and player['id'] == allowed_player_id)):
            player['email'] = None

    return player_list if is_list else player_list[0]

def save_profile_picture(file, upload_folder):
    """Save uploaded profile picture with validation"""
    if not file or not file.filename:
        return None

    # Generate unique filename
    safe_name = sanitize_filename(file.filename)
    ext = safe_name.rsplit('.', 1)[1].lower() if '.' in safe_name else 'jpg'
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(upload_folder, filename)

    # Create directory if it doesn't exist
    os.makedirs(upload_folder, exist_ok=True)

    # Save file
    file.save(filepath)
    return filename


@bp.route('/')
def list_players():
    """List all players"""
    players = Player.get_all(active_only=False)

    # Add achievement scores to each player
    for player in players:
        player['achievement_score'] = AchievementService.get_achievement_score(player['id'])

    # Get best and worst scores for each player
    from models.database import get_db
    db = get_db()
    conn = db.get_connection()

    best_scores = {}
    worst_scores = {}
    cursor = conn.execute("""
        SELECT rs.player_id, rs.score, c.id as course_id, c.name as course_name
        FROM round_scores rs
        JOIN rounds r ON rs.round_id = r.id
        JOIN courses c ON r.course_id = c.id
        ORDER BY rs.score ASC
    """)
    for row in cursor.fetchall():
        player_id = row['player_id']
        score_data = {
            'score': row['score'],
            'course_id': row['course_id'],
            'course_name': row['course_name']
        }
        # First occurrence is best (lowest), track worst (highest) as we go
        if player_id not in best_scores:
            best_scores[player_id] = score_data
        worst_scores[player_id] = score_data  # Last one will be highest

    for player in players:
        player_id = player['id']
        player['best_score'] = best_scores.get(player_id)
        player['worst_score'] = worst_scores.get(player_id)

    # Filter emails based on user permissions
    players = filter_email_from_players(players)

    return render_template('players/list.html', players=players)


@bp.route('/add', methods=['GET', 'POST'])
@admin_required
@limiter.limit("20 per hour")
def add_player():
    """Add new player"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        favorite_color = request.form.get('favorite_color', '#2e7d32')

        # Handle profile picture upload
        profile_picture = None
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file.filename:
                # Validate file
                is_valid, error = validate_image_file(file, current_app.config['MAX_CONTENT_LENGTH'])
                if not is_valid:
                    flash(error, 'error')
                    return render_template('players/add.html', name=name, email=email, favorite_color=favorite_color)

                from config import Config
                profile_picture = save_profile_picture(file, str(Config.PROFILE_PICTURES_DIR))

        success, message, player = Player.create(
            name,
            email if email else None,
            profile_picture,
            favorite_color
        )

        if success:
            flash(message, 'success')
            return redirect(url_for('players.list_players'))
        else:
            flash(message, 'error')
            return render_template('players/add.html', name=name, email=email, favorite_color=favorite_color)

    return render_template('players/add.html')


@bp.route('/<player_id>')
def player_detail(player_id):
    """Player detail page with statistics"""
    player = Player.get_by_id(player_id)

    if not player:
        flash('Player not found', 'error')
        return redirect(url_for('players.list_players'))

    # Filter email (allow if admin or viewing own profile)
    player = filter_email_from_players(player, allowed_player_id=player_id)

    # Get player's rounds
    rounds = Round.get_by_player(player_id)

    # Calculate statistics
    stats = {
        'total_rounds': 0,
        'total_score': 0,
        'average_score': 0,
        'best_score': None,
        'worst_score': None,
        'wins': 0,
        'gold_trophies': 0,    # 1st place finishes
        'silver_trophies': 0,  # 2nd place finishes
        'bronze_trophies': 0   # 3rd place finishes
    }

    # Track personal bests per course
    personal_bests = {}  # {course_id: {'score': X, 'date': 'YYYY-MM-DD', 'course_name': 'Name'}}

    if rounds:
        scores = []
        for round_data in rounds:
            score = Round.get_player_score_in_round(round_data, player_id)
            if score:
                scores.append(score)

                # Only count placements for multi-player rounds (2+ players)
                if len(round_data['scores']) >= 2:
                    # Sort scores to determine placement
                    sorted_scores = sorted(round_data['scores'], key=lambda x: x['score'])

                    # Find this player's position
                    position = 0
                    last_score = None
                    for idx, score_entry in enumerate(sorted_scores):
                        # Handle ties - same score = same position
                        if last_score is None or score_entry['score'] != last_score:
                            position = idx + 1
                        last_score = score_entry['score']

                        if score_entry['player_id'] == player_id:
                            # Increment appropriate trophy counter
                            if position == 1:
                                stats['wins'] += 1
                                stats['gold_trophies'] += 1
                            elif position == 2:
                                stats['silver_trophies'] += 1
                            elif position == 3:
                                stats['bronze_trophies'] += 1
                            break

                # Track personal best for this course
                course_id = round_data['course_id']
                if course_id not in personal_bests or score < personal_bests[course_id]['score']:
                    personal_bests[course_id] = {
                        'score': score,
                        'date': round_data['date_played'],
                        'course_name': round_data['course_name'],
                        'round_id': round_data['id']
                    }

        if scores:
            stats['total_rounds'] = len(scores)
            stats['total_score'] = sum(scores)
            stats['average_score'] = round(sum(scores) / len(scores), 2)
            stats['best_score'] = min(scores)
            stats['worst_score'] = max(scores)

    # Convert personal_bests dict to sorted list
    personal_bests_list = sorted(
        personal_bests.values(),
        key=lambda x: x['course_name']
    )

    # Get player achievements
    achievements = AchievementService.get_player_achievements(player_id)

    # Get player trophies (wins by course)
    trophies = Player.get_player_trophies(player_id)

    # Get owned course trophies
    owned_course_trophies = CourseTrophy.get_trophies_owned_by_player(player_id)

    return render_template('players/detail.html', player=player, rounds=rounds, stats=stats,
                         achievements=achievements, personal_bests=personal_bests_list, trophies=trophies,
                         owned_course_trophies=owned_course_trophies)


@bp.route('/<player_id>/edit', methods=['POST'])
@player_or_admin_required
@limiter.limit("30 per hour")
def edit_player(player_id):
    """Edit player"""
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    favorite_color = request.form.get('favorite_color')
    meta_quest_username = request.form.get('meta_quest_username', '').strip()

    # Get current player data
    player = Player.get_by_id(player_id)
    if not player:
        flash('Player not found', 'error')
        return redirect(url_for('players.list_players'))

    # Handle profile picture upload or removal
    profile_picture = player.get('profile_picture')  # Keep current picture by default

    # Check if user wants to remove current picture
    if request.form.get('remove_picture'):
        profile_picture = ''
        # Delete old file
        if player.get('profile_picture'):
            from config import Config
            old_file = os.path.join(str(Config.PROFILE_PICTURES_DIR), player['profile_picture'])
            try:
                os.remove(old_file)
            except OSError:
                # File already deleted or doesn't exist - safe to ignore
                pass

    # Check if new picture is uploaded
    elif 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file.filename:
            # Validate file
            is_valid, error = validate_image_file(file, current_app.config['MAX_CONTENT_LENGTH'])
            if not is_valid:
                flash(error, 'error')
                return redirect(url_for('players.player_detail', player_id=player_id))

            from config import Config
            new_picture = save_profile_picture(file, str(Config.PROFILE_PICTURES_DIR))
            if new_picture:
                # Delete old file if exists
                if player.get('profile_picture'):
                    old_file = os.path.join(str(Config.PROFILE_PICTURES_DIR), player['profile_picture'])
                    try:
                        os.remove(old_file)
                    except OSError:
                        # File already deleted or doesn't exist - safe to ignore
                        pass
                profile_picture = new_picture

    success, message = Player.update(
        player_id,
        name=name,
        email=email if email else None,
        profile_picture=profile_picture,
        favorite_color=favorite_color
    )

    if success:
        # Update Meta Quest username if changed
        quest_success, quest_message = Player.set_meta_quest_username(
            player_id,
            meta_quest_username if meta_quest_username else None
        )
        if not quest_success:
            flash(quest_message, 'warning')
        else:
            flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('players.player_detail', player_id=player_id))


@bp.route('/<player_id>/delete', methods=['POST'])
@admin_required
def delete_player(player_id):
    """Delete player"""
    success, message = Player.delete(player_id)

    if success:
        flash(message, 'success')
        return redirect(url_for('players.list_players'))
    else:
        flash(message, 'error')
        return redirect(url_for('players.player_detail', player_id=player_id))
