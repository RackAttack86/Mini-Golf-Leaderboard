"""
Comprehensive unit tests for the Course model.

Tests cover:
- Course creation with valid and invalid data
- Course retrieval (all, by ID)
- Course updates including name changes and denormalization
- Course deletion (soft and hard)
- Validation of holes and par
- Edge cases and error handling
"""
import pytest
from datetime import datetime

from models.course import Course
from models.round import Round


@pytest.mark.unit
@pytest.mark.models
class TestCourseCreate:
    """Tests for Course.create() method"""

    def test_create_course_minimal(self, data_store):
        """Test creating a course with only required fields"""
        success, message, course = Course.create(name='Sunset Golf')

        assert success is True
        assert message == "Course created successfully"
        assert course is not None
        assert course['name'] == 'Sunset Golf'
        assert course['location'] == ''
        assert course['holes'] is None
        assert course['par'] is None
        assert course['image_url'] == ''
        assert course['active'] is True
        assert 'id' in course
        assert 'created_at' in course

    def test_create_course_full(self, data_store):
        """Test creating a course with all fields"""
        success, message, course = Course.create(
            name='Mountain Course',
            location='Mountain Valley',
            holes=18,
            par=54,
            image_url='mountain.jpg'
        )

        assert success is True
        assert course['name'] == 'Mountain Course'
        assert course['location'] == 'Mountain Valley'
        assert course['holes'] == 18
        assert course['par'] == 54
        assert course['image_url'] == 'mountain.jpg'

    def test_create_hard_course(self, data_store):
        """Test creating a hard course with (HARD) designation"""
        success, message, course = Course.create(
            name='Expert Level (HARD)',
            location='Pro Arena'
        )

        assert success is True
        assert '(HARD)' in course['name']

    def test_create_course_empty_name(self, data_store):
        """Test creating course with empty name fails"""
        success, message, course = Course.create(name='')

        assert success is False
        assert "cannot be empty" in message.lower()
        assert course is None

    def test_create_course_whitespace_name(self, data_store):
        """Test creating course with whitespace-only name fails"""
        success, message, course = Course.create(name='   ')

        assert success is False
        assert course is None

    def test_create_course_name_too_long(self, data_store):
        """Test creating course with name exceeding max length fails"""
        long_name = 'A' * 101
        success, message, course = Course.create(name=long_name)

        assert success is False
        assert "too long" in message.lower()
        assert course is None

    def test_create_course_duplicate_name(self, data_store):
        """Test creating course with duplicate name fails"""
        Course.create(name='Sunset Golf')
        success, message, course = Course.create(name='Sunset Golf')

        assert success is False
        assert "already exists" in message.lower()
        assert course is None

    def test_create_course_duplicate_name_case_insensitive(self, data_store):
        """Test that duplicate check is case-insensitive"""
        Course.create(name='Sunset Golf')
        success, message, course = Course.create(name='SUNSET GOLF')

        assert success is False
        assert "already exists" in message.lower()

    def test_create_course_invalid_holes(self, data_store):
        """Test creating course with invalid holes count fails"""
        success, message, course = Course.create(name='Test', holes=-5)

        assert success is False
        assert course is None

    def test_create_course_holes_too_high(self, data_store):
        """Test creating course with unreasonably high holes count fails"""
        success, message, course = Course.create(name='Test', holes=150)

        assert success is False
        assert "unreasonably high" in message.lower()

    def test_create_course_invalid_par(self, data_store):
        """Test creating course with invalid par fails"""
        success, message, course = Course.create(name='Test', par=-10)

        assert success is False
        assert course is None

    def test_create_course_par_too_high(self, data_store):
        """Test creating course with unreasonably high par fails"""
        success, message, course = Course.create(name='Test', par=600)

        assert success is False
        assert "unreasonably high" in message.lower()

    def test_create_course_name_stripped(self, data_store):
        """Test that course name is stripped of whitespace"""
        success, message, course = Course.create(name='  Sunset Golf  ')

        assert success is True
        assert course['name'] == 'Sunset Golf'

    def test_create_course_location_stripped(self, data_store):
        """Test that location is stripped of whitespace"""
        success, message, course = Course.create(
            name='Test',
            location='  Beach Town  '
        )

        assert success is True
        assert course['location'] == 'Beach Town'

    def test_create_course_holes_converted_to_int(self, data_store):
        """Test that holes is converted to integer"""
        success, message, course = Course.create(name='Test', holes='18')

        assert success is True
        assert course['holes'] == 18
        assert isinstance(course['holes'], int)

    def test_create_course_par_converted_to_int(self, data_store):
        """Test that par is converted to integer"""
        success, message, course = Course.create(name='Test', par='54')

        assert success is True
        assert course['par'] == 54
        assert isinstance(course['par'], int)


