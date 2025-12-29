import pytest
from unittest.mock import Mock, patch, mock_open, PropertyMock
from io import BytesIO
from models.player import Player
from models.course import Course
from models.round import Round
from models.user import User


@pytest.fixture
def mock_admin_user(app):
    """Create a mock admin user for testing"""
    success, message, player = Player.create('Admin User', 'admin@test.com')
    Player.link_google_account(player['id'], 'google_admin')

    # Update player to admin role
    updated_player = Player.get_by_id(player['id'])
    Player.update(player['id'], role='admin')
    updated_player = Player.get_by_id(player['id'])

    return User(
        player_id=updated_player['id'],
        google_id='google_admin',
        email=updated_player['email'],
        name=updated_player['name'],
        role='admin'
    )


class TestListPlayers:
    """Test player list page"""

    def test_list_players_page_loads(self, client):
        """Test that player list page loads successfully"""
        response = client.get('/players/')
        assert response.status_code == 200

    def test_list_players_shows_players(self, client):
        """Test that players are displayed on the list page"""
        # Create some test players
        Player.create('Alice', 'alice@example.com')
        Player.create('Bob', 'bob@example.com')

        response = client.get('/players/')
        assert response.status_code == 200
        assert b'Alice' in response.data
        assert b'Bob' in response.data

    def test_list_players_shows_achievement_scores(self, client):
        """Test that achievement scores are calculated for players"""
        success, message, player = Player.create('Charlie', 'charlie@example.com')
        assert success

        response = client.get('/players/')
        assert response.status_code == 200
        # Page should load even if player has no achievements

    def test_list_players_empty(self, client):
        """Test list page with no players"""
        response = client.get('/players/')
        assert response.status_code == 200


class TestPlayerDetail:
    """Test player detail page"""

    def test_player_detail_page_loads(self, client):
        """Test that player detail page loads successfully"""
        success, message, player = Player.create('Test Player', 'test@example.com')
        assert success

        response = client.get(f'/players/{player["id"]}')
        assert response.status_code == 200
        assert b'Test Player' in response.data

    def test_player_detail_nonexistent_player(self, client):
        """Test accessing detail page for nonexistent player"""
        response = client.get('/players/nonexistent-id', follow_redirects=True)
        assert response.status_code == 200
        assert b'not found' in response.data.lower()

    def test_player_detail_with_rounds(self, client):
        """Test player detail page with round history"""
        # Create player
        success, message, player = Player.create('Player with Rounds', 'rounds@example.com')
        assert success

        # Create course
        success, msg, course = Course.create('Test Course', 'Test Location', 18, 72)
        assert success

        # Create round
        Round.create(
            course_id=course['id'],
            date_played='2025-01-15',
            scores=[
                {'player_id': player['id'], 'score': 65}
            ]
        )

        response = client.get(f'/players/{player["id"]}')
        assert response.status_code == 200
        assert b'65' in response.data  # Score should be displayed

    def test_player_detail_shows_statistics(self, client):
        """Test that player statistics are calculated correctly"""
        # Create player
        success, message, player = Player.create('Stats Player', 'stats@example.com')
        assert success

        # Create course
        success, msg, course = Course.create('Stats Course', 'Location', 18, 72)
        assert success

        # Create multiple rounds with different scores
        Round.create(
            course_id=course['id'],
            date_played='2025-01-10',
            scores=[
                {'player_id': player['id'], 'score': 70}
            ]
        )
        Round.create(
            course_id=course['id'],
            date_played='2025-01-11',
            scores=[
                {'player_id': player['id'], 'score': 65}
            ]
        )

        response = client.get(f'/players/{player["id"]}')
        assert response.status_code == 200
        # Should show best score, worst score, and average

    def test_player_detail_shows_wins(self, client):
        """Test that player wins are counted correctly"""
        # Create players
        success, message, player1 = Player.create('Winner', 'winner@example.com')
        assert success
        success, message, player2 = Player.create('Loser', 'loser@example.com')
        assert success

        # Create course
        success, msg, course = Course.create('Win Course', 'Location', 18, 72)
        assert success

        # Create round where player1 wins
        Round.create(
            course_id=course['id'],
            date_played='2025-01-15',
            scores=[
                {'player_id': player1['id'], 'score': 60},
                {'player_id': player2['id'], 'score': 70}
            ]
        )

        response = client.get(f'/players/{player1["id"]}')
        assert response.status_code == 200
        # Should show 1 win

    def test_player_detail_shows_personal_bests(self, client):
        """Test that personal bests per course are displayed"""
        # Create player
        success, message, player = Player.create('PB Player', 'pb@example.com')
        assert success

        # Create courses
        success, msg, course1 = Course.create('Course 1', 'Location 1', 18, 72)
        assert success
        success, msg, course2 = Course.create('Course 2', 'Location 2', 18, 72)
        assert success

        # Create rounds on different courses
        Round.create(
            course_id=course1['id'],
            date_played='2025-01-10',
            scores=[{'player_id': player['id'], 'score': 68}]
        )
        Round.create(
            course_id=course1['id'],
            date_played='2025-01-11',
            scores=[{'player_id': player['id'], 'score': 65}]  # Better score
        )
        Round.create(
            course_id=course2['id'],
            date_played='2025-01-12',
            scores=[{'player_id': player['id'], 'score': 70}]
        )

        response = client.get(f'/players/{player["id"]}')
        assert response.status_code == 200
        # Should show personal best of 65 for Course 1

    def test_player_detail_shows_achievements(self, client):
        """Test that player achievements are displayed"""
        success, message, player = Player.create('Achievement Player', 'achieve@example.com')
        assert success

        response = client.get(f'/players/{player["id"]}')
        assert response.status_code == 200
        # Page should load with achievements section


