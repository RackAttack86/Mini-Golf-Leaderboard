"""
Tests for CourseService

Tests course statistics and difficulty ranking functionality.
"""
import pytest
from services.course_service import CourseService
from models.player import Player
from models.course import Course
from models.round import Round


class TestGetCourseStats:
    """Test get_course_stats method"""

    def test_get_stats_for_multiple_courses(self, app):
        """Test getting stats for multiple courses"""
        # Create players
        _, _, player1 = Player.create('Alice', 'alice@test.com')
        _, _, player2 = Player.create('Bob', 'bob@test.com')

        # Create courses
        _, _, course1 = Course.create('Easy Course', 'Location', 18, 54)
        _, _, course2 = Course.create('Hard Course', 'Location', 18, 54)

        # Create rounds - Hard course has higher average
        Round.create(course1['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30},
            {'player_id': player2['id'], 'score': 40}
        ])
        Round.create(course2['id'], '2024-01-02', [
            {'player_id': player1['id'], 'score': 60},
            {'player_id': player2['id'], 'score': 70}
        ])

        stats = CourseService.get_course_stats()

        assert len(stats) == 2
        # Should be sorted by difficulty (higher average first)
        assert stats[0]['course']['name'] == 'Hard Course'
        assert stats[0]['stats']['average_score'] == 65
        assert stats[0]['stats']['difficulty_rank'] == 1
        assert stats[1]['course']['name'] == 'Easy Course'
        assert stats[1]['stats']['average_score'] == 35
        assert stats[1]['stats']['difficulty_rank'] == 2

    def test_excludes_unplayed_courses(self, app):
        """Test that courses with no rounds are excluded"""
        # Create courses
        _, _, course1 = Course.create('Played Course', 'Location', 18, 54)
        _, _, course2 = Course.create('Unplayed Course', 'Location', 18, 54)

        # Create player and round only for course1
        _, _, player = Player.create('Alice', 'alice@test.com')
        Round.create(course1['id'], '2024-01-01', [
            {'player_id': player['id'], 'score': 30}
        ])

        stats = CourseService.get_course_stats()

        # Only played course should be included
        assert len(stats) == 1
        assert stats[0]['course']['name'] == 'Played Course'

    def test_difficulty_ranking_order(self, app):
        """Test courses are ranked by difficulty (higher average = harder)"""
        # Create players
        _, _, player = Player.create('Alice', 'alice@test.com')

        # Create three courses with different difficulties
        _, _, easy = Course.create('Easy', 'Location', 18, 54)
        _, _, medium = Course.create('Medium', 'Location', 18, 54)
        _, _, hard = Course.create('Hard', 'Location', 18, 54)

        # Create rounds with different average scores
        Round.create(easy['id'], '2024-01-01', [
            {'player_id': player['id'], 'score': 20}
        ])
        Round.create(medium['id'], '2024-01-02', [
            {'player_id': player['id'], 'score': 50}
        ])
        Round.create(hard['id'], '2024-01-03', [
            {'player_id': player['id'], 'score': 80}
        ])

        stats = CourseService.get_course_stats()

        # Should be sorted hardest to easiest
        assert stats[0]['course']['name'] == 'Hard'
        assert stats[0]['stats']['difficulty_rank'] == 1
        assert stats[1]['course']['name'] == 'Medium'
        assert stats[1]['stats']['difficulty_rank'] == 2
        assert stats[2]['course']['name'] == 'Easy'
        assert stats[2]['stats']['difficulty_rank'] == 3

    def test_empty_course_list(self, app):
        """Test getting stats when no courses exist"""
        stats = CourseService.get_course_stats()
        assert stats == []

    def test_no_played_courses(self, app):
        """Test when courses exist but none have been played"""
        Course.create('Course 1', 'Location', 18, 54)
        Course.create('Course 2', 'Location', 18, 54)

        stats = CourseService.get_course_stats()
        assert stats == []

    def test_single_course(self, app):
        """Test with only one played course"""
        _, _, player = Player.create('Alice', 'alice@test.com')
        _, _, course = Course.create('Solo Course', 'Location', 18, 54)

        Round.create(course['id'], '2024-01-01', [
            {'player_id': player['id'], 'score': 42}
        ])

        stats = CourseService.get_course_stats()

        assert len(stats) == 1
        assert stats[0]['course']['name'] == 'Solo Course'
        assert stats[0]['stats']['difficulty_rank'] == 1
        assert stats[0]['stats']['average_score'] == 42

    def test_courses_with_same_difficulty(self, app):
        """Test courses with identical average scores"""
        _, _, player = Player.create('Alice', 'alice@test.com')
        _, _, course1 = Course.create('Course A', 'Location', 18, 54)
        _, _, course2 = Course.create('Course B', 'Location', 18, 54)

        # Both have same average
        Round.create(course1['id'], '2024-01-01', [
            {'player_id': player['id'], 'score': 50}
        ])
        Round.create(course2['id'], '2024-01-02', [
            {'player_id': player['id'], 'score': 50}
        ])

        stats = CourseService.get_course_stats()

        # Both should be included with different ranks
        assert len(stats) == 2
        assert stats[0]['stats']['average_score'] == 50
        assert stats[1]['stats']['average_score'] == 50
        assert stats[0]['stats']['difficulty_rank'] == 1
        assert stats[1]['stats']['difficulty_rank'] == 2

    def test_course_stats_structure(self, app):
        """Test that course stats have correct structure"""
        _, _, player = Player.create('Alice', 'alice@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        Round.create(course['id'], '2024-01-01', [
            {'player_id': player['id'], 'score': 30}
        ])

        stats = CourseService.get_course_stats()

        # Verify structure
        assert 'course' in stats[0]
        assert 'stats' in stats[0]
        assert 'times_played' in stats[0]['stats']
        assert 'average_score' in stats[0]['stats']
        assert 'best_score' in stats[0]['stats']
        assert 'best_score_player' in stats[0]['stats']
        assert 'worst_score' in stats[0]['stats']
        assert 'worst_score_player' in stats[0]['stats']
        assert 'difficulty_rank' in stats[0]['stats']


