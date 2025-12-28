from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, jsonify
from flask_login import current_user
from models.course import Course
from models.round import Round
from models.course_rating import CourseRating
from utils.auth_decorators import admin_required
import os
import uuid
from werkzeug.utils import secure_filename

bp = Blueprint('courses', __name__)

# Allowed image extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """Check if file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_course_image(file, upload_folder):
    """Save uploaded course image and return filename"""
    if file and allowed_file(file.filename):
        # Generate unique filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"

        # Ensure upload directory exists
        filepath = os.path.join(upload_folder, filename)
        os.makedirs(upload_folder, exist_ok=True)

        # Save file
        file.save(filepath)
        return filename
    return None

def delete_course_image(filename, upload_folder):
    """Delete a course image file"""
    if filename:
        filepath = os.path.join(upload_folder, filename)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                print(f"Error deleting course image: {e}")


@bp.route('/')
def list_courses():
    """List all courses"""
    courses = Course.get_all(active_only=False)

    # Get all course ratings
    all_ratings = CourseRating.get_all_course_ratings()

    # Add rating info to each course
    for course in courses:
        course_id = course['id']
        if course_id in all_ratings:
            avg_rating, count = all_ratings[course_id]
            course['avg_rating'] = avg_rating
            course['rating_count'] = count
        else:
            course['avg_rating'] = None
            course['rating_count'] = 0

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
            saved_filename = save_course_image(uploaded_file, upload_folder)
            if saved_filename:
                image_url = saved_filename

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
    if current_user.is_authenticated:
        user_rating = CourseRating.get_player_rating(current_user.google_id, course_id)

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

    return render_template('courses/detail.html',
                         course=course,
                         rounds=rounds,
                         stats=stats,
                         avg_rating=avg_rating,
                         rating_count=rating_count,
                         user_rating=user_rating,
                         user_rounds=user_rounds,
                         user_rounds_page=user_rounds_page,
                         user_rounds_total_pages=user_rounds_total_pages,
                         user_rounds_total=user_rounds_total)


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

        # Delete old image if exists
        course = Course.get_by_id(course_id)
        if course and course.get('image_url') and not course['image_url'].startswith('http'):
            delete_course_image(course['image_url'], upload_folder)

        # Save new image
        saved_filename = save_course_image(uploaded_file, upload_folder)
        if saved_filename:
            image_url = saved_filename

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
        success, message = CourseRating.rate_course(current_user.google_id, course_id, rating)

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
