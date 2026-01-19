"""
Comprehensive unit tests for the Round model.

Tests cover:
- Round creation with valid and invalid data
- Round retrieval (all, by ID, by player, by course, with filters)
- Round updates
- Round deletion
- Score validation
- Duplicate player detection
- Denormalized data handling
- Edge cases and error handling
"""
import pytest
from datetime import datetime, timedelta

from models.round import Round
from models.player import Player
from models.course import Course


@pytest.mark.unit
@pytest.mark.models
class TestRoundCreate:
    """Tests for Round.create() method"""

    def test_create_round_minimal(self, populated_data_store, dates_helper):
        """Test creating a round with minimal data"""
        scores = [
            {'player_id': 'test-player-1', 'score': 50},
            {'player_id': 'test-player-2', 'score': 52}
        ]

        success, message, round_data = Round.create(
            course_id='test-course-1',
            date_played=dates_helper['yesterday'](),
            scores=scores
        )

        assert success is True
        assert message == "Round created successfully"
        assert round_data is not None
        assert round_data['course_id'] == 'test-course-1'
        assert round_data['course_name'] == 'Sunset Golf'
        assert len(round_data['scores']) == 2
        assert round_data['notes'] == ''
        assert 'id' in round_data
        assert 'timestamp' in round_data

    def test_create_round_with_notes(self, populated_data_store, dates_helper):
        """Test creating a round with notes"""
        scores = [
            {'player_id': 'test-player-1', 'score': 50}
        ]

        success, message, round_data = Round.create(
            course_id='test-course-1',
            date_played=dates_helper['yesterday'](),
            scores=scores,
            notes='Great game today!'
        )

        assert success is True
        assert round_data['notes'] == 'Great game today!'

    def test_create_round_denormalized_data(self, populated_data_store, dates_helper):
        """Test that player and course names are denormalized"""
        scores = [
            {'player_id': 'test-player-1', 'score': 50}
        ]

        success, message, round_data = Round.create(
            course_id='test-course-1',
            date_played=dates_helper['yesterday'](),
            scores=scores
        )

        assert success is True
        assert round_data['course_name'] == 'Sunset Golf'
        assert round_data['scores'][0]['player_name'] == 'John Doe'

    def test_create_round_invalid_date(self, populated_data_store):
        """Test creating round with invalid date fails"""
        scores = [{'player_id': 'test-player-1', 'score': 50}]

        success, message, round_data = Round.create(
            course_id='test-course-1',
            date_played='invalid-date',
            scores=scores
        )

        assert success is False
        assert "invalid date" in message.lower()
        assert round_data is None

    def test_create_round_future_date(self, populated_data_store, dates_helper):
        """Test creating round with future date fails"""
        scores = [{'player_id': 'test-player-1', 'score': 50}]

        success, message, round_data = Round.create(
            course_id='test-course-1',
            date_played=dates_helper['next_week'](),
            scores=scores
        )

        assert success is False
        assert "cannot be in the future" in message.lower()
        assert round_data is None

    def test_create_round_nonexistent_course(self, populated_data_store, dates_helper):
        """Test creating round with nonexistent course fails"""
        scores = [{'player_id': 'test-player-1', 'score': 50}]

        success, message, round_data = Round.create(
            course_id='nonexistent-course',
            date_played=dates_helper['yesterday'](),
            scores=scores
        )

        assert success is False
        assert "course not found" in message.lower()
        assert round_data is None

    def test_create_round_no_scores(self, populated_data_store, dates_helper):
        """Test creating round with no scores fails"""
        success, message, round_data = Round.create(
            course_id='test-course-1',
            date_played=dates_helper['yesterday'](),
            scores=[]
        )

        assert success is False
        assert "at least one player" in message.lower()
        assert round_data is None

    def test_create_round_nonexistent_player(self, populated_data_store, dates_helper):
        """Test creating round with nonexistent player fails"""
        scores = [{'player_id': 'nonexistent-player', 'score': 50}]

        success, message, round_data = Round.create(
            course_id='test-course-1',
            date_played=dates_helper['yesterday'](),
            scores=scores
        )

        assert success is False
        assert "player not found" in message.lower()
        assert round_data is None

    def test_create_round_duplicate_player(self, populated_data_store, dates_helper):
        """Test creating round with duplicate player fails"""
        scores = [
            {'player_id': 'test-player-1', 'score': 50},
            {'player_id': 'test-player-1', 'score': 52}
        ]

        success, message, round_data = Round.create(
            course_id='test-course-1',
            date_played=dates_helper['yesterday'](),
            scores=scores
        )

        assert success is False
        assert "duplicate player" in message.lower()
        assert round_data is None

    def test_create_round_invalid_score(self, populated_data_store, dates_helper):
        """Test creating round with invalid score fails"""
        scores = [{'player_id': 'test-player-1', 'score': 'abc'}]

        success, message, round_data = Round.create(
            course_id='test-course-1',
            date_played=dates_helper['yesterday'](),
            scores=scores
        )

        assert success is False
        assert "invalid score" in message.lower()
        assert round_data is None

    def test_create_round_score_too_low(self, populated_data_store, dates_helper):
        """Test creating round with unreasonably low score fails"""
        scores = [{'player_id': 'test-player-1', 'score': -100}]

        success, message, round_data = Round.create(
            course_id='test-course-1',
            date_played=dates_helper['yesterday'](),
            scores=scores
        )

        assert success is False
        assert round_data is None

    def test_create_round_score_too_high(self, populated_data_store, dates_helper):
        """Test creating round with unreasonably high score fails"""
        scores = [{'player_id': 'test-player-1', 'score': 600}]

        success, message, round_data = Round.create(
            course_id='test-course-1',
            date_played=dates_helper['yesterday'](),
            scores=scores
        )

        assert success is False
        assert round_data is None

    def test_create_round_multiple_players(self, populated_data_store, dates_helper):
        """Test creating round with multiple players"""
        scores = [
            {'player_id': 'test-player-1', 'score': 50},
            {'player_id': 'test-player-2', 'score': 52}
        ]

        success, message, round_data = Round.create(
            course_id='test-course-1',
            date_played=dates_helper['yesterday'](),
            scores=scores
        )

        assert success is True
        assert len(round_data['scores']) == 2

    def test_create_round_negative_score(self, populated_data_store, dates_helper):
        """Test creating round with negative score (relative to par)"""
        scores = [{'player_id': 'test-player-1', 'score': -5}]

        success, message, round_data = Round.create(
            course_id='test-course-1',
            date_played=dates_helper['yesterday'](),
            scores=scores
        )

        assert success is True
        assert round_data['scores'][0]['score'] == -5


