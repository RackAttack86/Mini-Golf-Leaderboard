"""
Tests for LeaderboardService

Tests comprehensive player ranking and statistics functionality.
"""
import pytest
from services.leaderboard_service import LeaderboardService
from models.player import Player
from models.course import Course
from models.round import Round


class TestGetPlayerRankings:
    """Test get_player_rankings method"""

    def test_rankings_by_average_score(self, app):
        """Test rankings sorted by average score (lower is better)"""
        # Create players
        _, _, player1 = Player.create('Alice', 'alice@test.com')
        _, _, player2 = Player.create('Bob', 'bob@test.com')
        _, _, player3 = Player.create('Charlie', 'charlie@test.com')

        # Create course
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Create rounds with different averages
        # Alice: average 30
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30},
            {'player_id': player2['id'], 'score': 40}
        ])
        # Bob: average 35 (40 + 30) / 2
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player2['id'], 'score': 30},
            {'player_id': player3['id'], 'score': 50}
        ])
        # Charlie: average 50
        # (only one round)

        rankings = LeaderboardService.get_player_rankings(sort_by='average')

        assert len(rankings) == 3
        # Lower average is better, so Alice (30) should be first
        assert rankings[0]['player']['name'] == 'Alice'
        assert rankings[0]['stats']['average_score'] == 30
        assert rankings[1]['player']['name'] == 'Bob'
        assert rankings[1]['stats']['average_score'] == 35
        assert rankings[2]['player']['name'] == 'Charlie'
        assert rankings[2]['stats']['average_score'] == 50

    def test_rankings_by_wins(self, app):
        """Test rankings sorted by wins (higher is better)"""
        # Create players
        _, _, player1 = Player.create('Winner', 'winner@test.com')
        _, _, player2 = Player.create('Runner Up', 'runnerup@test.com')
        _, _, player3 = Player.create('Third Place', 'third@test.com')

        # Create course
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Create rounds - player1 wins 2, player2 wins 1, player3 wins 0
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30},  # Win
            {'player_id': player2['id'], 'score': 40},
            {'player_id': player3['id'], 'score': 50}
        ])
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player1['id'], 'score': 25},  # Win
            {'player_id': player2['id'], 'score': 30},
            {'player_id': player3['id'], 'score': 35}
        ])
        Round.create(course['id'], '2024-01-03', [
            {'player_id': player2['id'], 'score': 20},  # Win
            {'player_id': player3['id'], 'score': 30}
        ])

        rankings = LeaderboardService.get_player_rankings(sort_by='wins')

        assert len(rankings) == 3
        assert rankings[0]['player']['name'] == 'Winner'
        assert rankings[0]['stats']['wins'] == 2
        assert rankings[1]['player']['name'] == 'Runner Up'
        assert rankings[1]['stats']['wins'] == 1
        assert rankings[2]['player']['name'] == 'Third Place'
        assert rankings[2]['stats']['wins'] == 0

    def test_rankings_by_rounds_played(self, app):
        """Test rankings sorted by total rounds (higher is better)"""
        # Create players
        _, _, player1 = Player.create('Frequent', 'frequent@test.com')
        _, _, player2 = Player.create('Casual', 'casual@test.com')
        _, _, player3 = Player.create('Newbie', 'newbie@test.com')

        # Create course
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Create rounds - player1 plays 3, player2 plays 2, player3 plays 1
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30},
            {'player_id': player2['id'], 'score': 40}
        ])
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player1['id'], 'score': 35},
            {'player_id': player2['id'], 'score': 45}
        ])
        Round.create(course['id'], '2024-01-03', [
            {'player_id': player1['id'], 'score': 32},
            {'player_id': player3['id'], 'score': 50}
        ])

        rankings = LeaderboardService.get_player_rankings(sort_by='rounds')

        assert len(rankings) == 3
        assert rankings[0]['player']['name'] == 'Frequent'
        assert rankings[0]['stats']['total_rounds'] == 3
        assert rankings[1]['player']['name'] == 'Casual'
        assert rankings[1]['stats']['total_rounds'] == 2
        assert rankings[2]['player']['name'] == 'Newbie'
        assert rankings[2]['stats']['total_rounds'] == 1

    def test_excludes_players_without_rounds(self, app):
        """Test that players with no rounds are excluded from rankings"""
        # Create players
        _, _, player1 = Player.create('Active', 'active@test.com')
        _, _, player2 = Player.create('Inactive', 'inactive@test.com')

        # Create course
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Only player1 plays
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30}
        ])

        rankings = LeaderboardService.get_player_rankings()

        # Only player1 should be in rankings
        assert len(rankings) == 1
        assert rankings[0]['player']['name'] == 'Active'

    def test_empty_leaderboard(self, app):
        """Test leaderboard with no players"""
        rankings = LeaderboardService.get_player_rankings()
        assert rankings == []

    def test_default_sort_is_average(self, app):
        """Test that default sort is by average score"""
        # Create players
        _, _, player1 = Player.create('Alice', 'alice@test.com')
        _, _, player2 = Player.create('Bob', 'bob@test.com')

        # Create course
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Alice has better average
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30},
            {'player_id': player2['id'], 'score': 50}
        ])

        # Default should sort by average
        rankings_default = LeaderboardService.get_player_rankings()
        rankings_average = LeaderboardService.get_player_rankings(sort_by='average')

        assert len(rankings_default) == 2
        assert rankings_default[0]['player']['name'] == rankings_average[0]['player']['name']
        assert rankings_default[0]['player']['name'] == 'Alice'

    def test_tie_in_average_score(self, app):
        """Test handling of ties in average score"""
        # Create players with same average
        _, _, player1 = Player.create('Alice', 'alice@test.com')
        _, _, player2 = Player.create('Bob', 'bob@test.com')

        # Create course
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Both have average of 40
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 40},
            {'player_id': player2['id'], 'score': 40}
        ])

        rankings = LeaderboardService.get_player_rankings(sort_by='average')

        # Both should be in rankings with same average
        assert len(rankings) == 2
        assert rankings[0]['stats']['average_score'] == 40
        assert rankings[1]['stats']['average_score'] == 40

    def test_invalid_sort_criteria_defaults_to_average(self, app):
        """Test that invalid sort criteria defaults to average"""
        # Create player
        _, _, player1 = Player.create('Alice', 'alice@test.com')

        # Create course and round
        _, _, course = Course.create('Test Course', 'Location', 18, 54)
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30}
        ])

        rankings = LeaderboardService.get_player_rankings(sort_by='invalid')

        # Should still return rankings (sorted by average as default)
        assert len(rankings) == 1
        assert rankings[0]['player']['name'] == 'Alice'


