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
    def initialize(cls, db_path: Path) -> 'Database':
        """
        Initialize database singleton

        Args:
            db_path: Path to SQLite database file

        Returns:
            Database instance
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(db_path)
                cls._instance._create_schema()
        return cls._instance

    def _create_schema(self):
        """Create database schema if it doesn't exist"""
        schema_file = Path(__file__).parent.parent / 'migrations' / 'schema.sql'

        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_file}")

        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        conn = self.get_connection()
        conn.executescript(schema_sql)
        conn.commit()

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


def init_database(db_path: Path) -> Database:
    """
    Initialize database singleton

    Args:
        db_path: Path to SQLite database file

    Returns:
        Database instance
    """
    return Database.initialize(db_path)


def set_database(database: Database):
    """
    Set database instance (for testing)

    Args:
        database: Database instance to set
    """
    with Database._lock:
        Database._instance = database
