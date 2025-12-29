"""
Tests for CoursesPlayedService

This module tests the courses played statistics service which tracks:
- How many times selected players have played courses together
- Win tracking per player on each course
- Course sorting and filtering logic
"""

import pytest
from services.courses_played_service import CoursesPlayedService
from models.player import Player
from models.course import Course
from models.round import Round
from datetime import datetime, timedelta


class TestGetCoursesPlayedByPlayers:
    """Tests for get_courses_played_by_players method"""

    def test_single_player_multiple_courses(self, app):
        """Test courses played by a single player"""
        _, _, player = Player.create('Player1', 'player1@test.com')
        success, msg, course1 = Course.create('Course A', 'Test Location', 18, 54)
        success, msg, course2 = Course.create('Course B', 'Test Location', 18, 54)

        # Player plays course1 twice, course2 once
        Round.create(course_id=course1['id'], scores=[
            {'player_id': player['id'], 'player_name': player['name'], 'score': 35}
        ], date_played='2024-01-01')
        Round.create(course_id=course1['id'], scores=[
            {'player_id': player['id'], 'player_name': player['name'], 'score': 38}
        ], date_played='2024-01-01')
        Round.create(course_id=course2['id'], scores=[
            {'player_id': player['id'], 'player_name': player['name'], 'score': 42}
        ], date_played='2024-01-01')

        result = CoursesPlayedService.get_courses_played_by_players([player['id']])

        assert len(result) == 2
        # Default sort is descending by play count
        assert result[0]['course']['name'] == 'Course A'
        assert result[0]['play_count'] == 2
        assert result[1]['course']['name'] == 'Course B'
        assert result[1]['play_count'] == 1

    def test_multiple_players_all_must_play_together(self, app):
        """Test that rounds only count when ALL selected players participated"""
        _, _, player1 = Player.create('Player1', 'player1@test.com')
        _, _, player2 = Player.create('Player2', 'player2@test.com')
        success, msg, course = Course.create('Test Course', 'Test Location', 18, 54)

        # Round 1: Both players
        Round.create(course_id=course['id'], scores=[
            {'player_id': player1['id'], 'player_name': player1['name'], 'score': 35},
            {'player_id': player2['id'], 'player_name': player2['name'], 'score': 40}
        ], date_played='2024-01-01')

        # Round 2: Only player1
        Round.create(course_id=course['id'], scores=[
            {'player_id': player1['id'], 'player_name': player1['name'], 'score': 38}
        ], date_played='2024-01-01')

        # Round 3: Only player2
        Round.create(course_id=course['id'], scores=[
            {'player_id': player2['id'], 'player_name': player2['name'], 'score': 42}
        ], date_played='2024-01-01')

        result = CoursesPlayedService.get_courses_played_by_players([player1['id'], player2['id']])

        assert len(result) == 1
        assert result[0]['play_count'] == 1  # Only the round where both played

    def test_sort_by_play_count_descending(self, app):
        """Test sorting by play count in descending order (default)"""
        _, _, player = Player.create('Player', 'player@test.com')
        success, msg, course1 = Course.create('Popular Course', 'Test Location', 18, 54)
        success, msg, course2 = Course.create('Rare Course', 'Test Location', 18, 54)
        success, msg, course3 = Course.create('Medium Course', 'Test Location', 18, 54)

        # Create different numbers of rounds
        for _ in range(5):
            Round.create(course_id=course1['id'], scores=[
                {'player_id': player['id'], 'player_name': player['name'], 'score': 35}
            ], date_played='2024-01-01')

        for _ in range(2):
            Round.create(course_id=course3['id'], scores=[
                {'player_id': player['id'], 'player_name': player['name'], 'score': 35}
            ], date_played='2024-01-01')

        Round.create(course_id=course2['id'], scores=[
            {'player_id': player['id'], 'player_name': player['name'], 'score': 35}
        ], date_played='2024-01-01')

        result = CoursesPlayedService.get_courses_played_by_players([player['id']], sort_order='desc')

        assert result[0]['course']['name'] == 'Popular Course'
        assert result[0]['play_count'] == 5
        assert result[1]['course']['name'] == 'Medium Course'
        assert result[1]['play_count'] == 2
        assert result[2]['course']['name'] == 'Rare Course'
        assert result[2]['play_count'] == 1

    def test_sort_by_play_count_ascending(self, app):
        """Test sorting by play count in ascending order"""
        _, _, player = Player.create('Player', 'player@test.com')
        success, msg, course1 = Course.create('Most Played', 'Test Location', 18, 54)
        success, msg, course2 = Course.create('Least Played', 'Test Location', 18, 54)

        for _ in range(3):
            Round.create(course_id=course1['id'], scores=[
                {'player_id': player['id'], 'player_name': player['name'], 'score': 35}
            ], date_played='2024-01-01')

        Round.create(course_id=course2['id'], scores=[
            {'player_id': player['id'], 'player_name': player['name'], 'score': 35}
        ], date_played='2024-01-01')

        result = CoursesPlayedService.get_courses_played_by_players([player['id']], sort_order='asc')

        assert result[0]['course']['name'] == 'Least Played'
        assert result[0]['play_count'] == 1
        assert result[1]['course']['name'] == 'Most Played'
        assert result[1]['play_count'] == 3

    def test_sort_by_name_alphabetical(self, app):
        """Test sorting by course name alphabetically"""
        _, _, player = Player.create('Player', 'player@test.com')
        success, msg, course_z = Course.create('Zebra Course', 'Test Location', 18, 54)
        success, msg, course_a = Course.create('Apple Course', 'Test Location', 18, 54)
        success, msg, course_m = Course.create('Mango Course', 'Test Location', 18, 54)

        # Create rounds in random order
        Round.create(course_id=course_z['id'], scores=[
            {'player_id': player['id'], 'player_name': player['name'], 'score': 35}
        ], date_played='2024-01-01')
        Round.create(course_id=course_a['id'], scores=[
            {'player_id': player['id'], 'player_name': player['name'], 'score': 35}
        ], date_played='2024-01-01')
        Round.create(course_id=course_m['id'], scores=[
            {'player_id': player['id'], 'player_name': player['name'], 'score': 35}
        ], date_played='2024-01-01')

        result = CoursesPlayedService.get_courses_played_by_players([player['id']], sort_order='name')

        assert result[0]['course']['name'] == 'Apple Course'
        assert result[1]['course']['name'] == 'Mango Course'
        assert result[2]['course']['name'] == 'Zebra Course'

    def test_includes_unplayed_courses(self, app):
        """Test that unplayed courses are included with 0 plays"""
        _, _, player = Player.create('Player', 'player@test.com')
        success, msg, course_played = Course.create('Played Course', 'Test Location', 18, 54)
        success, msg, course_unplayed = Course.create('Unplayed Course', 'Test Location', 18, 54)

        Round.create(course_id=course_played['id'], scores=[
            {'player_id': player['id'], 'player_name': player['name'], 'score': 35}
        ], date_played='2024-01-01')

        result = CoursesPlayedService.get_courses_played_by_players([player['id']])

        assert len(result) == 2
        played = next(r for r in result if r['course']['name'] == 'Played Course')
        unplayed = next(r for r in result if r['course']['name'] == 'Unplayed Course')

        assert played['play_count'] == 1
        assert unplayed['play_count'] == 0

    def test_empty_player_list(self, app):
        """Test with empty player list returns empty results"""
        success, msg, course = Course.create('Test Course', 'Test Location', 18, 54)

        result = CoursesPlayedService.get_courses_played_by_players([])

        assert result == []

    def test_no_rounds_scenario(self, app):
        """Test when no rounds have been played"""
        _, _, player = Player.create('Player', 'player@test.com')
        success, msg, course1 = Course.create('Course 1', 'Test Location', 18, 54)
        success, msg, course2 = Course.create('Course 2', 'Test Location', 18, 54)

        result = CoursesPlayedService.get_courses_played_by_players([player['id']])

        assert len(result) == 2
        assert all(r['play_count'] == 0 for r in result)

    def test_percentage_calculation(self, app):
        """Test percentage calculation based on max plays"""
        _, _, player = Player.create('Player', 'player@test.com')
        success, msg, course1 = Course.create('Most Played', 'Test Location', 18, 54)
        success, msg, course2 = Course.create('Half Played', 'Test Location', 18, 54)

        for _ in range(10):
            Round.create(course_id=course1['id'], scores=[
                {'player_id': player['id'], 'player_name': player['name'], 'score': 35}
            ], date_played='2024-01-01')

        for _ in range(5):
            Round.create(course_id=course2['id'], scores=[
                {'player_id': player['id'], 'player_name': player['name'], 'score': 35}
            ], date_played='2024-01-01')

        result = CoursesPlayedService.get_courses_played_by_players([player['id']])

        most_played = next(r for r in result if r['course']['name'] == 'Most Played')
        half_played = next(r for r in result if r['course']['name'] == 'Half Played')

        assert most_played['percentage'] == 100.0
        assert half_played['percentage'] == 50.0

    def test_top_winner_tracking(self, app):
        """Test tracking of top winner per course"""
        _, _, player1 = Player.create('Winner', 'player1@test.com')
        _, _, player2 = Player.create('Loser', 'player2@test.com')
        success, msg, course = Course.create('Test Course', 'Test Location', 18, 54)

        # Player1 wins 3 times
        for _ in range(3):
            Round.create(course_id=course['id'], scores=[
                {'player_id': player1['id'], 'player_name': player1['name'], 'score': 30},
                {'player_id': player2['id'], 'player_name': player2['name'], 'score': 40}
            ], date_played='2024-01-01')

        # Player2 wins 1 time
        Round.create(course_id=course['id'], scores=[
            {'player_id': player1['id'], 'player_name': player1['name'], 'score': 45},
            {'player_id': player2['id'], 'player_name': player2['name'], 'score': 35}
        ], date_played='2024-01-01')

        result = CoursesPlayedService.get_courses_played_by_players([player1['id'], player2['id']])

        assert len(result) == 1
        assert result[0]['top_winner_name'] == 'Winner'
        assert result[0]['top_winner_wins'] == 3

    def test_name_abbreviation_long_names(self, app):
        """Test that long player names are abbreviated"""
        _, _, player1 = Player.create('VeryLongFirstName VeryLongLastName', 'player1@test.com')
        _, _, player2 = Player.create('Short', 'player2@test.com')
        success, msg, course = Course.create('Test Course', 'Test Location', 18, 54)

        # Long name player wins
        Round.create(course_id=course['id'], scores=[
            {'player_id': player1['id'], 'player_name': player1['name'], 'score': 30},
            {'player_id': player2['id'], 'player_name': player2['name'], 'score': 40}
        ], date_played='2024-01-01')

        result = CoursesPlayedService.get_courses_played_by_players([player1['id'], player2['id']])

        assert len(result) == 1
        # Should be abbreviated to "FirstName L."
        assert result[0]['top_winner_name'] == 'VeryLongFirstName V.'
        assert len(result[0]['top_winner_name']) <= 20  # Reasonable length

    def test_name_abbreviation_single_word(self, app):
        """Test abbreviation of single-word long names"""
        _, _, player1 = Player.create('VeryVeryLongSingleUsername', 'player1@test.com')
        _, _, player2 = Player.create('Short', 'player2@test.com')
        success, msg, course = Course.create('Test Course', 'Test Location', 18, 54)

        Round.create(course_id=course['id'], scores=[
            {'player_id': player1['id'], 'player_name': player1['name'], 'score': 30},
            {'player_id': player2['id'], 'player_name': player2['name'], 'score': 40}
        ], date_played='2024-01-01')

        result = CoursesPlayedService.get_courses_played_by_players([player1['id'], player2['id']])

        assert len(result) == 1
        # Should be truncated with ellipsis
        assert result[0]['top_winner_name'] == 'VeryVeryLong...'

    def test_no_winner_for_unplayed_course(self, app):
        """Test that unplayed courses have no winner"""
        _, _, player = Player.create('Player', 'player@test.com')
        success, msg, course = Course.create('Unplayed Course', 'Test Location', 18, 54)

        result = CoursesPlayedService.get_courses_played_by_players([player['id']])

        assert len(result) == 1
        assert result[0]['top_winner_name'] is None
        assert result[0]['top_winner_wins'] == 0

    def test_three_players_all_together(self, app):
        """Test with three players - rounds only count when all three play"""
        _, _, player1 = Player.create('Player1', 'player1@test.com')
        _, _, player2 = Player.create('Player2', 'player2@test.com')
        _, _, player3 = Player.create('Player3', 'player3@test.com')
        success, msg, course = Course.create('Test Course', 'Test Location', 18, 54)

        # Round with all three
        Round.create(course_id=course['id'], scores=[
            {'player_id': player1['id'], 'player_name': player1['name'], 'score': 30},
            {'player_id': player2['id'], 'player_name': player2['name'], 'score': 35},
            {'player_id': player3['id'], 'player_name': player3['name'], 'score': 40}
        ], date_played='2024-01-01')

        # Round with only two
        Round.create(course_id=course['id'], scores=[
            {'player_id': player1['id'], 'player_name': player1['name'], 'score': 30},
            {'player_id': player2['id'], 'player_name': player2['name'], 'score': 35}
        ], date_played='2024-01-01')

        result = CoursesPlayedService.get_courses_played_by_players(
            [player1['id'], player2['id'], player3['id']]
        )

        assert len(result) == 1
        assert result[0]['play_count'] == 1  # Only the round with all three

    def test_winner_among_selected_players_only(self, app):
        """Test that winner is determined only among selected players"""
        _, _, player1 = Player.create('Selected1', 'player1@test.com')
        _, _, player2 = Player.create('Selected2', 'player2@test.com')
        _, _, player3 = Player.create('NotSelected', 'player3@test.com')
        success, msg, course = Course.create('Test Course', 'Test Location', 18, 54)

        # Player3 (not selected) has best score, but Selected1 wins among selected
        Round.create(course_id=course['id'], scores=[
            {'player_id': player1['id'], 'player_name': player1['name'], 'score': 35},
            {'player_id': player2['id'], 'player_name': player2['name'], 'score': 40},
            {'player_id': player3['id'], 'player_name': player3['name'], 'score': 25}
        ], date_played='2024-01-01')

        result = CoursesPlayedService.get_courses_played_by_players([player1['id'], player2['id']])

        assert len(result) == 1
        assert result[0]['top_winner_name'] == 'Selected1'
        assert result[0]['top_winner_wins'] == 1


