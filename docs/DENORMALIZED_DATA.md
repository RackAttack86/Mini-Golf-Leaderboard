# Denormalized Data Architecture

## Overview

The Mini Golf Leaderboard application uses denormalized data in certain places to improve query performance and reduce the need for joins across multiple JSON files. This document explains where denormalization occurs and how data consistency is maintained.

## Denormalized Fields

### Round Model

The `Round` model stores denormalized copies of player and course names for performance:

```python
{
    'id': 'round-uuid',
    'course_id': 'course-uuid',
    'course_name': 'Pirate Adventure Mini Golf',  # Denormalized
    'date_played': '2025-01-15',
    'scores': [
        {
            'player_id': 'player-uuid',
            'player_name': 'John Doe',  # Denormalized
            'score': 45
        }
    ]
}
```

**Why denormalize?**
- Displaying a list of rounds requires showing player and course names
- Without denormalization, each round display would require looking up the player and course in separate files
- With 100+ rounds, this would mean hundreds of file reads for a single page load
- Denormalization allows reading just the rounds file to display complete information

## Maintaining Data Consistency

### Automatic Sync on Updates

When a player or course name is updated, the denormalized copies in all related rounds are automatically updated:

#### Player Name Updates

`models/player.py`:
```python
def update(player_id: str, name: Optional[str] = None, ...):
    # ... validate and update player ...

    # If name changed, update denormalized copies in rounds
    if name and name != old_name:
        Player._update_name_in_rounds(player_id, player['name'])
```

The `_update_name_in_rounds()` method:
1. Reads all rounds
2. Finds rounds containing the player
3. Updates the `player_name` in those rounds
4. Writes the rounds back to disk

#### Course Name Updates

`models/course.py`:
```python
def update(course_id: str, name: Optional[str] = None, ...):
    # ... validate and update course ...

    # If name changed, update denormalized copies in rounds
    if name and name != old_name:
        Course._update_name_in_rounds(course_id, course['name'])
```

Works similarly to player updates.

### Performance Considerations

**Write Performance:**
- Updating a player/course name requires reading and writing the entire rounds file
- This is acceptable because:
  - Name changes are infrequent
  - The application is designed for small-to-medium datasets (< 10,000 rounds)
  - Write operations are atomic (no corruption risk)

**Read Performance:**
- Displaying rounds is fast - single file read with complete data
- No need for complex joins or lookups
- Trade-off: Slower writes for much faster reads

## Testing

The denormalized data sync is tested in:
- `tests/models/test_player.py::TestPlayerUpdate::test_update_name_updates_rounds`
- `tests/models/test_course.py::TestCourseUpdate::test_update_name_updates_rounds`

These tests verify that:
1. When a player/course name is updated
2. All rounds containing that player/course are updated
3. The denormalized names match the new names

## Edge Cases & Limitations

### Deletion
When a player or course is deleted:
- **Soft delete**: The rounds keep the old denormalized names (player/course still exists but is inactive)
- **Force delete**: The rounds are also deleted (data integrity maintained)

### Data Migration
If you need to repair inconsistent denormalized data, you can:

1. Run a data consistency check (future feature)
2. Or manually rebuild denormalized data using:

```python
from models.player import Player
from models.course import Course
from models.round import Round
from models.data_store import get_data_store

def rebuild_denormalized_data():
    """Rebuild all denormalized player and course names in rounds"""
    store = get_data_store()
    data = store.read_rounds()

    for round_data in data['rounds']:
        # Update course name
        course = Course.get_by_id(round_data['course_id'])
        if course:
            round_data['course_name'] = course['name']

        # Update player names
        for score in round_data['scores']:
            player = Player.get_by_id(score['player_id'])
            if player:
                score['player_name'] = player['name']

    store.write_rounds(data)
```

## Design Decisions

### Why Not Use IDs Only?

Alternative approach: Store only IDs and always look up names on read.

**Rejected because:**
- Would require reading 3 files (rounds, players, courses) for every page load
- With JSON file storage, this is slow (no database indexes)
- Displaying 50 rounds would mean 50+ player lookups and 50+ course lookups
- Complexity increases for sorting/filtering

### Why Not Use a Database?

This project intentionally uses JSON file storage for:
- Simplicity - no database setup required
- Portability - data is human-readable JSON files
- Version control - data can be committed to git
- Education - good learning example of file-based storage

For larger applications, a relational database would be more appropriate.

## Future Improvements

Potential enhancements to consider:

1. **Consistency Checker**: CLI command to validate denormalized data
2. **Automatic Repair**: Detect and fix inconsistencies on startup
3. **Change Tracking**: Log when denormalized data is updated
4. **Caching**: Cache player/course lookups to reduce repeated file reads

## Related Files

- `models/player.py` - Player model with `_update_name_in_rounds()`
- `models/course.py` - Course model with `_update_name_in_rounds()`
- `models/round.py` - Round model with denormalized fields
- `models/data_store.py` - Atomic file operations for thread safety
