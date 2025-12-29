"""
Tests for ComparisonService

Tests head-to-head player comparison functionality.
"""
import pytest
from services.comparison_service import ComparisonService
from models.player import Player
from models.course import Course
from models.round import Round


class TestComparePlayers:
    """Test compare_players method"""

    def test_compare_two_players_with_matchups(self, app):
        """Test comparing two players who have played against each other"""
        # Create players
        _, _, player1 = Player.create('Alice', 'alice@test.com')
        _, _, player2 = Player.create('Bob', 'bob@test.com')

        # Create course
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Create head-to-head rounds
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30},  # Alice wins
            {'player_id': player2['id'], 'score': 40}
        ])
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player1['id'], 'score': 45},
            {'player_id': player2['id'], 'score': 35}   # Bob wins
        ])

        result = ComparisonService.compare_players(player1['id'], player2['id'])

        # Check structure
        assert 'player1_stats' in result
        assert 'player2_stats' in result
        assert 'head_to_head' in result
        assert 'overall_winner' in result

        # Check head-to-head
        assert result['head_to_head']['total_matchups'] == 2
        assert result['head_to_head']['player1_wins'] == 1
        assert result['head_to_head']['player2_wins'] == 1
        assert result['head_to_head']['ties'] == 0

        # Check stats
        assert result['player1_stats']['total_rounds'] == 2
        assert result['player2_stats']['total_rounds'] == 2

    def test_compare_players_no_matchups(self, app):
        """Test comparing two players who never played together"""
        # Create players
        _, _, player1 = Player.create('Alice', 'alice@test.com')
        _, _, player2 = Player.create('Bob', 'bob@test.com')
        _, _, player3 = Player.create('Charlie', 'charlie@test.com')

        # Create course
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Player1 plays with player3
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30},
            {'player_id': player3['id'], 'score': 40}
        ])
        # Player2 plays with player3
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player2['id'], 'score': 35},
            {'player_id': player3['id'], 'score': 45}
        ])

        result = ComparisonService.compare_players(player1['id'], player2['id'])

        # Check head-to-head
        assert result['head_to_head']['total_matchups'] == 0
        assert result['head_to_head']['player1_wins'] == 0
        assert result['head_to_head']['player2_wins'] == 0
        assert result['head_to_head']['ties'] == 0
        assert result['head_to_head']['matchups'] == []

        # Check both players still have stats
        assert result['player1_stats']['total_rounds'] == 1
        assert result['player2_stats']['total_rounds'] == 1

    def test_compare_players_one_sided_dominance(self, app):
        """Test when one player wins all matchups"""
        _, _, player1 = Player.create('Champion', 'champion@test.com')
        _, _, player2 = Player.create('Challenger', 'challenger@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Player1 wins all three matchups
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30},
            {'player_id': player2['id'], 'score': 40}
        ])
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player1['id'], 'score': 25},
            {'player_id': player2['id'], 'score': 35}
        ])
        Round.create(course['id'], '2024-01-03', [
            {'player_id': player1['id'], 'score': 28},
            {'player_id': player2['id'], 'score': 38}
        ])

        result = ComparisonService.compare_players(player1['id'], player2['id'])

        assert result['head_to_head']['total_matchups'] == 3
        assert result['head_to_head']['player1_wins'] == 3
        assert result['head_to_head']['player2_wins'] == 0
        assert result['overall_winner'] == player1['id']

    def test_compare_players_with_ties(self, app):
        """Test comparison with tied scores"""
        _, _, player1 = Player.create('Alice', 'alice@test.com')
        _, _, player2 = Player.create('Bob', 'bob@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Two ties and one win for each
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30},  # Tie
            {'player_id': player2['id'], 'score': 30}
        ])
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player1['id'], 'score': 35},  # Alice wins
            {'player_id': player2['id'], 'score': 40}
        ])
        Round.create(course['id'], '2024-01-03', [
            {'player_id': player1['id'], 'score': 40},  # Bob wins
            {'player_id': player2['id'], 'score': 35}
        ])
        Round.create(course['id'], '2024-01-04', [
            {'player_id': player1['id'], 'score': 50},  # Tie
            {'player_id': player2['id'], 'score': 50}
        ])

        result = ComparisonService.compare_players(player1['id'], player2['id'])

        assert result['head_to_head']['total_matchups'] == 4
        assert result['head_to_head']['player1_wins'] == 1
        assert result['head_to_head']['player2_wins'] == 1
        assert result['head_to_head']['ties'] == 2

    def test_compare_players_overall_winner_determination(self, app):
        """Test overall winner is determined by better average"""
        _, _, player1 = Player.create('Alice', 'alice@test.com')
        _, _, player2 = Player.create('Bob', 'bob@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Alice: average 30, Bob: average 40
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30},
            {'player_id': player2['id'], 'score': 40}
        ])

        result = ComparisonService.compare_players(player1['id'], player2['id'])

        assert result['overall_winner'] == player1['id']
        assert result['player1_stats']['average_score'] < result['player2_stats']['average_score']

    def test_compare_players_overall_winner_tie(self, app):
        """Test no overall winner when averages are equal"""
        _, _, player1 = Player.create('Alice', 'alice@test.com')
        _, _, player2 = Player.create('Bob', 'bob@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Both have same average: 35
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30},
            {'player_id': player2['id'], 'score': 40}
        ])
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player1['id'], 'score': 40},
            {'player_id': player2['id'], 'score': 30}
        ])

        result = ComparisonService.compare_players(player1['id'], player2['id'])

        assert result['overall_winner'] is None
        assert result['player1_stats']['average_score'] == result['player2_stats']['average_score']

    def test_compare_players_one_has_no_rounds(self, app):
        """Test comparing when one player has no rounds"""
        _, _, player1 = Player.create('Active', 'active@test.com')
        _, _, player2 = Player.create('Inactive', 'inactive@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Only player1 plays
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30}
        ])

        result = ComparisonService.compare_players(player1['id'], player2['id'])

        assert result['player1_stats']['total_rounds'] == 1
        assert result['player2_stats']['total_rounds'] == 0
        assert result['head_to_head']['total_matchups'] == 0
        assert result['overall_winner'] is None

    def test_compare_players_both_no_rounds(self, app):
        """Test comparing when both players have no rounds"""
        _, _, player1 = Player.create('Newbie1', 'newbie1@test.com')
        _, _, player2 = Player.create('Newbie2', 'newbie2@test.com')

        result = ComparisonService.compare_players(player1['id'], player2['id'])

        assert result['player1_stats']['total_rounds'] == 0
        assert result['player2_stats']['total_rounds'] == 0
        assert result['head_to_head']['total_matchups'] == 0
        assert result['overall_winner'] is None