@pytest.mark.unit
@pytest.mark.models
class TestRoundRetrieval:
    """Tests for Round retrieval methods"""

    def test_get_all_empty(self, data_store):
        """Test getting all rounds when none exist"""
        rounds = Round.get_all()

        assert rounds == []

    def test_get_all_rounds(self, populated_data_store):
        """Test getting all rounds"""
        rounds = Round.get_all()

        assert len(rounds) >= 1

    def test_get_by_id_existing(self, populated_data_store):
        """Test getting round by ID when it exists"""
        round_data = Round.get_by_id('test-round-1')

        assert round_data is not None
        assert round_data['id'] == 'test-round-1'

    def test_get_by_id_nonexistent(self, data_store):
        """Test getting round by ID when it doesn't exist"""
        round_data = Round.get_by_id('nonexistent-id')

        assert round_data is None

    def test_get_by_player(self, populated_data_store):
        """Test getting rounds by player"""
        rounds = Round.get_by_player('test-player-1')

        assert len(rounds) >= 1
        for round_data in rounds:
            player_ids = [s['player_id'] for s in round_data['scores']]
            assert 'test-player-1' in player_ids

    def test_get_by_course(self, populated_data_store):
        """Test getting rounds by course"""
        rounds = Round.get_by_course('test-course-1')

        assert len(rounds) >= 1
        for round_data in rounds:
            assert round_data['course_id'] == 'test-course-1'

    def test_get_all_with_player_filter(self, populated_data_store):
        """Test getting rounds filtered by player"""
        filters = {'player_id': 'test-player-1'}
        rounds = Round.get_all(filters=filters)

        assert len(rounds) >= 1
        for round_data in rounds:
            player_ids = [s['player_id'] for s in round_data['scores']]
            assert 'test-player-1' in player_ids

    def test_get_all_with_course_filter(self, populated_data_store):
        """Test getting rounds filtered by course"""
        filters = {'course_id': 'test-course-1'}
        rounds = Round.get_all(filters=filters)

        assert len(rounds) >= 1
        for round_data in rounds:
            assert round_data['course_id'] == 'test-course-1'

    def test_get_all_with_date_range_filter(self, populated_data_store):
        """Test getting rounds filtered by date range"""
        filters = {
            'start_date': '2024-01-01',
            'end_date': '2024-12-31'
        }
        rounds = Round.get_all(filters=filters)

        for round_data in rounds:
            assert round_data['date_played'] >= '2024-01-01'
            assert round_data['date_played'] <= '2024-12-31'

    def test_get_all_sorted_by_date(self, populated_data_store, dates_helper):
        """Test that rounds are sorted by date (newest first)"""
        # Create rounds on different dates
        scores = [{'player_id': 'test-player-1', 'score': 50}]

        Round.create('test-course-1', dates_helper['days_ago'](10), scores)
        Round.create('test-course-1', dates_helper['days_ago'](5), scores)
        Round.create('test-course-1', dates_helper['yesterday'](), scores)

        rounds = Round.get_all()

        # Verify sorting (newest first)
        for i in range(len(rounds) - 1):
            assert rounds[i]['date_played'] >= rounds[i + 1]['date_played']


