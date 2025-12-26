# Testing Guide for Mini Golf Leaderboard

This guide provides comprehensive instructions for running and writing tests for the Mini Golf Leaderboard application.

## Table of Contents

- [Overview](#overview)
- [Test Structure](#test-structure)
- [Installation](#installation)
- [Running Tests](#running-tests)
- [Test Coverage](#test-coverage)
- [Writing Tests](#writing-tests)
- [Best Practices](#best-practices)
- [Continuous Integration](#continuous-integration)
- [Troubleshooting](#troubleshooting)

## Overview

The Mini Golf Leaderboard application uses **pytest** as the primary testing framework. The test suite includes:

- **Unit Tests**: Test individual components (models, services, validators) in isolation
- **Integration Tests**: Test Flask routes and component interactions
- **Fixtures**: Reusable test data and configuration
- **Code Coverage**: Minimum 80% coverage requirement

### Test Statistics

- **Total Test Files**: 10+
- **Test Coverage Target**: 80%
- **Test Categories**: Unit, Integration, Authentication

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Shared fixtures and configuration
├── models/                     # Model tests
│   ├── __init__.py
│   ├── test_player.py         # Player model tests
│   ├── test_course.py         # Course model tests
│   ├── test_round.py          # Round model tests
│   └── test_course_rating.py  # CourseRating model tests
├── services/                   # Service layer tests
│   ├── __init__.py
│   ├── test_auth_service.py   # Authentication service tests
│   └── test_achievement_service.py  # Achievement service tests
├── utils/                      # Utility tests
│   ├── __init__.py
│   └── test_validators.py     # Validation function tests
└── routes/                     # Route integration tests
    ├── __init__.py
    └── test_main_routes.py    # Main route tests
```

## Installation

### Install Testing Dependencies

Install all testing dependencies using pip:

```bash
# Install test dependencies
pip install -r requirements-test.txt
```

Or install just pytest and coverage:

```bash
pip install pytest pytest-cov pytest-flask
```

### Verify Installation

```bash
pytest --version
```

You should see pytest version 7.4.3 or higher.

## Running Tests

### Run All Tests

```bash
# Run all tests with verbose output
pytest -v

# Run with coverage report
pytest --cov=models --cov=services --cov=utils --cov=routes
```

### Run Specific Test Categories

```bash
# Run only unit tests
pytest -v -m unit

# Run only integration tests
pytest -v -m integration

# Run only model tests
pytest -v -m models

# Run only authentication tests
pytest -v -m auth
```

### Run Specific Test Files

```bash
# Run player model tests
pytest tests/models/test_player.py -v

# Run auth service tests
pytest tests/services/test_auth_service.py -v

# Run validator tests
pytest tests/utils/test_validators.py -v
```

### Run Specific Test Classes or Functions

```bash
# Run a specific test class
pytest tests/models/test_player.py::TestPlayerCreate -v

# Run a specific test function
pytest tests/models/test_player.py::TestPlayerCreate::test_create_player_minimal -v
```

### Parallel Test Execution

For faster test execution, run tests in parallel:

```bash
# Run tests using 4 CPU cores
pytest -n 4

# Run tests using all available CPU cores
pytest -n auto
```

## Test Coverage

### Generate Coverage Report

```bash
# Generate terminal coverage report
pytest --cov=models --cov=services --cov=utils --cov=routes --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=models --cov=services --cov=utils --cov=routes --cov-report=html

# Open HTML coverage report (generated in htmlcov/index.html)
```

### Coverage Requirements

The project enforces a minimum of **80% code coverage**. The pytest configuration (`pytest.ini`) will fail the test run if coverage falls below this threshold.

### View Coverage Report

After running tests with coverage, open the HTML report:

```bash
# Windows
start htmlcov/index.html

# macOS
open htmlcov/index.html

# Linux
xdg-open htmlcov/index.html
```

## Writing Tests

### Test File Naming

- Test files must start with `test_` (e.g., `test_player.py`)
- Test functions must start with `test_` (e.g., `test_create_player`)
- Test classes should start with `Test` (e.g., `TestPlayerCreate`)

### Using Fixtures

Fixtures provide reusable test data and setup. Use the fixtures defined in `conftest.py`:

```python
def test_example(data_store, sample_player_data):
    """Example test using fixtures"""
    # data_store provides a clean database
    # sample_player_data provides sample player dictionary

    from models.player import Player
    success, message, player = Player.create(**sample_player_data)
    assert success is True
```

### Common Fixtures

- `data_store`: Fresh DataStore instance with clean test data
- `populated_data_store`: DataStore with sample players, courses, and rounds
- `sample_player_data`: Sample player dictionary
- `sample_course_data`: Sample course dictionary
- `sample_round_data`: Sample round dictionary
- `dates_helper`: Helper functions for generating test dates
- `client`: Flask test client for route testing
- `app`: Flask application instance in test mode

### Test Markers

Use markers to categorize tests:

```python
import pytest

@pytest.mark.unit
@pytest.mark.models
def test_create_player(data_store):
    """Test player creation"""
    # Test code here
```

Available markers:
- `unit`: Unit tests
- `integration`: Integration tests
- `slow`: Long-running tests
- `auth`: Authentication tests
- `models`: Model tests
- `services`: Service layer tests
- `routes`: Route tests
- `validators`: Validator tests

### Test Structure Best Practices

```python
import pytest
from models.player import Player


@pytest.mark.unit
@pytest.mark.models
class TestPlayerCreate:
    """Tests for Player.create() method"""

    def test_create_player_minimal(self, data_store):
        """
        Test creating a player with only required fields.

        This test verifies:
        1. Player creation succeeds with minimal data
        2. Default values are set correctly
        3. Player is marked as active
        """
        # Arrange
        name = 'John Doe'

        # Act
        success, message, player = Player.create(name=name)

        # Assert
        assert success is True
        assert message == "Player created successfully"
        assert player['name'] == name
        assert player['active'] is True
        assert 'id' in player
```

### Testing Error Cases

Always test both success and failure scenarios:

```python
def test_create_player_empty_name(self, data_store):
    """Test that creating player with empty name fails"""
    success, message, player = Player.create(name='')

    assert success is False
    assert "cannot be empty" in message.lower()
    assert player is None
```

### Testing Edge Cases

```python
def test_create_player_name_at_max_length(self, data_store):
    """Test creating player with name at maximum length"""
    max_name = 'A' * 100
    success, message, player = Player.create(name=max_name)

    assert success is True
    assert len(player['name']) == 100
```

## Best Practices

### 1. Test Isolation

Each test should be independent and not rely on other tests:

```python
# Good - test is isolated
def test_create_player(data_store):
    player = Player.create(name='Test')
    assert player is not None

# Bad - test depends on previous test
def test_update_player():
    # Assumes player from previous test exists
    Player.update(player_id, name='Updated')  # May fail if run alone
```

### 2. Clear Test Names

Use descriptive test names that explain what is being tested:

```python
# Good
def test_create_player_with_invalid_email_fails():
    pass

# Bad
def test_player():
    pass
```

### 3. Use Docstrings

Add docstrings to explain what each test verifies:

```python
def test_create_round_denormalized_data(self, populated_data_store):
    """
    Test that player and course names are denormalized in rounds.

    This ensures that if a player or course name is changed later,
    historical round data retains the original names.
    """
    # Test implementation
```

### 4. Arrange-Act-Assert Pattern

Structure tests using the AAA pattern:

```python
def test_example(data_store):
    # Arrange - Set up test data
    name = 'Test Player'

    # Act - Perform the action
    success, message, player = Player.create(name=name)

    # Assert - Verify the results
    assert success is True
    assert player['name'] == name
```

### 5. Test One Thing

Each test should verify one specific behavior:

```python
# Good - tests one thing
def test_create_player_sets_default_color():
    player = Player.create(name='Test')
    assert player['favorite_color'] == '#2e7d32'

# Bad - tests multiple things
def test_create_player():
    player = Player.create(name='Test')
    assert player['name'] == 'Test'
    assert player['favorite_color'] == '#2e7d32'
    assert player['active'] is True
    # ... testing too many things
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        pip install -r requirements-test.txt

    - name: Run tests with coverage
      run: |
        pytest --cov=models --cov=services --cov=utils --cov=routes --cov-report=xml

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v2
```

## Troubleshooting

### Common Issues

#### 1. Import Errors

**Problem**: `ModuleNotFoundError: No module named 'models'`

**Solution**: Ensure you're running tests from the project root directory:

```bash
cd /path/to/Mini-Golf-Leaderboard
pytest
```

#### 2. Fixture Not Found

**Problem**: `fixture 'data_store' not found`

**Solution**: Ensure `conftest.py` is in the `tests/` directory and pytest can find it.

#### 3. Tests Fail Due to Existing Data

**Problem**: Tests fail because of leftover data from previous runs

**Solution**: Tests use temporary directories that are cleaned up automatically. If issues persist, check that fixtures are properly isolated.

#### 4. Coverage Too Low

**Problem**: Coverage report shows less than 80%

**Solution**:
- Check which files have low coverage: `pytest --cov=models --cov-report=term-missing`
- Add tests for uncovered lines
- Focus on critical paths first

### Debug Mode

Run tests with more verbose output:

```bash
# Show print statements
pytest -v -s

# Show full error tracebacks
pytest -v --tb=long

# Stop at first failure
pytest -x

# Drop into debugger on failure
pytest --pdb
```

### Check Test Collection

See which tests will be run without executing them:

```bash
pytest --collect-only
```

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Flask Testing Documentation](https://flask.palletsprojects.com/en/latest/testing/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Writing Better Tests (Blog)](https://docs.pytest.org/en/latest/explanation/goodpractices.html)

## Getting Help

If you encounter issues with tests:

1. Check this documentation
2. Review test examples in `tests/` directory
3. Check pytest documentation
4. Review test output carefully for error messages

---

**Last Updated**: December 2024
**Maintained By**: Development Team