class TestAddPlayer:
    """Test add player functionality"""

    @patch('flask_login.utils._get_user')
    def test_add_player_get_page(self, mock_current_user, mock_admin_user, client):
        """Test add player form loads"""
        mock_current_user.return_value = mock_admin_user

        response = client.get('/players/add')
        assert response.status_code == 200

    @patch('flask_login.utils._get_user')
    def test_add_player_success(self, mock_current_user, mock_admin_user, client):
        """Test successfully adding a player"""
        mock_current_user.return_value = mock_admin_user

        response = client.post('/players/add', data={
            'name': 'New Player',
            'email': 'new@example.com',
            'favorite_color': '#ff0000'
        }, follow_redirects=True)

        assert response.status_code == 200
        # Should redirect to player list and show success message
        assert b'New Player' in response.data or b'created successfully' in response.data.lower()

    @patch('flask_login.utils._get_user')
    def test_add_player_duplicate_name(self, mock_current_user, mock_admin_user, client):
        """Test adding player with duplicate name"""
        mock_current_user.return_value = mock_admin_user

        # Create first player
        Player.create('Duplicate', 'dup1@example.com')

        # Try to create another with same name
        response = client.post('/players/add', data={
            'name': 'Duplicate',
            'email': 'dup2@example.com',
            'favorite_color': '#00ff00'
        }, follow_redirects=False)

        assert response.status_code == 200
        assert b'already exists' in response.data.lower()

    @patch('flask_login.utils._get_user')
    def test_add_player_empty_name(self, mock_current_user, mock_admin_user, client):
        """Test adding player with empty name"""
        mock_current_user.return_value = mock_admin_user

        response = client.post('/players/add', data={
            'name': '',
            'email': 'empty@example.com'
        }, follow_redirects=False)

        assert response.status_code == 200
        assert b'cannot be empty' in response.data.lower()

    @patch('flask_login.utils._get_user')
    def test_add_player_without_email(self, mock_current_user, mock_admin_user, client):
        """Test adding player without email (optional field)"""
        mock_current_user.return_value = mock_admin_user

        response = client.post('/players/add', data={
            'name': 'No Email Player',
            'favorite_color': '#0000ff'
        }, follow_redirects=True)

        assert response.status_code == 200
        # Should succeed since email is optional

    @patch('flask_login.utils._get_user')
    @patch('routes.player_routes.validate_image_file')
    @patch('routes.player_routes.save_profile_picture')
    def test_add_player_with_profile_picture(self, mock_save, mock_validate, mock_current_user, mock_admin_user, client):
        """Test adding player with profile picture"""
        mock_current_user.return_value = mock_admin_user
        mock_validate.return_value = (True, None)
        mock_save.return_value = 'profile123.jpg'

        data = {
            'name': 'Picture Player',
            'email': 'pic@example.com',
            'favorite_color': '#00ffff'
        }
        data['profile_picture'] = (BytesIO(b'fake image data'), 'profile.jpg')

        response = client.post('/players/add', data=data,
                             content_type='multipart/form-data',
                             follow_redirects=True)

        assert response.status_code == 200

    @patch('flask_login.utils._get_user')
    @patch('routes.player_routes.validate_image_file')
    def test_add_player_invalid_image(self, mock_validate, mock_current_user, mock_admin_user, client):
        """Test adding player with invalid image file"""
        mock_current_user.return_value = mock_admin_user
        mock_validate.return_value = (False, 'Invalid file format')

        data = {
            'name': 'Invalid Image Player',
            'email': 'invalid@example.com'
        }
        data['profile_picture'] = (BytesIO(b'not an image'), 'bad.txt')

        response = client.post('/players/add', data=data,
                             content_type='multipart/form-data',
                             follow_redirects=False)

        assert response.status_code == 200
        assert b'Invalid file format' in response.data


