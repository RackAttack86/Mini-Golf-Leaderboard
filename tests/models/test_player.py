"""
Comprehensive unit tests for the Player model.

Tests cover:
- Player creation with valid and invalid data
- Player retrieval (all, by ID, by Google ID)
- Player updates including name changes and denormalization
- Player deletion (soft and hard)
- Google account linking
- Admin role checking
- Edge cases and error handling
"""
import pytest
from datetime import datetime

from models.player import Player
from models.round import Round


@pytest.mark.unit
@pytest.mark.models
class TestPlayerCreate:
    """Tests for Player.create() method"""

    def test_create_player_minimal(self, data_store):
        """Test creating a player with only required fields"""
        success, message, player = Player.create(name='John Doe')

        assert success is True
        assert message == "Player created successfully"
        assert player is not None
        assert player['name'] == 'John Doe'
        assert player['email'] == ''
        assert player['role'] == 'player'
        assert player['active'] is True
        assert 'id' in player
        assert 'created_at' in player

    def test_create_player_full(self, data_store):
        """Test creating a player with all fields"""
        success, message, player = Player.create(
            name='Jane Smith',
            email='jane@example.com',
            profile_picture='jane.jpg',
            favorite_color='#ff0000',
            role='admin'
        )

        assert success is True
        assert player['name'] == 'Jane Smith'
        assert player['email'] == 'jane@example.com'
        assert player['profile_picture'] == 'jane.jpg'
        assert player['favorite_color'] == '#ff0000'
        assert player['role'] == 'admin'

    def test_create_player_default_color(self, data_store):
        """Test that default favorite color is set"""
        success, message, player = Player.create(name='Test Player')

        assert success is True
        assert player['favorite_color'] == '#2e7d32'

    def test_create_player_invalid_role(self, data_store):
        """Test that invalid role defaults to 'player'"""
        success, message, player = Player.create(name='Test', role='superadmin')

        assert success is True
        assert player['role'] == 'player'

    def test_create_player_empty_name(self, data_store):
        """Test creating player with empty name fails"""
        success, message, player = Player.create(name='')

        assert success is False
        assert "cannot be empty" in message.lower()
        assert player is None

    def test_create_player_whitespace_name(self, data_store):
        """Test creating player with whitespace-only name fails"""
        success, message, player = Player.create(name='   ')

        assert success is False
        assert player is None

    def test_create_player_name_too_long(self, data_store):
        """Test creating player with name exceeding max length fails"""
        long_name = 'A' * 101
        success, message, player = Player.create(name=long_name)

        assert success is False
        assert "too long" in message.lower()
        assert player is None

    def test_create_player_duplicate_name(self, data_store):
        """Test creating player with duplicate name fails"""
        Player.create(name='John Doe')
        success, message, player = Player.create(name='John Doe')

        assert success is False
        assert "already exists" in message.lower()
        assert player is None

    def test_create_player_duplicate_name_case_insensitive(self, data_store):
        """Test that duplicate check is case-insensitive"""
        Player.create(name='John Doe')
        success, message, player = Player.create(name='JOHN DOE')

        assert success is False
        assert "already exists" in message.lower()

    def test_create_player_invalid_email(self, data_store):
        """Test creating player with invalid email fails"""
        success, message, player = Player.create(
            name='Test',
            email='invalid-email'
        )

        assert success is False
        assert "email" in message.lower()
        assert player is None

    def test_create_player_email_too_long(self, data_store):
        """Test creating player with email exceeding max length fails"""
        long_email = 'a' * 95 + '@example.com'
        success, message, player = Player.create(name='Test', email=long_email)

        assert success is False
        assert "too long" in message.lower()

    def test_create_player_name_stripped(self, data_store):
        """Test that player name is stripped of whitespace"""
        success, message, player = Player.create(name='  John Doe  ')

        assert success is True
        assert player['name'] == 'John Doe'

    def test_create_player_email_stripped(self, data_store):
        """Test that email is stripped of whitespace"""
        success, message, player = Player.create(
            name='Test',
            email='  test@example.com  '
        )

        assert success is True
        assert player['email'] == 'test@example.com'


@pytest.mark.unit
@pytest.mark.models
class TestPlayerRetrieval:
    """Tests for Player retrieval methods"""

    def test_get_all_empty(self, data_store):
        """Test getting all players when none exist"""
        players = Player.get_all()

        assert players == []

    def test_get_all_players(self, populated_data_store):
        """Test getting all active players"""
        players = Player.get_all()

        assert len(players) == 2
        assert all(p['active'] for p in players)

    def test_get_all_including_inactive(self, data_store):
        """Test getting all players including inactive ones"""
        Player.create(name='Active Player')
        success, message, inactive = Player.create(name='Inactive Player')
        # Deactivate the second player
        Player.delete(inactive['id'])

        active_only = Player.get_all(active_only=True)
        all_players = Player.get_all(active_only=False)

        assert len(active_only) == 1
        assert len(all_players) == 2

    def test_get_by_id_existing(self, populated_data_store):
        """Test getting player by ID when it exists"""
        player = Player.get_by_id('test-player-1')

        assert player is not None
        assert player['id'] == 'test-player-1'
        assert player['name'] == 'John Doe'

    def test_get_by_id_nonexistent(self, data_store):
        """Test getting player by ID when it doesn't exist"""
        player = Player.get_by_id('nonexistent-id')

        assert player is None

    def test_get_by_google_id_existing(self, data_store):
        """Test getting player by Google ID when linked"""
        success, message, player = Player.create(name='Google User')
        Player.link_google_account(player['id'], 'google-123')

        found = Player.get_by_google_id('google-123')

        assert found is not None
        assert found['id'] == player['id']
        assert found['google_id'] == 'google-123'

    def test_get_by_google_id_nonexistent(self, data_store):
        """Test getting player by Google ID when not linked"""
        player = Player.get_by_google_id('nonexistent-google-id')

        assert player is None


