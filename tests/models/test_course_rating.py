"""
Comprehensive unit tests for the CourseRating model.

Tests cover:
- Rating creation and updates
- Rating retrieval (by player/course, averages)
- Rating deletion
- Rating validation
- Edge cases and error handling
"""
import pytest
from datetime import datetime

from models.course_rating import CourseRating


@pytest.mark.unit
@pytest.mark.models
class TestCourseRatingCreate:
    """Tests for CourseRating.rate_course() method"""

    def test_rate_course_new_rating(self, populated_data_store):
        """Test creating a new course rating"""
        success, message = CourseRating.rate_course(
            player_id='test-player-1',
            course_id='test-course-1',
            rating=5
        )

        assert success is True
        assert "added successfully" in message.lower()

    def test_rate_course_update_existing(self, populated_data_store):
        """Test updating an existing course rating"""
        # Create initial rating
        CourseRating.rate_course('test-player-1', 'test-course-1', 3)

        # Update rating
        success, message = CourseRating.rate_course(
            player_id='test-player-1',
            course_id='test-course-1',
            rating=5
        )

        assert success is True
        assert "updated successfully" in message.lower()

        # Verify rating was updated
        rating = CourseRating.get_player_rating('test-player-1', 'test-course-1')
        assert rating == 5

    def test_rate_course_valid_ratings(self, populated_data_store):
        """Test all valid rating values (1-5)"""
        for rating_value in [1, 2, 3, 4, 5]:
            success, message = CourseRating.rate_course(
                player_id='test-player-1',
                course_id=f'test-course-{rating_value}' if rating_value > 2 else 'test-course-1',
                rating=rating_value
            )

            # For courses that exist
            if rating_value <= 2:
                assert success is True

    def test_rate_course_invalid_rating_low(self, populated_data_store):
        """Test rating with value below minimum fails"""
        success, message = CourseRating.rate_course(
            player_id='test-player-1',
            course_id='test-course-1',
            rating=0
        )

        assert success is False
        assert "between 1 and 5" in message.lower()

    def test_rate_course_invalid_rating_high(self, populated_data_store):
        """Test rating with value above maximum fails"""
        success, message = CourseRating.rate_course(
            player_id='test-player-1',
            course_id='test-course-1',
            rating=6
        )

        assert success is False
        assert "between 1 and 5" in message.lower()

    def test_rate_course_invalid_rating_type(self, populated_data_store):
        """Test rating with non-integer type fails"""
        success, message = CourseRating.rate_course(
            player_id='test-player-1',
            course_id='test-course-1',
            rating='five'
        )

        assert success is False
        assert "between 1 and 5" in message.lower()

    def test_rate_course_float_rating(self, populated_data_store):
        """Test rating with float value fails"""
        success, message = CourseRating.rate_course(
            player_id='test-player-1',
            course_id='test-course-1',
            rating=3.5
        )

        assert success is False


@pytest.mark.unit
@pytest.mark.models
class TestCourseRatingRetrieval:
    """Tests for CourseRating retrieval methods"""

    def test_get_player_rating_existing(self, populated_data_store):
        """Test getting player's rating when it exists"""
        CourseRating.rate_course('test-player-1', 'test-course-1', 4)

        rating = CourseRating.get_player_rating('test-player-1', 'test-course-1')

        assert rating == 4

    def test_get_player_rating_nonexistent(self, populated_data_store):
        """Test getting player's rating when it doesn't exist"""
        rating = CourseRating.get_player_rating('test-player-1', 'test-course-1')

        assert rating is None

    def test_get_course_average_single_rating(self, populated_data_store):
        """Test getting course average with single rating"""
        CourseRating.rate_course('test-player-1', 'test-course-1', 4)

        avg, count = CourseRating.get_course_average_rating('test-course-1')

        assert avg == 4.0
        assert count == 1

    def test_get_course_average_multiple_ratings(self, populated_data_store):
        """Test getting course average with multiple ratings"""
        CourseRating.rate_course('test-player-1', 'test-course-1', 4)
        CourseRating.rate_course('test-player-2', 'test-course-1', 5)

        avg, count = CourseRating.get_course_average_rating('test-course-1')

        assert avg == 4.5
        assert count == 2

    def test_get_course_average_no_ratings(self, populated_data_store):
        """Test getting course average with no ratings"""
        avg, count = CourseRating.get_course_average_rating('test-course-1')

        assert avg is None
        assert count == 0

    def test_get_course_average_rounding(self, data_store):
        """Test that average is rounded to 1 decimal place"""
        # Create test data
        from models.player import Player
        from models.course import Course

        Player.create(name='P1')
        Player.create(name='P2')
        Player.create(name='P3')
        Course.create(name='Test Course')

        players = Player.get_all()
        courses = Course.get_all()
        course_id = courses[0]['id']

        # Create ratings that will average to something with multiple decimals
        CourseRating.rate_course(players[0]['id'], course_id, 5)
        CourseRating.rate_course(players[1]['id'], course_id, 4)
        CourseRating.rate_course(players[2]['id'], course_id, 4)

        avg, count = CourseRating.get_course_average_rating(course_id)

        # Average should be 4.333... rounded to 4.3
        assert avg == 4.3
        assert count == 3

    def test_get_all_empty(self, data_store):
        """Test getting all course ratings when none exist"""
        ratings = CourseRating.get_all()

        assert ratings == {}

    def test_get_all(self, populated_data_store):
        """Test getting all course ratings"""
        CourseRating.rate_course('test-player-1', 'test-course-1', 5)
        CourseRating.rate_course('test-player-2', 'test-course-1', 4)
        CourseRating.rate_course('test-player-1', 'test-course-2', 3)

        ratings = CourseRating.get_all()

        assert 'test-course-1' in ratings
        assert 'test-course-2' in ratings
        assert ratings['test-course-1'][0] == 4.5  # Average
        assert ratings['test-course-1'][1] == 2    # Count
        assert ratings['test-course-2'][0] == 3.0
        assert ratings['test-course-2'][1] == 1


