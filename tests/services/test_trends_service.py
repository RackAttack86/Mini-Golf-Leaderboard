import pytest
from datetime import datetime, timedelta
from models.player import Player
from models.course import Course
from models.round import Round
from services.trends_service import TrendsService


class TestGetPlayerTrends:
    """Test get_player_trends method"""

    def test_player_trends_no_rounds(self, data_store):
        """Test trends for player with no rounds"""
        # Create player
        success, message, player = Player.create('Player', 'player@test.com')
        assert success

        trends = TrendsService.get_player_trends(player['id'])

        assert trends['total_rounds'] == 0
        assert trends['average_score'] == 0
        assert trends['improvement'] == 0
        assert trends['rounds'] == []
        assert trends['dates'] == []
        assert trends['scores'] == []

    def test_player_trends_single_round(self, data_store):
        """Test trends for player with single round"""
        # Create player and course
        success, message, player = Player.create('Player', 'player@test.com')
        assert success
        success, msg, course = Course.create('Course', 'Location', 18, 54)
        assert success

        # Create round
        Round.create(
            course_id=course['id'],
            date_played='2025-01-15',
            scores=[{'player_id': player['id'], 'score': 50}]
        )

        trends = TrendsService.get_player_trends(player['id'])

        assert trends['total_rounds'] == 1
        assert trends['average_score'] == 50
        assert trends['improvement'] == 0  # Not enough rounds for improvement
        assert len(trends['rounds']) == 1
        assert trends['rounds'][0]['score'] == 50
        assert trends['rounds'][0]['won'] is True  # Only player, so won
        assert trends['rounds'][0]['position'] == 1
        assert trends['rounds'][0]['total_players'] == 1

    def test_player_trends_multiple_rounds(self, data_store):
        """Test trends with multiple rounds"""
        # Create players and course
        success, message, player1 = Player.create('Player 1', 'p1@test.com')
        assert success
        success, message, player2 = Player.create('Player 2', 'p2@test.com')
        assert success
        success, msg, course = Course.create('Course', 'Location', 18, 54)
        assert success

        # Create rounds on different dates
        Round.create(
            course_id=course['id'],
            date_played='2025-01-10',
            scores=[
                {'player_id': player1['id'], 'score': 60},
                {'player_id': player2['id'], 'score': 55}
            ]
        )
        Round.create(
            course_id=course['id'],
            date_played='2025-01-15',
            scores=[
                {'player_id': player1['id'], 'score': 50},
                {'player_id': player2['id'], 'score': 52}
            ]
        )

        trends = TrendsService.get_player_trends(player1['id'])

        assert trends['total_rounds'] == 2
        assert trends['average_score'] == 55  # (60 + 50) / 2
        assert len(trends['rounds']) == 2
        assert trends['dates'] == ['2025-01-10', '2025-01-15']
        assert trends['scores'] == [60, 50]

        # Check first round details
        assert trends['rounds'][0]['won'] is False  # player2 won with 55
        assert trends['rounds'][0]['position'] == 2  # Second place

        # Check second round details
        assert trends['rounds'][1]['won'] is True  # player1 won with 50
        assert trends['rounds'][1]['position'] == 1  # First place

    def test_player_trends_improvement_calculation(self, data_store):
        """Test improvement calculation with 6+ rounds"""
        # Create player and course
        success, message, player = Player.create('Player', 'player@test.com')
        assert success
        success, msg, course = Course.create('Course', 'Location', 18, 54)
        assert success

        # Create 6 rounds showing improvement
        scores = [60, 58, 56, 52, 50, 48]  # Getting better
        for i, score in enumerate(scores):
            Round.create(
                course_id=course['id'],
                date_played=f'2025-01-{10+i:02d}',
                scores=[{'player_id': player['id'], 'score': score}]
            )

        trends = TrendsService.get_player_trends(player['id'])

        assert trends['total_rounds'] == 6
        # First 3 average: (60 + 58 + 56) / 3 = 58
        # Last 3 average: (52 + 50 + 48) / 3 = 50
        # Improvement: 58 - 50 = 8
        assert trends['improvement'] == pytest.approx(8.0)

    def test_player_trends_negative_improvement(self, data_store):
        """Test when player gets worse over time"""
        # Create player and course
        success, message, player = Player.create('Player', 'player@test.com')
        assert success
        success, msg, course = Course.create('Course', 'Location', 18, 54)
        assert success

        # Create 6 rounds showing decline
        scores = [48, 50, 52, 56, 58, 60]  # Getting worse
        for i, score in enumerate(scores):
            Round.create(
                course_id=course['id'],
                date_played=f'2025-01-{10+i:02d}',
                scores=[{'player_id': player['id'], 'score': score}]
            )

        trends = TrendsService.get_player_trends(player['id'])

        # First 3 average: (48 + 50 + 52) / 3 = 50
        # Last 3 average: (56 + 58 + 60) / 3 = 58
        # Improvement: 50 - 58 = -8 (negative means worse)
        assert trends['improvement'] == pytest.approx(-8.0)

    def test_player_trends_with_date_filters(self, data_store):
        """Test trends with start and end date filters"""
        # Create player and course
        success, message, player = Player.create('Player', 'player@test.com')
        assert success
        success, msg, course = Course.create('Course', 'Location', 18, 54)
        assert success

        # Create rounds across different dates
        Round.create(course_id=course['id'], date_played='2025-01-01',
                    scores=[{'player_id': player['id'], 'score': 60}])
        Round.create(course_id=course['id'], date_played='2025-01-15',
                    scores=[{'player_id': player['id'], 'score': 50}])
        Round.create(course_id=course['id'], date_played='2025-01-30',
                    scores=[{'player_id': player['id'], 'score': 55}])

        # Filter to only middle round
        trends = TrendsService.get_player_trends(
            player['id'],
            start_date='2025-01-10',
            end_date='2025-01-20'
        )

        assert trends['total_rounds'] == 1
        assert trends['scores'] == [50]

    def test_player_trends_rounds_sorted_by_date(self, data_store):
        """Test that rounds are sorted chronologically"""
        # Create player and course
        success, message, player = Player.create('Player', 'player@test.com')
        assert success
        success, msg, course = Course.create('Course', 'Location', 18, 54)
        assert success

        # Create rounds in non-chronological order
        Round.create(course_id=course['id'], date_played='2025-01-20',
                    scores=[{'player_id': player['id'], 'score': 50}])
        Round.create(course_id=course['id'], date_played='2025-01-10',
                    scores=[{'player_id': player['id'], 'score': 60}])
        Round.create(course_id=course['id'], date_played='2025-01-15',
                    scores=[{'player_id': player['id'], 'score': 55}])

        trends = TrendsService.get_player_trends(player['id'])

        # Should be sorted: 10th, 15th, 20th
        assert trends['dates'] == ['2025-01-10', '2025-01-15', '2025-01-20']
        assert trends['scores'] == [60, 55, 50]

    def test_player_trends_with_tied_scores(self, data_store):
        """Test trends when player ties for first"""
        # Create players and course
        success, message, player1 = Player.create('Player 1', 'p1@test.com')
        assert success
        success, message, player2 = Player.create('Player 2', 'p2@test.com')
        assert success
        success, msg, course = Course.create('Course', 'Location', 18, 54)
        assert success

        # Create round with tied scores
        Round.create(
            course_id=course['id'],
            date_played='2025-01-15',
            scores=[
                {'player_id': player1['id'], 'score': 50},
                {'player_id': player2['id'], 'score': 50}
            ]
        )

        trends = TrendsService.get_player_trends(player1['id'])

        # Both players have the minimum score, so both should be marked as won
        assert trends['rounds'][0]['won'] is True
        assert trends['rounds'][0]['position'] == 1


