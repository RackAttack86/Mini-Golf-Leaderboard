from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from models.friendship import Friendship
from models.player import Player
from extensions import limiter

bp = Blueprint('friends', __name__)


@bp.route('/')
@login_required
def friends_list():
    """Display friends list and pending requests"""
    # Get friends
    friends = Friendship.get_friends(current_user.id)

    # Get pending requests received
    pending_requests = Friendship.get_pending_requests_received(current_user.id)

    # Get pending requests sent
    sent_requests = Friendship.get_pending_requests_sent(current_user.id)

    return render_template('friends/list.html',
                           friends=friends,
                           pending_requests=pending_requests,
                           sent_requests=sent_requests)


@bp.route('/request/<player_id>', methods=['POST'])
@login_required
@limiter.limit("20 per hour")
def send_request(player_id):
    """Send a friend request"""
    success, message = Friendship.send_request(current_user.id, player_id)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')

    # Redirect back to the player's profile
    return redirect(url_for('players.player_detail', player_id=player_id))


@bp.route('/accept/<int:friendship_id>', methods=['POST'])
@login_required
def accept_request(friendship_id):
    """Accept a pending friend request"""
    success, message = Friendship.accept_request(friendship_id, current_user.id)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('friends.friends_list'))


@bp.route('/reject/<int:friendship_id>', methods=['POST'])
@login_required
def reject_request(friendship_id):
    """Reject a pending friend request"""
    success, message = Friendship.reject_request(friendship_id, current_user.id)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('friends.friends_list'))


@bp.route('/remove/<player_id>', methods=['POST'])
@login_required
def remove_friend(player_id):
    """Remove a friend"""
    success, message = Friendship.remove_friend(current_user.id, player_id)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')

    # Check if we came from a player detail page
    referrer = request.referrer
    if referrer and 'players/' in referrer:
        return redirect(url_for('players.player_detail', player_id=player_id))

    return redirect(url_for('friends.friends_list'))


@bp.route('/toggle-view', methods=['POST'])
@login_required
def toggle_view_mode():
    """Toggle between friends/everyone view mode"""
    data = request.get_json()
    mode = data.get('mode', 'everyone') if data else 'everyone'

    # Validate mode
    if mode not in ('friends', 'everyone'):
        mode = 'everyone'

    # Store in session
    session['view_mode'] = mode

    return jsonify({'success': True, 'mode': mode})
