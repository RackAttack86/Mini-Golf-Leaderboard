from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, jsonify
from flask_login import current_user
from models.course import Course
from models.round import Round
from models.course_rating import CourseRating
from models.course_notes import CourseNotes
from models.course_trophy import CourseTrophy
from models.friendship import Friendship
from utils.auth_decorators import admin_required
from utils.file_validators import validate_image_file, sanitize_filename
import os
import uuid

bp = Blueprint('courses', __name__)

def save_course_image(file, upload_folder, max_size):
    """
    Save uploaded course image with secure validation

    Args:
        file: Uploaded file from request.files
        upload_folder: Directory to save the file
        max_size: Maximum file size in bytes

    Returns:
        Tuple of (success, filename_or_error_message)
    """
    if not file or not file.filename:
        return False, "No file provided"

    # Validate file using secure validator
    is_valid, error = validate_image_file(file, max_size)
    if not is_valid:
        return False, error

    # Generate unique filename
    safe_name = sanitize_filename(file.filename)
    ext = safe_name.rsplit('.', 1)[1].lower() if '.' in safe_name else 'jpg'
    filename = f"{uuid.uuid4().hex}.{ext}"

    # Ensure upload directory exists
    filepath = os.path.join(upload_folder, filename)
    os.makedirs(upload_folder, exist_ok=True)

    # Save file
    file.save(filepath)
    return True, filename

def delete_course_image(filename, upload_folder):
    """Delete a course image file"""
    if filename:
        filepath = os.path.join(upload_folder, filename)
        try:
            os.remove(filepath)
        except FileNotFoundError:
            # File already deleted, not an error
            pass
        except Exception as e:
            print(f"Error deleting course image: {e}")


@bp.route('/')
def list_courses():
    """List all courses"""
    courses = Course.get_all(active_only=False)

    # Get all course ratings
    all_ratings = CourseRating.get_all()

    # Get all trophy owners
    all_trophy_owners = {}
    from models.database import get_db
    db = get_db()
    conn = db.get_connection()
    cursor = conn.execute("""
        SELECT ct.course_id, p.id as player_id, p.name as player_name
        FROM course_trophies ct
        JOIN players p ON ct.player_id = p.id
    """)
    for row in cursor.fetchall():
        all_trophy_owners[row['course_id']] = {
            'player_id': row['player_id'],
            'player_name': row['player_name']
        }

    # Get best and worst scores for each course
    best_scores = {}
    worst_scores = {}
    cursor = conn.execute("""
        SELECT r.course_id, rs.score, p.id as player_id, p.name as player_name
        FROM round_scores rs
        JOIN rounds r ON rs.round_id = r.id
        JOIN players p ON rs.player_id = p.id
        ORDER BY rs.score ASC
    """)
    for row in cursor.fetchall():
        course_id = row['course_id']
        score_data = {
            'score': row['score'],
            'player_id': row['player_id'],
            'player_name': row['player_name']
        }
        # First occurrence is best (lowest), track worst (highest) as we go
        if course_id not in best_scores:
            best_scores[course_id] = score_data
        worst_scores[course_id] = score_data  # Last one will be highest

    # Add rating info and trophy owner to each course
    for course in courses:
        course_id = course['id']
        if course_id in all_ratings:
            avg_rating, count = all_ratings[course_id]
            course['avg_rating'] = avg_rating
            course['rating_count'] = count
        else:
            course['avg_rating'] = None
            course['rating_count'] = 0

        # Add trophy owner info
        if course_id in all_trophy_owners:
            course['trophy_owner'] = all_trophy_owners[course_id]
        else:
            course['trophy_owner'] = None

        # Add best/worst scores
        course['best_score'] = best_scores.get(course_id)
        course['worst_score'] = worst_scores.get(course_id)

    return render_template('courses/list.html', courses=courses)


