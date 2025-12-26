"""
Comprehensive unit tests for the AuthService.

Tests cover:
- Google OAuth user retrieval and creation
- Player-Google account linking
- User loading for Flask-Login
- Unlinked players retrieval
- Player creation with Google linking
- Edge cases and error handling
"""
import pytest
from datetime import datetime

from services.auth_service import AuthService
from models.player import Player
from models.user import User


@pytest.mark.unit
@pytest.mark.services
@pytest.mark.auth
class TestAuthServiceGetUserFromGoogle:
    """Tests for AuthService.get_user_from_google()"""

    def test_get_user_existing_linked_account(self, data_store):
        """Test getting user with existing linked Google account"""
        # Create player and link Google account
        success, message, player = Player.create(
            name='Test User',
            email='test@example.com'
        )
        Player.link_google_account(player['id'], 'google-123')

        # Get user from Google
        user = AuthService.get_user_from_google(
            google_id='google-123',
            email='test@example.com',
            name='Test User'
        )

        assert user is not None
        assert isinstance(user, User)
        assert user.id == player['id']
        assert user.google_id == 'google-123'
        assert user.email == 'test@example.com'
        assert user.name == 'Test User'

    def test_get_user_no_linked_account(self, data_store):
        """Test getting user with no linked Google account"""
        user = AuthService.get_user_from_google(
            google_id='google-999',
            email='new@example.com',
            name='New User'
        )

        assert user is None

    def test_get_user_updates_last_login(self, data_store):
        """Test that getting user updates last_login timestamp"""
        # Create player and link Google account
        success, message, player = Player.create(name='Test User')
        Player.link_google_account(player['id'], 'google-123')

        # Get user from Google
        user = AuthService.get_user_from_google(
            google_id='google-123',
            email='test@example.com',
            name='Test User'
        )

        # Verify last_login was updated
        updated_player = Player.get_by_id(player['id'])
        assert updated_player['last_login'] is not None

    def test_get_user_with_admin_role(self, data_store):
        """Test getting user with admin role"""
        success, message, player = Player.create(name='Admin User', role='admin')
        Player.link_google_account(player['id'], 'google-admin')

        user = AuthService.get_user_from_google(
            google_id='google-admin',
            email='admin@example.com',
            name='Admin User'
        )

        assert user is not None
        assert user.role == 'admin'
        assert user.is_admin is True


@pytest.mark.unit
@pytest.mark.services
@pytest.mark.auth
class TestAuthServiceLinkGoogleToPlayer:
    """Tests for AuthService.link_google_to_player()"""

    def test_link_google_to_player_success(self, data_store):
        """Test successfully linking Google account to player"""
        success, message, player = Player.create(name='Test User')

        success, message, user = AuthService.link_google_to_player(
            google_id='google-123',
            player_id=player['id']
        )

        assert success is True
        assert 'linked successfully' in message.lower()
        assert user is not None
        assert isinstance(user, User)
        assert user.google_id == 'google-123'

    def test_link_google_already_linked(self, data_store):
        """Test linking Google account that's already linked to another player"""
        # Create two players
        success1, message1, player1 = Player.create(name='User 1')
        success2, message2, player2 = Player.create(name='User 2')

        # Link Google to first player
        Player.link_google_account(player1['id'], 'google-123')

        # Try to link same Google ID to second player
        success, message, user = AuthService.link_google_to_player(
            google_id='google-123',
            player_id=player2['id']
        )

        assert success is False
        assert 'already linked' in message.lower()
        assert user is None

    def test_link_google_to_nonexistent_player(self, data_store):
        """Test linking Google account to nonexistent player"""
        success, message, user = AuthService.link_google_to_player(
            google_id='google-123',
            player_id='nonexistent-id'
        )

        assert success is False
        assert 'not found' in message.lower()
        assert user is None

    def test_link_google_creates_user_object(self, data_store):
        """Test that linking creates proper User object"""
        success, message, player = Player.create(
            name='Test User',
            email='test@example.com',
            role='player'
        )

        success, message, user = AuthService.link_google_to_player(
            google_id='google-123',
            player_id=player['id']
        )

        assert success is True
        assert user.id == player['id']
        assert user.name == 'Test User'
        assert user.email == 'test@example.com'
        assert user.role == 'player'