@pytest.mark.unit
@pytest.mark.models
class TestRoundUpdate:
    """Tests for Round.update() method"""

    def test_update_round_course(self, populated_data_store, dates_helper):
        """Test updating round course"""
        scores = [{'player_id': 'test-player-1', 'score': 50}]

        success, message = Round.update(
            'test-round-1',
            course_id='test-course-2',
            date_played=dates_helper['yesterday'](),
            scores=scores
        )

        assert success is True
        round_data = Round.get_by_id('test-round-1')
        assert round_data['course_id'] == 'test-course-2'
        assert round_data['course_name'] == 'Mountain Course (HARD)'

    def test_update_round_date(self, populated_data_store):
        """Test updating round date"""
        scores = [{'player_id': 'test-player-1', 'score': 50}]

        success, message = Round.update(
            'test-round-1',
            course_id='test-course-1',
            date_played='2024-02-01',
            scores=scores
        )

        assert success is True
        round_data = Round.get_by_id('test-round-1')
        assert round_data['date_played'] == '2024-02-01'

    def test_update_round_scores(self, populated_data_store, dates_helper):
        """Test updating round scores"""
        new_scores = [
            {'player_id': 'test-player-1', 'score': 45},
            {'player_id': 'test-player-2', 'score': 48}
        ]

        success, message = Round.update(
            'test-round-1',
            course_id='test-course-1',
            date_played=dates_helper['yesterday'](),
            scores=new_scores
        )

        assert success is True
        round_data = Round.get_by_id('test-round-1')
        assert round_data['scores'][0]['score'] == 45
        assert round_data['scores'][1]['score'] == 48

    def test_update_round_notes(self, populated_data_store, dates_helper):
        """Test updating round notes"""
        scores = [{'player_id': 'test-player-1', 'score': 50}]

        success, message = Round.update(
            'test-round-1',
            course_id='test-course-1',
            date_played=dates_helper['yesterday'](),
            scores=scores,
            notes='Updated notes'
        )

        assert success is True
        round_data = Round.get_by_id('test-round-1')
        assert round_data['notes'] == 'Updated notes'

    def test_update_nonexistent_round(self, populated_data_store, dates_helper):
        """Test updating nonexistent round fails"""
        scores = [{'player_id': 'test-player-1', 'score': 50}]

        success, message = Round.update(
            'nonexistent-id',
            course_id='test-course-1',
            date_played=dates_helper['yesterday'](),
            scores=scores
        )

        assert success is False
        assert "not found" in message.lower()

    def test_update_round_invalid_date(self, populated_data_store):
        """Test updating round with invalid date fails"""
        scores = [{'player_id': 'test-player-1', 'score': 50}]

        success, message = Round.update(
            'test-round-1',
            course_id='test-course-1',
            date_played='invalid-date',
            scores=scores
        )

        assert success is False
        assert "invalid date" in message.lower()

    def test_update_round_nonexistent_course(self, populated_data_store, dates_helper):
        """Test updating round with nonexistent course fails"""
        scores = [{'player_id': 'test-player-1', 'score': 50}]

        success, message = Round.update(
            'test-round-1',
            course_id='nonexistent-course',
            date_played=dates_helper['yesterday'](),
            scores=scores
        )

        assert success is False
        assert "course not found" in message.lower()

    def test_update_round_no_scores(self, populated_data_store, dates_helper):
        """Test updating round with no scores fails"""
        success, message = Round.update(
            'test-round-1',
            course_id='test-course-1',
            date_played=dates_helper['yesterday'](),
            scores=[]
        )

        assert success is False
        assert "at least one player" in message.lower()