class TestGetPlayerStats:
    """Test _get_player_stats method"""

    def test_get_player_stats_with_rounds(self, app):
        """Test getting stats for player with rounds"""
        _, _, player = Player.create('Alice', 'alice@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Create rounds
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player['id'], 'score': 30}
        ])
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player['id'], 'score': 40}
        ])

        all_rounds = Round.get_all()
        stats = ComparisonService._get_player_stats(player['id'], all_rounds)

        assert stats['total_rounds'] == 2
        assert stats['average_score'] == 35
        assert stats['best_score'] == 30
        assert stats['win_rate'] == 1.0  # Won both solo rounds

    def test_get_player_stats_no_rounds(self, app):
        """Test getting stats for player with no rounds"""
        _, _, player = Player.create('Newbie', 'newbie@test.com')

        all_rounds = Round.get_all()
        stats = ComparisonService._get_player_stats(player['id'], all_rounds)

        assert stats['total_rounds'] == 0
        assert stats['average_score'] == 0
        assert stats['best_score'] is None
        assert stats['win_rate'] == 0

    def test_get_player_stats_win_rate(self, app):
        """Test win rate calculation"""
        _, _, player1 = Player.create('Alice', 'alice@test.com')
        _, _, player2 = Player.create('Bob', 'bob@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Player1 wins 2 out of 3
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30},
            {'player_id': player2['id'], 'score': 40}
        ])
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player1['id'], 'score': 45},
            {'player_id': player2['id'], 'score': 35}
        ])
        Round.create(course['id'], '2024-01-03', [
            {'player_id': player1['id'], 'score': 25},
            {'player_id': player2['id'], 'score': 30}
        ])

        all_rounds = Round.get_all()
        stats = ComparisonService._get_player_stats(player1['id'], all_rounds)

        assert stats['total_rounds'] == 3
        assert abs(stats['win_rate'] - 2/3) < 0.01


