from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename
from models.round import Round
from models.player import Player
from models.course import Course
from models.course_trophy import CourseTrophy
from models.database import get_db
from utils.auth_decorators import login_required, admin_required
from utils.ocr_service import WalkaboutOCRService
from utils.file_validators import validate_image_file
from config import Config
from pathlib import Path
import uuid
import os
import sqlite3

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

    # Add winner player data and course image to each round
    for round_data in rounds:
        if round_data['scores']:
            winner_score = min(round_data['scores'], key=lambda x: x['score'])
            winner_player = Player.get_by_id(winner_score['player_id'])
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

    # Get trophy ownership data for JavaScript
    course_trophy_owners = CourseTrophy.get_all_trophy_owners_dict()

    if request.method == 'POST':
        course_id = request.form.get('course_id')
        date_played = request.form.get('date_played')
        notes = request.form.get('notes', '').strip()

        # Get player scores
        player_ids = request.form.getlist('player_id[]')
        player_scores = request.form.getlist('score[]')

        # Check if hole-by-hole scores were provided
        hole_1_scores = request.form.getlist('hole_1_[]')
        has_hole_scores = bool(hole_1_scores and any(hole_1_scores))

        # Build scores list
        scores = []
        for i in range(len(player_ids)):
            if player_ids[i] and player_scores[i]:
                score_data = {
                    'player_id': player_ids[i],
                    'score': player_scores[i]
                }

                # If hole scores were provided, collect them for this player
                if has_hole_scores:
                    hole_scores = []
                    for hole_num in range(1, 19):
                        hole_field = f'hole_{hole_num}_[]'
                        hole_values = request.form.getlist(hole_field)
                        if i < len(hole_values) and hole_values[i]:
                            try:
                                hole_scores.append(int(hole_values[i]))
                            except ValueError:
                                flash(f'Invalid score for hole {hole_num}', 'error')
                                return render_template('rounds/add.html',
                                                       players=players,
                                                       courses=courses,
                                                       course_trophy_owners=course_trophy_owners,
                                                       form_data={
                                                           'course_id': course_id,
                                                           'date_played': date_played,
                                                           'notes': notes,
                                                           'scores': scores
                                                       })

                    # Only add hole_scores if we got all 18
                    if len(hole_scores) == 18:
                        score_data['hole_scores'] = hole_scores

                scores.append(score_data)

        success, message, round_data = Round.create(
            course_id,
            date_played,
            scores,
            notes if notes else None
        )

        if success:
            # Handle trophy award/transfer if applicable
            trophy_up_for_grabs = request.form.get('trophy_up_for_grabs') == 'on'

            # Check if course has a trophy owner
            current_trophy_owner = CourseTrophy.get_trophy_owner(course_id)

            # Award trophy if:
            # 1. Trophy was marked "up for grabs" (contested), OR
            # 2. Course has no trophy owner yet (first trophy)
            # AND round has 4+ players
            should_award_trophy = (trophy_up_for_grabs or not current_trophy_owner) and len(player_ids) >= 4

            if should_award_trophy:
                # Build scores list for winner determination
                score_list = [{'player_id': pid, 'score': int(score)}
                              for pid, score in zip(player_ids, player_scores)]

                winner_id = CourseTrophy.determine_round_winner(score_list)

                if winner_id:
                    CourseTrophy.transfer_trophy(
                        course_id, winner_id, round_data['id'], date_played
                    )

                    # Different message for first trophy vs transfer
                    if not current_trophy_owner:
                        flash('Trophy awarded for first time!', 'success')
                    else:
                        flash('Trophy transferred!', 'success')
                else:
                    # Tie scenario
                    if current_trophy_owner:
                        flash('Round ended in tie - trophy stays with current owner', 'info')
                    else:
                        flash('Round ended in tie - no trophy awarded', 'info')

                # Mark round as trophy contest
                conn = get_db().get_connection()
                conn.execute(
                    "UPDATE rounds SET trophy_up_for_grabs = 1 WHERE id = ?",
                    (round_data['id'],)
                )

            flash(message, 'success')
            return redirect(url_for('rounds.round_detail', round_id=round_data['id']))
        else:
            flash(message, 'error')
            return render_template('rounds/add.html',
                                   players=players,
                                   courses=courses,
                                   course_trophy_owners=course_trophy_owners,
                                   form_data={
                                       'course_id': course_id,
                                       'date_played': date_played,
                                       'notes': notes,
                                       'scores': scores
                                   })

    return render_template('rounds/add.html', players=players, courses=courses, course_trophy_owners=course_trophy_owners)


