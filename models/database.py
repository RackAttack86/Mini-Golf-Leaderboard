"""
SQLite database connection management

This module provides thread-safe database connection handling using a singleton pattern.
Each thread gets its own connection via thread-local storage.
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Optional
import threading


class Database:
    """Singleton SQLite database connection manager with thread-local connections"""

    _instance: Optional['Database'] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Path):
        """
        Initialize database manager

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._local = threading.local()

    @classmethod
    def initialize(cls, db_path: Path, skip_seed_data: bool = False) -> 'Database':
        """
        Initialize database singleton

        Args:
            db_path: Path to SQLite database file
            skip_seed_data: If True, skip loading seed data (for testing)

        Returns:
            Database instance
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(db_path)
                cls._instance._create_schema(skip_seed_data=skip_seed_data)
        return cls._instance

    def _create_schema(self, skip_seed_data: bool = False):
        """Create database schema if it doesn't exist

        Args:
            skip_seed_data: If True, skip loading seed data (for testing)
        """
        schema_file = Path(__file__).parent.parent / 'migrations' / 'schema.sql'

        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_file}")

        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        conn = self.get_connection()
        conn.executescript(schema_sql)
        conn.commit()

        # Skip seed data for testing
        if skip_seed_data:
            return

        # Load seed data if tables are empty
        cursor = conn.execute("SELECT COUNT(*) as count FROM players")
        player_count = cursor.fetchone()[0]

        if player_count == 0:
            player_seed_file = Path(__file__).parent.parent / 'migrations' / 'seed_players.sql'
            if player_seed_file.exists():
                with open(player_seed_file, 'r', encoding='utf-8') as f:
                    seed_sql = f.read()
                conn.executescript(seed_sql)
                conn.commit()
                print(f"Loaded player seed data from {player_seed_file}")

        cursor = conn.execute("SELECT COUNT(*) as count FROM courses")
        course_count = cursor.fetchone()[0]

        if course_count == 0:
            course_seed_file = Path(__file__).parent.parent / 'migrations' / 'seed_courses.sql'
            if course_seed_file.exists():
                with open(course_seed_file, 'r', encoding='utf-8') as f:
                    seed_sql = f.read()
                conn.executescript(seed_sql)
                conn.commit()
                print(f"Loaded course seed data from {course_seed_file}")

        # Run additional migrations
        self._run_migrations(conn)

    def _run_migrations(self, conn: sqlite3.Connection):
        """Run additional migration files that haven't been applied yet"""
        migrations_dir = Path(__file__).parent.parent / 'migrations'

        # Get current schema version
        cursor = conn.execute("SELECT MAX(version) FROM schema_version")
        row = cursor.fetchone()
        current_version = row[0] if row and row[0] else 0

        # Find and run migration files with version > current_version
        migration_files = sorted(migrations_dir.glob('0*.sql'))

        for migration_file in migration_files:
            # Extract version number from filename (e.g., 003_add_friendships.sql -> 3)
            try:
                version = int(migration_file.stem.split('_')[0])
            except (ValueError, IndexError):
                continue

            if version > current_version:
                print(f"Running migration: {migration_file.name}")
                with open(migration_file, 'r', encoding='utf-8') as f:
                    migration_sql = f.read()
                conn.executescript(migration_sql)
                conn.commit()
                print(f"Migration {migration_file.name} applied successfully")

    def get_connection(self) -> sqlite3.Connection:
        """
        Get thread-local database connection

        Returns:
            SQLite connection for current thread
        """
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                isolation_level=None  # Autocommit mode, we'll manage transactions manually
            )
            # Enable foreign keys
            self._local.connection.execute('PRAGMA foreign_keys = ON')
            # Use Row factory for dict-like access
            self._local.connection.row_factory = sqlite3.Row

        return self._local.connection

    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions

        Yields:
            SQLite connection

        Example:
            with db.transaction() as conn:
                conn.execute("INSERT INTO ...")
                conn.execute("UPDATE ...")
            # Automatically commits on success, rolls back on exception
        """
        conn = self.get_connection()
        try:
            conn.execute('BEGIN')
            yield conn
            conn.execute('COMMIT')
        except Exception:
            conn.execute('ROLLBACK')
            raise

    def close(self):
        """Close thread-local connection"""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None

    @classmethod
    def reset(cls):
        """Reset singleton instance (for testing)"""
        with cls._lock:
            if cls._instance:
                cls._instance.close()
            cls._instance = None


# Global functions for easy access

def get_db() -> Database:
    """
    Get database instance

    Returns:
        Database singleton instance

    Raises:
        RuntimeError: If database not initialized
    """
    if Database._instance is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return Database._instance


def init_database(db_path: Path, skip_seed_data: bool = False) -> Database:
    """
    Initialize database singleton

    Args:
        db_path: Path to SQLite database file
        skip_seed_data: If True, skip loading seed data (for testing)

    Returns:
        Database instance
    """
    return Database.initialize(db_path, skip_seed_data=skip_seed_data)


def set_database(database: Database):
    """
    Set database instance (for testing)

    Args:
        database: Database instance to set
    """
    with Database._lock:
        Database._instance = database