class TestGetHeadToHead:
    """Test _get_head_to_head method"""

    def test_head_to_head_basic(self, app):
        """Test basic head-to-head functionality"""
        _, _, player1 = Player.create('Alice', 'alice@test.com')
        _, _, player2 = Player.create('Bob', 'bob@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30},
            {'player_id': player2['id'], 'score': 40}
        ])

        all_rounds = Round.get_all()
        h2h = ComparisonService._get_head_to_head(player1['id'], player2['id'], all_rounds)

        assert h2h['total_matchups'] == 1
        assert h2h['player1_wins'] == 1
        assert h2h['player2_wins'] == 0
        assert h2h['ties'] == 0
        assert len(h2h['matchups']) == 1
        assert h2h['matchups'][0]['player1_score'] == 30
        assert h2h['matchups'][0]['player2_score'] == 40
        assert h2h['matchups'][0]['winner'] == player1['id']

    def test_head_to_head_no_matchups(self, app):
        """Test head-to-head with no matchups"""
        _, _, player1 = Player.create('Alice', 'alice@test.com')
        _, _, player2 = Player.create('Bob', 'bob@test.com')

        all_rounds = Round.get_all()
        h2h = ComparisonService._get_head_to_head(player1['id'], player2['id'], all_rounds)

        assert h2h['total_matchups'] == 0
        assert h2h['player1_wins'] == 0
        assert h2h['player2_wins'] == 0
        assert h2h['ties'] == 0
        assert h2h['matchups'] == []

    def test_head_to_head_sorted_by_date(self, app):
        """Test matchups are sorted by date (newest first)"""
        _, _, player1 = Player.create('Alice', 'alice@test.com')
        _, _, player2 = Player.create('Bob', 'bob@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30},
            {'player_id': player2['id'], 'score': 40}
        ])
        Round.create(course['id'], '2024-01-03', [
            {'player_id': player1['id'], 'score': 25},
            {'player_id': player2['id'], 'score': 35}
        ])
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player1['id'], 'score': 28},
            {'player_id': player2['id'], 'score': 38}
        ])

        all_rounds = Round.get_all()
        h2h = ComparisonService._get_head_to_head(player1['id'], player2['id'], all_rounds)

        # Should be sorted newest first
        assert h2h['matchups'][0]['date'] == '2024-01-03'
        assert h2h['matchups'][1]['date'] == '2024-01-02'
        assert h2h['matchups'][2]['date'] == '2024-01-01'

    def test_head_to_head_with_other_players(self, app):
        """Test head-to-head excludes rounds with other players"""
        _, _, player1 = Player.create('Alice', 'alice@test.com')
        _, _, player2 = Player.create('Bob', 'bob@test.com')
        _, _, player3 = Player.create('Charlie', 'charlie@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Round with all three players - should be included
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 30},
            {'player_id': player2['id'], 'score': 40},
            {'player_id': player3['id'], 'score': 50}
        ])
        # Round with only player1 and player3 - should be excluded
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player1['id'], 'score': 25},
            {'player_id': player3['id'], 'score': 35}
        ])
        # Round with only player1 and player2 - should be included
        Round.create(course['id'], '2024-01-03', [
            {'player_id': player1['id'], 'score': 28},
            {'player_id': player2['id'], 'score': 38}
        ])

        all_rounds = Round.get_all()
        h2h = ComparisonService._get_head_to_head(player1['id'], player2['id'], all_rounds)

        assert h2h['total_matchups'] == 2
        assert len(h2h['matchups']) == 2

    def test_head_to_head_tie_winner_is_none(self, app):
        """Test that tied matchups have winner as None"""
        _, _, player1 = Player.create('Alice', 'alice@test.com')
        _, _, player2 = Player.create('Bob', 'bob@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        Round.create(course['id'], '2024-01-01', [
            {'player_id': player1['id'], 'score': 35},
            {'player_id': player2['id'], 'score': 35}
        ])

        all_rounds = Round.get_all()
        h2h = ComparisonService._get_head_to_head(player1['id'], player2['id'], all_rounds)

        assert h2h['ties'] == 1
        assert h2h['matchups'][0]['winner'] is None