@pytest.mark.unit
@pytest.mark.models
class TestRoundDelete:
    """Tests for Round.delete() method"""

    def test_delete_round(self, populated_data_store):
        """Test deleting a round"""
        success, message = Round.delete('test-round-1')

        assert success is True
        assert "deleted successfully" in message.lower()
        assert Round.get_by_id('test-round-1') is None

    def test_delete_nonexistent_round(self, data_store):
        """Test deleting nonexistent round fails"""
        success, message = Round.delete('nonexistent-id')

        assert success is False
        assert "not found" in message.lower()


@pytest.mark.unit
@pytest.mark.models
class TestRoundPlayerScore:
    """Tests for Round.get_player_score_in_round() method"""

    def test_get_player_score_existing(self, populated_data_store):
        """Test getting player score when player is in round"""
        round_data = Round.get_by_id('test-round-1')
        score = Round.get_player_score_in_round(round_data, 'test-player-1')

        assert score is not None
        assert score == 50

    def test_get_player_score_nonexistent(self, populated_data_store):
        """Test getting player score when player is not in round"""
        round_data = Round.get_by_id('test-round-1')
        score = Round.get_player_score_in_round(round_data, 'nonexistent-player')

        assert score is None


@pytest.mark.unit
@pytest.mark.models
class TestRoundEdgeCases:
    """Tests for edge cases and special scenarios"""

    def test_create_round_single_player(self, populated_data_store, dates_helper):
        """Test creating round with single player (solo round)"""
        scores = [{'player_id': 'test-player-1', 'score': 50}]

        success, message, round_data = Round.create(
            course_id='test-course-1',
            date_played=dates_helper['yesterday'](),
            scores=scores
        )

        assert success is True
        assert len(round_data['scores']) == 1

    def test_create_round_many_players(self, data_store, dates_helper):
        """Test creating round with many players"""
        # Create multiple players
        player_ids = []
        for i in range(10):
            success, message, player = Player.create(name=f'Player {i}')
            player_ids.append(player['id'])

        # Create a course
        success, message, course = Course.create(name='Test Course')

        # Create round with all players
        scores = [{'player_id': pid, 'score': 50 + i} for i, pid in enumerate(player_ids)]

        success, message, round_data = Round.create(
            course_id=course['id'],
            date_played=dates_helper['yesterday'](),
            scores=scores
        )

        assert success is True
        assert len(round_data['scores']) == 10

    def test_round_timestamp_format(self, populated_data_store, dates_helper):
        """Test that timestamp is in correct format"""
        scores = [{'player_id': 'test-player-1', 'score': 50}]

        success, message, round_data = Round.create(
            course_id='test-course-1',
            date_played=dates_helper['yesterday'](),
            scores=scores
        )

        assert success is True
        # Verify ISO 8601 format
        timestamp = datetime.strptime(
            round_data['timestamp'],
            '%Y-%m-%dT%H:%M:%SZ'
        )
        assert timestamp is not None

    def test_round_id_is_uuid(self, populated_data_store, dates_helper):
        """Test that round ID is a valid UUID"""
        scores = [{'player_id': 'test-player-1', 'score': 50}]

        success, message, round_data = Round.create(
            course_id='test-course-1',
            date_played=dates_helper['yesterday'](),
            scores=scores
        )

        assert success is True
        # UUID format: 8-4-4-4-12 characters
        parts = round_data['id'].split('-')
        assert len(parts) == 5

    def test_scores_converted_to_int(self, populated_data_store, dates_helper):
        """Test that scores are converted to integers"""
        scores = [{'player_id': 'test-player-1', 'score': '50'}]

        success, message, round_data = Round.create(
            course_id='test-course-1',
            date_played=dates_helper['yesterday'](),
            scores=scores
        )

        assert success is True
        assert isinstance(round_data['scores'][0]['score'], int)

    def test_notes_stripped(self, populated_data_store, dates_helper):
        """Test that notes are stripped of whitespace"""
        scores = [{'player_id': 'test-player-1', 'score': 50}]

        success, message, round_data = Round.create(
            course_id='test-course-1',
            date_played=dates_helper['yesterday'](),
            scores=scores,
            notes='  Test notes  '
        )

        assert success is True
        assert round_data['notes'] == 'Test notes'

    def test_filter_combinations(self, populated_data_store, dates_helper):
        """Test multiple filter combinations"""
        filters = {
            'player_id': 'test-player-1',
            'course_id': 'test-course-1',
            'start_date': '2024-01-01',
            'end_date': '2024-12-31'
        }
        rounds = Round.get_all(filters=filters)

        for round_data in rounds:
            assert round_data['course_id'] == 'test-course-1'
            player_ids = [s['player_id'] for s in round_data['scores']]
            assert 'test-player-1' in player_ids
            assert '2024-01-01' <= round_data['date_played'] <= '2024-12-31'


