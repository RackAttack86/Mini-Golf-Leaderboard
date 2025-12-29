import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Dict, Any

# Current schema version for all JSON files
CURRENT_SCHEMA_VERSION = 1


class DataStore:
    """Thread-safe JSON data storage with atomic writes and schema versioning"""

    def __init__(self, data_dir: Path):
        """Initialize data store and create directory if needed"""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        self.players_file = self.data_dir / 'players.json'
        self.courses_file = self.data_dir / 'courses.json'
        self.rounds_file = self.data_dir / 'rounds.json'
        self.course_ratings_file = self.data_dir / 'course_ratings.json'
        self.tournaments_file = self.data_dir / 'tournaments.json'

        # Thread locks for each file
        self._players_lock = threading.Lock()
        self._courses_lock = threading.Lock()
        self._rounds_lock = threading.Lock()
        self._course_ratings_lock = threading.Lock()
        self._tournaments_lock = threading.Lock()

        # Initialize files if they don't exist
        self._initialize_files()

    def _initialize_files(self):
        """Create JSON files with empty structures if they don't exist"""
        if not self.players_file.exists():
            self._write_file(self.players_file, {
                'schema_version': CURRENT_SCHEMA_VERSION,
                'players': []
            }, self._players_lock)

        if not self.courses_file.exists():
            self._write_file(self.courses_file, {
                'schema_version': CURRENT_SCHEMA_VERSION,
                'courses': []
            }, self._courses_lock)

        if not self.rounds_file.exists():
            self._write_file(self.rounds_file, {
                'schema_version': CURRENT_SCHEMA_VERSION,
                'rounds': []
            }, self._rounds_lock)

        if not self.course_ratings_file.exists():
            self._write_file(self.course_ratings_file, {
                'schema_version': CURRENT_SCHEMA_VERSION,
                'ratings': []
            }, self._course_ratings_lock)

        if not self.tournaments_file.exists():
            self._write_file(self.tournaments_file, {
                'schema_version': CURRENT_SCHEMA_VERSION,
                'tournaments': []
            }, self._tournaments_lock)

    def _atomic_write(self, file_path: Path, data: Dict[str, Any]):
        """Write data atomically to prevent corruption"""
        file_path = Path(file_path)

        # Write to temporary file first
        fd, temp_path = tempfile.mkstemp(
            dir=file_path.parent,
            prefix=f'.{file_path.name}.',
            suffix='.tmp'
        )

        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Atomic rename (replaces original)
            os.replace(temp_path, file_path)
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    def _migrate_data(self, data: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """
        Migrate data to current schema version if needed

        Args:
            data: The data dictionary from JSON file
            file_path: Path to the file being read

        Returns:
            Migrated data dictionary
        """
        # If schema_version is missing, it's version 0 (old format)
        current_version = data.get('schema_version', 0)

        if current_version == CURRENT_SCHEMA_VERSION:
            return data  # Already at current version

        # Migration from version 0 to version 1
        if current_version == 0:
            # Add schema_version field
            data['schema_version'] = CURRENT_SCHEMA_VERSION
            # Data structure is the same, just adding version field

        # Future migrations would go here:
        # if current_version == 1:
        #     # Migrate from version 1 to version 2
        #     data['schema_version'] = 2
        #     # Apply migration logic...

        return data

    def _read_file(self, file_path: Path, lock: threading.Lock) -> Dict[str, Any]:
        """Read JSON file with thread safety and automatic migration"""
        with lock:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Migrate data if needed
                migrated_data = self._migrate_data(data, file_path)

                # Write back if migration occurred
                if migrated_data.get('schema_version') != data.get('schema_version'):
                    self._atomic_write(file_path, migrated_data)

                return migrated_data
            except (FileNotFoundError, json.JSONDecodeError):
                # Return empty structure if file is missing or corrupted
                return {
                    'schema_version': CURRENT_SCHEMA_VERSION,
                    file_path.stem: []
                }

    def _write_file(self, file_path: Path, data: Dict[str, Any], lock: threading.Lock):
        """Write JSON file with thread safety and atomic writes"""
        with lock:
            self._atomic_write(file_path, data)

    # Players
    def read_players(self) -> Dict[str, Any]:
        """Read players data"""
        return self._read_file(self.players_file, self._players_lock)

    def write_players(self, data: Dict[str, Any]):
        """Write players data"""
        self._write_file(self.players_file, data, self._players_lock)

    # Courses
    def read_courses(self) -> Dict[str, Any]:
        """Read courses data"""
        return self._read_file(self.courses_file, self._courses_lock)

    def write_courses(self, data: Dict[str, Any]):
        """Write courses data"""
        self._write_file(self.courses_file, data, self._courses_lock)

    # Rounds
    def read_rounds(self) -> Dict[str, Any]:
        """Read rounds data"""
        return self._read_file(self.rounds_file, self._rounds_lock)

    def write_rounds(self, data: Dict[str, Any]):
        """Write rounds data"""
        self._write_file(self.rounds_file, data, self._rounds_lock)

    # Course Ratings
    def read_course_ratings(self) -> Dict[str, Any]:
        """Read course ratings data"""
        return self._read_file(self.course_ratings_file, self._course_ratings_lock)

    def write_course_ratings(self, data: Dict[str, Any]):
        """Write course ratings data"""
        self._write_file(self.course_ratings_file, data, self._course_ratings_lock)

    # Tournaments
    def read_tournaments(self) -> Dict[str, Any]:
        """Read tournaments data"""
        return self._read_file(self.tournaments_file, self._tournaments_lock)

    def write_tournaments(self, data: Dict[str, Any]):
        """Write tournaments data"""
        self._write_file(self.tournaments_file, data, self._tournaments_lock)


# Global data store instance (initialized by app.py)
_data_store = None


def init_data_store(data_dir: Path):
    """Initialize the global data store"""
    global _data_store
    _data_store = DataStore(data_dir)
    return _data_store


def get_data_store() -> DataStore:
    """Get the global data store instance"""
    if _data_store is None:
        raise RuntimeError('Data store not initialized. Call init_data_store() first.')
    return _data_store