class TestGetPlayerRounds:
    """Test _get_player_rounds method"""

    def test_get_player_rounds_basic(self, app):
        """Test getting player rounds"""
        _, _, player = Player.create('Alice', 'alice@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        Round.create(course['id'], '2024-01-01', [
            {'player_id': player['id'], 'score': 30}
        ])
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player['id'], 'score': 35}
        ])

        all_rounds = Round.get_all()
        player_rounds = ComparisonService._get_player_rounds(player['id'], all_rounds)

        assert len(player_rounds) == 2
        assert player_rounds[0]['date'] == '2024-01-01'
        assert player_rounds[0]['score'] == 30
        assert player_rounds[0]['course'] == 'Test Course'
        assert player_rounds[1]['date'] == '2024-01-02'
        assert player_rounds[1]['score'] == 35

    def test_get_player_rounds_sorted_by_date(self, app):
        """Test rounds are sorted by date (oldest first)"""
        _, _, player = Player.create('Alice', 'alice@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        Round.create(course['id'], '2024-01-03', [
            {'player_id': player['id'], 'score': 25}
        ])
        Round.create(course['id'], '2024-01-01', [
            {'player_id': player['id'], 'score': 30}
        ])
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player['id'], 'score': 35}
        ])

        all_rounds = Round.get_all()
        player_rounds = ComparisonService._get_player_rounds(player['id'], all_rounds)

        # Should be sorted oldest first for chart display
        assert player_rounds[0]['date'] == '2024-01-01'
        assert player_rounds[1]['date'] == '2024-01-02'
        assert player_rounds[2]['date'] == '2024-01-03'

    def test_get_player_rounds_no_rounds(self, app):
        """Test getting rounds for player with no rounds"""
        _, _, player = Player.create('Newbie', 'newbie@test.com')

        all_rounds = Round.get_all()
        player_rounds = ComparisonService._get_player_rounds(player['id'], all_rounds)

        assert player_rounds == []


class TestGetCourseBreakdown:
    """Test _get_course_breakdown method"""

    def test_course_breakdown_single_course(self, app):
        """Test course breakdown with one course"""
        _, _, player = Player.create('Alice', 'alice@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        Round.create(course['id'], '2024-01-01', [
            {'player_id': player['id'], 'score': 30}
        ])
        Round.create(course['id'], '2024-01-02', [
            {'player_id': player['id'], 'score': 40}
        ])

        all_rounds = Round.get_all()
        breakdown = ComparisonService._get_course_breakdown(player['id'], all_rounds)

        assert len(breakdown) == 1
        assert 'Test Course' in breakdown
        assert breakdown['Test Course'] == 35  # Average of 30 and 40

    def test_course_breakdown_multiple_courses(self, app):
        """Test course breakdown with multiple courses"""
        _, _, player = Player.create('Alice', 'alice@test.com')
        _, _, course1 = Course.create('Course A', 'Location', 18, 54)
        _, _, course2 = Course.create('Course B', 'Location', 18, 54)

        Round.create(course1['id'], '2024-01-01', [
            {'player_id': player['id'], 'score': 30}
        ])
        Round.create(course1['id'], '2024-01-02', [
            {'player_id': player['id'], 'score': 40}
        ])
        Round.create(course2['id'], '2024-01-03', [
            {'player_id': player['id'], 'score': 50}
        ])
        Round.create(course2['id'], '2024-01-04', [
            {'player_id': player['id'], 'score': 60}
        ])

        all_rounds = Round.get_all()
        breakdown = ComparisonService._get_course_breakdown(player['id'], all_rounds)

        assert len(breakdown) == 2
        assert breakdown['Course A'] == 35  # Average of 30, 40
        assert breakdown['Course B'] == 55  # Average of 50, 60

    def test_course_breakdown_no_rounds(self, app):
        """Test course breakdown for player with no rounds"""
        _, _, player = Player.create('Newbie', 'newbie@test.com')

        all_rounds = Round.get_all()
        breakdown = ComparisonService._get_course_breakdown(player['id'], all_rounds)

        assert breakdown == {}

    def test_course_breakdown_single_round_per_course(self, app):
        """Test course breakdown with one round per course"""
        _, _, player = Player.create('Alice', 'alice@test.com')
        _, _, course1 = Course.create('Course A', 'Location', 18, 54)
        _, _, course2 = Course.create('Course B', 'Location', 18, 54)

        Round.create(course1['id'], '2024-01-01', [
            {'player_id': player['id'], 'score': 42}
        ])
        Round.create(course2['id'], '2024-01-02', [
            {'player_id': player['id'], 'score': 68}
        ])

        all_rounds = Round.get_all()
        breakdown = ComparisonService._get_course_breakdown(player['id'], all_rounds)

        assert breakdown['Course A'] == 42
        assert breakdown['Course B'] == 68


