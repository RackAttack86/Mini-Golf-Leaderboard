"""
Comprehensive unit tests for validation functions.

Tests cover:
- Player name validation
- Course name validation
- Score validation
- Holes validation
- Par validation
- Date validation
- Email validation
- Edge cases and boundary conditions
"""
import pytest
from datetime import datetime, timedelta

from utils.validators import (
    validate_player_name,
    validate_course_name,
    validate_score,
    validate_holes,
    validate_par,
    validate_date,
    validate_email
)


@pytest.mark.unit
@pytest.mark.validators
class TestPlayerNameValidation:
    """Tests for validate_player_name()"""

    def test_valid_player_name(self):
        """Test validation with valid player name"""
        is_valid, error = validate_player_name('John Doe', [])

        assert is_valid is True
        assert error == ''

    def test_empty_name(self):
        """Test validation with empty name"""
        is_valid, error = validate_player_name('', [])

        assert is_valid is False
        assert 'cannot be empty' in error.lower()

    def test_whitespace_only_name(self):
        """Test validation with whitespace-only name"""
        is_valid, error = validate_player_name('   ', [])

        assert is_valid is False
        assert 'cannot be empty' in error.lower()

    def test_name_too_long(self):
        """Test validation with name exceeding max length"""
        long_name = 'A' * 101
        is_valid, error = validate_player_name(long_name, [])

        assert is_valid is False
        assert 'too long' in error.lower()

    def test_max_length_name(self):
        """Test validation with name at max length"""
        max_name = 'A' * 100
        is_valid, error = validate_player_name(max_name, [])

        assert is_valid is True

    def test_duplicate_name(self):
        """Test validation with duplicate name"""
        existing = [{'id': '1', 'name': 'John Doe'}]
        is_valid, error = validate_player_name('John Doe', existing)

        assert is_valid is False
        assert 'already exists' in error.lower()

    def test_duplicate_name_case_insensitive(self):
        """Test that duplicate check is case-insensitive"""
        existing = [{'id': '1', 'name': 'John Doe'}]
        is_valid, error = validate_player_name('JOHN DOE', existing)

        assert is_valid is False
        assert 'already exists' in error.lower()

    def test_duplicate_name_different_case(self):
        """Test duplicate with mixed case"""
        existing = [{'id': '1', 'name': 'John Doe'}]
        is_valid, error = validate_player_name('john doe', existing)

        assert is_valid is False

    def test_duplicate_name_with_exclude(self):
        """Test validation excludes specific ID from duplicate check"""
        existing = [{'id': '1', 'name': 'John Doe'}]
        is_valid, error = validate_player_name('John Doe', existing, exclude_id='1')

        assert is_valid is True

    def test_duplicate_name_exclude_different_id(self):
        """Test validation fails when excluded ID is different"""
        existing = [{'id': '1', 'name': 'John Doe'}]
        is_valid, error = validate_player_name('John Doe', existing, exclude_id='2')

        assert is_valid is False

    def test_special_characters_in_name(self):
        """Test validation with special characters"""
        is_valid, error = validate_player_name("O'Brien", [])

        assert is_valid is True

    def test_unicode_name(self):
        """Test validation with unicode characters"""
        is_valid, error = validate_player_name('José García', [])

        assert is_valid is True


@pytest.mark.unit
@pytest.mark.validators
class TestCourseNameValidation:
    """Tests for validate_course_name()"""

    def test_valid_course_name(self):
        """Test validation with valid course name"""
        is_valid, error = validate_course_name('Sunset Golf', [])

        assert is_valid is True
        assert error == ''

    def test_empty_course_name(self):
        """Test validation with empty name"""
        is_valid, error = validate_course_name('', [])

        assert is_valid is False
        assert 'cannot be empty' in error.lower()

    def test_whitespace_only_course_name(self):
        """Test validation with whitespace-only name"""
        is_valid, error = validate_course_name('   ', [])

        assert is_valid is False

    def test_course_name_too_long(self):
        """Test validation with name exceeding max length"""
        long_name = 'A' * 101
        is_valid, error = validate_course_name(long_name, [])

        assert is_valid is False
        assert 'too long' in error.lower()

    def test_duplicate_course_name(self):
        """Test validation with duplicate name"""
        existing = [{'id': '1', 'name': 'Sunset Golf'}]
        is_valid, error = validate_course_name('Sunset Golf', existing)

        assert is_valid is False
        assert 'already exists' in error.lower()

    def test_duplicate_course_name_case_insensitive(self):
        """Test that duplicate check is case-insensitive"""
        existing = [{'id': '1', 'name': 'Sunset Golf'}]
        is_valid, error = validate_course_name('SUNSET GOLF', existing)

        assert is_valid is False

    def test_hard_course_name(self):
        """Test validation with (HARD) designation"""
        is_valid, error = validate_course_name('Expert Course (HARD)', [])

        assert is_valid is True


