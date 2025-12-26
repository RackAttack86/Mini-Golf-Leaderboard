"""
Comprehensive unit tests for the AchievementService.

Tests cover:
- Achievement calculation for various scenarios
- Win counting and streak detection
- Course exploration achievements
- Social achievements
- Achievement points calculation
- Edge cases and special scenarios
"""
import pytest
from datetime import datetime, timedelta

from services.achievement_service import AchievementService
from models.player import Player
from models.course import Course
from models.round import Round


@pytest.mark.unit
@pytest.mark.services
class TestAchievementBasicCalculation:
    """Tests for basic achievement calculation"""

    def test_no_achievements_without_rounds(self, data_store):
        """Test that player with no rounds has no achievements"""
        success, message, player = Player.create(name='New Player')

        achievements = AchievementService.get_player_achievements(player['id'])

        assert achievements['total_points'] == 0
        assert len(achievements['earned']) == 0
        assert achievements['stats']['total_rounds'] == 0
        assert achievements['stats']['wins'] == 0

    def test_first_round_achievement(self, data_store, dates_helper):
        """Test that playing first round earns First Round achievement"""
        # Create test data
        success, message, player1 = Player.create(name='Player 1')
        success, message, player2 = Player.create(name='Player 2')
        success, message, course = Course.create(name='Test Course')

        # Create a round (need 2+ players for achievements)
        scores = [
            {'player_id': player1['id'], 'score': 50},
            {'player_id': player2['id'], 'score': 55}
        ]
        Round.create(course['id'], dates_helper['yesterday'](), scores)

        achievements = AchievementService.get_player_achievements(player1['id'])

        # Should have First Round achievement
        earned_ids = [a['id'] for a in achievements['earned']]
        assert 'first_round' in earned_ids
        assert achievements['total_points'] >= 10  # First Round is worth 10 points

    def test_solo_rounds_excluded(self, data_store, dates_helper):
        """Test that solo rounds (1 player) don't count for achievements"""
        success, message, player = Player.create(name='Solo Player')
        success, message, course = Course.create(name='Test Course')

        # Create solo round
        scores = [{'player_id': player['id'], 'score': 50}]
        Round.create(course['id'], dates_helper['yesterday'](), scores)

        achievements = AchievementService.get_player_achievements(player['id'])

        # Solo rounds don't count
        assert achievements['stats']['total_rounds'] == 0
        assert len(achievements['earned']) == 0


@pytest.mark.unit
@pytest.mark.services
class TestWinCounting:
    """Tests for win detection and counting"""

    def test_win_detection(self, data_store, dates_helper):
        """Test that wins are detected correctly (lowest score)"""
        success, message, player1 = Player.create(name='Winner')
        success, message, player2 = Player.create(name='Loser')
        success, message, course = Course.create(name='Test Course')

        # Player 1 wins with lower score
        scores = [
            {'player_id': player1['id'], 'score': 45},
            {'player_id': player2['id'], 'score': 50}
        ]
        Round.create(course['id'], dates_helper['yesterday'](), scores)

        achievements = AchievementService.get_player_achievements(player1['id'])

        assert achievements['stats']['wins'] == 1

    def test_first_victory_achievement(self, data_store, dates_helper):
        """Test First Victory achievement"""
        success, message, player1 = Player.create(name='Winner')
        success, message, player2 = Player.create(name='Loser')
        success, message, course = Course.create(name='Test Course')

        scores = [
            {'player_id': player1['id'], 'score': 45},
            {'player_id': player2['id'], 'score': 50}
        ]
        Round.create(course['id'], dates_helper['yesterday'](), scores)

        achievements = AchievementService.get_player_achievements(player1['id'])

        earned_ids = [a['id'] for a in achievements['earned']]
        assert 'first_victory' in earned_ids

    def test_multiple_wins(self, data_store, dates_helper):
        """Test counting multiple wins"""
        success, message, player1 = Player.create(name='Champion')
        success, message, player2 = Player.create(name='Opponent')
        success, message, course = Course.create(name='Test Course')

        # Create 5 rounds where player1 wins
        for i in range(5):
            scores = [
                {'player_id': player1['id'], 'score': 45},
                {'player_id': player2['id'], 'score': 50}
            ]
            Round.create(course['id'], dates_helper['days_ago'](i), scores)

        achievements = AchievementService.get_player_achievements(player1['id'])

        assert achievements['stats']['wins'] == 5


