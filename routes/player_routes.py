from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.player import Player
from models.round import Round

bp = Blueprint('players', __name__)


@bp.route('/')
def list_players():
    """List all players"""
    players = Player.get_all(active_only=False)
    return render_template('players/list.html', players=players)


@bp.route('/add', methods=['GET', 'POST'])
def add_player():
    """Add new player"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()

        success, message, player = Player.create(name, email if email else None)

        if success:
            flash(message, 'success')
            return redirect(url_for('players.list_players'))
        else:
            flash(message, 'error')
            return render_template('players/add.html', name=name, email=email)

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

    return render_template('players/detail.html', player=player, rounds=rounds, stats=stats)


@bp.route('/<player_id>/edit', methods=['POST'])
def edit_player(player_id):
    """Edit player"""
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()

    success, message = Player.update(player_id, name=name, email=email if email else None)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('players.player_detail', player_id=player_id))


@bp.route('/<player_id>/delete', methods=['POST'])
def delete_player(player_id):
    """Delete player"""
    success, message = Player.delete(player_id)

    if success:
        flash(message, 'success')
        return redirect(url_for('players.list_players'))
    else:
        flash(message, 'error')
        return redirect(url_for('players.player_detail', player_id=player_id))