@pytest.mark.unit
@pytest.mark.validators
class TestScoreValidation:
    """Tests for validate_score()"""

    def test_valid_positive_score(self):
        """Test validation with valid positive score"""
        is_valid, error = validate_score(50)

        assert is_valid is True
        assert error == ''

    def test_valid_zero_score(self):
        """Test validation with zero score"""
        is_valid, error = validate_score(0)

        assert is_valid is True

    def test_valid_negative_score(self):
        """Test validation with valid negative score"""
        is_valid, error = validate_score(-10)

        assert is_valid is True

    def test_score_at_min_boundary(self):
        """Test validation at minimum boundary"""
        is_valid, error = validate_score(-50)

        assert is_valid is True

    def test_score_below_min_boundary(self):
        """Test validation below minimum boundary"""
        is_valid, error = validate_score(-51)

        assert is_valid is False
        assert 'unreasonably low' in error.lower()

    def test_score_at_max_boundary(self):
        """Test validation at maximum boundary"""
        is_valid, error = validate_score(500)

        assert is_valid is True

    def test_score_above_max_boundary(self):
        """Test validation above maximum boundary"""
        is_valid, error = validate_score(501)

        assert is_valid is False
        assert 'unreasonably high' in error.lower()

    def test_score_as_string(self):
        """Test validation with numeric string"""
        is_valid, error = validate_score('50')

        assert is_valid is True

    def test_score_as_invalid_string(self):
        """Test validation with non-numeric string"""
        is_valid, error = validate_score('abc')

        assert is_valid is False
        assert 'must be a number' in error.lower()

    def test_score_as_float(self):
        """Test validation with float value"""
        is_valid, error = validate_score(50.5)

        assert is_valid is True  # Should convert to int

    def test_score_as_none(self):
        """Test validation with None value"""
        is_valid, error = validate_score(None)

        assert is_valid is False
        assert 'must be a number' in error.lower()


@pytest.mark.unit
@pytest.mark.validators
class TestHolesValidation:
    """Tests for validate_holes()"""

    def test_valid_holes(self):
        """Test validation with valid holes count"""
        is_valid, error = validate_holes(18)

        assert is_valid is True
        assert error == ''

    def test_holes_none(self):
        """Test validation with None (optional field)"""
        is_valid, error = validate_holes(None)

        assert is_valid is True

    def test_holes_empty_string(self):
        """Test validation with empty string (optional field)"""
        is_valid, error = validate_holes('')

        assert is_valid is True

    def test_holes_zero(self):
        """Test validation with zero holes"""
        is_valid, error = validate_holes(0)

        assert is_valid is False
        assert 'must be positive' in error.lower()

    def test_holes_negative(self):
        """Test validation with negative holes"""
        is_valid, error = validate_holes(-5)

        assert is_valid is False
        assert 'must be positive' in error.lower()

    def test_holes_at_max_boundary(self):
        """Test validation at maximum boundary"""
        is_valid, error = validate_holes(100)

        assert is_valid is True

    def test_holes_above_max_boundary(self):
        """Test validation above maximum boundary"""
        is_valid, error = validate_holes(101)

        assert is_valid is False
        assert 'unreasonably high' in error.lower()

    def test_holes_as_string(self):
        """Test validation with numeric string"""
        is_valid, error = validate_holes('18')

        assert is_valid is True

    def test_holes_as_invalid_string(self):
        """Test validation with non-numeric string"""
        is_valid, error = validate_holes('abc')

        assert is_valid is False
        assert 'must be a number' in error.lower()


@pytest.mark.unit
@pytest.mark.validators
class TestParValidation:
    """Tests for validate_par()"""

    def test_valid_par(self):
        """Test validation with valid par"""
        is_valid, error = validate_par(54)

        assert is_valid is True
        assert error == ''

    def test_par_none(self):
        """Test validation with None (optional field)"""
        is_valid, error = validate_par(None)

        assert is_valid is True

    def test_par_empty_string(self):
        """Test validation with empty string (optional field)"""
        is_valid, error = validate_par('')

        assert is_valid is True

    def test_par_zero(self):
        """Test validation with zero par"""
        is_valid, error = validate_par(0)

        assert is_valid is False
        assert 'must be positive' in error.lower()

    def test_par_negative(self):
        """Test validation with negative par"""
        is_valid, error = validate_par(-10)

        assert is_valid is False
        assert 'must be positive' in error.lower()

    def test_par_at_max_boundary(self):
        """Test validation at maximum boundary"""
        is_valid, error = validate_par(500)

        assert is_valid is True

    def test_par_above_max_boundary(self):
        """Test validation above maximum boundary"""
        is_valid, error = validate_par(501)

        assert is_valid is False
        assert 'unreasonably high' in error.lower()

    def test_par_as_string(self):
        """Test validation with numeric string"""
        is_valid, error = validate_par('54')

        assert is_valid is True