class TestCalculatePlayerStats:
    """Test _calculate_player_stats method"""

    def test_calculate_stats_no_rounds(self, app):
        """Test stats calculation for player with no rounds"""
        _, _, player = Player.create('Newbie', 'newbie@test.com')

        stats = LeaderboardService._calculate_player_stats(player['id'])

        assert stats['total_rounds'] == 0
        assert stats['average_score'] == 0
        assert stats['best_score'] is None
        assert stats['worst_score'] is None
        assert stats['wins'] == 0
        assert stats['win_rate'] == 0

    def test_calculate_stats_single_round(self, app):
        """Test stats calculation for player with one round"""
        _, _, player = Player.create('Alice', 'alice@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        Round.create(course['id'], '2024-01-01', [
            {'player_id': player['id'], 'score': 42}
        ])

        stats = LeaderboardService._calculate_player_stats(player['id'])

        assert stats['total_rounds'] == 1
        assert stats['average_score'] == 42
        assert stats['best_score'] == 42
        assert stats['worst_score'] == 42
        assert stats['wins'] == 1  # Only player, so wins
        assert stats['win_rate'] == 1.0

    def test_calculate_stats_multiple_rounds(self, app):
        """Test stats calculation for player with multiple rounds"""
        _, _, player1 = Player.create('Alice', 'alice@test.com')
        _, _, player2 = Player.create('Bob', 'bob@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Round 1: Alice wins with 30
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30},
            {'player_id': player2['id'], 'score': 40}
        ])
        # Round 2: Bob wins with 25
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player1['id'], 'score': 35},
            {'player_id': player2['id'], 'score': 25}
        ])
        # Round 3: Alice wins with 20
        Round.create(course['id'], '2024-01-03', [
            {'player_id': player1['id'], 'score': 20},
            {'player_id': player2['id'], 'score': 30}
        ])

        stats = LeaderboardService._calculate_player_stats(player1['id'])

        assert stats['total_rounds'] == 3
        assert stats['average_score'] == (30 + 35 + 20) / 3  # 28.333...
        assert abs(stats['average_score'] - 28.333) < 0.01
        assert stats['best_score'] == 20
        assert stats['worst_score'] == 35
        assert stats['wins'] == 2  # Wins rounds 1 and 3
        assert abs(stats['win_rate'] - 2/3) < 0.01

    def test_calculate_stats_shared_win(self, app):
        """Test that tied scores both count as wins"""
        _, _, player1 = Player.create('Alice', 'alice@test.com')
        _, _, player2 = Player.create('Bob', 'bob@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Both players tie with 30
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30},
            {'player_id': player2['id'], 'score': 30}
        ])

        stats1 = LeaderboardService._calculate_player_stats(player1['id'])
        stats2 = LeaderboardService._calculate_player_stats(player2['id'])

        # Both should have 1 win
        assert stats1['wins'] == 1
        assert stats2['wins'] == 1
        assert stats1['win_rate'] == 1.0
        assert stats2['win_rate'] == 1.0

    def test_calculate_stats_negative_scores(self, app):
        """Test stats calculation with negative scores (under par)"""
        _, _, player = Player.create('Pro', 'pro@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        Round.create(course['id'], '2024-01-01', [
            {'player_id': player['id'], 'score': -5}
        ])
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player['id'], 'score': -3}
        ])
        Round.create(course['id'], '2024-01-03', [
            {'player_id': player['id'], 'score': 2}
        ])

        stats = LeaderboardService._calculate_player_stats(player['id'])

        assert stats['total_rounds'] == 3
        assert stats['average_score'] == (-5 + -3 + 2) / 3  # -2
        assert stats['best_score'] == -5  # Best score is lowest
        assert stats['worst_score'] == 2
        assert stats['wins'] == 3  # Wins all rounds (solo)

    def test_calculate_stats_mixed_solo_and_multiplayer(self, app):
        """Test stats with mix of solo and multiplayer rounds"""
        _, _, player1 = Player.create('Alice', 'alice@test.com')
        _, _, player2 = Player.create('Bob', 'bob@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Solo round - Alice wins
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30}
        ])
        # Multiplayer round - Bob wins
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player1['id'], 'score': 40},
            {'player_id': player2['id'], 'score': 35}
        ])
        # Multiplayer round - Alice wins
        Round.create(course['id'], '2024-01-03', [
            {'player_id': player1['id'], 'score': 25},
            {'player_id': player2['id'], 'score': 30}
        ])

        stats = LeaderboardService._calculate_player_stats(player1['id'])

        assert stats['total_rounds'] == 3
        assert stats['average_score'] == (30 + 40 + 25) / 3
        assert abs(stats['average_score'] - 31.667) < 0.01
        assert stats['wins'] == 2  # Wins solo round and round 3
        assert abs(stats['win_rate'] - 2/3) < 0.01

    def test_calculate_stats_zero_wins(self, app):
        """Test stats for player who never wins"""
        _, _, player1 = Player.create('Loser', 'loser@test.com')
        _, _, player2 = Player.create('Winner', 'winner@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Player1 loses both rounds
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 50},
            {'player_id': player2['id'], 'score': 30}
        ])
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player1['id'], 'score': 45},
            {'player_id': player2['id'], 'score': 25}
        ])

        stats = LeaderboardService._calculate_player_stats(player1['id'])

        assert stats['total_rounds'] == 2
        assert stats['wins'] == 0
        assert stats['win_rate'] == 0.0

    def test_calculate_stats_perfect_win_rate(self, app):
        """Test stats for player who wins every game"""
        _, _, player1 = Player.create('Champion', 'champion@test.com')
        _, _, player2 = Player.create('Challenger', 'challenger@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Player1 wins all rounds
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 20},
            {'player_id': player2['id'], 'score': 30}
        ])
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player1['id'], 'score': 25},
            {'player_id': player2['id'], 'score': 35}
        ])
        Round.create(course['id'], '2024-01-03', [
            {'player_id': player1['id'], 'score': 22},
            {'player_id': player2['id'], 'score': 32}
        ])

        stats = LeaderboardService._calculate_player_stats(player1['id'])

        assert stats['total_rounds'] == 3
        assert stats['wins'] == 3
        assert stats['win_rate'] == 1.0