class TestCoursesPlayedIntegration:
    """Integration tests for complete courses played scenarios"""

    def test_full_multi_player_scenario(self, app):
        """Test complete scenario with multiple players and courses"""
        # Create players
        _, _, alice = Player.create('Alice', 'alice@test.com')
        _, _, bob = Player.create('Bob', 'bob@test.com')

        # Create courses
        success, msg, course_a = Course.create('Awesome Course', 'Test Location', 18, 54)
        success, msg, course_b = Course.create('Boring Course', 'Test Location', 18, 54)
        success, msg, course_c = Course.create('Cool Course', 'Test Location', 18, 54)

        # Alice and Bob play together on Course A (3 times) - Alice wins 2, Bob wins 1
        Round.create(course_id=course_a['id'], scores=[
            {'player_id': alice['id'], 'player_name': alice['name'], 'score': 30},
            {'player_id': bob['id'], 'player_name': bob['name'], 'score': 35}
        ], date_played='2024-01-01')

        Round.create(course_id=course_a['id'], scores=[
            {'player_id': alice['id'], 'player_name': alice['name'], 'score': 32},
            {'player_id': bob['id'], 'player_name': bob['name'], 'score': 38}
        ], date_played='2024-01-02')

        Round.create(course_id=course_a['id'], scores=[
            {'player_id': alice['id'], 'player_name': alice['name'], 'score': 40},
            {'player_id': bob['id'], 'player_name': bob['name'], 'score': 35}
        ], date_played='2024-01-03')

        # Alice and Bob play together on Course B (1 time) - Bob wins
        Round.create(course_id=course_b['id'], scores=[
            {'player_id': alice['id'], 'player_name': alice['name'], 'score': 45},
            {'player_id': bob['id'], 'player_name': bob['name'], 'score': 42}
        ], date_played='2024-01-02')

        # Alice plays solo on Course C (doesn't count when filtering for both)
        Round.create(course_id=course_c['id'], scores=[
            {'player_id': alice['id'], 'player_name': alice['name'], 'score': 35}
        ], date_played='2024-01-01')

        # Get stats for both players
        result = CoursesPlayedService.get_courses_played_by_players(
            [alice['id'], bob['id']],
            sort_order='desc'
        )

        # Should have all 3 courses
        assert len(result) == 3

        # Course A should be first (most played together)
        assert result[0]['course']['name'] == 'Awesome Course'
        assert result[0]['play_count'] == 3
        assert result[0]['top_winner_name'] == 'Alice'
        assert result[0]['top_winner_wins'] == 2
        assert result[0]['percentage'] == 100.0

        # Course B should be second
        assert result[1]['course']['name'] == 'Boring Course'
        assert result[1]['play_count'] == 1
        assert result[1]['top_winner_name'] == 'Bob'
        assert result[1]['top_winner_wins'] == 1
        assert result[1]['percentage'] == pytest.approx(33.33, rel=0.1)

        # Course C should be last (never played together)
        assert result[2]['course']['name'] == 'Cool Course'
        assert result[2]['play_count'] == 0
        assert result[2]['top_winner_name'] is None
        assert result[2]['percentage'] == 0.0

    def test_alphabetical_sorting_integration(self, app):
        """Test alphabetical sorting with real data"""
        _, _, player = Player.create('Player', 'player@test.com')

        # Create courses with varied names
        success, msg, course_z = Course.create('Zebra Mini Golf', 'Test Location', 18, 54)
        success, msg, course_a = Course.create('Apple Valley Course', 'Test Location', 18, 54)
        success, msg, course_m = Course.create('Mango Beach Golf', 'Test Location', 18, 54)
        success, msg, course_b = Course.create('Banana Island', 'Test Location', 18, 54)

        # Create some rounds (doesn't matter which courses)
        Round.create(course_id=course_z['id'], scores=[
            {'player_id': player['id'], 'player_name': player['name'], 'score': 35}
        ], date_played='2024-01-01')

        result = CoursesPlayedService.get_courses_played_by_players([player['id']], sort_order='name')

        # Verify alphabetical order
        names = [r['course']['name'] for r in result]
        assert names == ['Apple Valley Course', 'Banana Island', 'Mango Beach Golf', 'Zebra Mini Golf']

    def test_percentage_with_zero_plays(self, app):
        """Test that percentage calculation handles all zero plays correctly"""
        _, _, player = Player.create('Player', 'player@test.com')
        success, msg, course1 = Course.create('Course 1', 'Test Location', 18, 54)
        success, msg, course2 = Course.create('Course 2', 'Test Location', 18, 54)

        result = CoursesPlayedService.get_courses_played_by_players([player['id']])

        # When all courses have 0 plays, percentage should be 0
        assert all(r['percentage'] == 0.0 for r in result)