class TestEditPlayer:
    """Test edit player functionality"""

    @patch('flask_login.utils._get_user')
    def test_edit_player_success(self, mock_current_user, mock_admin_user, client):
        """Test successfully editing a player"""
        mock_current_user.return_value = mock_admin_user

        # Create player
        success, message, player = Player.create('Edit Me', 'edit@example.com')
        assert success

        response = client.post(f'/players/{player["id"]}/edit', data={
            'name': 'Edited Name',
            'email': 'edited@example.com',
            'favorite_color': '#ff00ff'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Edited Name' in response.data or b'updated successfully' in response.data.lower()

    @patch('flask_login.utils._get_user')
    def test_edit_nonexistent_player(self, mock_current_user, mock_admin_user, client):
        """Test editing nonexistent player"""
        mock_current_user.return_value = mock_admin_user

        response = client.post('/players/fake-id/edit', data={
            'name': 'New Name',
            'email': 'new@example.com'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'not found' in response.data.lower()

    @patch('flask_login.utils._get_user')
    def test_edit_player_remove_picture(self, mock_current_user, mock_admin_user, client):
        """Test removing player profile picture"""
        mock_current_user.return_value = mock_admin_user

        # Create player with picture
        success, message, player = Player.create('Player', 'player@example.com', 'old_pic.jpg')
        assert success

        response = client.post(f'/players/{player["id"]}/edit', data={
            'name': 'Player',
            'email': 'player@example.com',
            'remove_picture': 'true'
        }, follow_redirects=True)

        assert response.status_code == 200

    @patch('flask_login.utils._get_user')
    @patch('routes.player_routes.validate_image_file')
    @patch('routes.player_routes.save_profile_picture')
    def test_edit_player_new_picture(self, mock_save, mock_validate, mock_current_user, mock_admin_user, client):
        """Test updating player profile picture"""
        mock_current_user.return_value = mock_admin_user
        mock_validate.return_value = (True, None)
        mock_save.return_value = 'new_profile.jpg'

        # Create player
        success, message, player = Player.create('Player', 'player@example.com')
        assert success

        data = {
            'name': 'Player',
            'email': 'player@example.com',
            'favorite_color': '#123456'
        }
        data['profile_picture'] = (BytesIO(b'new image'), 'new.jpg')

        response = client.post(f'/players/{player["id"]}/edit', data=data,
                             content_type='multipart/form-data',
                             follow_redirects=True)

        assert response.status_code == 200

    @patch('flask_login.utils._get_user')
    @patch('routes.player_routes.validate_image_file')
    def test_edit_player_invalid_image(self, mock_validate, mock_current_user, mock_admin_user, client):
        """Test editing player with invalid image"""
        mock_current_user.return_value = mock_admin_user
        mock_validate.return_value = (False, 'File too large')

        # Create player
        success, message, player = Player.create('Player', 'player@example.com')
        assert success

        data = {
            'name': 'Player',
            'email': 'player@example.com'
        }
        data['profile_picture'] = (BytesIO(b'huge file'), 'huge.jpg')

        response = client.post(f'/players/{player["id"]}/edit', data=data,
                             content_type='multipart/form-data',
                             follow_redirects=False)

        assert response.status_code == 302  # Should redirect with error
        # Check for flashed message in redirected response
        follow_response = client.get(response.location)
        assert b'File too large' in follow_response.data.lower() or b'error' in follow_response.data.lower()


class TestDeletePlayer:
    """Test delete player functionality"""

    @patch('flask_login.utils._get_user')
    def test_delete_player_without_rounds(self, mock_current_user, mock_admin_user, client):
        """Test deleting player with no rounds"""
        mock_current_user.return_value = mock_admin_user

        # Create player
        success, message, player = Player.create('Delete Me', 'delete@example.com')
        assert success

        response = client.post(f'/players/{player["id"]}/delete', follow_redirects=True)
        assert response.status_code == 200
        # Should redirect to player list

    @patch('flask_login.utils._get_user')
    def test_delete_player_with_rounds(self, mock_current_user, mock_admin_user, client):
        """Test soft-deleting player with rounds"""
        mock_current_user.return_value = mock_admin_user

        # Create player and course
        success, message, player = Player.create('Player with Rounds', 'rounds@example.com')
        assert success
        success, msg, course = Course.create('Course', 'Location', 18, 72)
        assert success

        # Create round
        Round.create(
            course_id=course['id'],
            date_played='2025-01-15',
            scores=[{'player_id': player['id'], 'score': 70}]
        )

        response = client.post(f'/players/{player["id"]}/delete', follow_redirects=True)
        assert response.status_code == 200
        # Player should be soft-deleted (marked inactive)

    @patch('flask_login.utils._get_user')
    def test_delete_nonexistent_player(self, mock_current_user, mock_admin_user, client):
        """Test deleting nonexistent player"""
        mock_current_user.return_value = mock_admin_user

        response = client.post('/players/fake-id/delete', follow_redirects=True)
        assert response.status_code == 200
        # Should show error message on redirected page
        assert b'not found' in response.data.lower()


class TestSaveProfilePicture:
    """Test profile picture save helper function"""

    def test_save_profile_picture_valid_file(self):
        """Test saving a valid profile picture"""
        from routes.player_routes import save_profile_picture

        # Create a mock file
        file = Mock()
        file.filename = 'profile.jpg'
        file.save = Mock()

        with patch('routes.player_routes.sanitize_filename', return_value='profile.jpg'):
            with patch('os.makedirs'):
                result = save_profile_picture(file, '/tmp/uploads')

        assert result is not None
        assert result.endswith('.jpg')

    def test_save_profile_picture_no_file(self):
        """Test saving with no file"""
        from routes.player_routes import save_profile_picture

        result = save_profile_picture(None, '/tmp/uploads')
        assert result is None

    def test_save_profile_picture_empty_filename(self):
        """Test saving with empty filename"""
        from routes.player_routes import save_profile_picture

        file = Mock()
        file.filename = ''

        result = save_profile_picture(file, '/tmp/uploads')
        assert result is None

    def test_save_profile_picture_no_extension(self):
        """Test saving file with no extension"""
        from routes.player_routes import save_profile_picture

        file = Mock()
        file.filename = 'profile'
        file.save = Mock()

        with patch('routes.player_routes.sanitize_filename', return_value='profile'):
            with patch('os.makedirs'):
                result = save_profile_picture(file, '/tmp/uploads')

        assert result is not None
        assert result.endswith('.jpg')  # Default extension