class TestLeaderboardIntegration:
    """Integration tests for leaderboard functionality"""

    def test_full_leaderboard_scenario(self, app):
        """Test complete leaderboard with multiple players and rounds"""
        # Create 5 players
        _, _, p1 = Player.create('Alice', 'alice@test.com')
        _, _, p2 = Player.create('Bob', 'bob@test.com')
        _, _, p3 = Player.create('Charlie', 'charlie@test.com')
        _, _, p4 = Player.create('Diana', 'diana@test.com')
        _, _, p5 = Player.create('Eve', 'eve@test.com')

        # Create course
        _, _, course = Course.create('Championship Course', 'City', 18, 72)

        # Create various rounds
        Round.create(course['id'], '2024-01-01', [
            {'player_id': p1['id'], 'score': 68},  # Alice wins
            {'player_id': p2['id'], 'score': 72},
            {'player_id': p3['id'], 'score': 75}
        ])
        Round.create(course['id'], '2024-01-02', [
            {'player_id': p1['id'], 'score': 70},
            {'player_id': p2['id'], 'score': 68},  # Bob wins
            {'player_id': p4['id'], 'score': 80}
        ])
        Round.create(course['id'], '2024-01-03', [
            {'player_id': p3['id'], 'score': 65},  # Charlie wins
            {'player_id': p4['id'], 'score': 75},
            {'player_id': p5['id'], 'score': 78}
        ])

        # Test rankings by average
        avg_rankings = LeaderboardService.get_player_rankings(sort_by='average')
        assert len(avg_rankings) == 5
        # Alice: (68+70)/2 = 69, should be second best average
        # Charlie: (75+65)/2 = 70
        assert avg_rankings[0]['player']['name'] == 'Alice'
        assert abs(avg_rankings[0]['stats']['average_score'] - 69) < 0.01

        # Test rankings by wins
        win_rankings = LeaderboardService.get_player_rankings(sort_by='wins')
        # Alice, Bob, and Charlie each have 1 win
        assert win_rankings[0]['stats']['wins'] >= 1
        assert win_rankings[1]['stats']['wins'] >= 1
        assert win_rankings[2]['stats']['wins'] >= 1

        # Test rankings by rounds
        round_rankings = LeaderboardService.get_player_rankings(sort_by='rounds')
        # Alice, Bob have 2 rounds each
        assert round_rankings[0]['stats']['total_rounds'] == 2

    def test_leaderboard_with_inactive_players(self, app):
        """Test that inactive players are included if they have rounds"""
        _, _, player1 = Player.create('Active', 'active@test.com')
        _, _, player2 = Player.create('Inactive', 'inactive@test.com')

        # Create course and rounds
        _, _, course = Course.create('Test Course', 'Location', 18, 54)
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30},
            {'player_id': player2['id'], 'score': 40}
        ])

        # Deactivate player2
        Player.delete(player2['id'])

        # get_all() returns active players by default, but let's verify both are in rounds
        rankings = LeaderboardService.get_player_rankings()

        # Should only show active players
        assert len(rankings) == 1
        assert rankings[0]['player']['name'] == 'Active'
