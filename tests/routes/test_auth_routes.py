import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from flask import session
from models.player import Player
from models.user import User


class TestAuthLogin:
    """Test login page"""

    def test_login_page_loads(self, client):
        """Test that login page loads successfully"""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'Sign in with Google' in response.data or b'login' in response.data.lower()

    def test_login_redirects_if_authenticated(self, client, app):
        """Test that authenticated users are redirected from login page"""
        # Create a test player
        success, message, player = Player.create('Test User', 'test@example.com')
        assert success
        Player.link_google_account(player['id'], 'google123')

        # Reload player to get updated google_id
        from models.player import Player as PlayerModel
        updated_player = PlayerModel.get_by_id(player['id'])

        # Create a user with correct signature: player_id, google_id, email, name, role
        user = User(
            player_id=updated_player['id'],
            google_id=updated_player['google_id'],
            email=updated_player['email'],
            name=updated_player['name'],
            role=updated_player.get('role', 'player')
        )

        with client.session_transaction() as sess:
            sess['_user_id'] = user.id
            sess['_fresh'] = True

        with app.test_request_context():
            response = client.get('/auth/login', follow_redirects=False)
            assert response.status_code == 302
            assert '/auth/login' not in response.location


class TestAuthLogout:
    """Test logout functionality"""

    def test_logout_clears_session(self, client, app):
        """Test that logout clears the session"""
        # Create a test player
        success, message, player = Player.create('Test User', 'test@example.com')
        assert success

        # Simulate logged in user
        with client.session_transaction() as sess:
            sess['_user_id'] = player['id']

        response = client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200
        assert b'logged out' in response.data.lower()

        # Verify session is cleared
        with client.session_transaction() as sess:
            assert '_user_id' not in sess

    def test_logout_without_login(self, client):
        """Test logout when not logged in"""
        response = client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200


class TestAuthUnauthorized:
    """Test unauthorized page"""

    def test_unauthorized_page(self, client):
        """Test that unauthorized page returns 403"""
        response = client.get('/auth/unauthorized')
        assert response.status_code == 403
        assert b'unauthorized' in response.data.lower() or b'403' in response.data


class TestIsSafeUrl:
    """Test URL redirect validation"""

    def test_is_safe_url_same_host(self, client, app):
        """Test that same-host URLs are safe"""
        from routes.auth_routes import is_safe_url

        with app.test_request_context('http://localhost/'):
            assert is_safe_url('/dashboard')
            assert is_safe_url('/players')
            assert is_safe_url('http://localhost/courses')

    def test_is_safe_url_different_host(self, client, app):
        """Test that different-host URLs are not safe"""
        from routes.auth_routes import is_safe_url

        with app.test_request_context('http://localhost/'):
            assert not is_safe_url('http://evil.com/steal')
            assert not is_safe_url('https://phishing.com/login')

    def test_is_safe_url_relative(self, client, app):
        """Test that relative URLs are safe"""
        from routes.auth_routes import is_safe_url

        with app.test_request_context('http://localhost/'):
            assert is_safe_url('/courses/123')
            assert is_safe_url('/players/list')


class TestGoogleOAuthFlow:
    """Test Google OAuth integration"""

    def test_google_login_redirects(self, client):
        """Test Google login endpoint redirects"""
        response = client.get('/auth/google', follow_redirects=False)
        assert response.status_code == 302
        # Should redirect to either Google OAuth or callback


class TestGoogleCallback:
    """Test Google OAuth callback"""

    def test_callback_requires_oauth(self, client):
        """Test callback without OAuth redirects to login"""
        response = client.get('/auth/google/callback', follow_redirects=True)
        assert response.status_code == 200
        # Without proper OAuth setup, should redirect to login or show error