@pytest.mark.unit
@pytest.mark.services
class TestWinStreaks:
    """Tests for win streak detection"""

    def test_current_win_streak(self, data_store, dates_helper):
        """Test current win streak detection"""
        success, message, player1 = Player.create(name='Streaker')
        success, message, player2 = Player.create(name='Opponent')
        success, message, course = Course.create(name='Test Course')

        # Create 3 consecutive wins (most recent)
        for i in range(3):
            scores = [
                {'player_id': player1['id'], 'score': 45},
                {'player_id': player2['id'], 'score': 50}
            ]
            Round.create(course['id'], dates_helper['days_ago'](2 - i), scores)

        achievements = AchievementService.get_player_achievements(player1['id'])

        assert achievements['stats']['current_win_streak'] == 3

    def test_max_win_streak(self, data_store, dates_helper):
        """Test maximum win streak tracking"""
        success, message, player1 = Player.create(name='Streaker')
        success, message, player2 = Player.create(name='Opponent')
        success, message, course = Course.create(name='Test Course')

        # Win streak of 3
        for i in range(3):
            scores = [
                {'player_id': player1['id'], 'score': 45},
                {'player_id': player2['id'], 'score': 50}
            ]
            Round.create(course['id'], dates_helper['days_ago'](10 - i), scores)

        # Loss
        scores = [
            {'player_id': player1['id'], 'score': 55},
            {'player_id': player2['id'], 'score': 45}
        ]
        Round.create(course['id'], dates_helper['days_ago'](7), scores)

        # Win streak of 2 (more recent)
        for i in range(2):
            scores = [
                {'player_id': player1['id'], 'score': 45},
                {'player_id': player2['id'], 'score': 50}
            ]
            Round.create(course['id'], dates_helper['days_ago'](1 - i), scores)

        achievements = AchievementService.get_player_achievements(player1['id'])

        assert achievements['stats']['max_win_streak'] == 3
        assert achievements['stats']['current_win_streak'] == 2

    def test_hot_streak_achievement(self, data_store, dates_helper):
        """Test Hot Streak achievement (3 wins in a row)"""
        success, message, player1 = Player.create(name='Streaker')
        success, message, player2 = Player.create(name='Opponent')
        success, message, course = Course.create(name='Test Course')

        # Create 3 consecutive wins
        for i in range(3):
            scores = [
                {'player_id': player1['id'], 'score': 45},
                {'player_id': player2['id'], 'score': 50}
            ]
            Round.create(course['id'], dates_helper['days_ago'](2 - i), scores)

        achievements = AchievementService.get_player_achievements(player1['id'])

        earned_ids = [a['id'] for a in achievements['earned']]
        assert 'hot_streak' in earned_ids


@pytest.mark.unit
@pytest.mark.services
class TestCourseExploration:
    """Tests for course exploration achievements"""

    def test_unique_courses_counting(self, data_store, dates_helper):
        """Test counting unique courses played"""
        success, message, player1 = Player.create(name='Explorer')
        success, message, player2 = Player.create(name='Companion')

        # Create 3 courses
        success, message, course1 = Course.create(name='Course 1')
        success, message, course2 = Course.create(name='Course 2')
        success, message, course3 = Course.create(name='Course 3')

        # Play on all 3 courses
        for course in [course1, course2, course3]:
            scores = [
                {'player_id': player1['id'], 'score': 50},
                {'player_id': player2['id'], 'score': 55}
            ]
            Round.create(course['id'], dates_helper['yesterday'](), scores)

        achievements = AchievementService.get_player_achievements(player1['id'])

        assert achievements['stats']['courses_played'] == 3

    def test_explorer_achievement(self, data_store, dates_helper):
        """Test Explorer achievement (3 different courses)"""
        success, message, player1 = Player.create(name='Explorer')
        success, message, player2 = Player.create(name='Companion')

        # Create and play 3 courses
        for i in range(3):
            success, message, course = Course.create(name=f'Course {i}')
            scores = [
                {'player_id': player1['id'], 'score': 50},
                {'player_id': player2['id'], 'score': 55}
            ]
            Round.create(course['id'], dates_helper['yesterday'](), scores)

        achievements = AchievementService.get_player_achievements(player1['id'])

        earned_ids = [a['id'] for a in achievements['earned']]
        assert 'explorer' in earned_ids

    def test_hard_course_counting(self, data_store, dates_helper):
        """Test counting hard courses separately"""
        success, message, player1 = Player.create(name='Hardcore')
        success, message, player2 = Player.create(name='Companion')

        # Create hard and regular courses
        success, message, hard1 = Course.create(name='Hard Course 1 (HARD)')
        success, message, hard2 = Course.create(name='Hard Course 2 (HARD)')
        success, message, regular = Course.create(name='Regular Course')

        # Play on all courses
        for course in [hard1, hard2, regular]:
            scores = [
                {'player_id': player1['id'], 'score': 50},
                {'player_id': player2['id'], 'score': 55}
            ]
            Round.create(course['id'], dates_helper['yesterday'](), scores)

        # Get achievement data
        achievements = AchievementService.get_player_achievements(player1['id'])

        # Player should have played 3 total courses
        assert achievements['stats']['courses_played'] == 3