class TestCalculateCourseStats:
    """Test _calculate_course_stats method"""

    def test_calculate_stats_no_rounds(self, app):
        """Test stats calculation for unplayed course"""
        _, _, course = Course.create('Unplayed', 'Location', 18, 54)

        stats = CourseService._calculate_course_stats(course['id'])

        assert stats['times_played'] == 0
        assert stats['average_score'] == 0
        assert stats['best_score'] is None
        assert stats['best_score_player'] is None
        assert stats['worst_score'] is None
        assert stats['worst_score_player'] is None

    def test_calculate_stats_single_round_single_player(self, app):
        """Test stats with one round and one player"""
        _, _, player = Player.create('Alice', 'alice@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        Round.create(course['id'], '2024-01-01', [
            {'player_id': player['id'], 'score': 42}
        ])

        stats = CourseService._calculate_course_stats(course['id'])

        assert stats['times_played'] == 1
        assert stats['average_score'] == 42
        assert stats['best_score'] == 42
        assert stats['best_score_player'] == 'Alice'
        assert stats['worst_score'] == 42
        assert stats['worst_score_player'] == 'Alice'

    def test_calculate_stats_single_round_multiple_players(self, app):
        """Test stats with one round and multiple players"""
        _, _, player1 = Player.create('Alice', 'alice@test.com')
        _, _, player2 = Player.create('Bob', 'bob@test.com')
        _, _, player3 = Player.create('Charlie', 'charlie@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30},  # Best
            {'player_id': player2['id'], 'score': 40},
            {'player_id': player3['id'], 'score': 50}   # Worst
        ])

        stats = CourseService._calculate_course_stats(course['id'])

        assert stats['times_played'] == 1
        assert stats['average_score'] == 40  # (30 + 40 + 50) / 3
        assert stats['best_score'] == 30
        assert stats['best_score_player'] == 'Alice'
        assert stats['worst_score'] == 50
        assert stats['worst_score_player'] == 'Charlie'

    def test_calculate_stats_multiple_rounds(self, app):
        """Test stats with multiple rounds"""
        _, _, player1 = Player.create('Alice', 'alice@test.com')
        _, _, player2 = Player.create('Bob', 'bob@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Round 1
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30},
            {'player_id': player2['id'], 'score': 40}
        ])
        # Round 2
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player1['id'], 'score': 25},  # Overall best
            {'player_id': player2['id'], 'score': 45}
        ])
        # Round 3
        Round.create(course['id'], '2024-01-03', [
            {'player_id': player1['id'], 'score': 35},
            {'player_id': player2['id'], 'score': 50}   # Overall worst
        ])

        stats = CourseService._calculate_course_stats(course['id'])

        assert stats['times_played'] == 3
        # Average: (30+40+25+45+35+50) / 6 = 225 / 6 = 37.5
        assert stats['average_score'] == 37.5
        assert stats['best_score'] == 25
        assert stats['best_score_player'] == 'Alice'
        assert stats['worst_score'] == 50
        assert stats['worst_score_player'] == 'Bob'

    def test_calculate_stats_negative_scores(self, app):
        """Test stats with negative scores (under par)"""
        _, _, player = Player.create('Pro', 'pro@test.com')
        _, _, course = Course.create('Championship', 'Location', 18, 54)

        Round.create(course['id'], '2024-01-01', [
            {'player_id': player['id'], 'score': -5}  # Under par
        ])
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player['id'], 'score': -3}
        ])
        Round.create(course['id'], '2024-01-03', [
            {'player_id': player['id'], 'score': 2}
        ])

        stats = CourseService._calculate_course_stats(course['id'])

        assert stats['times_played'] == 3
        assert stats['average_score'] == (-5 + -3 + 2) / 3  # -2
        assert stats['best_score'] == -5  # Most under par
        assert stats['worst_score'] == 2

    def test_calculate_stats_tied_best_score(self, app):
        """Test when multiple players have the same best score"""
        _, _, player1 = Player.create('Alice', 'alice@test.com')
        _, _, player2 = Player.create('Bob', 'bob@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30}
        ])
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player2['id'], 'score': 30}  # Same best score
        ])

        stats = CourseService._calculate_course_stats(course['id'])

        assert stats['best_score'] == 30
        # Should use whichever player is mapped (first occurrence)
        assert stats['best_score_player'] in ['Alice', 'Bob']

    def test_calculate_stats_large_score_range(self, app):
        """Test stats with large range of scores"""
        _, _, player = Player.create('Alice', 'alice@test.com')
        _, _, course = Course.create('Varied Course', 'Location', 18, 54)

        # Create rounds with wide score range
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player['id'], 'score': 10}
        ])
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player['id'], 'score': 100}
        ])

        stats = CourseService._calculate_course_stats(course['id'])

        assert stats['times_played'] == 2
        assert stats['average_score'] == 55
        assert stats['best_score'] == 10
        assert stats['worst_score'] == 100

    def test_calculate_stats_many_players_one_round(self, app):
        """Test stats with many players in single round"""
        # Create 5 players
        players = []
        for i in range(5):
            _, _, player = Player.create(f'Player{i+1}', f'player{i+1}@test.com')
            players.append(player)

        _, _, course = Course.create('Popular Course', 'Location', 18, 54)

        # Create round with all players
        scores = [
            {'player_id': players[0]['id'], 'score': 25},  # Best
            {'player_id': players[1]['id'], 'score': 35},
            {'player_id': players[2]['id'], 'score': 45},
            {'player_id': players[3]['id'], 'score': 55},
            {'player_id': players[4]['id'], 'score': 65}   # Worst
        ]
        Round.create(course['id'], '2024-01-01', scores)

        stats = CourseService._calculate_course_stats(course['id'])

        assert stats['times_played'] == 1
        assert stats['average_score'] == 45  # (25+35+45+55+65) / 5
        assert stats['best_score'] == 25
        assert stats['best_score_player'] == 'Player1'
        assert stats['worst_score'] == 65
        assert stats['worst_score_player'] == 'Player5'

    def test_calculate_stats_floating_point_average(self, app):
        """Test that average handles non-integer results correctly"""
        _, _, player = Player.create('Alice', 'alice@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Scores that don't divide evenly
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player['id'], 'score': 33}
        ])
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player['id'], 'score': 34}
        ])

        stats = CourseService._calculate_course_stats(course['id'])

        assert stats['average_score'] == 33.5