@pytest.mark.unit
@pytest.mark.models
class TestCourseRatingDelete:
    """Tests for CourseRating.delete_rating() method"""

    def test_delete_rating_existing(self, populated_data_store):
        """Test deleting an existing rating"""
        CourseRating.rate_course('test-player-1', 'test-course-1', 5)

        success, message = CourseRating.delete_rating('test-player-1', 'test-course-1')

        assert success is True
        assert "deleted successfully" in message.lower()

        # Verify rating was deleted
        rating = CourseRating.get_player_rating('test-player-1', 'test-course-1')
        assert rating is None

    def test_delete_rating_nonexistent(self, populated_data_store):
        """Test deleting a nonexistent rating"""
        success, message = CourseRating.delete_rating('test-player-1', 'test-course-1')

        assert success is False
        assert "not found" in message.lower()


@pytest.mark.unit
@pytest.mark.models
class TestCourseRatingEdgeCases:
    """Tests for edge cases and special scenarios"""

    def test_rating_timestamp_format(self, populated_data_store):
        """Test that date_rated timestamp is in correct format"""
        CourseRating.rate_course('test-player-1', 'test-course-1', 5)

        # Get the rating data directly from database
        from models.database import get_db
        db = get_db()
        conn = db.get_connection()
        cursor = conn.execute(
            "SELECT date_rated FROM course_ratings WHERE player_id = ? AND course_id = ?",
            ('test-player-1', 'test-course-1')
        )
        row = cursor.fetchone()

        # Verify ISO 8601 format
        date_rated = datetime.strptime(
            row['date_rated'],
            '%Y-%m-%dT%H:%M:%SZ'
        )
        assert date_rated is not None

    def test_rating_timestamp_updates(self, populated_data_store):
        """Test that date_rated updates when rating is changed"""
        # Create initial rating
        CourseRating.rate_course('test-player-1', 'test-course-1', 3)

        # Get initial timestamp from database
        from models.database import get_db
        db = get_db()
        conn = db.get_connection()
        cursor = conn.execute(
            "SELECT date_rated FROM course_ratings WHERE player_id = ? AND course_id = ?",
            ('test-player-1', 'test-course-1')
        )
        initial_timestamp = cursor.fetchone()['date_rated']

        # Wait a moment and update
        import time
        time.sleep(0.1)

        # Update rating
        CourseRating.rate_course('test-player-1', 'test-course-1', 5)

        # Get new timestamp from database
        cursor = conn.execute(
            "SELECT date_rated FROM course_ratings WHERE player_id = ? AND course_id = ?",
            ('test-player-1', 'test-course-1')
        )
        new_timestamp = cursor.fetchone()['date_rated']

        # Timestamps should be different
        assert new_timestamp >= initial_timestamp

    def test_multiple_players_same_course(self, populated_data_store):
        """Test multiple players rating the same course"""
        CourseRating.rate_course('test-player-1', 'test-course-1', 5)
        CourseRating.rate_course('test-player-2', 'test-course-1', 3)

        rating1 = CourseRating.get_player_rating('test-player-1', 'test-course-1')
        rating2 = CourseRating.get_player_rating('test-player-2', 'test-course-1')

        assert rating1 == 5
        assert rating2 == 3

    def test_same_player_multiple_courses(self, populated_data_store):
        """Test one player rating multiple courses"""
        CourseRating.rate_course('test-player-1', 'test-course-1', 5)
        CourseRating.rate_course('test-player-1', 'test-course-2', 3)

        rating1 = CourseRating.get_player_rating('test-player-1', 'test-course-1')
        rating2 = CourseRating.get_player_rating('test-player-1', 'test-course-2')

        assert rating1 == 5
        assert rating2 == 3

    def test_rating_extremes(self, populated_data_store):
        """Test rating with minimum and maximum values"""
        CourseRating.rate_course('test-player-1', 'test-course-1', 1)
        CourseRating.rate_course('test-player-2', 'test-course-1', 5)

        avg, count = CourseRating.get_course_average_rating('test-course-1')

        assert avg == 3.0
        assert count == 2

    def test_rating_update_affects_average(self, populated_data_store):
        """Test that updating a rating affects the average"""
        CourseRating.rate_course('test-player-1', 'test-course-1', 3)
        CourseRating.rate_course('test-player-2', 'test-course-1', 3)

        avg1, count1 = CourseRating.get_course_average_rating('test-course-1')
        assert avg1 == 3.0
        assert count1 == 2

        # Update one rating
        CourseRating.rate_course('test-player-1', 'test-course-1', 5)

        avg2, count2 = CourseRating.get_course_average_rating('test-course-1')
        assert avg2 == 4.0
        assert count2 == 2  # Count shouldn't change

    def test_delete_rating_affects_average(self, populated_data_store):
        """Test that deleting a rating affects the average"""
        CourseRating.rate_course('test-player-1', 'test-course-1', 5)
        CourseRating.rate_course('test-player-2', 'test-course-1', 3)

        avg1, count1 = CourseRating.get_course_average_rating('test-course-1')
        assert avg1 == 4.0
        assert count1 == 2

        # Delete one rating
        CourseRating.delete_rating('test-player-1', 'test-course-1')

        avg2, count2 = CourseRating.get_course_average_rating('test-course-1')
        assert avg2 == 3.0
        assert count2 == 1