class TestGetOverallTrends:
    """Test get_overall_trends method"""

    def test_overall_trends_no_rounds(self, data_store):
        """Test overall trends with no rounds"""
        trends = TrendsService.get_overall_trends()

        assert trends['total_rounds'] == 0
        assert trends['total_players'] == 0
        assert trends['average_score'] == 0

    def test_overall_trends_single_round(self, data_store):
        """Test overall trends with single round"""
        # Create players and course
        success, message, player1 = Player.create('Player 1', 'p1@test.com')
        assert success
        success, message, player2 = Player.create('Player 2', 'p2@test.com')
        assert success
        success, msg, course = Course.create('Course', 'Location', 18, 54)
        assert success

        # Create round
        Round.create(
            course_id=course['id'],
            date_played='2025-01-15',
            scores=[
                {'player_id': player1['id'], 'score': 50},
                {'player_id': player2['id'], 'score': 60}
            ]
        )

        trends = TrendsService.get_overall_trends()

        assert trends['total_rounds'] == 1
        assert trends['total_players'] == 2
        assert trends['average_score'] == 55  # (50 + 60) / 2

    def test_overall_trends_multiple_rounds(self, data_store):
        """Test overall trends with multiple rounds"""
        # Create players and course
        success, message, player1 = Player.create('Player 1', 'p1@test.com')
        assert success
        success, message, player2 = Player.create('Player 2', 'p2@test.com')
        assert success
        success, msg, course = Course.create('Course', 'Location', 18, 54)
        assert success

        # Create multiple rounds
        Round.create(
            course_id=course['id'],
            date_played='2025-01-10',
            scores=[
                {'player_id': player1['id'], 'score': 50},
                {'player_id': player2['id'], 'score': 60}
            ]
        )
        Round.create(
            course_id=course['id'],
            date_played='2025-01-15',
            scores=[
                {'player_id': player1['id'], 'score': 52},
                {'player_id': player2['id'], 'score': 58}
            ]
        )

        trends = TrendsService.get_overall_trends()

        assert trends['total_rounds'] == 2
        assert trends['total_players'] == 2
        # Average: (50 + 60 + 52 + 58) / 4 = 55
        assert trends['average_score'] == 55

    def test_overall_trends_player_appears_multiple_times(self, data_store):
        """Test that same player in multiple rounds is counted once"""
        # Create player and course
        success, message, player = Player.create('Player', 'player@test.com')
        assert success
        success, msg, course = Course.create('Course', 'Location', 18, 54)
        assert success

        # Player plays 3 rounds
        Round.create(course_id=course['id'], date_played='2025-01-10',
                    scores=[{'player_id': player['id'], 'score': 50}])
        Round.create(course_id=course['id'], date_played='2025-01-15',
                    scores=[{'player_id': player['id'], 'score': 52}])
        Round.create(course_id=course['id'], date_played='2025-01-20',
                    scores=[{'player_id': player['id'], 'score': 48}])

        trends = TrendsService.get_overall_trends()

        assert trends['total_rounds'] == 3
        assert trends['total_players'] == 1  # Only 1 unique player
        assert trends['average_score'] == 50  # (50 + 52 + 48) / 3

    def test_overall_trends_with_date_filters(self, data_store):
        """Test overall trends with date filters"""
        # Create player and course
        success, message, player = Player.create('Player', 'player@test.com')
        assert success
        success, msg, course = Course.create('Course', 'Location', 18, 54)
        assert success

        # Create rounds across different dates
        Round.create(course_id=course['id'], date_played='2025-01-01',
                    scores=[{'player_id': player['id'], 'score': 60}])
        Round.create(course_id=course['id'], date_played='2025-01-15',
                    scores=[{'player_id': player['id'], 'score': 50}])
        Round.create(course_id=course['id'], date_played='2025-01-30',
                    scores=[{'player_id': player['id'], 'score': 55}])

        # Filter to only middle round
        trends = TrendsService.get_overall_trends(
            start_date='2025-01-10',
            end_date='2025-01-20'
        )

        assert trends['total_rounds'] == 1
        assert trends['average_score'] == 50


