from flask import Blueprint, render_template, request, jsonify
from models.player import Player
from models.course import Course
from models.round import Round

bp = Blueprint('stats', __name__)


@bp.route('/leaderboard')
def leaderboard():
    """Player leaderboard"""
    from services.leaderboard_service import LeaderboardService

    sort_by = request.args.get('sort_by', 'average')
    rankings = LeaderboardService.get_player_rankings(sort_by)

    return render_template('stats/leaderboard.html', rankings=rankings, sort_by=sort_by)


@bp.route('/courses')
def course_stats():
    """Course statistics"""
    from services.course_service import CourseService

    course_stats = CourseService.get_course_stats()

    return render_template('stats/course_stats.html', course_stats=course_stats)


@bp.route('/trends')
def trends():
    """Historical trends"""
    from services.trends_service import TrendsService

    player_id = request.args.get('player_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    players = Player.get_all()

    # If player selected, get their trends
    player_trends = None
    selected_player = None
    if player_id:
        selected_player = Player.get_by_id(player_id)
        if selected_player:
            player_trends = TrendsService.get_player_trends(player_id, start_date, end_date)

    # Get overall trends
    overall_trends = TrendsService.get_overall_trends(start_date, end_date)

    return render_template('stats/trends.html',
                           players=players,
                           selected_player=selected_player,
                           player_trends=player_trends,
                           overall_trends=overall_trends,
                           start_date=start_date,
                           end_date=end_date)


@bp.route('/comparison')
def comparison():
    """Head-to-head player comparison"""
    from services.comparison_service import ComparisonService

    player1_id = request.args.get('player1_id')
    player2_id = request.args.get('player2_id')

    players = Player.get_all()

    # If both players selected, get comparison
    comparison_data = None
    player1 = None
    player2 = None

    if player1_id and player2_id:
        player1 = Player.get_by_id(player1_id)
        player2 = Player.get_by_id(player2_id)

        if player1 and player2:
            comparison_data = ComparisonService.compare_players(player1_id, player2_id)

    return render_template('stats/comparison.html',
                           players=players,
                           player1=player1,
                           player2=player2,
                           comparison=comparison_data)


@bp.route('/courses-played')
def courses_played():
    """Courses played by selected player(s)"""
    from services.courses_played_service import CoursesPlayedService

    # Get selected player IDs from query string
    selected_player_ids = request.args.getlist('player_id')

    # Get sort order
    sort_order = request.args.get('sort', 'desc')

    players = Player.get_all()

    # Get courses played data if players selected
    courses_data = None
    selected_players = []

    if selected_player_ids:
        selected_players = [Player.get_by_id(pid) for pid in selected_player_ids if Player.get_by_id(pid)]
        courses_data = CoursesPlayedService.get_courses_played_by_players(selected_player_ids, sort_order)

    return render_template('stats/courses_played.html',
                           players=players,
                           selected_players=selected_players,
                           courses_data=courses_data,
                           selected_player_ids=selected_player_ids,
                           sort_order=sort_order)