class TestCourseServiceIntegration:
    """Integration tests for course service"""

    def test_full_course_stats_scenario(self, app):
        """Test complete course stats scenario with multiple courses and players"""
        # Create players
        _, _, alice = Player.create('Alice', 'alice@test.com')
        _, _, bob = Player.create('Bob', 'bob@test.com')
        _, _, charlie = Player.create('Charlie', 'charlie@test.com')

        # Create courses with different characteristics
        _, _, beginner = Course.create('Beginner Hills', 'Easy Park', 9, 27)
        _, _, intermediate = Course.create('City Course', 'Downtown', 18, 54)
        _, _, advanced = Course.create('Mountain Challenge', 'Highlands', 18, 72)
        _, _, unplayed = Course.create('New Course', 'Coming Soon', 18, 54)

        # Beginner course - easy scores
        Round.create(beginner['id'], '2024-01-01', [
            {'player_id': alice['id'], 'score': 25},
            {'player_id': bob['id'], 'score': 28}
        ])
        Round.create(beginner['id'], '2024-01-02', [
            {'player_id': charlie['id'], 'score': 26}
        ])

        # Intermediate course - medium scores
        Round.create(intermediate['id'], '2024-01-03', [
            {'player_id': alice['id'], 'score': 50},
            {'player_id': bob['id'], 'score': 55},
            {'player_id': charlie['id'], 'score': 52}
        ])

        # Advanced course - difficult scores
        Round.create(advanced['id'], '2024-01-04', [
            {'player_id': alice['id'], 'score': 75},
            {'player_id': bob['id'], 'score': 80}
        ])
        Round.create(advanced['id'], '2024-01-05', [
            {'player_id': charlie['id'], 'score': 78}
        ])

        stats = CourseService.get_course_stats()

        # Should only include played courses
        assert len(stats) == 3

        # Should be sorted by difficulty (hardest first)
        assert stats[0]['course']['name'] == 'Mountain Challenge'
        assert stats[0]['stats']['difficulty_rank'] == 1
        assert stats[0]['stats']['times_played'] == 2
        assert abs(stats[0]['stats']['average_score'] - 77.67) < 0.01

        assert stats[1]['course']['name'] == 'City Course'
        assert stats[1]['stats']['difficulty_rank'] == 2
        assert stats[1]['stats']['times_played'] == 1
        assert abs(stats[1]['stats']['average_score'] - 52.33) < 0.01

        assert stats[2]['course']['name'] == 'Beginner Hills'
        assert stats[2]['stats']['difficulty_rank'] == 3
        assert stats[2]['stats']['times_played'] == 2
        assert abs(stats[2]['stats']['average_score'] - 26.33) < 0.01

    def test_real_world_golf_scenario(self, app):
        """Test with realistic golf scores and scenarios"""
        # Create players with different skill levels
        _, _, pro = Player.create('Tiger Woods', 'pro@golf.com')
        _, _, amateur = Player.create('Weekend Warrior', 'amateur@golf.com')
        _, _, beginner = Player.create('First Timer', 'beginner@golf.com')

        # Create championship course
        _, _, course = Course.create('Augusta National', 'Georgia', 18, 72)

        # Multiple rounds showing skill differences
        Round.create(course['id'], '2024-04-01', [
            {'player_id': pro['id'], 'score': -5},      # 67 (5 under par)
            {'player_id': amateur['id'], 'score': 3},   # 75 (3 over par)
            {'player_id': beginner['id'], 'score': 18}  # 90 (18 over par)
        ])

        Round.create(course['id'], '2024-04-02', [
            {'player_id': pro['id'], 'score': -3},      # 69
            {'player_id': amateur['id'], 'score': 5},   # 77
            {'player_id': beginner['id'], 'score': 20}  # 92
        ])

        stats = CourseService.get_course_stats()

        assert len(stats) == 1
        assert stats[0]['course']['name'] == 'Augusta National'
        assert stats[0]['stats']['times_played'] == 2
        # Average: (-5 + 3 + 18 + -3 + 5 + 20) / 6 = 38 / 6 ≈ 6.33
        assert abs(stats[0]['stats']['average_score'] - 6.33) < 0.01
        assert stats[0]['stats']['best_score'] == -5
        assert stats[0]['stats']['best_score_player'] == 'Tiger Woods'
        assert stats[0]['stats']['worst_score'] == 20
        assert stats[0]['stats']['worst_score_player'] == 'First Timer'

    def test_course_popularity_tracking(self, app):
        """Test tracking which courses are most popular"""
        _, _, player = Player.create('Alice', 'alice@test.com')

        # Create courses
        _, _, popular = Course.create('Popular Course', 'Location', 18, 54)
        _, _, unpopular = Course.create('Unpopular Course', 'Location', 18, 54)

        # Popular course played many times
        for i in range(10):
            Round.create(popular['id'], f'2024-01-{i+1:02d}', [
                {'player_id': player['id'], 'score': 40 + i}
            ])

        # Unpopular course played once
        Round.create(unpopular['id'], '2024-01-15', [
            {'player_id': player['id'], 'score': 50}
        ])

        stats = CourseService.get_course_stats()

        # Find the popular course
        popular_stats = next(s for s in stats if s['course']['name'] == 'Popular Course')
        unpopular_stats = next(s for s in stats if s['course']['name'] == 'Unpopular Course')

        assert popular_stats['stats']['times_played'] == 10
        assert unpopular_stats['stats']['times_played'] == 1