class TestComparisonIntegration:
    """Integration tests for comparison functionality"""

    def test_full_comparison_scenario(self, app):
        """Test complete comparison scenario"""
        # Create players
        _, _, alice = Player.create('Alice', 'alice@test.com')
        _, _, bob = Player.create('Bob', 'bob@test.com')

        # Create courses
        _, _, course1 = Course.create('Pebble Beach', 'California', 18, 72)
        _, _, course2 = Course.create('Augusta National', 'Georgia', 18, 72)

        # Create various rounds
        # Head-to-head at Pebble Beach - Alice wins
        Round.create(course1['id'], '2024-01-01', [
            {'player_id': alice['id'], 'score': 70},
            {'player_id': bob['id'], 'score': 75}
        ])
        # Head-to-head at Augusta - Bob wins
        Round.create(course2['id'], '2024-01-05', [
            {'player_id': alice['id'], 'score': 80},
            {'player_id': bob['id'], 'score': 73}
        ])
        # Alice solo at Pebble Beach
        Round.create(course1['id'], '2024-01-10', [
            {'player_id': alice['id'], 'score': 68}
        ])
        # Bob solo at Augusta
        Round.create(course2['id'], '2024-01-15', [
            {'player_id': bob['id'], 'score': 71}
        ])

        result = ComparisonService.compare_players(alice['id'], bob['id'])

        # Verify head-to-head
        assert result['head_to_head']['total_matchups'] == 2
        assert result['head_to_head']['player1_wins'] == 1
        assert result['head_to_head']['player2_wins'] == 1

        # Verify overall stats
        assert result['player1_stats']['total_rounds'] == 3
        assert result['player2_stats']['total_rounds'] == 3

        # Verify course breakdowns
        assert len(result['player1_courses']) == 2
        assert len(result['player2_courses']) == 2
        assert result['player1_courses']['Pebble Beach'] == 69  # (70 + 68) / 2
        assert result['player2_courses']['Augusta National'] == 72  # (73 + 71) / 2

        # Verify round history
        assert len(result['player1_rounds']) == 3
        assert len(result['player2_rounds']) == 3
        assert result['player1_rounds'][0]['date'] == '2024-01-01'
        assert result['player1_rounds'][-1]['date'] == '2024-01-10'

    def test_asymmetric_comparison(self, app):
        """Test comparison where players have very different histories"""
        _, _, veteran = Player.create('Veteran', 'veteran@test.com')
        _, _, newbie = Player.create('Newbie', 'newbie@test.com')
        _, _, course = Course.create('Test Course', 'Location', 18, 54)

        # Veteran has many rounds
        for i in range(10):
            Round.create(course['id'], f'2024-01-{i+1:02d}', [
                {'player_id': veteran['id'], 'score': 30 + i}
            ])

        # Only one head-to-head where newbie wins
        Round.create(course['id'], '2024-01-20', [
            {'player_id': veteran['id'], 'score': 50},
            {'player_id': newbie['id'], 'score': 40}
        ])

        result = ComparisonService.compare_players(veteran['id'], newbie['id'])

        # Veteran has way more rounds
        assert result['player1_stats']['total_rounds'] == 11
        assert result['player2_stats']['total_rounds'] == 1

        # But newbie won the only matchup
        assert result['head_to_head']['total_matchups'] == 1
        assert result['head_to_head']['player1_wins'] == 0
        assert result['head_to_head']['player2_wins'] == 1

        # Veteran has better overall average
        assert result['overall_winner'] == veteran['id']