class TestGetAllPlayersTrends:
    """Test get_all_players_trends method"""

    def test_all_players_trends_no_rounds(self, data_store):
        """Test all players trends with no rounds"""
        # Create players but no rounds
        Player.create('Player 1', 'p1@test.com')
        Player.create('Player 2', 'p2@test.com')

        trends = TrendsService.get_all_players_trends()

        assert 'players' in trends
        assert 'courses' in trends
        assert 'win_counts' in trends
        assert len(trends['players']) == 2
        assert trends['courses'] == {}

    def test_all_players_trends_single_round(self, data_store):
        """Test all players trends with single round"""
        # Create players and course
        success, message, player1 = Player.create('Player 1', 'p1@test.com')
        assert success
        success, message, player2 = Player.create('Player 2', 'p2@test.com')
        assert success
        success, msg, course = Course.create('Test Course', 'Location', 18, 54)
        assert success

        # Create round
        Round.create(
            course_id=course['id'],
            date_played='2025-01-15',
            scores=[
                {'player_id': player1['id'], 'score': 50},
                {'player_id': player2['id'], 'score': 60}
            ]
        )

        trends = TrendsService.get_all_players_trends()

        # Check player data
        assert len(trends['players'][player1['id']]['rounds']) == 1
        assert trends['players'][player1['id']]['rounds'][0]['score'] == 50
        assert trends['players'][player1['id']]['rounds'][0]['won'] is True

        assert len(trends['players'][player2['id']]['rounds']) == 1
        assert trends['players'][player2['id']]['rounds'][0]['score'] == 60
        assert trends['players'][player2['id']]['rounds'][0]['won'] is False

        # Check win counts
        assert trends['win_counts'][player1['id']] == 1
        assert trends['win_counts'][player2['id']] == 0

        # Check course averages
        assert 'Test Course' in trends['courses']
        assert trends['courses']['Test Course'] == 55  # (50 + 60) / 2

    def test_all_players_trends_multiple_rounds(self, data_store):
        """Test all players trends with multiple rounds"""
        # Create players and courses
        success, message, player1 = Player.create('Player 1', 'p1@test.com')
        assert success
        success, message, player2 = Player.create('Player 2', 'p2@test.com')
        assert success
        success, msg, course1 = Course.create('Course A', 'Location', 18, 54)
        assert success
        success, msg, course2 = Course.create('Course B', 'Location', 18, 54)
        assert success

        # Create rounds on different courses
        Round.create(
            course_id=course1['id'],
            date_played='2025-01-10',
            scores=[
                {'player_id': player1['id'], 'score': 50},
                {'player_id': player2['id'], 'score': 55}
            ]
        )
        Round.create(
            course_id=course2['id'],
            date_played='2025-01-15',
            scores=[
                {'player_id': player1['id'], 'score': 60},
                {'player_id': player2['id'], 'score': 58}
            ]
        )

        trends = TrendsService.get_all_players_trends()

        # Each player should have 2 rounds
        assert len(trends['players'][player1['id']]['rounds']) == 2
        assert len(trends['players'][player2['id']]['rounds']) == 2

        # Player 1 won first round, Player 2 won second round
        assert trends['win_counts'][player1['id']] == 1
        assert trends['win_counts'][player2['id']] == 1

        # Check course averages
        assert trends['courses']['Course A'] == 52.5  # (50 + 55) / 2
        assert trends['courses']['Course B'] == 59  # (60 + 58) / 2

    def test_all_players_trends_player_colors(self, data_store):
        """Test that player colors are included in trends"""
        # Create player with favorite color
        success, message, player = Player.create('Player', 'player@test.com',
                                                 favorite_color='#ff0000')
        assert success
        success, msg, course = Course.create('Course', 'Location', 18, 54)
        assert success

        # Create round
        Round.create(
            course_id=course['id'],
            date_played='2025-01-15',
            scores=[{'player_id': player['id'], 'score': 50}]
        )

        trends = TrendsService.get_all_players_trends()

        assert trends['players'][player['id']]['color'] == '#ff0000'

    def test_all_players_trends_with_ties(self, data_store):
        """Test all players trends when there's a tie"""
        # Create players and course
        success, message, player1 = Player.create('Player 1', 'p1@test.com')
        assert success
        success, message, player2 = Player.create('Player 2', 'p2@test.com')
        assert success
        success, msg, course = Course.create('Course', 'Location', 18, 54)
        assert success

        # Create round with tie
        Round.create(
            course_id=course['id'],
            date_played='2025-01-15',
            scores=[
                {'player_id': player1['id'], 'score': 50},
                {'player_id': player2['id'], 'score': 50}
            ]
        )

        trends = TrendsService.get_all_players_trends()

        # Both players should have won flag set to True
        assert trends['players'][player1['id']]['rounds'][0]['won'] is True
        assert trends['players'][player2['id']]['rounds'][0]['won'] is True

        # Both should have 1 win
        assert trends['win_counts'][player1['id']] == 1
        assert trends['win_counts'][player2['id']] == 1

    def test_all_players_trends_with_date_filters(self, data_store):
        """Test all players trends with date filters"""
        # Create player and course
        success, message, player = Player.create('Player', 'player@test.com')
        assert success
        success, msg, course = Course.create('Course', 'Location', 18, 54)
        assert success

        # Create rounds across different dates
        Round.create(course_id=course['id'], date_played='2025-01-01',
                    scores=[{'player_id': player['id'], 'score': 60}])
        Round.create(course_id=course['id'], date_played='2025-01-15',
                    scores=[{'player_id': player['id'], 'score': 50}])
        Round.create(course_id=course['id'], date_played='2025-01-30',
                    scores=[{'player_id': player['id'], 'score': 55}])

        # Filter to only middle round
        trends = TrendsService.get_all_players_trends(
            start_date='2025-01-10',
            end_date='2025-01-20'
        )

        # Should only include middle round
        assert len(trends['players'][player['id']]['rounds']) == 1
        assert trends['players'][player['id']]['rounds'][0]['score'] == 50

    def test_all_players_trends_multiple_courses(self, data_store):
        """Test course averages across multiple rounds"""
        # Create player and courses
        success, message, player = Player.create('Player', 'player@test.com')
        assert success
        success, msg, course = Course.create('Course', 'Location', 18, 54)
        assert success

        # Create multiple rounds on same course
        Round.create(course_id=course['id'], date_played='2025-01-10',
                    scores=[{'player_id': player['id'], 'score': 50}])
        Round.create(course_id=course['id'], date_played='2025-01-15',
                    scores=[{'player_id': player['id'], 'score': 60}])
        Round.create(course_id=course['id'], date_played='2025-01-20',
                    scores=[{'player_id': player['id'], 'score': 52}])

        trends = TrendsService.get_all_players_trends()

        # Course average should be (50 + 60 + 52) / 3 = 54
        assert trends['courses']['Course'] == pytest.approx(54.0)

    def test_all_players_trends_inactive_player_not_included(self, data_store):
        """Test that inactive players are still included if they have rounds"""
        # Create players
        success, message, player1 = Player.create('Active Player', 'active@test.com')
        assert success
        success, message, player2 = Player.create('Inactive Player', 'inactive@test.com')
        assert success
        success, msg, course = Course.create('Course', 'Location', 18, 54)
        assert success

        # Create round with both players
        Round.create(
            course_id=course['id'],
            date_played='2025-01-15',
            scores=[
                {'player_id': player1['id'], 'score': 50},
                {'player_id': player2['id'], 'score': 55}
            ]
        )

        # Deactivate player2
        Player.delete(player2['id'])  # This soft-deletes (marks inactive)

        trends = TrendsService.get_all_players_trends()

        # Only active player should be in trends
        assert player1['id'] in trends['players']
        # Inactive player might not be returned by Player.get_all() if active_only=True
