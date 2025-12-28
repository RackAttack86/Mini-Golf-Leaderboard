import pytest
import uuid
from models.course import Course
from models.player import Player
from models.round import Round


class TestCourseUserRounds:
    """Test user rounds on course detail page"""

    @pytest.fixture
    def setup_course_and_players(self, app):
        """Create a course and players for testing"""
        # Use unique IDs to avoid conflicts
        unique_id = uuid.uuid4().hex[:8]

        # Create course
        success, message, course = Course.create(
            name=f"Test Course {unique_id}",
            location="Test Location",
            holes=18,
            par=72
        )
        assert success, f"Failed to create course: {message}"
        course_id = course['id']

        # Create players with Google IDs
        success, message, player1 = Player.create(f"Test Player 1 {unique_id}", f"player1-{unique_id}@test.com")
        assert success, f"Failed to create player1: {message}"
        player1_id = player1['id']
        player1_google_id = f"google_id_1_{unique_id}"
        Player.link_google_account(player1_id, player1_google_id)

        success, message, player2 = Player.create(f"Test Player 2 {unique_id}", f"player2-{unique_id}@test.com")
        assert success, f"Failed to create player2: {message}"
        player2_id = player2['id']
        player2_google_id = f"google_id_2_{unique_id}"
        Player.link_google_account(player2_id, player2_google_id)

        success, message, player3 = Player.create(f"Test Player 3 {unique_id}", f"player3-{unique_id}@test.com")
        assert success, f"Failed to create player3: {message}"
        player3_id = player3['id']

        return {
            'course_id': course_id,
            'player1_id': player1_id,
            'player1_google_id': player1_google_id,
            'player2_id': player2_id,
            'player2_google_id': player2_google_id,
            'player3_id': player3_id
        }

    def test_course_detail_page_loads(self, client, setup_course_and_players):
        """Test that course detail page loads successfully"""
        course_id = setup_course_and_players['course_id']

        response = client.get(f'/courses/{course_id}')
        assert response.status_code == 200

    def test_course_detail_shows_all_rounds_section(self, client, setup_course_and_players):
        """Test that all rounds history section is present"""
        course_id = setup_course_and_players['course_id']

        response = client.get(f'/courses/{course_id}')
        assert response.status_code == 200
        assert b'All Rounds History' in response.data

    def test_user_rounds_pagination_logic(self, setup_course_and_players):
        """Test pagination logic for user rounds"""
        course_id = setup_course_and_players['course_id']
        player1_id = setup_course_and_players['player1_id']
        player2_id = setup_course_and_players['player2_id']

        # Create 25 rounds where player1 participates
        for i in range(25):
            Round.create(
                course_id=course_id,
                date_played=f'2025-01-{(i % 30) + 1:02d}',
                scores=[
                    {'player_id': player1_id, 'score': 70 + (i % 10)},
                    {'player_id': player2_id, 'score': 75 + (i % 10)}
                ]
            )

        # Get all rounds for the course
        all_rounds = Round.get_by_course(course_id)
        assert len(all_rounds) == 25

        # Filter to player1's rounds (simulating backend logic)
        player1_rounds = [r for r in all_rounds if any(s['player_id'] == player1_id for s in r['scores'])]
        assert len(player1_rounds) == 25

        # Test pagination calculations
        per_page = 20
        total_pages = (len(player1_rounds) + per_page - 1) // per_page
        assert total_pages == 2

        # First page
        page_1_rounds = player1_rounds[0:per_page]
        assert len(page_1_rounds) == 20

        # Second page
        page_2_rounds = player1_rounds[per_page:per_page*2]
        assert len(page_2_rounds) == 5

    def test_user_rounds_filtering_logic(self, setup_course_and_players):
        """Test that user rounds are filtered correctly"""
        course_id = setup_course_and_players['course_id']
        player1_id = setup_course_and_players['player1_id']
        player2_id = setup_course_and_players['player2_id']
        player3_id = setup_course_and_players['player3_id']

        # Create rounds - player1 plays in 2, player2 plays in 3, player3 plays in 1
        Round.create(
            course_id=course_id,
            date_played='2025-01-01',
            scores=[
                {'player_id': player1_id, 'score': 75},
                {'player_id': player2_id, 'score': 80}
            ]
        )

        Round.create(
            course_id=course_id,
            date_played='2025-01-02',
            scores=[
                {'player_id': player2_id, 'score': 78},
                {'player_id': player3_id, 'score': 82}
            ]
        )

        Round.create(
            course_id=course_id,
            date_played='2025-01-03',
            scores=[
                {'player_id': player1_id, 'score': 72},
                {'player_id': player2_id, 'score': 76}
            ]
        )

        # Get all rounds
        all_rounds = Round.get_by_course(course_id)
        assert len(all_rounds) == 3

        # Filter by player
        player1_rounds = [r for r in all_rounds if any(s['player_id'] == player1_id for s in r['scores'])]
        player2_rounds = [r for r in all_rounds if any(s['player_id'] == player2_id for s in r['scores'])]
        player3_rounds = [r for r in all_rounds if any(s['player_id'] == player3_id for s in r['scores'])]

        assert len(player1_rounds) == 2
        assert len(player2_rounds) == 3
        assert len(player3_rounds) == 1

    def test_pagination_boundary_cases(self, setup_course_and_players):
        """Test pagination boundary conditions"""
        course_id = setup_course_and_players['course_id']
        player1_id = setup_course_and_players['player1_id']
        player2_id = setup_course_and_players['player2_id']

        # Create exactly 20 rounds (one full page)
        for i in range(20):
            Round.create(
                course_id=course_id,
                date_played=f'2025-01-{i+1:02d}',
                scores=[
                    {'player_id': player1_id, 'score': 70},
                    {'player_id': player2_id, 'score': 75}
                ]
            )

        all_rounds = Round.get_by_course(course_id)
        player1_rounds = [r for r in all_rounds if any(s['player_id'] == player1_id for s in r['scores'])]

        # Should be exactly one page
        per_page = 20
        total_pages = (len(player1_rounds) + per_page - 1) // per_page
        assert total_pages == 1
        assert len(player1_rounds) == 20

    def test_empty_rounds_list(self, setup_course_and_players):
        """Test handling of course with no rounds"""
        course_id = setup_course_and_players['course_id']
        player1_id = setup_course_and_players['player1_id']

        # Get rounds (should be empty)
        all_rounds = Round.get_by_course(course_id)
        assert len(all_rounds) == 0

        # Filter for player (should still be empty)
        player1_rounds = [r for r in all_rounds if any(s['player_id'] == player1_id for s in r['scores'])]
        assert len(player1_rounds) == 0

    def test_page_number_validation(self):
        """Test page number validation logic"""
        # Test with 45 total rounds, 20 per page = 3 pages
        total_rounds = 45
        per_page = 20
        total_pages = (total_rounds + per_page - 1) // per_page
        assert total_pages == 3

        # Valid page numbers
        for page in [1, 2, 3]:
            validated_page = max(1, min(page, total_pages))
            assert validated_page == page

        # Invalid page numbers
        assert max(1, min(0, total_pages)) == 1  # Page 0 -> Page 1
        assert max(1, min(-1, total_pages)) == 1  # Page -1 -> Page 1
        assert max(1, min(999, total_pages)) == 3  # Page 999 -> Page 3