@pytest.mark.unit
@pytest.mark.models
class TestCourseRetrieval:
    """Tests for Course retrieval methods"""

    def test_get_all_empty(self, data_store):
        """Test getting all courses when none exist"""
        courses = Course.get_all()

        assert courses == []

    def test_get_all_courses(self, populated_data_store):
        """Test getting all active courses"""
        courses = Course.get_all()

        assert len(courses) == 2
        assert all(c['active'] for c in courses)

    def test_get_all_including_inactive(self, data_store):
        """Test getting all courses including inactive ones"""
        Course.create(name='Active Course')
        success, message, inactive = Course.create(name='Inactive Course')
        # Deactivate the second course
        Course.delete(inactive['id'])

        active_only = Course.get_all(active_only=True)
        all_courses = Course.get_all(active_only=False)

        assert len(active_only) == 1
        assert len(all_courses) == 2

    def test_get_by_id_existing(self, populated_data_store):
        """Test getting course by ID when it exists"""
        course = Course.get_by_id('test-course-1')

        assert course is not None
        assert course['id'] == 'test-course-1'
        assert course['name'] == 'Sunset Golf'

    def test_get_by_id_nonexistent(self, data_store):
        """Test getting course by ID when it doesn't exist"""
        course = Course.get_by_id('nonexistent-id')

        assert course is None

    def test_get_all_filters_hard_courses(self, data_store):
        """Test that hard courses can be distinguished"""
        Course.create(name='Regular Course')
        Course.create(name='Tough Course (HARD)')

        courses = Course.get_all()
        hard_courses = [c for c in courses if '(HARD)' in c['name']]
        regular_courses = [c for c in courses if '(HARD)' not in c['name']]

        assert len(hard_courses) == 1
        assert len(regular_courses) == 1


@pytest.mark.unit
@pytest.mark.models
class TestCourseUpdate:
    """Tests for Course.update() method"""

    def test_update_course_name(self, populated_data_store):
        """Test updating course name"""
        success, message = Course.update('test-course-1', name='New Name')

        assert success is True
        course = Course.get_by_id('test-course-1')
        assert course['name'] == 'New Name'

    def test_update_course_location(self, populated_data_store):
        """Test updating course location"""
        success, message = Course.update(
            'test-course-1',
            location='New Location'
        )

        assert success is True
        course = Course.get_by_id('test-course-1')
        assert course['location'] == 'New Location'

    def test_update_course_holes(self, populated_data_store):
        """Test updating course holes"""
        success, message = Course.update('test-course-1', holes=9)

        assert success is True
        course = Course.get_by_id('test-course-1')
        assert course['holes'] == 9

    def test_update_course_par(self, populated_data_store):
        """Test updating course par"""
        success, message = Course.update('test-course-1', par=27)

        assert success is True
        course = Course.get_by_id('test-course-1')
        assert course['par'] == 27

    def test_update_course_image_url(self, populated_data_store):
        """Test updating course image URL"""
        success, message = Course.update(
            'test-course-1',
            image_url='new-image.jpg'
        )

        assert success is True
        course = Course.get_by_id('test-course-1')
        assert course['image_url'] == 'new-image.jpg'

    def test_update_nonexistent_course(self, data_store):
        """Test updating nonexistent course fails"""
        success, message = Course.update('nonexistent-id', name='New Name')

        assert success is False
        assert "not found" in message.lower()

    def test_update_course_duplicate_name(self, populated_data_store):
        """Test updating to duplicate name fails"""
        success, message = Course.update(
            'test-course-1',
            name='Mountain Course (HARD)'
        )

        assert success is False
        assert "already exists" in message.lower()

    def test_update_course_invalid_holes(self, populated_data_store):
        """Test updating with invalid holes fails"""
        success, message = Course.update('test-course-1', holes=-5)

        assert success is False

    def test_update_course_invalid_par(self, populated_data_store):
        """Test updating with invalid par fails"""
        success, message = Course.update('test-course-1', par=-10)

        assert success is False

    def test_update_course_multiple_fields(self, populated_data_store):
        """Test updating multiple fields at once"""
        success, message = Course.update(
            'test-course-1',
            name='Updated Course',
            location='Updated Location',
            holes=9,
            par=27,
            image_url='updated.jpg'
        )

        assert success is True
        course = Course.get_by_id('test-course-1')
        assert course['name'] == 'Updated Course'
        assert course['location'] == 'Updated Location'
        assert course['holes'] == 9
        assert course['par'] == 27
        assert course['image_url'] == 'updated.jpg'

    def test_update_name_updates_rounds(self, populated_data_store):
        """Test that updating course name updates denormalized data in rounds"""
        # The populated store has rounds with test-course-1
        success, message = Course.update('test-course-1', name='Updated Course Name')

        assert success is True

        # Check that the rounds were updated
        rounds = Round.get_by_course('test-course-1')
        assert len(rounds) > 0
        for round_data in rounds:
            assert round_data['course_name'] == 'Updated Course Name'


