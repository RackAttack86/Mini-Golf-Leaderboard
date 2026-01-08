# Codebase Cleanup TODO

This document tracks the remaining cleanup work from the refactoring plan. Phases 4 and 5 have been completed and merged to main.

## Status Summary
- ✅ Phase 4: Model Refactoring (COMPLETED)
- ✅ Phase 5: Minor Code Cleanup (COMPLETED)
- ⏳ Phase 1: Dead Code Removal (PENDING)
- ⏳ Phase 2: Import Organization (PENDING)
- ⏳ Phase 3: Template Refactoring (PENDING)

---

## Phase 1: Dead Code Removal (HIGH PRIORITY - Safe & Quick Wins)

### 1.1 Delete Temporary Test/Debug Files
**Files to DELETE:**
- `test_stats.py` (17 lines) - Quick test of CourseService stats
- `test_ocr.py` (42 lines) - Debug script for testing OCR
- `test_ocr_flow.py` (242 lines) - End-to-end OCR flow test
- `remove_backgrounds.py` (38 lines) - One-time image processing utility

**Total Removal:** ~340 lines of dead code

### 1.2 Delete Unused Model File
**File to DELETE:**
- `models/tournament.py` (332 lines)
  - Complete tournament CRUD implementation with NO routes or UI using it
  - Tournament tables exist in database but are not exposed in the application

### 1.3 Clean Up Data Directory
**Old JSON files to ARCHIVE/DELETE:**
- `data/courses.json` - Replaced by SQLite
- `data/course_ratings.json` - Replaced by SQLite
- `data/players.json` - Replaced by SQLite
- `data/rounds.json` - Replaced by SQLite
- `data/tournaments.json` - Replaced by SQLite

**Old backup directories to ARCHIVE/DELETE:**
- `data/backup_20251230_101229/`
- `data/backup_20251230_101341/`
- `data/backup_20251230_101640/`
- `data/backup_20251230_101751/`

**Empty database file to DELETE:**
- `data/leaderboard.db` (0 bytes)

### 1.4 Clean Up Cache Files
**Ensure these are in `.gitignore`:**
- `htmlcov/` directory
- All `__pycache__/` directories

### 1.5 Archive Migration Scripts
**Files to MOVE to `migrations/archive/`:**
- `migrations/json_to_sqlite.py` (424 lines) - One-time migration, completed
- `migrations/run_course_notes_migration.py` (50 lines) - One-time migration, completed
- `scripts/migrate_trophy_ownership.py` (109 lines) - One-time migration, completed

---

## Phase 2: Import Organization (MEDIUM PRIORITY - Low Risk)

### 2.1 Standardize Import Ordering
Follow PEP 8 convention: stdlib → third-party → local (with blank lines between groups)

**Files Needing Reordering:**
- `app.py` (lines 1-21)
- `utils/ocr_service.py` (lines 1-11)
- `routes/main_routes.py` (lines 1-7)
- `routes/round_routes.py`
- `models/round.py`
- `models/player.py`
- `models/course.py`

### 2.2 Move Function-Level Imports to Module Level
**Files with inline imports:**

**routes/round_routes.py:**
- Line 316: `from flask import send_from_directory`
- Line 411: `from models.database import get_db`

**routes/main_routes.py:**
- Line 15: `from datetime import datetime, timedelta`

**app.py:**
- Line 159: `from flask import flash` (already imported at top)

**services/trends_service.py:**
- Line 144: `from models.player import Player`

### 2.3 Remove Unused Imports
**routes/player_routes.py (line 2):**
- `from werkzeug.utils import secure_filename` - Not directly used

---

## Phase 3: Template Refactoring (MEDIUM PRIORITY - Improves Maintainability)

### 3.1 Create Reusable Macros
**New file:** `templates/macros.html`

**Macros to create:**
1. **Profile Picture Display** (used in 5 templates)
   - templates/index.html
   - templates/players/list.html
   - templates/players/detail.html
   - templates/rounds/list.html
   - templates/rounds/detail.html

2. **Course Image Display** (used in 3 templates)
   - templates/index.html
   - templates/rounds/list.html
   - templates/courses/list.html

3. **Placement Trophy** (used in 2 templates)
   - templates/index.html (lines 82-88)
   - templates/players/detail.html

4. **Card Header with Icon** (used throughout)

5. **Empty State Message** (used in 4 templates)
   - templates/players/list.html
   - templates/courses/list.html
   - templates/rounds/list.html
   - templates/stats/leaderboard.html

6. **Delete Confirmation Modal** (used in 3 templates)
   - templates/players/detail.html
   - templates/courses/detail.html
   - templates/rounds/detail.html

### 3.2 Extract JavaScript to Shared Functions
**Add to:** `static/js/main.js`

**Functions to extract:**
1. Auto-submit form listeners (templates/stats/courses_played.html lines 131-149)
2. Course preview with HTTP/file handling (3 templates)
3. Chart.js presets (4 templates)
4. Table filtering (templates/courses/list.html lines 134-176)
5. Total score calculation (2 templates)
6. Form loading states (2 templates)

### 3.3 Move Inline Styles to CSS Classes
**Issues to fix:**
- templates/index.html: Inline styles for trophy heights (lines 82-88)
- templates/trophies.html: Move `<style>` block to main.css (lines 45-86)
- templates/stats/course_stats.html: Move `<style>` block to main.css (lines 6-24)

**Standardize form layouts:**
- Choose consistent pattern between `col-md-6 mx-auto` vs `col-12`

### 3.4 Add Missing Error Handling
**Improvements needed:**
- Add consistent `onerror` handlers to all course/trophy images
- Add null checks before processing chart data
- Improve fetch error messages with specific guidance

---

## Implementation Strategy

### Recommended Order:
1. **Phase 1** - Dead code removal (Safe, immediate wins)
2. **Phase 2** - Import organization (Low risk, improves code quality)
3. **Phase 3** - Template refactoring (Higher effort, improves maintainability)

### Testing Approach:
- Run full test suite after each phase: `python -m pytest tests/ -q -o addopts=""`
- Manual testing for template changes (verify all pages render correctly)
- Check for any broken imports after Phase 2

---

## Expected Benefits

**Code Reduction:**
- ~1,270 lines of dead code removed
- Reduced duplication via macros and shared functions

**Maintainability:**
- Consistent import style across all files
- Reusable template components
- Better error handling in templates
- Standardized patterns

**Quality:**
- Cleaner codebase
- Better documentation
- Improved consistency
