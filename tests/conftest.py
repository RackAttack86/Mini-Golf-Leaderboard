"""
Pytest fixtures and configuration for Mini Golf Leaderboard tests.

This module provides shared fixtures for testing the application,
including test data, SQLite database setup, and Flask app configurations.
"""
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, UTC, timedelta
from unittest.mock import MagicMock

from app import create_app
from models.database import Database, init_database
from models.player import Player
from models.course import Course
from models.round import Round


@pytest.fixture(scope='session')
def test_data_dir():
    """
    Create a temporary directory for test data that persists for the entire test session.

    Yields:
        Path: Path to temporary test data directory
    """
    temp_dir = tempfile.mkdtemp(prefix='minigolf_test_')
    yield Path(temp_dir)
    # Cleanup after all tests
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def database(test_data_dir):
    """
    Create a fresh SQLite database for each test.

    This ensures test isolation by providing a clean database
    with no pre-existing data.

    Args:
        test_data_dir: Temporary directory for test data

    Returns:
        Database: Fresh Database instance
    """
    # Create a unique database file for this test
    db_file = test_data_dir / f'test_{datetime.now().timestamp()}.db'

    # Reset any existing database singleton
    Database.reset()

    # Initialize new database with schema (skip seed data for clean tests)
    db = init_database(db_file, skip_seed_data=True)

    yield db

    # Cleanup
    db.close()
    Database.reset()
    if db_file.exists():
        db_file.unlink()


@pytest.fixture
def data_store(database):
    """
    Alias for database fixture for backward compatibility.

    Many tests still reference 'data_store' - this allows them to work
    without immediate refactoring.

    Args:
        database: Database fixture

    Returns:
        Database: Same as database fixture
    """
    return database


@pytest.fixture
def app(database):
    """
    Create and configure a Flask application for testing.

    Args:
        database: Test database fixture

    Returns:
        Flask: Configured Flask application in testing mode
    """
    # Set testing environment variables
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['SECRET_KEY'] = 'test-secret-key'
    os.environ['GOOGLE_OAUTH_CLIENT_ID'] = 'test-client-id'
    os.environ['GOOGLE_OAUTH_CLIENT_SECRET'] = 'test-client-secret'

    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['RATELIMIT_ENABLED'] = False  # Disable rate limiting in tests

    # Provide mock csp_nonce for templates (Talisman is disabled in debug/test mode)
    @app.context_processor
    def inject_csp_nonce():
        def csp_nonce():
            return 'test-nonce'
        return {'csp_nonce': csp_nonce}

    yield app


@pytest.fixture
def client(app):
    """
    Create a test client for making HTTP requests.

    Args:
        app: Flask application fixture

    Returns:
        FlaskClient: Test client for the application
    """
    return app.test_client()


@pytest.fixture
def runner(app):
    """
    Create a test CLI runner.

    Args:
        app: Flask application fixture

    Returns:
        FlaskCliRunner: CLI runner for testing commands
    """
    return app.test_cli_runner()


# Sample test data fixtures

@pytest.fixture
def sample_player_data():
    """
    Provide sample player data for testing.

    Returns:
        dict: Sample player dictionary
    """
    return {
        'id': 'test-player-1',
        'name': 'John Doe',
        'email': 'john@example.com',
        'profile_picture': '',
        'favorite_color': '#2e7d32',
        'google_id': None,
        'role': 'player',
        'last_login': None,
        'created_at': datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'active': True
    }


@pytest.fixture
def sample_course_data():
    """
    Provide sample course data for testing.

    Returns:
        dict: Sample course dictionary
    """
    return {
        'id': 'test-course-1',
        'name': 'Sunset Golf',
        'location': 'Beach Town',
        'holes': 18,
        'par': 54,
        'image_url': '',
        'created_at': datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'active': True
    }


@pytest.fixture
def sample_round_data():
    """
    Provide sample round data for testing.

    Returns:
        dict: Sample round dictionary
    """
    return {
        'id': 'test-round-1',
        'course_id': 'test-course-1',
        'course_name': 'Sunset Golf',
        'date_played': '2024-01-15',
        'timestamp': datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'scores': [
            {
                'player_id': 'test-player-1',
                'player_name': 'John Doe',
                'score': 50
            },
            {
                'player_id': 'test-player-2',
                'player_name': 'Jane Smith',
                'score': 52
            }
        ],
        'notes': 'Great game!'
    }


@pytest.fixture
def sample_rating_data():
    """
    Provide sample course rating data for testing.

    Returns:
        dict: Sample rating dictionary
    """
    return {
        'player_id': 'test-player-1',
        'course_id': 'test-course-1',
        'rating': 5,
        'date_rated': datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
    }