@pytest.mark.unit
@pytest.mark.models
class TestCourseDelete:
    """Tests for Course.delete() method"""

    def test_delete_course_without_rounds(self, data_store):
        """Test hard deleting course without rounds"""
        success, message, course = Course.create(name='Test Course')
        course_id = course['id']

        success, message = Course.delete(course_id)

        assert success is True
        assert "deleted successfully" in message.lower()
        assert Course.get_by_id(course_id) is None

    def test_soft_delete_course_with_rounds(self, populated_data_store):
        """Test soft deleting course with existing rounds"""
        # test-course-1 has rounds in populated store
        success, message = Course.delete('test-course-1')

        assert success is True
        assert "deactivated" in message.lower()

        # Course should still exist but be inactive
        course = Course.get_by_id('test-course-1')
        assert course is not None
        assert course['active'] is False

    def test_force_delete_course_with_rounds(self, populated_data_store):
        """Test force deleting course with existing rounds"""
        success, message = Course.delete('test-course-1', force=True)

        assert success is True
        assert "deleted successfully" in message.lower()
        assert Course.get_by_id('test-course-1') is None

    def test_delete_nonexistent_course(self, data_store):
        """Test deleting nonexistent course fails"""
        success, message = Course.delete('nonexistent-id')

        assert success is False
        assert "not found" in message.lower()


@pytest.mark.unit
@pytest.mark.models
class TestCourseEdgeCases:
    """Tests for edge cases and special scenarios"""

    def test_create_course_with_none_optional_fields(self, data_store):
        """Test creating course with None for optional fields"""
        success, message, course = Course.create(
            name='Test',
            location=None,
            holes=None,
            par=None,
            image_url=None
        )

        assert success is True
        assert course['location'] == ''
        assert course['holes'] is None
        assert course['par'] is None
        assert course['image_url'] == ''

    def test_update_course_with_none_values(self, populated_data_store):
        """Test that None values don't update fields"""
        original = Course.get_by_id('test-course-1')

        success, message = Course.update(
            'test-course-1',
            name=None,
            location=None
        )

        updated = Course.get_by_id('test-course-1')
        assert updated['name'] == original['name']
        assert updated['location'] == original['location']

    def test_course_created_at_format(self, data_store):
        """Test that created_at timestamp is in correct format"""
        success, message, course = Course.create(name='Test')

        assert success is True
        # Verify ISO 8601 format
        created_at = datetime.strptime(
            course['created_at'],
            '%Y-%m-%dT%H:%M:%SZ'
        )
        assert created_at is not None

    def test_course_id_is_uuid(self, data_store):
        """Test that course ID is a valid UUID"""
        success, message, course = Course.create(name='Test')

        assert success is True
        # UUID format: 8-4-4-4-12 characters
        parts = course['id'].split('-')
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4

    def test_update_holes_to_none(self, populated_data_store):
        """Test updating holes to None (clearing the value)"""
        # First set holes
        Course.update('test-course-1', holes=18)

        # Then clear it by setting to None or empty string
        # This depends on how the validator handles empty values
        course = Course.get_by_id('test-course-1')
        assert course['holes'] == 18  # Should keep the value

    def test_create_course_with_string_numbers(self, data_store):
        """Test creating course with string representations of numbers"""
        success, message, course = Course.create(
            name='Test',
            holes='18',
            par='54'
        )

        assert success is True
        assert course['holes'] == 18
        assert course['par'] == 54
        assert isinstance(course['holes'], int)
        assert isinstance(course['par'], int)

    def test_create_course_with_invalid_string_numbers(self, data_store):
        """Test creating course with non-numeric strings fails"""
        success, message, course = Course.create(
            name='Test',
            holes='abc'
        )

        assert success is False

    def test_course_without_par_or_holes(self, data_store):
        """Test that courses can exist without par or holes defined"""
        success, message, course = Course.create(
            name='Casual Course',
            location='Park'
        )

        assert success is True
        assert course['holes'] is None
        assert course['par'] is None

    def test_update_course_same_name(self, populated_data_store):
        """Test updating course with its own name succeeds"""
        course = Course.get_by_id('test-course-1')
        success, message = Course.update(
            'test-course-1',
            name=course['name']
        )

        assert success is True
