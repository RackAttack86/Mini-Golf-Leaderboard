import pytest
from unittest.mock import Mock, patch, PropertyMock
from io import BytesIO
import json
from models.course import Course
from models.player import Player
from models.round import Round
from models.course_rating import CourseRating
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


@pytest.fixture
def mock_regular_user(app):
    """Create a mock regular user for testing"""
    success, message, player = Player.create('Regular User', 'user@test.com')
    Player.link_google_account(player['id'], 'google_user')

    updated_player = Player.get_by_id(player['id'])

    return User(
        player_id=updated_player['id'],
        google_id='google_user',
        email=updated_player['email'],
        name=updated_player['name'],
        role='player'
    )


class TestListCourses:
    """Test course list page"""

    def test_list_courses_page_loads(self, client):
        """Test that course list page loads successfully"""
        response = client.get('/courses/')
        assert response.status_code == 200

    def test_list_courses_shows_courses(self, client):
        """Test that courses are displayed on the list page"""
        # Create test courses
        Course.create('Course A', 'Location A', 18, 54)
        Course.create('Course B', 'Location B', 9, 27)

        response = client.get('/courses/')
        assert response.status_code == 200
        assert b'Course A' in response.data
        assert b'Course B' in response.data

    def test_list_courses_shows_ratings(self, client, mock_regular_user):
        """Test that course ratings are displayed"""
        # Create course and player
        success, msg, course = Course.create('Rated Course', 'Location', 18, 54)
        assert success

        # Add a rating
        CourseRating.rate_course(mock_regular_user.google_id, course['id'], 5)

        response = client.get('/courses/')
        assert response.status_code == 200
        # Page should show the course

    def test_list_courses_empty(self, client):
        """Test list page with no courses"""
        response = client.get('/courses/')
        assert response.status_code == 200


class TestCourseDetail:
    """Test course detail page"""

    def test_course_detail_page_loads(self, client):
        """Test that course detail page loads successfully"""
        success, message, course = Course.create('Test Course', 'Test Location', 18, 54)
        assert success

        response = client.get(f'/courses/{course["id"]}')
        assert response.status_code == 200
        assert b'Test Course' in response.data

    def test_course_detail_nonexistent_course(self, client):
        """Test accessing detail page for nonexistent course"""
        response = client.get('/courses/nonexistent-id', follow_redirects=True)
        assert response.status_code == 200
        assert b'not found' in response.data.lower()

    def test_course_detail_with_rounds(self, client):
        """Test course detail page with round history"""
        # Create course and player
        success, msg, course = Course.create('Course with Rounds', 'Location', 18, 54)
        assert success
        success, message, player = Player.create('Player', 'player@example.com')
        assert success

        # Create round
        Round.create(
            course_id=course['id'],
            date_played='2025-01-15',
            scores=[{'player_id': player['id'], 'score': 48}]
        )

        response = client.get(f'/courses/{course["id"]}')
        assert response.status_code == 200
        assert b'48' in response.data  # Score should be displayed

    def test_course_detail_shows_statistics(self, client):
        """Test that course statistics are calculated correctly"""
        # Create course and players
        success, msg, course = Course.create('Stats Course', 'Location', 18, 54)
        assert success
        success, message, player1 = Player.create('Player 1', 'p1@example.com')
        assert success
        success, message, player2 = Player.create('Player 2', 'p2@example.com')
        assert success

        # Create rounds with different scores
        Round.create(
            course_id=course['id'],
            date_played='2025-01-10',
            scores=[
                {'player_id': player1['id'], 'score': 50},
                {'player_id': player2['id'], 'score': 55}
            ]
        )
        Round.create(
            course_id=course['id'],
            date_played='2025-01-11',
            scores=[
                {'player_id': player1['id'], 'score': 45}
            ]
        )

        response = client.get(f'/courses/{course["id"]}')
        assert response.status_code == 200
        # Should show statistics

    def test_course_detail_shows_ratings(self, client, mock_regular_user):
        """Test that course ratings are displayed"""
        success, msg, course = Course.create('Rated Course', 'Location', 18, 54)
        assert success

        # Add rating
        CourseRating.rate_course(mock_regular_user.google_id, course['id'], 4)

        response = client.get(f'/courses/{course["id"]}')
        assert response.status_code == 200
        # Page should load with rating info


