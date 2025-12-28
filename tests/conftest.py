"""
Pytest fixtures and configuration for Mini Golf Leaderboard tests.

This module provides shared fixtures for testing the application,
including test data, mock data stores, and Flask app configurations.
"""
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, UTC, timedelta
from unittest.mock import MagicMock

from app import create_app
from models.data_store import DataStore, init_data_store


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
def data_store(test_data_dir):
    """
    Create a fresh DataStore instance for each test.

    This ensures test isolation by providing a clean data store
    with no pre-existing data.

    Args:
        test_data_dir: Temporary directory for test data

    Returns:
        DataStore: Fresh DataStore instance
    """
    # Create a unique subdirectory for this test
    test_subdir = test_data_dir / f'test_{datetime.now().timestamp()}'
    test_subdir.mkdir(parents=True, exist_ok=True)

    store = init_data_store(test_subdir)
    yield store

    # Cleanup test subdirectory
    shutil.rmtree(test_subdir, ignore_errors=True)


@pytest.fixture
def app(data_store):
    """
    Create and configure a Flask application for testing.

    Args:
        data_store: Test data store fixture

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

    # Re-initialize data store with test directory after create_app()
    # This ensures tests use isolated test data instead of production data
    init_data_store(data_store.data_dir)

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
def populated_data_store(data_store, sample_player_data, sample_course_data, sample_round_data):
    """
    Create a data store pre-populated with sample data.

    This is useful for tests that need existing data to work with.

    Args:
        data_store: Empty data store fixture
        sample_player_data: Sample player data
        sample_course_data: Sample course data
        sample_round_data: Sample round data

    Returns:
        DataStore: Populated data store instance
    """
    # Add players
    players_data = data_store.read_players()
    players_data['players'].append(sample_player_data)
    players_data['players'].append({
        **sample_player_data,
        'id': 'test-player-2',
        'name': 'Jane Smith',
        'email': 'jane@example.com'
    })
    data_store.write_players(players_data)

    # Add courses
    courses_data = data_store.read_courses()
    courses_data['courses'].append(sample_course_data)
    courses_data['courses'].append({
        **sample_course_data,
        'id': 'test-course-2',
        'name': 'Mountain Course (HARD)',
        'location': 'Mountain Valley'
    })
    data_store.write_courses(courses_data)

    # Add rounds
    rounds_data = data_store.read_rounds()
    rounds_data['rounds'].append(sample_round_data)
    data_store.write_rounds(rounds_data)

    return data_store


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