@pytest.mark.unit
@pytest.mark.models
class TestPlayerUpdate:
    """Tests for Player.update() method"""

    def test_update_player_name(self, populated_data_store):
        """Test updating player name"""
        success, message = Player.update('test-player-1', name='John Smith')

        assert success is True
        player = Player.get_by_id('test-player-1')
        assert player['name'] == 'John Smith'

    def test_update_player_email(self, populated_data_store):
        """Test updating player email"""
        success, message = Player.update(
            'test-player-1',
            email='newemail@example.com'
        )

        assert success is True
        player = Player.get_by_id('test-player-1')
        assert player['email'] == 'newemail@example.com'

    def test_update_player_profile_picture(self, populated_data_store):
        """Test updating player profile picture"""
        success, message = Player.update(
            'test-player-1',
            profile_picture='new-pic.jpg'
        )

        assert success is True
        player = Player.get_by_id('test-player-1')
        assert player['profile_picture'] == 'new-pic.jpg'

    def test_update_player_favorite_color(self, populated_data_store):
        """Test updating player favorite color"""
        success, message = Player.update(
            'test-player-1',
            favorite_color='#ff0000'
        )

        assert success is True
        player = Player.get_by_id('test-player-1')
        assert player['favorite_color'] == '#ff0000'

    def test_update_player_role(self, populated_data_store):
        """Test updating player role"""
        success, message = Player.update('test-player-1', role='admin')

        assert success is True
        player = Player.get_by_id('test-player-1')
        assert player['role'] == 'admin'

    def test_update_player_invalid_role(self, populated_data_store):
        """Test that invalid role is not updated"""
        Player.update('test-player-1', role='superadmin')

        player = Player.get_by_id('test-player-1')
        assert player['role'] == 'player'  # Should remain unchanged

    def test_update_nonexistent_player(self, data_store):
        """Test updating nonexistent player fails"""
        success, message = Player.update('nonexistent-id', name='New Name')

        assert success is False
        assert "not found" in message.lower()

    def test_update_player_duplicate_name(self, populated_data_store):
        """Test updating to duplicate name fails"""
        success, message = Player.update('test-player-1', name='Jane Smith')

        assert success is False
        assert "already exists" in message.lower()

    def test_update_player_invalid_email(self, populated_data_store):
        """Test updating with invalid email fails"""
        success, message = Player.update(
            'test-player-1',
            email='invalid-email'
        )

        assert success is False
        assert "email" in message.lower()

    def test_update_player_multiple_fields(self, populated_data_store):
        """Test updating multiple fields at once"""
        success, message = Player.update(
            'test-player-1',
            name='New Name',
            email='new@example.com',
            favorite_color='#0000ff',
            role='admin'
        )

        assert success is True
        player = Player.get_by_id('test-player-1')
        assert player['name'] == 'New Name'
        assert player['email'] == 'new@example.com'
        assert player['favorite_color'] == '#0000ff'
        assert player['role'] == 'admin'

    def test_update_name_updates_rounds(self, populated_data_store):
        """Test that updating player name updates denormalized data in rounds"""
        # The populated store has a round with test-player-1
        success, message = Player.update('test-player-1', name='Updated Name')

        assert success is True

        # Check that the round was updated
        rounds = Round.get_by_player('test-player-1')
        assert len(rounds) > 0
        for round_data in rounds:
            for score in round_data['scores']:
                if score['player_id'] == 'test-player-1':
                    assert score['player_name'] == 'Updated Name'


@pytest.mark.unit
@pytest.mark.models
class TestPlayerDelete:
    """Tests for Player.delete() method"""

    def test_delete_player_without_rounds(self, data_store):
        """Test hard deleting player without rounds"""
        success, message, player = Player.create(name='Test Player')
        player_id = player['id']

        success, message = Player.delete(player_id)

        assert success is True
        assert "deleted successfully" in message.lower()
        assert Player.get_by_id(player_id) is None

    def test_soft_delete_player_with_rounds(self, populated_data_store):
        """Test soft deleting player with existing rounds"""
        # test-player-1 has rounds in populated store
        success, message = Player.delete('test-player-1')

        assert success is True
        assert "deactivated" in message.lower()

        # Player should still exist but be inactive
        player = Player.get_by_id('test-player-1')
        assert player is not None
        assert player['active'] is False

    def test_force_delete_player_with_rounds(self, populated_data_store):
        """Test force deleting player with existing rounds"""
        success, message = Player.delete('test-player-1', force=True)

        assert success is True
        assert "deleted successfully" in message.lower()
        assert Player.get_by_id('test-player-1') is None

    def test_delete_nonexistent_player(self, data_store):
        """Test deleting nonexistent player fails"""
        success, message = Player.delete('nonexistent-id')

        assert success is False
        assert "not found" in message.lower()