@bp.route('/upload-picture', methods=['GET', 'POST'])
@login_required
def upload_picture():
    """Upload round picture with OCR extraction"""

    if request.method == 'GET':
        return render_template('rounds/upload_picture.html')

    # POST: Handle file upload
    if 'scorecard_image' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(request.url)

    file = request.files['scorecard_image']

    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(request.url)

    # Validate file
    is_valid, error_message = validate_image_file(file)
    if not is_valid:
        flash(error_message, 'error')
        return redirect(request.url)

    # Save file temporarily
    temp_dir = Path(Config.BASE_DIR) / 'data' / 'temp'
    temp_dir.mkdir(parents=True, exist_ok=True)

    temp_filename = f"temp_{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    temp_path = temp_dir / temp_filename
    file.save(str(temp_path))

    try:
        # Run OCR extraction
        try:
            ocr_result = WalkaboutOCRService.extract_scorecard_data(str(temp_path))
        except Exception as ocr_error:
            # OCR failed (probably Tesseract not installed) - provide manual entry
            flash(
                f"OCR extraction unavailable (Tesseract not installed). Please enter data manually.",
                'warning'
            )
            ocr_result = {
                'success': False,
                'confidence': 0.0,
                'data': {
                    'course_name': None,
                    'player_username': None,
                    'start_time': None,
                    'hole_scores': None,
                    'total_score': None
                },
                'errors': [f'OCR extraction failed: {str(ocr_error)}'],
                'raw_text': ''
            }

        if not ocr_result['success'] or ocr_result['confidence'] < Config.OCR_CONFIDENCE_THRESHOLD:
            # Low confidence or errors - show manual entry with suggestions
            if ocr_result['confidence'] > 0:
                flash(
                    f"OCR confidence low ({ocr_result['confidence']:.0%}). Please review and correct the data.",
                    'warning'
                )

        # Get all courses for fuzzy matching
        courses = Course.get_all()

        # Try to match course
        matched_course_id = None
        course_suggestions = []
        suggested_course_ids = set()
        match_score = 0

        if ocr_result['data'].get('course_name'):
            matched_course_id, match_score, suggestions = WalkaboutOCRService.find_matching_course(
                ocr_result['data']['course_name'],
                courses
            )
            course_suggestions = suggestions
            # Create set of suggested course IDs for template filtering
            suggested_course_ids = {s[0]['id'] for s in suggestions[:5]}

        # Try to match player by Meta Quest username
        matched_player = None
        if ocr_result['data'].get('player_username'):
            matched_player = Player.get_by_meta_quest_username(ocr_result['data']['player_username'])

        # Get all players for manual selection
        players = Player.get_all()

        # Store temporary file path in session for later use
        session['temp_scorecard_path'] = str(temp_path)

        # Render review screen
        return render_template('rounds/review_ocr_data.html',
                               ocr_result=ocr_result,
                               matched_course_id=matched_course_id,
                               course_match_score=match_score,
                               course_suggestions=course_suggestions,
                               suggested_course_ids=suggested_course_ids,
                               matched_player=matched_player,
                               courses=courses,
                               players=players,
                               temp_image_path=temp_filename)

    except Exception as e:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()

        flash(f'Error processing image: {str(e)}', 'error')
        return redirect(url_for('rounds.upload_picture'))


@bp.route('/upload-picture/temp/<filename>')
@login_required
def serve_temp_image(filename):
    """Serve temporary uploaded image for preview"""
    temp_dir = Path(Config.BASE_DIR) / 'data' / 'temp'
    return send_from_directory(temp_dir, filename)


