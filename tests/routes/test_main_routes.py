"""
Integration tests for main application routes.

Tests cover:
- Home page rendering
- Basic route accessibility
- Error handling
- Authentication requirements
"""
import pytest


@pytest.mark.integration
@pytest.mark.routes
class TestMainRoutes:
    """Tests for main application routes"""

    def test_home_page_accessible(self, client):
        """Test that home page is accessible"""
        response = client.get('/')

        assert response.status_code == 200

    def test_home_page_renders(self, client):
        """Test that home page renders without errors"""
        response = client.get('/')

        assert response.status_code == 200
        assert b'Mini Golf' in response.data or b'Leaderboard' in response.data

    def test_404_page(self, client):
        """Test 404 error handling"""
        response = client.get('/nonexistent-page')

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.routes
class TestPlayerRoutes:
    """Tests for player-related routes"""

    def test_players_list_accessible(self, client):
        """Test that players list page is accessible"""
        response = client.get('/players/')

        # Should either render or redirect to login
        assert response.status_code in [200, 302]

    def test_player_detail_nonexistent(self, client):
        """Test accessing nonexistent player"""
        response = client.get('/players/nonexistent-id')

        # Should either 404 or redirect
        assert response.status_code in [302, 404]


@pytest.mark.integration
@pytest.mark.routes
class TestCourseRoutes:
    """Tests for course-related routes"""

    def test_courses_list_accessible(self, client):
        """Test that courses list page is accessible"""
        response = client.get('/courses/')

        # Should either render or redirect to login
        assert response.status_code in [200, 302]

    def test_course_detail_nonexistent(self, client):
        """Test accessing nonexistent course"""
        response = client.get('/courses/nonexistent-id')

        # Should either 404 or redirect
        assert response.status_code in [302, 404]


@pytest.mark.integration
@pytest.mark.routes
class TestRoundRoutes:
    """Tests for round-related routes"""

    def test_rounds_list_accessible(self, client):
        """Test that rounds list page is accessible"""
        response = client.get('/rounds/')

        # Should either render or redirect to login
        assert response.status_code in [200, 302]