@pytest.mark.unit
@pytest.mark.services
@pytest.mark.auth
class TestAuthServiceGetUnlinkedPlayers:
    """Tests for AuthService.get_unlinked_players()"""

    def test_get_unlinked_players_empty(self, data_store):
        """Test getting unlinked players when none exist"""
        unlinked = AuthService.get_unlinked_players()

        assert unlinked == []

    def test_get_unlinked_players_all_unlinked(self, data_store):
        """Test getting unlinked players when all are unlinked"""
        Player.create(name='User 1')
        Player.create(name='User 2')
        Player.create(name='User 3')

        unlinked = AuthService.get_unlinked_players()

        assert len(unlinked) == 3

    def test_get_unlinked_players_mixed(self, data_store):
        """Test getting unlinked players when some are linked"""
        success1, message1, player1 = Player.create(name='Linked User')
        success2, message2, player2 = Player.create(name='Unlinked User 1')
        success3, message3, player3 = Player.create(name='Unlinked User 2')

        # Link one player
        Player.link_google_account(player1['id'], 'google-123')

        unlinked = AuthService.get_unlinked_players()

        assert len(unlinked) == 2
        unlinked_names = [p['name'] for p in unlinked]
        assert 'Linked User' not in unlinked_names
        assert 'Unlinked User 1' in unlinked_names
        assert 'Unlinked User 2' in unlinked_names

    def test_get_unlinked_players_excludes_inactive(self, data_store):
        """Test that inactive players are excluded"""
        success1, message1, player1 = Player.create(name='Active Unlinked')
        success2, message2, player2 = Player.create(name='Inactive Unlinked')

        # Deactivate second player
        Player.delete(player2['id'])

        unlinked = AuthService.get_unlinked_players()

        assert len(unlinked) == 1
        assert unlinked[0]['name'] == 'Active Unlinked'


@pytest.mark.unit
@pytest.mark.services
@pytest.mark.auth
class TestAuthServiceLoadUser:
    """Tests for AuthService.load_user()"""

    def test_load_user_existing_linked(self, data_store):
        """Test loading user that exists and is linked"""
        success, message, player = Player.create(name='Test User')
        Player.link_google_account(player['id'], 'google-123')

        user = AuthService.load_user(player['id'])

        assert user is not None
        assert isinstance(user, User)
        assert user.id == player['id']

    def test_load_user_nonexistent(self, data_store):
        """Test loading nonexistent user"""
        user = AuthService.load_user('nonexistent-id')

        assert user is None

    def test_load_user_not_linked(self, data_store):
        """Test loading user that exists but is not linked to Google"""
        success, message, player = Player.create(name='Test User')

        user = AuthService.load_user(player['id'])

        assert user is None  # Should return None if not linked


@pytest.mark.unit
@pytest.mark.services
@pytest.mark.auth
class TestAuthServiceCreateAndLinkPlayer:
    """Tests for AuthService.create_and_link_player()"""

    def test_create_and_link_player_success(self, data_store):
        """Test successfully creating and linking a new player"""
        success, message, user = AuthService.create_and_link_player(
            google_id='google-123',
            name='New User',
            email='new@example.com',
            favorite_color='#ff0000'
        )

        assert success is True
        assert 'created and linked successfully' in message.lower()
        assert user is not None
        assert isinstance(user, User)
        assert user.name == 'New User'
        assert user.email == 'new@example.com'
        assert user.google_id == 'google-123'

    def test_create_and_link_player_invalid_name(self, data_store):
        """Test creating player with invalid name fails"""
        success, message, user = AuthService.create_and_link_player(
            google_id='google-123',
            name='',
            email='test@example.com'
        )

        assert success is False
        assert user is None

    def test_create_and_link_player_invalid_email(self, data_store):
        """Test creating player with invalid email fails"""
        success, message, user = AuthService.create_and_link_player(
            google_id='google-123',
            name='Test User',
            email='invalid-email'
        )

        assert success is False
        assert user is None

    def test_create_and_link_player_duplicate_name(self, data_store):
        """Test creating player with duplicate name fails"""
        Player.create(name='Existing User')

        success, message, user = AuthService.create_and_link_player(
            google_id='google-123',
            name='Existing User',
            email='test@example.com'
        )

        assert success is False
        assert user is None

    def test_create_and_link_player_default_role(self, data_store):
        """Test that created player has player role by default"""
        success, message, user = AuthService.create_and_link_player(
            google_id='google-123',
            name='Test User',
            email='test@example.com'
        )

        assert success is True
        assert user.role == 'player'
        assert user.is_admin is False

    def test_create_and_link_player_with_color(self, data_store):
        """Test creating player with custom favorite color"""
        success, message, user = AuthService.create_and_link_player(
            google_id='google-123',
            name='Test User',
            email='test@example.com',
            favorite_color='#0000ff'
        )

        assert success is True

        # Verify color was set
        player = Player.get_by_id(user.id)
        assert player['favorite_color'] == '#0000ff'

    def test_create_and_link_player_without_color(self, data_store):
        """Test creating player without favorite color uses default"""
        success, message, user = AuthService.create_and_link_player(
            google_id='google-123',
            name='Test User',
            email='test@example.com'
        )

        assert success is True

        # Verify default color was set
        player = Player.get_by_id(user.id)
        assert player['favorite_color'] == '#2e7d32'


