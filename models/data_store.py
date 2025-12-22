import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Dict, Any


class DataStore:
    """Thread-safe JSON data storage with atomic writes"""

    def __init__(self, data_dir: Path):
        """Initialize data store and create directory if needed"""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        self.players_file = self.data_dir / 'players.json'
        self.courses_file = self.data_dir / 'courses.json'
        self.rounds_file = self.data_dir / 'rounds.json'

        # Thread locks for each file
        self._players_lock = threading.Lock()
        self._courses_lock = threading.Lock()
        self._rounds_lock = threading.Lock()

        # Initialize files if they don't exist
        self._initialize_files()

    def _initialize_files(self):
        """Create JSON files with empty structures if they don't exist"""
        if not self.players_file.exists():
            self._write_file(self.players_file, {'players': []}, self._players_lock)

        if not self.courses_file.exists():
            self._write_file(self.courses_file, {'courses': []}, self._courses_lock)

        if not self.rounds_file.exists():
            self._write_file(self.rounds_file, {'rounds': []}, self._rounds_lock)

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

    def _read_file(self, file_path: Path, lock: threading.Lock) -> Dict[str, Any]:
        """Read JSON file with thread safety"""
        with lock:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                # Return empty structure if file is missing or corrupted
                return {file_path.stem: []}

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