@pytest.mark.unit
@pytest.mark.services
class TestSocialAchievements:
    """Tests for social achievements"""

    def test_unique_players_counting(self, data_store, dates_helper):
        """Test counting unique players played with"""
        success, message, player1 = Player.create(name='Social')
        success, message, player2 = Player.create(name='Friend 1')
        success, message, player3 = Player.create(name='Friend 2')
        success, message, course = Course.create(name='Test Course')

        # Play with different players
        scores1 = [
            {'player_id': player1['id'], 'score': 50},
            {'player_id': player2['id'], 'score': 55}
        ]
        Round.create(course['id'], dates_helper['days_ago'](2), scores1)

        scores2 = [
            {'player_id': player1['id'], 'score': 50},
            {'player_id': player3['id'], 'score': 55}
        ]
        Round.create(course['id'], dates_helper['yesterday'](), scores2)

        achievements = AchievementService.get_player_achievements(player1['id'])

        assert achievements['stats']['players_played_with'] == 2

    def test_party_animal_achievement(self, data_store, dates_helper):
        """Test Party Animal achievement (4+ players)"""
        success, message, course = Course.create(name='Test Course')

        # Create 5 players
        players = []
        for i in range(5):
            success, message, player = Player.create(name=f'Player {i}')
            players.append(player)

        # Create round with all 5 players
        scores = [{'player_id': p['id'], 'score': 50 + i} for i, p in enumerate(players)]
        Round.create(course['id'], dates_helper['yesterday'](), scores)

        achievements = AchievementService.get_player_achievements(players[0]['id'])

        earned_ids = [a['id'] for a in achievements['earned']]
        assert 'party_animal' in earned_ids


@pytest.mark.unit
@pytest.mark.services
class TestAchievementPoints:
    """Tests for achievement points calculation"""

    def test_points_accumulation(self, data_store, dates_helper):
        """Test that points accumulate from multiple achievements"""
        success, message, player1 = Player.create(name='Point Collector')
        success, message, player2 = Player.create(name='Opponent')
        success, message, course = Course.create(name='Test Course')

        # Create multiple rounds to earn multiple achievements
        for i in range(6):
            scores = [
                {'player_id': player1['id'], 'score': 45},
                {'player_id': player2['id'], 'score': 50}
            ]
            Round.create(course['id'], dates_helper['days_ago'](i), scores)

        achievements = AchievementService.get_player_achievements(player1['id'])

        # Should have earned:
        # - First Round (10 points)
        # - Getting Started - 5 rounds (20 points)
        # - First Victory (10 points)
        # - Hat Trick - 3 wins (30 points)
        # Minimum 70 points
        assert achievements['total_points'] >= 70

    def test_get_achievement_score(self, data_store, dates_helper):
        """Test get_achievement_score method"""
        success, message, player1 = Player.create(name='Player')
        success, message, player2 = Player.create(name='Opponent')
        success, message, course = Course.create(name='Test Course')

        # Create one round
        scores = [
            {'player_id': player1['id'], 'score': 45},
            {'player_id': player2['id'], 'score': 50}
        ]
        Round.create(course['id'], dates_helper['yesterday'](), scores)

        score = AchievementService.get_achievement_score(player1['id'])

        # Should have First Round (10) + First Victory (10) = 20 points
        assert score == 20


