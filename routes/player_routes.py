from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
import uuid
from models.player import Player
from models.round import Round
from services.achievement_service import AchievementService
from utils.auth_decorators import admin_required, player_or_admin_required

bp = Blueprint('players', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_profile_picture(file, upload_folder):
    """Save uploaded profile picture and return filename"""
    if file and allowed_file(file.filename):
        # Generate unique filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(upload_folder, filename)

        # Create directory if it doesn't exist
        os.makedirs(upload_folder, exist_ok=True)

        # Save file
        file.save(filepath)
        return filename
    return None


@bp.route('/')
def list_players():
    """List all players"""
    players = Player.get_all(active_only=False)

    # Add achievement scores to each player
    for player in players:
        player['achievement_score'] = AchievementService.get_achievement_score(player['id'])

    return render_template('players/list.html', players=players)


@bp.route('/add', methods=['GET', 'POST'])
@admin_required
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
                upload_folder = os.path.join('static', 'uploads', 'profiles')
                profile_picture = save_profile_picture(file, upload_folder)
                if not profile_picture:
                    flash('Invalid file type. Please upload a JPG, PNG, or GIF image.', 'error')
                    return render_template('players/add.html', name=name, email=email, favorite_color=favorite_color)

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

    # Get player's rounds
    rounds = Round.get_by_player(player_id)

    # Calculate statistics
    stats = {
        'total_rounds': 0,
        'total_score': 0,
        'average_score': 0,
        'best_score': None,
        'worst_score': None,
        'wins': 0
    }

    if rounds:
        scores = []
        for round_data in rounds:
            score = Round.get_player_score_in_round(round_data, player_id)
            if score:
                scores.append(score)

                # Check if this was a win (lowest score in the round)
                min_score = min(s['score'] for s in round_data['scores'])
                if score == min_score:
                    stats['wins'] += 1

        if scores:
            stats['total_rounds'] = len(scores)
            stats['total_score'] = sum(scores)
            stats['average_score'] = round(sum(scores) / len(scores), 2)
            stats['best_score'] = min(scores)
            stats['worst_score'] = max(scores)

    # Get player achievements
    achievements = AchievementService.get_player_achievements(player_id)

    return render_template('players/detail.html', player=player, rounds=rounds, stats=stats, achievements=achievements)


@bp.route('/<player_id>/edit', methods=['POST'])
@player_or_admin_required
def edit_player(player_id):
    """Edit player"""
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    favorite_color = request.form.get('favorite_color')

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
            old_file = os.path.join('static', 'uploads', 'profiles', player['profile_picture'])
            if os.path.exists(old_file):
                os.remove(old_file)

    # Check if new picture is uploaded
    elif 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file.filename:
            upload_folder = os.path.join('static', 'uploads', 'profiles')
            new_picture = save_profile_picture(file, upload_folder)
            if new_picture:
                # Delete old file if exists
                if player.get('profile_picture'):
                    old_file = os.path.join('static', 'uploads', 'profiles', player['profile_picture'])
                    if os.path.exists(old_file):
                        os.remove(old_file)
                profile_picture = new_picture
            else:
                flash('Invalid file type. Please upload a JPG, PNG, or GIF image.', 'error')
                return redirect(url_for('players.player_detail', player_id=player_id))

    success, message = Player.update(
        player_id,
        name=name,
        email=email if email else None,
        profile_picture=profile_picture,
        favorite_color=favorite_color
    )

    if success:
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