class TestRegister:
    """Test registration page"""

    def test_register_without_google_session(self, client):
        """Test register page without Google session data"""
        response = client.get('/auth/register', follow_redirects=True)
        assert response.status_code == 200
        assert b'Google account information' in response.data or b'sign in' in response.data.lower()

    def test_register_page_with_google_session(self, client):
        """Test register page with Google session data"""
        with client.session_transaction() as sess:
            sess['google_id'] = 'google123'
            sess['google_email'] = 'test@example.com'
            sess['google_name'] = 'Test User'

        response = client.get('/auth/register')
        assert response.status_code == 200
        assert b'test@example.com' in response.data or b'Test User' in response.data

    @patch('routes.auth_routes.AuthService')
    def test_register_create_new_player(self, mock_auth_service, client):
        """Test creating a new player profile"""
        # Set up session
        with client.session_transaction() as sess:
            sess['google_id'] = 'google_new'
            sess['google_email'] = 'new@example.com'
            sess['google_name'] = 'New User'

        # Create a player for the mock
        success, message, player = Player.create('New Player', 'new@example.com')
        assert success
        # User(player_id, google_id, email, name, role)
        mock_user = User(
            player_id=player['id'],
            google_id='google_new',
            email='new@example.com',
            name='New Player',
            role='player'
        )
        mock_auth_service.create_and_link_player.return_value = (True, 'Success', mock_user)

        response = client.post('/auth/register', data={
            'action': 'create',
            'new_name': 'New Player',
            'new_email': 'new@example.com',
            'favorite_color': '#ff0000'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'created successfully' in response.data.lower() or b'welcome' in response.data.lower()

        # Verify session is cleared
        with client.session_transaction() as sess:
            assert 'google_id' not in sess

    @patch('routes.auth_routes.AuthService')
    def test_register_link_existing_player(self, mock_auth_service, client):
        """Test linking Google account to existing player"""
        # Create an existing player
        success, message, player = Player.create('Existing Player', 'existing@example.com')
        assert success

        # Set up session
        with client.session_transaction() as sess:
            sess['google_id'] = 'google_link'
            sess['google_email'] = 'link@example.com'
            sess['google_name'] = 'Link User'

        # Mock successful link - User(player_id, google_id, email, name, role)
        mock_user = User(
            player_id=player['id'],
            google_id='google_link',
            email=player['email'],
            name=player['name'],
            role='player'
        )
        mock_auth_service.link_google_to_player.return_value = (True, 'Success', mock_user)

        response = client.post('/auth/register', data={
            'action': 'link',
            'player_id': player['id']
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'linked successfully' in response.data.lower() or b'welcome' in response.data.lower()

    def test_register_create_without_name(self, client):
        """Test creating player without providing name"""
        with client.session_transaction() as sess:
            sess['google_id'] = 'google123'
            sess['google_email'] = 'test@example.com'
            sess['google_name'] = 'Test User'

        response = client.post('/auth/register', data={
            'action': 'create',
            'new_name': '',
            'new_email': 'test@example.com'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'enter a name' in response.data.lower()

    def test_register_link_without_selection(self, client):
        """Test linking without selecting a player"""
        with client.session_transaction() as sess:
            sess['google_id'] = 'google123'
            sess['google_email'] = 'test@example.com'
            sess['google_name'] = 'Test User'

        response = client.post('/auth/register', data={
            'action': 'link',
            'player_id': ''
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'select a player' in response.data.lower()

    @patch('routes.auth_routes.AuthService')
    def test_register_create_player_failure(self, mock_auth_service, client):
        """Test handling of player creation failure"""
        with client.session_transaction() as sess:
            sess['google_id'] = 'google123'
            sess['google_email'] = 'test@example.com'
            sess['google_name'] = 'Test User'

        mock_auth_service.create_and_link_player.return_value = (False, 'Creation failed', None)

        response = client.post('/auth/register', data={
            'action': 'create',
            'new_name': 'Test Player',
            'new_email': 'test@example.com'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Creation failed' in response.data or b'failed' in response.data.lower()

    @patch('routes.auth_routes.AuthService')
    def test_register_link_player_failure(self, mock_auth_service, client):
        """Test handling of player linking failure"""
        success, message, player = Player.create('Test Player', 'test@example.com')
        assert success

        with client.session_transaction() as sess:
            sess['google_id'] = 'google123'
            sess['google_email'] = 'test@example.com'
            sess['google_name'] = 'Test User'

        mock_auth_service.link_google_to_player.return_value = (False, 'Link failed', None)

        response = client.post('/auth/register', data={
            'action': 'link',
            'player_id': player['id']
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Link failed' in response.data or b'failed' in response.data.lower()