@bp.route('/upload-picture/create', methods=['POST'])
@login_required
def create_from_upload():
    """Create round from reviewed OCR data"""

    # Get form data
    course_id = request.form.get('course_id')
    player_id = request.form.get('player_id')
    start_time = request.form.get('start_time')
    notes = request.form.get('notes', '').strip()

    # Get 18 hole scores
    hole_scores = []
    for i in range(1, 19):
        score = request.form.get(f'hole_{i}')
        if score:
            try:
                hole_scores.append(int(score))
            except ValueError:
                flash(f'Invalid score for hole {i}', 'error')
                return redirect(url_for('rounds.upload_picture'))

    if len(hole_scores) != 18:
        flash('All 18 hole scores are required', 'error')
        return redirect(url_for('rounds.upload_picture'))

    # Calculate total score
    total_score = sum(hole_scores)

    # Validate required fields
    if not all([course_id, player_id, start_time]):
        flash('Course, player, and start time are required', 'error')
        return redirect(url_for('rounds.upload_picture'))

    # Get the date from start_time
    try:
        from datetime import datetime
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        date_played = start_dt.strftime('%Y-%m-%d')
    except Exception:
        flash('Invalid start time format', 'error')
        return redirect(url_for('rounds.upload_picture'))

    # Check for duplicate round (same course + start time)
    try:
        # Create round with hole scores
        success, message, round_data = Round.create(
            course_id=course_id,
            date_played=date_played,
            scores=[{
                'player_id': player_id,
                'score': total_score,
                'hole_scores': hole_scores
            }],
            notes=notes if notes else None,
            round_start_time=start_time,
            picture_filename=None  # Will be set after moving file
        )

        if not success:
            # Check if it's a duplicate round error
            if 'already exists' in message.lower() or 'duplicate' in message.lower():
                flash('A round for this course and time already exists', 'error')
            else:
                flash(message, 'error')

            # Clean up temp file
            temp_path = session.get('temp_scorecard_path')
            if temp_path and Path(temp_path).exists():
                Path(temp_path).unlink()
            session.pop('temp_scorecard_path', None)

            return redirect(url_for('rounds.upload_picture'))

        # Move temp file to permanent location
        temp_path = session.get('temp_scorecard_path')
        if temp_path and Path(temp_path).exists():
            # Create round_pictures directory if needed
            pictures_dir = Path(Config.ROUND_PICTURES_DIR)
            pictures_dir.mkdir(parents=True, exist_ok=True)

            # Generate permanent filename
            file_ext = Path(temp_path).suffix
            permanent_filename = f"{round_data['id']}{file_ext}"
            permanent_path = pictures_dir / permanent_filename

            # Move file
            Path(temp_path).rename(permanent_path)

            # Update round with picture filename
            db = get_db()
            conn = db.get_connection()
            conn.execute(
                "UPDATE rounds SET picture_filename = ? WHERE id = ?",
                (permanent_filename, round_data['id'])
            )

        # Clean up session
        session.pop('temp_scorecard_path', None)

        flash(f'{message} Round created with hole-by-hole scores from uploaded scorecard!', 'success')
        return redirect(url_for('rounds.round_detail', round_id=round_data['id']))

    except sqlite3.IntegrityError as e:
        # Duplicate round constraint violated
        flash('A round for this course and time already exists', 'error')

        # Clean up temp file
        temp_path = session.get('temp_scorecard_path')
        if temp_path and Path(temp_path).exists():
            Path(temp_path).unlink()
        session.pop('temp_scorecard_path', None)

        return redirect(url_for('rounds.upload_picture'))

    except Exception as e:
        # Clean up temp file
        temp_path = session.get('temp_scorecard_path')
        if temp_path and Path(temp_path).exists():
            Path(temp_path).unlink()
        session.pop('temp_scorecard_path', None)

        flash(f'Error creating round: {str(e)}', 'error')
        return redirect(url_for('rounds.upload_picture'))


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

    # Get all courses and players for edit modal
    courses = Course.get_all()
    players = Player.get_all()

    # Filter out players already in this round for the "add player" dropdown
    existing_player_ids = {score['player_id'] for score in round_data['scores']}
    available_players = [p for p in players if p['id'] not in existing_player_ids]

    # Get trophy contest information if trophy was up for grabs
    trophy_contest_info = None
    if round_data.get('trophy_up_for_grabs'):
        course_id = round_data['course_id']
        trophy_owner = CourseTrophy.get_trophy_owner(course_id)

        # Determine the winner of this round
        if round_data['scores']:
            winner = round_data['scores'][0]  # Already sorted by score
            min_score = winner['score']
            # Check for tie
            tied_winners = [s for s in round_data['scores'] if s['score'] == min_score]
            is_tie = len(tied_winners) > 1

            # Determine if trophy was defended (winner was already owner) or changed hands
            was_defended = False
            if trophy_owner and not is_tie:
                was_defended = winner['player_id'] == trophy_owner['player_id']

            trophy_contest_info = {
                'winner': winner,
                'is_tie': is_tie,
                'tied_players': tied_winners if is_tie else None,
                'current_owner': trophy_owner,
                'was_defended': was_defended
            }

    # Determine trophy image to display
    trophy_image = None
    if round_data.get('trophy_up_for_grabs'):
        # Course trophy was awarded - show the course trophy
        course_name = round_data['course_name']
        difficulty, trophy_filename = CourseTrophy.generate_trophy_filename(course_name)
        trophy_image = f'uploads/trophies/{difficulty}/{trophy_filename}'
    else:
        # Regular round - show gold trophy
        trophy_image = 'images/trophies/GoldTrophy.png'

    return render_template('rounds/detail.html', round=round_data, courses=courses,
                         players=players, available_players=available_players,
                         trophy_contest_info=trophy_contest_info, trophy_image=trophy_image)


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