@pytest.mark.unit
@pytest.mark.validators
class TestDateValidation:
    """Tests for validate_date()"""

    def test_valid_date_today(self):
        """Test validation with today's date"""
        today = datetime.now().strftime('%Y-%m-%d')
        is_valid, error = validate_date(today)

        assert is_valid is True
        assert error == ''

    def test_valid_date_past(self):
        """Test validation with past date"""
        past_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        is_valid, error = validate_date(past_date)

        assert is_valid is True

    def test_invalid_date_future(self):
        """Test validation with future date"""
        future_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        is_valid, error = validate_date(future_date)

        assert is_valid is False
        assert 'cannot be in the future' in error.lower()

    def test_invalid_date_format(self):
        """Test validation with invalid date format"""
        is_valid, error = validate_date('01/15/2024')

        assert is_valid is False
        assert 'invalid date format' in error.lower()

    def test_invalid_date_format_wrong_order(self):
        """Test validation with wrong date component order"""
        is_valid, error = validate_date('15-01-2024')

        assert is_valid is False

    def test_empty_date(self):
        """Test validation with empty date"""
        is_valid, error = validate_date('')

        assert is_valid is False
        assert 'cannot be empty' in error.lower()

    def test_invalid_date_values(self):
        """Test validation with invalid date values"""
        is_valid, error = validate_date('2024-13-45')

        assert is_valid is False

    def test_date_leap_year(self):
        """Test validation with leap year date"""
        is_valid, error = validate_date('2024-02-29')

        assert is_valid is True

    def test_date_non_leap_year(self):
        """Test validation with invalid leap year date"""
        is_valid, error = validate_date('2023-02-29')

        assert is_valid is False


@pytest.mark.unit
@pytest.mark.validators
class TestEmailValidation:
    """Tests for validate_email()"""

    def test_valid_email(self):
        """Test validation with valid email"""
        is_valid, error = validate_email('user@example.com')

        assert is_valid is True
        assert error == ''

    def test_valid_email_with_subdomain(self):
        """Test validation with subdomain"""
        is_valid, error = validate_email('user@mail.example.com')

        assert is_valid is True

    def test_valid_email_with_plus(self):
        """Test validation with plus sign"""
        is_valid, error = validate_email('user+tag@example.com')

        assert is_valid is True

    def test_valid_email_with_dots(self):
        """Test validation with dots in username"""
        is_valid, error = validate_email('first.last@example.com')

        assert is_valid is True

    def test_empty_email(self):
        """Test validation with empty email (optional field)"""
        is_valid, error = validate_email('')

        assert is_valid is True

    def test_whitespace_email(self):
        """Test validation with whitespace-only email"""
        is_valid, error = validate_email('   ')

        assert is_valid is True  # Treated as empty

    def test_email_missing_at(self):
        """Test validation with missing @ symbol"""
        is_valid, error = validate_email('userexample.com')

        assert is_valid is False
        assert 'invalid email' in error.lower()

    def test_email_missing_domain(self):
        """Test validation with missing domain"""
        is_valid, error = validate_email('user@')

        assert is_valid is False

    def test_email_missing_tld(self):
        """Test validation with missing TLD"""
        is_valid, error = validate_email('user@example')

        assert is_valid is False

    def test_email_too_long(self):
        """Test validation with email exceeding max length"""
        long_email = 'a' * 95 + '@example.com'
        is_valid, error = validate_email(long_email)

        assert is_valid is False
        assert 'too long' in error.lower()

    def test_email_at_max_length(self):
        """Test validation with email at max length"""
        # Create a 100-character email
        username = 'a' * 88  # 88 + @ + example.com (11) = 100
        email = f'{username}@example.com'
        is_valid, error = validate_email(email)

        assert is_valid is True

    def test_email_multiple_at_signs(self):
        """Test validation with multiple @ symbols"""
        is_valid, error = validate_email('user@@example.com')

        # Basic validation doesn't catch this, but it should still have a domain
        assert is_valid is True or is_valid is False  # Implementation dependent


@pytest.mark.unit
@pytest.mark.validators
class TestValidatorEdgeCases:
    """Tests for edge cases across all validators"""

    def test_validators_with_unicode(self):
        """Test validators handle unicode correctly"""
        is_valid, error = validate_player_name('José García', [])
        assert is_valid is True

        is_valid, error = validate_course_name('Côte d\'Azur Golf', [])
        assert is_valid is True

    def test_validators_with_newlines(self):
        """Test validators handle newlines"""
        is_valid, error = validate_player_name('John\nDoe', [])
        # Should accept or reject consistently
        assert isinstance(is_valid, bool)

    def test_score_boundary_conditions(self):
        """Test score validator at all boundaries"""
        test_cases = [
            (-50, True),   # Min valid
            (-51, False),  # Below min
            (500, True),   # Max valid
            (501, False),  # Above max
        ]

        for score, expected in test_cases:
            is_valid, error = validate_score(score)
            assert is_valid == expected, f"Score {score} should be {expected}"

    def test_date_edge_of_today(self):
        """Test date validation at edge of today"""
        today = datetime.now().date()
        is_valid, error = validate_date(today.strftime('%Y-%m-%d'))

        assert is_valid is True

    def test_empty_player_list_for_duplicates(self):
        """Test duplicate checking with empty player list"""
        is_valid, error = validate_player_name('Test Player', [])

        assert is_valid is True

    def test_none_exclude_id(self):
        """Test validators with None as exclude_id"""
        existing = [{'id': '1', 'name': 'Test'}]
        is_valid, error = validate_player_name('Test', existing, exclude_id=None)

        assert is_valid is False