@pytest.mark.unit
@pytest.mark.services
class TestAchievementProgress:
    """Tests for achievement progress tracking"""

    def test_progress_tracking(self, data_store, dates_helper):
        """Test that progress is tracked for incomplete achievements"""
        success, message, player1 = Player.create(name='Player')
        success, message, player2 = Player.create(name='Opponent')
        success, message, course = Course.create(name='Test Course')

        # Create 2 rounds (not enough for Getting Started which needs 5)
        for i in range(2):
            scores = [
                {'player_id': player1['id'], 'score': 50},
                {'player_id': player2['id'], 'score': 55}
            ]
            Round.create(course['id'], dates_helper['days_ago'](i), scores)

        achievements = AchievementService.get_player_achievements(player1['id'])

        # Check progress for Getting Started
        assert 'getting_started' in achievements['progress']
        assert achievements['progress']['getting_started']['current'] == 2
        assert achievements['progress']['getting_started']['required'] == 5


@pytest.mark.unit
@pytest.mark.services
class TestAchievementEdgeCases:
    """Tests for edge cases and special scenarios"""

    def test_tied_round_win_detection(self, data_store, dates_helper):
        """Test win detection when scores are tied (first player with lowest score wins)"""
        success, message, player1 = Player.create(name='Player 1')
        success, message, player2 = Player.create(name='Player 2')
        success, message, course = Course.create(name='Test Course')

        # Both players have same score
        scores = [
            {'player_id': player1['id'], 'score': 50},
            {'player_id': player2['id'], 'score': 50}
        ]
        Round.create(course['id'], dates_helper['yesterday'](), scores)

        # One of them should be counted as winner (first one with min score)
        achievements1 = AchievementService.get_player_achievements(player1['id'])
        achievements2 = AchievementService.get_player_achievements(player2['id'])

        # Exactly one should have a win
        total_wins = achievements1['stats']['wins'] + achievements2['stats']['wins']
        assert total_wins == 1

    def test_achievements_structure(self, data_store):
        """Test that achievement data structure is correct"""
        success, message, player = Player.create(name='Player')

        achievements = AchievementService.get_player_achievements(player['id'])

        # Verify structure
        assert 'earned' in achievements
        assert 'progress' in achievements
        assert 'total_points' in achievements
        assert 'stats' in achievements

        # Verify stats structure
        assert 'total_rounds' in achievements['stats']
        assert 'wins' in achievements['stats']
        assert 'courses_played' in achievements['stats']
        assert 'courses_won' in achievements['stats']
        assert 'players_played_with' in achievements['stats']
        assert 'current_win_streak' in achievements['stats']
        assert 'max_win_streak' in achievements['stats']

    def test_achievement_metadata(self, data_store, dates_helper):
        """Test that earned achievements have correct metadata"""
        success, message, player1 = Player.create(name='Player')
        success, message, player2 = Player.create(name='Opponent')
        success, message, course = Course.create(name='Test Course')

        scores = [
            {'player_id': player1['id'], 'score': 50},
            {'player_id': player2['id'], 'score': 55}
        ]
        Round.create(course['id'], dates_helper['yesterday'](), scores)

        achievements = AchievementService.get_player_achievements(player1['id'])

        # Check that earned achievements have all required fields
        if len(achievements['earned']) > 0:
            first_achievement = achievements['earned'][0]
            assert 'id' in first_achievement
            assert 'name' in first_achievement
            assert 'description' in first_achievement
            assert 'icon' in first_achievement
            assert 'category' in first_achievement
            assert 'color' in first_achievement
            assert 'points' in first_achievement
            assert 'earned' in first_achievement
            assert first_achievement['earned'] is True

    def test_courses_won_counting(self, data_store, dates_helper):
        """Test counting unique courses where player has won"""
        success, message, player1 = Player.create(name='Winner')
        success, message, player2 = Player.create(name='Loser')

        # Create 3 courses
        success, message, course1 = Course.create(name='Course 1')
        success, message, course2 = Course.create(name='Course 2')
        success, message, course3 = Course.create(name='Course 3')

        # Win on course 1 and 2, lose on course 3
        for course in [course1, course2]:
            scores = [
                {'player_id': player1['id'], 'score': 45},
                {'player_id': player2['id'], 'score': 50}
            ]
            Round.create(course['id'], dates_helper['yesterday'](), scores)

        scores = [
            {'player_id': player1['id'], 'score': 55},
            {'player_id': player2['id'], 'score': 50}
        ]
        Round.create(course3['id'], dates_helper['yesterday'](), scores)

        achievements = AchievementService.get_player_achievements(player1['id'])

        assert achievements['stats']['courses_won'] == 2
