from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.course import Course
from models.round import Round

bp = Blueprint('courses', __name__)


@bp.route('/')
def list_courses():
    """List all courses"""
    courses = Course.get_all(active_only=False)
    return render_template('courses/list.html', courses=courses)


@bp.route('/add', methods=['GET', 'POST'])
def add_course():
    """Add new course"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        location = request.form.get('location', '').strip()
        holes = request.form.get('holes', '').strip()
        par = request.form.get('par', '').strip()

        # Convert empty strings to None
        holes_int = int(holes) if holes else None
        par_int = int(par) if par else None

        success, message, course = Course.create(
            name,
            location if location else None,
            holes_int,
            par_int
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
                                   par=par)

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

    return render_template('courses/detail.html', course=course, rounds=rounds, stats=stats)


@bp.route('/<course_id>/edit', methods=['POST'])
def edit_course(course_id):
    """Edit course"""
    name = request.form.get('name', '').strip()
    location = request.form.get('location', '').strip()
    holes = request.form.get('holes', '').strip()
    par = request.form.get('par', '').strip()

    # Convert empty strings to None
    holes_int = int(holes) if holes else None
    par_int = int(par) if par else None

    success, message = Course.update(
        course_id,
        name=name,
        location=location if location else None,
        holes=holes_int,
        par=par_int
    )

    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('courses.course_detail', course_id=course_id))


@bp.route('/<course_id>/delete', methods=['POST'])
def delete_course(course_id):
    """Delete course"""
    success, message = Course.delete(course_id)

    if success:
        flash(message, 'success')
        return redirect(url_for('courses.list_courses'))
    else:
        flash(message, 'error')
        return redirect(url_for('courses.course_detail', course_id=course_id))