@pytest.mark.unit
@pytest.mark.models
class TestRoundDuplicateDetection:
    """Tests for duplicate round detection"""

    def test_reject_exact_duplicate_round(self, populated_data_store, dates_helper):
        """Test that exact duplicate round is rejected"""
        date = dates_helper['yesterday']()
        scores = [
            {'player_id': 'test-player-1', 'score': 45},
            {'player_id': 'test-player-2', 'score': 50}
        ]

        # First round succeeds
        success1, msg1, round1 = Round.create('test-course-1', date, scores)
        assert success1 is True

        # Same round again should fail
        success2, msg2, round2 = Round.create('test-course-1', date, scores)
        assert success2 is False
        assert "duplicate" in msg2.lower()
        assert round2 is None

    def test_reject_duplicate_with_different_player_order(self, populated_data_store, dates_helper):
        """Test that duplicate with players in different order is rejected"""
        date = dates_helper['yesterday']()

        # First round: player-1 first
        scores1 = [
            {'player_id': 'test-player-1', 'score': 45},
            {'player_id': 'test-player-2', 'score': 50}
        ]
        success1, _, _ = Round.create('test-course-1', date, scores1)
        assert success1 is True

        # Second round: player-2 first (same data, different order)
        scores2 = [
            {'player_id': 'test-player-2', 'score': 50},
            {'player_id': 'test-player-1', 'score': 45}
        ]
        success2, msg2, _ = Round.create('test-course-1', date, scores2)
        assert success2 is False
        assert "duplicate" in msg2.lower()

    def test_allow_same_players_different_scores(self, populated_data_store, dates_helper):
        """Test that same players with different scores is allowed"""
        date = dates_helper['yesterday']()

        scores1 = [
            {'player_id': 'test-player-1', 'score': 45},
            {'player_id': 'test-player-2', 'score': 50}
        ]
        success1, _, _ = Round.create('test-course-1', date, scores1)
        assert success1 is True

        # Same players, different scores
        scores2 = [
            {'player_id': 'test-player-1', 'score': 48},
            {'player_id': 'test-player-2', 'score': 52}
        ]
        success2, _, round2 = Round.create('test-course-1', date, scores2)
        assert success2 is True
        assert round2 is not None

    def test_allow_same_scores_different_date(self, populated_data_store, dates_helper):
        """Test that same round on different date is allowed"""
        scores = [
            {'player_id': 'test-player-1', 'score': 45},
            {'player_id': 'test-player-2', 'score': 50}
        ]

        # Day 1
        success1, _, _ = Round.create('test-course-1', dates_helper['days_ago'](2), scores)
        assert success1 is True

        # Day 2 (different date, same everything else)
        success2, _, round2 = Round.create('test-course-1', dates_helper['yesterday'](), scores)
        assert success2 is True
        assert round2 is not None

    def test_allow_same_scores_different_course(self, populated_data_store, dates_helper):
        """Test that same round on different course is allowed"""
        date = dates_helper['yesterday']()
        scores = [
            {'player_id': 'test-player-1', 'score': 45},
            {'player_id': 'test-player-2', 'score': 50}
        ]

        # Course 1
        success1, _, _ = Round.create('test-course-1', date, scores)
        assert success1 is True

        # Course 2 (different course, same everything else)
        success2, _, round2 = Round.create('test-course-2', date, scores)
        assert success2 is True
        assert round2 is not None

    def test_allow_partial_player_overlap(self, data_store, dates_helper):
        """Test that rounds with overlapping but not identical players allowed"""
        # Create players and course
        Player.create(name='Player A')
        Player.create(name='Player B')
        Player.create(name='Player C')
        Course.create(name='Test Course')

        players = Player.get_all()
        course = Course.get_all()[0]
        date = dates_helper['yesterday']()

        # Round with 2 players
        scores1 = [
            {'player_id': players[0]['id'], 'score': 45},
            {'player_id': players[1]['id'], 'score': 50}
        ]
        success1, _, _ = Round.create(course['id'], date, scores1)
        assert success1 is True

        # Round with 3 players (superset of first round)
        scores2 = [
            {'player_id': players[0]['id'], 'score': 45},
            {'player_id': players[1]['id'], 'score': 50},
            {'player_id': players[2]['id'], 'score': 55}
        ]
        success2, _, round2 = Round.create(course['id'], date, scores2)
        assert success2 is True
        assert round2 is not None

    def test_single_player_duplicate(self, populated_data_store, dates_helper):
        """Test duplicate detection works with single player rounds"""
        date = dates_helper['yesterday']()
        scores = [{'player_id': 'test-player-1', 'score': 45}]

        success1, _, _ = Round.create('test-course-1', date, scores)
        assert success1 is True

        success2, msg2, _ = Round.create('test-course-1', date, scores)
        assert success2 is False
        assert "duplicate" in msg2.lower()

    def test_allow_same_scores_different_players(self, data_store, dates_helper):
        """Test that same scores with different players is allowed"""
        # Create test players
        Player.create(name='Player A')
        Player.create(name='Player B')
        Player.create(name='Player C')
        Course.create(name='Test Course')

        players = Player.get_all()
        course = Course.get_all()[0]
        date = dates_helper['yesterday']()

        # Round with players A and B
        scores1 = [
            {'player_id': players[0]['id'], 'score': 45},
            {'player_id': players[1]['id'], 'score': 50}
        ]
        success1, _, _ = Round.create(course['id'], date, scores1)
        assert success1 is True

        # Round with players A and C (different player set, same scores)
        scores2 = [
            {'player_id': players[0]['id'], 'score': 45},
            {'player_id': players[2]['id'], 'score': 50}
        ]
        success2, _, round2 = Round.create(course['id'], date, scores2)
        assert success2 is True
        assert round2 is not None
