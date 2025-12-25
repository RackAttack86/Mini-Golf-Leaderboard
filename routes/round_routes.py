from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.round import Round
from models.player import Player
from models.course import Course
from utils.auth_decorators import login_required, admin_required

bp = Blueprint('rounds', __name__)


@bp.route('/')
def list_rounds():
    """List all rounds with filtering"""
    # Get filter parameters
    player_id = request.args.get('player_id')
    course_id = request.args.get('course_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Build filters
    filters = {}
    if player_id:
        filters['player_id'] = player_id
    if course_id:
        filters['course_id'] = course_id
    if start_date:
        filters['start_date'] = start_date
    if end_date:
        filters['end_date'] = end_date

    rounds = Round.get_all(filters if filters else None)

    # Add winner player data, course image, and achievement scores to each round
    for round_data in rounds:
        if round_data['scores']:
            winner_score = min(round_data['scores'], key=lambda x: x['score'])
            winner_player = Player.get_by_id(winner_score['player_id'])
            if winner_player:
                winner_player['achievement_score'] = AchievementService.get_achievement_score(winner_player['id'])
            round_data['winner_player'] = winner_player

        # Add course image data
        course = Course.get_by_id(round_data['course_id'])
        round_data['course_image_url'] = course.get('image_url', '') if course else ''

    # Get all players and courses for filter dropdowns
    players = Player.get_all()
    courses = Course.get_all()

    return render_template('rounds/list.html',
                           rounds=rounds,
                           players=players,
                           courses=courses,
                           filters={'player_id': player_id,
                                    'course_id': course_id,
                                    'start_date': start_date,
                                    'end_date': end_date})


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_round():
    """Add new round"""
    # Get active players and courses
    players = Player.get_all()
    courses = Course.get_all()

    if request.method == 'POST':
        course_id = request.form.get('course_id')
        date_played = request.form.get('date_played')
        notes = request.form.get('notes', '').strip()

        # Get player scores
        player_ids = request.form.getlist('player_id[]')
        player_scores = request.form.getlist('score[]')

        # Build scores list
        scores = []
        for i in range(len(player_ids)):
            if player_ids[i] and player_scores[i]:
                scores.append({
                    'player_id': player_ids[i],
                    'score': player_scores[i]
                })

        success, message, round_data = Round.create(
            course_id,
            date_played,
            scores,
            notes if notes else None
        )

        if success:
            flash(message, 'success')
            return redirect(url_for('rounds.round_detail', round_id=round_data['id']))
        else:
            flash(message, 'error')
            return render_template('rounds/add.html',
                                   players=players,
                                   courses=courses,
                                   form_data={
                                       'course_id': course_id,
                                       'date_played': date_played,
                                       'notes': notes,
                                       'scores': scores
                                   })

    return render_template('rounds/add.html', players=players, courses=courses)


@bp.route('/<round_id>')
def round_detail(round_id):
    """Round detail page"""
    round_data = Round.get_by_id(round_id)

    if not round_data:
        flash('Round not found', 'error')
        return redirect(url_for('rounds.list_rounds'))

    # Sort scores by score (lowest first - winner first)
    round_data['scores'] = sorted(round_data['scores'], key=lambda x: x['score'])

    # Add player data to each score
    for score in round_data['scores']:
        player = Player.get_by_id(score['player_id'])
        score['player_data'] = player

    # Get all courses for edit modal
    courses = Course.get_all()

    return render_template('rounds/detail.html', round=round_data, courses=courses)


@bp.route('/<round_id>/edit', methods=['POST'])
@admin_required
def edit_round(round_id):
    """Edit round"""
    course_id = request.form.get('course_id')
    date_played = request.form.get('date_played')
    notes = request.form.get('notes', '').strip()

    # Get player scores
    player_ids = request.form.getlist('player_ids[]')
    player_scores = request.form.getlist('scores[]')

    # Build scores list
    scores = []
    for i in range(len(player_ids)):
        if player_ids[i] and player_scores[i]:
            scores.append({
                'player_id': player_ids[i],
                'score': player_scores[i]
            })

    success, message = Round.update(
        round_id,
        course_id,
        date_played,
        scores,
        notes if notes else None
    )

    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('rounds.round_detail', round_id=round_id))


@bp.route('/<round_id>/delete', methods=['POST'])
@admin_required
def delete_round(round_id):
    """Delete round"""
    success, message = Round.delete(round_id)

    if success:
        flash(message, 'success')
        return redirect(url_for('rounds.list_rounds'))
    else:
        flash(message, 'error')
        return redirect(url_for('rounds.round_detail', round_id=round_id))