@pytest.fixture
def populated_data_store(database, sample_player_data, sample_course_data, sample_round_data):
    """
    Create a database pre-populated with sample data.

    This is useful for tests that need existing data to work with.
    Uses direct database inserts to maintain backward compatibility with tests
    that expect specific IDs like 'test-player-1', 'test-course-1', etc.

    Args:
        database: Empty database fixture
        sample_player_data: Sample player data
        sample_course_data: Sample course data
        sample_round_data: Sample round data

    Returns:
        Database: Populated database instance
    """
    conn = database.get_connection()

    # Insert players with fixed IDs for test compatibility
    conn.execute("""
        INSERT INTO players (id, name, email, profile_picture, favorite_color, google_id, role, last_login, created_at, active)
        VALUES ('test-player-1', 'John Doe', 'john@example.com', '', '#2e7d32', NULL, 'player', NULL, ?, 1)
    """, (datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),))

    conn.execute("""
        INSERT INTO players (id, name, email, profile_picture, favorite_color, google_id, role, last_login, created_at, active)
        VALUES ('test-player-2', 'Jane Smith', 'jane@example.com', '', '#1976d2', NULL, 'player', NULL, ?, 1)
    """, (datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),))

    # Insert courses with fixed IDs
    conn.execute("""
        INSERT INTO courses (id, name, location, holes, par, image_url, created_at, active)
        VALUES ('test-course-1', 'Sunset Golf', 'Beach Town', 18, 54, '', ?, 1)
    """, (datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),))

    conn.execute("""
        INSERT INTO courses (id, name, location, holes, par, image_url, created_at, active)
        VALUES ('test-course-2', 'Mountain Course (HARD)', 'Mountain Valley', 18, 54, '', ?, 1)
    """, (datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),))

    # Insert a round with fixed ID
    round_timestamp = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
    conn.execute("""
        INSERT INTO rounds (id, course_id, course_name, date_played, timestamp, round_start_time, notes, picture_filename)
        VALUES ('test-round-1', 'test-course-1', 'Sunset Golf', '2024-01-15', ?, NULL, 'Great game!', NULL)
    """, (round_timestamp,))

    # Insert round scores
    conn.execute("""
        INSERT INTO round_scores (round_id, player_id, player_name, score, hole_scores)
        VALUES ('test-round-1', 'test-player-1', 'John Doe', 50, NULL)
    """)

    conn.execute("""
        INSERT INTO round_scores (round_id, player_id, player_name, score, hole_scores)
        VALUES ('test-round-1', 'test-player-2', 'Jane Smith', 52, NULL)
    """)

    return database


@pytest.fixture
def mock_google_oauth():
    """
    Mock Google OAuth blueprint for testing authentication.

    Returns:
        MagicMock: Mocked OAuth blueprint
    """
    mock = MagicMock()
    mock.token = {'access_token': 'test-token'}
    return mock


@pytest.fixture
def dates_helper():
    """
    Provide helper functions for generating test dates.

    Returns:
        dict: Dictionary of date helper functions
    """
    return {
        'today': lambda: datetime.now().strftime('%Y-%m-%d'),
        'yesterday': lambda: (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
        'last_week': lambda: (datetime.now() - timedelta(weeks=1)).strftime('%Y-%m-%d'),
        'next_week': lambda: (datetime.now() + timedelta(weeks=1)).strftime('%Y-%m-%d'),
        'days_ago': lambda n: (datetime.now() - timedelta(days=n)).strftime('%Y-%m-%d'),
    }


@pytest.fixture
def validation_test_cases():
    """
    Provide common validation test cases.

    Returns:
        dict: Dictionary of validation test cases
    """
    return {
        'valid_emails': [
            'user@example.com',
            'test.user@domain.co.uk',
            'name+tag@test.org'
        ],
        'invalid_emails': [
            'notanemail',
            '@example.com',
            'user@',
            'user@domain',
            'a' * 100 + '@example.com'  # Too long
        ],
        'valid_names': [
            'John Doe',
            'Jane',
            'Bob Smith Jr.',
            'A' * 100  # Max length
        ],
        'invalid_names': [
            '',
            '   ',
            'A' * 101  # Too long
        ],
        'valid_scores': [
            0, 1, 50, 100, 500, -50
        ],
        'invalid_scores': [
            -51, 501, 'abc', None
        ]
    }


# Helper functions for assertions

def assert_player_equal(player1, player2, ignore_fields=None):
    """
    Assert that two player dictionaries are equal, optionally ignoring certain fields.

    Args:
        player1: First player dictionary
        player2: Second player dictionary
        ignore_fields: List of field names to ignore in comparison
    """
    ignore_fields = ignore_fields or []
    for key in player1:
        if key not in ignore_fields:
            assert player1[key] == player2[key], f"Field {key} differs: {player1[key]} != {player2[key]}"


def assert_course_equal(course1, course2, ignore_fields=None):
    """
    Assert that two course dictionaries are equal, optionally ignoring certain fields.

    Args:
        course1: First course dictionary
        course2: Second course dictionary
        ignore_fields: List of field names to ignore in comparison
    """
    ignore_fields = ignore_fields or []
    for key in course1:
        if key not in ignore_fields:
            assert course1[key] == course2[key], f"Field {key} differs: {course1[key]} != {course2[key]}"


# Export helper functions
pytest.assert_player_equal = assert_player_equal
pytest.assert_course_equal = assert_course_equal