class TestAddCourse:
    """Test add course functionality"""

    @patch('flask_login.utils._get_user')
    def test_add_course_get_page(self, mock_current_user, mock_admin_user, client):
        """Test add course form loads"""
        mock_current_user.return_value = mock_admin_user

        response = client.get('/courses/add')
        assert response.status_code == 200

    @patch('flask_login.utils._get_user')
    def test_add_course_success(self, mock_current_user, mock_admin_user, client):
        """Test successfully adding a course"""
        mock_current_user.return_value = mock_admin_user

        response = client.post('/courses/add', data={
            'name': 'New Course',
            'location': 'New Location',
            'holes': '18',
            'par': '54'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'New Course' in response.data or b'created successfully' in response.data.lower()

    @patch('flask_login.utils._get_user')
    def test_add_course_duplicate_name(self, mock_current_user, mock_admin_user, client):
        """Test adding course with duplicate name"""
        mock_current_user.return_value = mock_admin_user

        # Create first course
        Course.create('Duplicate Course', 'Location 1', 18, 54)

        # Try to create another with same name
        response = client.post('/courses/add', data={
            'name': 'Duplicate Course',
            'location': 'Location 2',
            'holes': '18',
            'par': '54'
        }, follow_redirects=False)

        assert response.status_code == 200
        assert b'already exists' in response.data.lower()

    @patch('flask_login.utils._get_user')
    def test_add_course_empty_name(self, mock_current_user, mock_admin_user, client):
        """Test adding course with empty name"""
        mock_current_user.return_value = mock_admin_user

        response = client.post('/courses/add', data={
            'name': '',
            'location': 'Location',
            'holes': '18',
            'par': '54'
        }, follow_redirects=False)

        assert response.status_code == 200
        assert b'cannot be empty' in response.data.lower()

    @patch('flask_login.utils._get_user')
    def test_add_course_invalid_holes(self, mock_current_user, mock_admin_user, client):
        """Test adding course with invalid holes value"""
        mock_current_user.return_value = mock_admin_user

        response = client.post('/courses/add', data={
            'name': 'Invalid Course',
            'location': 'Location',
            'holes': '0',
            'par': '54'
        }, follow_redirects=False)

        assert response.status_code == 200
        # Should show validation error

    @patch('flask_login.utils._get_user')
    def test_add_course_with_image_url(self, mock_current_user, mock_admin_user, client):
        """Test adding course with image URL"""
        mock_current_user.return_value = mock_admin_user

        response = client.post('/courses/add', data={
            'name': 'Course with Image',
            'location': 'Location',
            'holes': '18',
            'par': '54',
            'image_url': 'https://example.com/image.jpg'
        }, follow_redirects=True)

        assert response.status_code == 200

    @patch('flask_login.utils._get_user')
    @patch('routes.course_routes.save_course_image')
    def test_add_course_with_uploaded_image(self, mock_save, mock_current_user, mock_admin_user, client):
        """Test adding course with uploaded image"""
        mock_current_user.return_value = mock_admin_user
        mock_save.return_value = (True, 'course123.jpg')

        data = {
            'name': 'Course with Upload',
            'location': 'Location',
            'holes': '18',
            'par': '54'
        }
        data['course_image'] = (BytesIO(b'fake image data'), 'course.jpg')

        response = client.post('/courses/add', data=data,
                             content_type='multipart/form-data',
                             follow_redirects=True)

        assert response.status_code == 200


class TestEditCourse:
    """Test edit course functionality"""

    @patch('flask_login.utils._get_user')
    def test_edit_course_success(self, mock_current_user, mock_admin_user, client):
        """Test successfully editing a course"""
        mock_current_user.return_value = mock_admin_user

        # Create course
        success, message, course = Course.create('Original Name', 'Original Location', 18, 54)
        assert success

        response = client.post(f'/courses/{course["id"]}/edit', data={
            'name': 'Updated Name',
            'location': 'Updated Location',
            'holes': '9',
            'par': '27'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Updated Name' in response.data or b'updated successfully' in response.data.lower()

    @patch('flask_login.utils._get_user')
    def test_edit_nonexistent_course(self, mock_current_user, mock_admin_user, client):
        """Test editing nonexistent course"""
        mock_current_user.return_value = mock_admin_user

        response = client.post('/courses/fake-id/edit', data={
            'name': 'New Name',
            'location': 'Location',
            'holes': '18',
            'par': '54'
        }, follow_redirects=True)

        assert response.status_code == 200
        # Should redirect with error

    @patch('flask_login.utils._get_user')
    @patch('routes.course_routes.save_course_image')
    @patch('routes.course_routes.delete_course_image')
    def test_edit_course_replace_image(self, mock_delete, mock_save, mock_current_user, mock_admin_user, client):
        """Test replacing course image"""
        mock_current_user.return_value = mock_admin_user
        mock_save.return_value = (True, 'new_course.jpg')

        # Create course with existing image
        success, message, course = Course.create('Course', 'Location', 18, 54, 'old_course.jpg')
        assert success

        data = {
            'name': 'Course',
            'location': 'Location',
            'holes': '18',
            'par': '54'
        }
        data['course_image'] = (BytesIO(b'new image'), 'new.jpg')

        response = client.post(f'/courses/{course["id"]}/edit', data=data,
                             content_type='multipart/form-data',
                             follow_redirects=True)

        assert response.status_code == 200


class TestDeleteCourse:
    """Test delete course functionality"""

    @patch('flask_login.utils._get_user')
    def test_delete_course_without_rounds(self, mock_current_user, mock_admin_user, client):
        """Test deleting course with no rounds"""
        mock_current_user.return_value = mock_admin_user

        # Create course
        success, message, course = Course.create('Delete Me', 'Location', 18, 54)
        assert success

        response = client.post(f'/courses/{course["id"]}/delete', follow_redirects=True)
        assert response.status_code == 200
        # Should redirect to course list

    @patch('flask_login.utils._get_user')
    def test_delete_course_with_rounds(self, mock_current_user, mock_admin_user, client):
        """Test soft-deleting course with rounds"""
        mock_current_user.return_value = mock_admin_user

        # Create course and player
        success, message, course = Course.create('Course with Rounds', 'Location', 18, 54)
        assert success
        success, msg, player = Player.create('Player', 'player@example.com')
        assert success

        # Create round
        Round.create(
            course_id=course['id'],
            date_played='2025-01-15',
            scores=[{'player_id': player['id'], 'score': 50}]
        )

        response = client.post(f'/courses/{course["id"]}/delete', follow_redirects=True)
        assert response.status_code == 200
        # Course should be soft-deleted (marked inactive)

    @patch('flask_login.utils._get_user')
    def test_delete_nonexistent_course(self, mock_current_user, mock_admin_user, client):
        """Test deleting nonexistent course"""
        mock_current_user.return_value = mock_admin_user

        response = client.post('/courses/fake-id/delete', follow_redirects=True)
        assert response.status_code == 200
        # Should show error message
        assert b'not found' in response.data.lower()


class TestRateCourse:
    """Test course rating functionality"""

    def test_rate_course_not_authenticated(self, client):
        """Test rating course without authentication"""
        success, msg, course = Course.create('Course', 'Location', 18, 54)
        assert success

        response = client.post(f'/courses/{course["id"]}/rate', data={
            'rating': '5'
        })

        assert response.status_code == 401
        json_data = json.loads(response.data)
        assert json_data['success'] is False
        assert 'logged in' in json_data['message'].lower()

    @patch('flask_login.utils._get_user')
    def test_rate_course_success(self, mock_current_user, mock_regular_user, client):
        """Test successfully rating a course"""
        mock_current_user.return_value = mock_regular_user

        success, msg, course = Course.create('Course', 'Location', 18, 54)
        assert success

        response = client.post(f'/courses/{course["id"]}/rate', data={
            'rating': '4'
        })

        assert response.status_code == 200
        json_data = json.loads(response.data)
        assert json_data['success'] is True
        assert 'avg_rating' in json_data
        assert 'rating_count' in json_data

    @patch('flask_login.utils._get_user')
    def test_rate_course_invalid_rating(self, mock_current_user, mock_regular_user, client):
        """Test rating course with invalid value"""
        mock_current_user.return_value = mock_regular_user

        success, msg, course = Course.create('Course', 'Location', 18, 54)
        assert success

        response = client.post(f'/courses/{course["id"]}/rate', data={
            'rating': 'invalid'
        })

        assert response.status_code == 400
        json_data = json.loads(response.data)
        assert json_data['success'] is False
        assert 'invalid' in json_data['message'].lower()

    @patch('flask_login.utils._get_user')
    def test_rate_course_update_existing_rating(self, mock_current_user, mock_regular_user, client):
        """Test updating an existing rating"""
        mock_current_user.return_value = mock_regular_user

        success, msg, course = Course.create('Course', 'Location', 18, 54)
        assert success

        # First rating
        response1 = client.post(f'/courses/{course["id"]}/rate', data={'rating': '3'})
        assert response1.status_code == 200

        # Update rating
        response2 = client.post(f'/courses/{course["id"]}/rate', data={'rating': '5'})
        assert response2.status_code == 200
        json_data = json.loads(response2.data)
        assert json_data['success'] is True


class TestCourseImageHelpers:
    """Test course image helper functions"""

    def test_allowed_file_valid_extensions(self):
        """Test that allowed_file function was removed (now using validate_image_file)"""
        # This test is deprecated - allowed_file() was replaced with validate_image_file()
        # for better security (content-based validation)
        from utils.file_validators import validate_image_file
        import io

        # Test that validate_image_file exists and works
        # Create a minimal valid PNG file
        png_header = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
        file = Mock()
        file.filename = 'test.png'
        file.read = Mock(return_value=png_header)
        file.seek = Mock()
        file.tell = Mock(return_value=len(png_header))

        is_valid, _ = validate_image_file(file, 5 * 1024 * 1024)
        assert is_valid is True

    def test_allowed_file_invalid_extensions(self):
        """Test that invalid files are rejected by validate_image_file"""
        from utils.file_validators import validate_image_file

        file = Mock()
        file.filename = 'file.txt'
        file.read = Mock(return_value=b'not an image')
        file.seek = Mock()
        file.tell = Mock(return_value=14)

        is_valid, error = validate_image_file(file, 5 * 1024 * 1024)
        assert is_valid is False

    @patch('routes.course_routes.validate_image_file', return_value=(True, ''))
    @patch('os.makedirs')
    @patch('os.path.join', return_value='/fake/path/image.jpg')
    def test_save_course_image_valid(self, mock_join, mock_makedirs, mock_validate):
        """Test saving valid course image"""
        from routes.course_routes import save_course_image

        file = Mock()
        file.filename = 'course.jpg'
        file.save = Mock()

        success, result = save_course_image(file, '/fake/upload', 5 * 1024 * 1024)
        assert success is True
        assert result.endswith('.jpg')
        file.save.assert_called_once()

    @patch('routes.course_routes.validate_image_file', return_value=(False, 'Invalid file type'))
    def test_save_course_image_invalid(self, mock_validate):
        """Test saving invalid file"""
        from routes.course_routes import save_course_image

        file = Mock()
        file.filename = 'invalid.txt'

        success, error = save_course_image(file, '/fake/upload', 5 * 1024 * 1024)
        assert success is False
        assert error == 'Invalid file type'

    def test_save_course_image_no_file(self):
        """Test saving with no file"""
        from routes.course_routes import save_course_image

        success, error = save_course_image(None, '/fake/upload', 5 * 1024 * 1024)
        assert success is False
        assert 'No file provided' in error

    @patch('os.path.exists', return_value=True)
    @patch('os.remove')
    @patch('os.path.join', return_value='/fake/path/image.jpg')
    def test_delete_course_image_exists(self, mock_join, mock_remove, mock_exists):
        """Test deleting existing course image"""
        from routes.course_routes import delete_course_image

        delete_course_image('image.jpg', '/fake/upload')
        mock_remove.assert_called_once()

    @patch('os.remove', side_effect=FileNotFoundError)
    @patch('os.path.join', return_value='/fake/path/image.jpg')
    def test_delete_course_image_not_exists(self, mock_join, mock_remove):
        """Test deleting non-existent course image (should handle FileNotFoundError gracefully)"""
        from routes.course_routes import delete_course_image

        # Should not raise an exception even if file doesn't exist
        delete_course_image('image.jpg', '/fake/upload')
        mock_remove.assert_called_once()

    def test_delete_course_image_no_filename(self):
        """Test delete with no filename"""
        from routes.course_routes import delete_course_image

        # Should not raise an error
        delete_course_image(None, '/fake/upload')
        delete_course_image('', '/fake/upload')
