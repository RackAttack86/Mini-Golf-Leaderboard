# Quick Start Guide - Testing

Get up and running with tests in 5 minutes.

## Installation

```bash
# Install test dependencies
pip install -r requirements-test.txt
```

## Run Tests

```bash
# Run all tests
pytest

# Run with details
pytest -v

# Run with coverage
pytest --cov
```

## Common Commands

```bash
# Run specific test file
pytest tests/models/test_player.py

# Run specific test
pytest tests/models/test_player.py::TestPlayerCreate::test_create_player_minimal

# Run tests matching pattern
pytest -k "test_create"

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Stop at first failure
pytest -x

# Show print statements
pytest -s

# Parallel execution
pytest -n auto
```

## Check Coverage

```bash
# Terminal report
pytest --cov=models --cov=services --cov=utils --cov-report=term-missing

# HTML report
pytest --cov=models --cov=services --cov=utils --cov-report=html
# Open htmlcov/index.html in browser
```

## Test Structure

```
tests/
├── models/          # Model tests (Player, Course, Round, etc.)
├── services/        # Service tests (Auth, Achievements)
├── utils/           # Utility tests (Validators)
└── routes/          # Route tests (Integration)
```

## Writing a Test

```python
import pytest
from models.player import Player


@pytest.mark.unit
@pytest.mark.models
def test_create_player(data_store):
    """Test creating a new player"""
    # Arrange
    name = 'Test Player'

    # Act
    success, message, player = Player.create(name=name)

    # Assert
    assert success is True
    assert player['name'] == name
```

## Useful Markers

- `@pytest.mark.unit` - Unit test
- `@pytest.mark.integration` - Integration test
- `@pytest.mark.models` - Model test
- `@pytest.mark.services` - Service test
- `@pytest.mark.auth` - Authentication test

## Troubleshooting

**Tests not found?**
- Run from project root: `cd /path/to/Mini-Golf-Leaderboard`

**Import errors?**
- Install requirements: `pip install -r requirements-test.txt`

**Coverage too low?**
- Check missing lines: `pytest --cov-report=term-missing`

## Next Steps

- Read [TESTING.md](../TESTING.md) for detailed guide
- Read [TEST_SUMMARY.md](TEST_SUMMARY.md) for test overview
- Check [conftest.py](conftest.py) for available fixtures

---

Happy Testing! 🧪