@pytest.mark.unit
@pytest.mark.models
@pytest.mark.auth
class TestPlayerGoogleIntegration:
    """Tests for Google account linking functionality"""

    def test_link_google_account(self, data_store):
        """Test linking Google account to player"""
        success, message, player = Player.create(name='Test User')
        player_id = player['id']

        success, message = Player.link_google_account(player_id, 'google-123')

        assert success is True
        assert "linked successfully" in message.lower()

        updated = Player.get_by_id(player_id)
        assert updated['google_id'] == 'google-123'
        assert updated['last_login'] is not None

    def test_link_google_already_linked(self, data_store):
        """Test linking Google account that's already linked to another player"""
        success1, message1, player1 = Player.create(name='User 1')
        success2, message2, player2 = Player.create(name='User 2')

        Player.link_google_account(player1['id'], 'google-123')
        success, message = Player.link_google_account(player2['id'], 'google-123')

        assert success is False
        assert "already linked" in message.lower()

    def test_link_google_to_nonexistent_player(self, data_store):
        """Test linking Google account to nonexistent player fails"""
        success, message = Player.link_google_account('nonexistent-id', 'google-123')

        assert success is False
        assert "not found" in message.lower()

    def test_relink_same_google_account(self, data_store):
        """Test relinking the same Google account to the same player"""
        success, message, player = Player.create(name='Test User')
        player_id = player['id']

        Player.link_google_account(player_id, 'google-123')
        success, message = Player.link_google_account(player_id, 'google-123')

        assert success is True

    def test_update_last_login(self, data_store):
        """Test updating last login timestamp"""
        success, message, player = Player.create(name='Test User')
        player_id = player['id']

        result = Player.update_last_login(player_id)

        assert result is True
        updated = Player.get_by_id(player_id)
        assert updated['last_login'] is not None

    def test_update_last_login_nonexistent(self, data_store):
        """Test updating last login for nonexistent player"""
        result = Player.update_last_login('nonexistent-id')

        assert result is False


@pytest.mark.unit
@pytest.mark.models
class TestPlayerAdmin:
    """Tests for admin role checking"""

    def test_is_admin_true(self, data_store):
        """Test checking admin role for admin player"""
        success, message, player = Player.create(name='Admin', role='admin')

        assert Player.is_admin(player['id']) is True

    def test_is_admin_false(self, data_store):
        """Test checking admin role for regular player"""
        success, message, player = Player.create(name='Player')

        assert Player.is_admin(player['id']) is False

    def test_is_admin_nonexistent(self, data_store):
        """Test checking admin role for nonexistent player"""
        assert Player.is_admin('nonexistent-id') is False


@pytest.mark.unit
@pytest.mark.models
class TestPlayerEdgeCases:
    """Tests for edge cases and special scenarios"""

    def test_create_player_with_none_optional_fields(self, data_store):
        """Test creating player with None for optional fields"""
        success, message, player = Player.create(
            name='Test',
            email=None,
            profile_picture=None,
            favorite_color=None
        )

        assert success is True
        assert player['email'] == ''
        assert player['profile_picture'] == ''
        assert player['favorite_color'] == '#2e7d32'

    def test_update_player_with_none_values(self, populated_data_store):
        """Test that None values don't update fields"""
        original = Player.get_by_id('test-player-1')

        success, message = Player.update(
            'test-player-1',
            name=None,
            email=None
        )

        updated = Player.get_by_id('test-player-1')
        assert updated['name'] == original['name']
        assert updated['email'] == original['email']

    def test_player_created_at_format(self, data_store):
        """Test that created_at timestamp is in correct format"""
        success, message, player = Player.create(name='Test')

        assert success is True
        # Verify ISO 8601 format
        created_at = datetime.strptime(
            player['created_at'],
            '%Y-%m-%dT%H:%M:%SZ'
        )
        assert created_at is not None

    def test_concurrent_player_creation(self, data_store):
        """Test that unique constraint works with concurrent requests"""
        # First creation should succeed
        success1, message1, player1 = Player.create(name='Test Player')
        assert success1 is True

        # Second creation with same name should fail
        success2, message2, player2 = Player.create(name='Test Player')
        assert success2 is False

    def test_player_id_is_uuid(self, data_store):
        """Test that player ID is a valid UUID"""
        success, message, player = Player.create(name='Test')

        assert success is True
        # UUID format: 8-4-4-4-12 characters
        parts = player['id'].split('-')
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