@pytest.mark.unit
@pytest.mark.services
@pytest.mark.auth
class TestAuthServiceGetPlayerForUser:
    """Tests for AuthService.get_player_for_user()"""

    def test_get_player_for_user_existing(self, data_store):
        """Test getting player data for existing user"""
        success, message, player = Player.create(name='Test User')
        Player.link_google_account(player['id'], 'google-123')

        user = User(
            player_id=player['id'],
            google_id='google-123',
            email='test@example.com',
            name='Test User',
            role='player'
        )

        player_data = AuthService.get_player_for_user(user)

        assert player_data is not None
        assert player_data['id'] == player['id']
        assert player_data['name'] == 'Test User'

    def test_get_player_for_user_nonexistent(self, data_store):
        """Test getting player data for nonexistent user"""
        user = User(
            player_id='nonexistent-id',
            google_id='google-123',
            email='test@example.com',
            name='Test User',
            role='player'
        )

        player_data = AuthService.get_player_for_user(user)

        assert player_data is None


@pytest.mark.unit
@pytest.mark.services
@pytest.mark.auth
class TestAuthServiceEdgeCases:
    """Tests for edge cases and special scenarios"""

    def test_multiple_google_accounts_same_player(self, data_store):
        """Test that a player can only have one Google account"""
        success, message, player = Player.create(name='Test User')

        # Link first Google account
        Player.link_google_account(player['id'], 'google-123')

        # Try to link second Google account (should overwrite)
        Player.link_google_account(player['id'], 'google-456')

        # Verify only latest Google ID is linked
        updated = Player.get_by_id(player['id'])
        assert updated['google_id'] == 'google-456'

    def test_user_object_properties(self, data_store):
        """Test User object properties"""
        user = User(
            player_id='player-1',
            google_id='google-123',
            email='test@example.com',
            name='Test User',
            role='admin'
        )

        assert user.id == 'player-1'
        assert user.google_id == 'google-123'
        assert user.email == 'test@example.com'
        assert user.name == 'Test User'
        assert user.role == 'admin'
        assert user.is_admin is True

    def test_user_object_player_role(self, data_store):
        """Test User object with player role"""
        user = User(
            player_id='player-1',
            google_id='google-123',
            email='test@example.com',
            name='Test User',
            role='player'
        )

        assert user.is_admin is False

    def test_last_login_persists_after_link(self, data_store):
        """Test that last_login is set when linking Google account"""
        success, message, player = Player.create(name='Test User')

        # Link Google account
        success, message, user = AuthService.link_google_to_player(
            google_id='google-123',
            player_id=player['id']
        )

        # Verify last_login was set
        updated = Player.get_by_id(player['id'])
        assert updated['last_login'] is not None

        # Verify timestamp format
        last_login = datetime.strptime(
            updated['last_login'],
            '%Y-%m-%dT%H:%M:%SZ'
        )
        assert last_login is not None