@bp.route('/add', methods=['GET', 'POST'])
@admin_required
def add_course():
    """Add new course"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        location = request.form.get('location', '').strip()
        holes = request.form.get('holes', '').strip()
        par = request.form.get('par', '').strip()
        image_url = request.form.get('image_url', '').strip()

        # Handle image upload
        uploaded_file = request.files.get('course_image')
        if uploaded_file and uploaded_file.filename:
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'courses')
            success, result = save_course_image(uploaded_file, upload_folder, current_app.config['MAX_CONTENT_LENGTH'])
            if success:
                image_url = result
            else:
                flash(result, 'error')
                return render_template('courses/add.html',
                                       name=name,
                                       location=location,
                                       holes=holes,
                                       par=par,
                                       image_url=image_url)

        # Convert empty strings to None
        holes_int = int(holes) if holes else None
        par_int = int(par) if par else None

        success, message, course = Course.create(
            name,
            location if location else None,
            holes_int,
            par_int,
            image_url if image_url else None
        )

        if success:
            flash(message, 'success')
            return redirect(url_for('courses.list_courses'))
        else:
            flash(message, 'error')
            return render_template('courses/add.html',
                                   name=name,
                                   location=location,
                                   holes=holes,
                                   par=par,
                                   image_url=image_url)

    return render_template('courses/add.html')


@bp.route('/<course_id>')
def course_detail(course_id):
    """Course detail page with statistics"""
    course = Course.get_by_id(course_id)

    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('courses.list_courses'))

    # Get course rounds
    rounds = Round.get_by_course(course_id)

    # Apply friends filter if logged in and view mode is 'friends'
    view_mode = 'everyone'
    if current_user.is_authenticated:
        view_mode = session.get('view_mode', 'everyone')
        if view_mode == 'friends':
            friend_ids = Friendship.get_friends_and_self(current_user.id)
            # Filter rounds to only those involving friends
            rounds = [r for r in rounds if any(
                score['player_id'] in friend_ids for score in r.get('scores', [])
            )]

    # Calculate statistics
    stats = {
        'total_rounds': len(rounds),
        'total_scores': 0,
        'average_score': 0,
        'best_score': None,
        'best_score_player': None,
        'worst_score': None,
        'worst_score_player': None
    }

    if rounds:
        all_scores = []
        score_to_player = {}  # Map score to player name

        for round_data in rounds:
            for score_data in round_data['scores']:
                score = score_data['score']
                player_name = score_data['player_name']
                all_scores.append(score)

                # Track player for this score
                if score not in score_to_player:
                    score_to_player[score] = player_name

        if all_scores:
            stats['total_scores'] = len(all_scores)
            stats['average_score'] = round(sum(all_scores) / len(all_scores), 2)
            stats['best_score'] = min(all_scores)
            stats['worst_score'] = max(all_scores)
            stats['best_score_player'] = score_to_player[stats['best_score']]
            stats['worst_score_player'] = score_to_player[stats['worst_score']]

    # Get course rating info
    avg_rating, rating_count = CourseRating.get_course_average_rating(course_id)
    user_rating = None
    user_notes = None
    if current_user.is_authenticated:
        user_rating = CourseRating.get_player_rating(current_user.id, course_id)
        user_notes_data = CourseNotes.get_player_notes(current_user.id, course_id)
        user_notes = user_notes_data['notes'] if user_notes_data else ''

    # Get user's rounds on this course with pagination
    user_rounds = []
    user_rounds_page = 1
    user_rounds_total_pages = 0
    user_rounds_total = 0
    if current_user.is_authenticated:
        # Filter rounds where current user played
        user_rounds_all = [r for r in rounds if any(s['player_id'] == current_user.id for s in r['scores'])]
        user_rounds_total = len(user_rounds_all)

        # Pagination
        page = request.args.get('user_page', 1, type=int)
        per_page = current_app.config['ROUNDS_PER_PAGE']
        user_rounds_total_pages = (user_rounds_total + per_page - 1) // per_page

        # Ensure page is within valid range
        user_rounds_page = max(1, min(page, user_rounds_total_pages)) if user_rounds_total_pages > 0 else 1

        # Get paginated rounds
        start_idx = (user_rounds_page - 1) * per_page
        end_idx = start_idx + per_page
        user_rounds = user_rounds_all[start_idx:end_idx]

    # Get trophy owner for this course
    trophy_owner = CourseTrophy.get_trophy_owner(course_id)

    # Always determine trophy image path (shown even without owner)
    course_name = course['name']
    difficulty, trophy_filename = CourseTrophy.generate_trophy_filename(course_name)
    trophy_image = f'uploads/trophies/{difficulty}/{trophy_filename}'

    return render_template('courses/detail.html',
                         course=course,
                         rounds=rounds,
                         stats=stats,
                         avg_rating=avg_rating,
                         rating_count=rating_count,
                         user_rating=user_rating,
                         user_notes=user_notes,
                         user_rounds=user_rounds,
                         user_rounds_page=user_rounds_page,
                         user_rounds_total_pages=user_rounds_total_pages,
                         user_rounds_total=user_rounds_total,
                         trophy_owner=trophy_owner,
                         trophy_image=trophy_image)


@bp.route('/<course_id>/edit', methods=['POST'])
@admin_required
def edit_course(course_id):
    """Edit course"""
    name = request.form.get('name', '').strip()
    location = request.form.get('location', '').strip()
    holes = request.form.get('holes', '').strip()
    par = request.form.get('par', '').strip()
    image_url = request.form.get('image_url', '').strip()

    # Handle image upload
    uploaded_file = request.files.get('course_image')
    if uploaded_file and uploaded_file.filename:
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'courses')

        # Validate and save new image
        success, result = save_course_image(uploaded_file, upload_folder, current_app.config['MAX_CONTENT_LENGTH'])
        if success:
            # Delete old image if exists
            course = Course.get_by_id(course_id)
            if course and course.get('image_url') and not course['image_url'].startswith('http'):
                delete_course_image(course['image_url'], upload_folder)

            image_url = result
        else:
            flash(result, 'error')
            return redirect(url_for('courses.course_detail', course_id=course_id))

    # Convert empty strings to None
    holes_int = int(holes) if holes else None
    par_int = int(par) if par else None

    success, message = Course.update(
        course_id,
        name=name,
        location=location if location else None,
        holes=holes_int,
        par=par_int,
        image_url=image_url if image_url else None
    )

    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('courses.course_detail', course_id=course_id))


@bp.route('/<course_id>/delete', methods=['POST'])
@admin_required
def delete_course(course_id):
    """Delete course"""
    success, message = Course.delete(course_id)

    if success:
        flash(message, 'success')
        return redirect(url_for('courses.list_courses'))
    else:
        flash(message, 'error')
        return redirect(url_for('courses.course_detail', course_id=course_id))


@bp.route('/<course_id>/rate', methods=['POST'])
def rate_course(course_id):
    """Rate a course"""
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'message': 'You must be logged in to rate courses'}), 401

    try:
        rating = int(request.form.get('rating', 0))
        success, message = CourseRating.rate_course(current_user.id, course_id, rating)

        if success:
            # Get updated average rating
            avg_rating, rating_count = CourseRating.get_course_average_rating(course_id)
            return jsonify({
                'success': True,
                'message': message,
                'avg_rating': avg_rating,
                'rating_count': rating_count
            })
        else:
            return jsonify({'success': False, 'message': message}), 400
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid rating value'}), 400


@bp.route('/<course_id>/notes', methods=['POST'])
def save_course_notes(course_id):
    """Save player's personal notes for a course"""
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'message': 'You must be logged in to save notes'}), 401

    try:
        notes = request.form.get('notes', '').strip()
        success, message = CourseNotes.save_notes(current_user.id, course_id, notes)

        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@bp.route('/<course_id>/notes', methods=['GET'])
def get_course_notes(course_id):
    """Get player's personal notes for a course (AJAX)"""
    if not current_user.is_authenticated:
        return jsonify({'notes': None}), 401

    notes_data = CourseNotes.get_player_notes(current_user.id, course_id)

    return jsonify({
        'notes': notes_data['notes'] if notes_data else '',
        'date_updated': notes_data['date_updated'] if notes_data else None
    })
