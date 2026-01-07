"""Course Notes Model - Personal player notes for courses"""

from typing import Tuple, Optional, Dict, Any
from datetime import datetime, UTC
from models.database import get_db


class CourseNotes:
    """Model for player's personal course notes"""

    @staticmethod
    def save_notes(player_id: str, course_id: str, notes: str) -> Tuple[bool, str]:
        """
        Save or update player's notes for a course

        Args:
            player_id: Player UUID
            course_id: Course UUID
            notes: Note text (can be empty string to clear)

        Returns:
            (success: bool, message: str)
        """
        db = get_db()
        conn = db.get_connection()

        # Validate inputs
        if not player_id or not course_id:
            return False, "Invalid player or course ID"

        # Validate that player exists
        cursor = conn.execute("SELECT id FROM players WHERE id = ?", (player_id,))
        if not cursor.fetchone():
            return False, f"Player {player_id} does not exist"

        # Validate that course exists
        cursor = conn.execute("SELECT id FROM courses WHERE id = ?", (course_id,))
        if not cursor.fetchone():
            return False, f"Course {course_id} does not exist"

        # Trim whitespace
        notes = notes.strip() if notes else ""

        # Get current timestamp
        now = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')

        try:
            # Check if notes already exist
            cursor = conn.execute(
                "SELECT date_created FROM course_notes WHERE player_id = ? AND course_id = ?",
                (player_id, course_id)
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing notes
                conn.execute(
                    """UPDATE course_notes
                       SET notes = ?, date_updated = ?
                       WHERE player_id = ? AND course_id = ?""",
                    (notes, now, player_id, course_id)
                )
                return True, "Notes updated successfully"
            else:
                # Create new notes
                conn.execute(
                    """INSERT INTO course_notes (player_id, course_id, notes, date_created, date_updated)
                       VALUES (?, ?, ?, ?, ?)""",
                    (player_id, course_id, notes, now, now)
                )
                return True, "Notes saved successfully"

        except Exception as e:
            print(f"Error saving course notes: {e}")
            return False, f"Error saving notes: {str(e)}"

    @staticmethod
    def get_player_notes(player_id: str, course_id: str) -> Optional[Dict[str, Any]]:
        """
        Get player's notes for a specific course

        Returns:
            Dict with 'notes', 'date_created', 'date_updated' or None if no notes exist
        """
        db = get_db()
        conn = db.get_connection()

        cursor = conn.execute(
            """SELECT notes, date_created, date_updated
               FROM course_notes
               WHERE player_id = ? AND course_id = ?""",
            (player_id, course_id)
        )

        row = cursor.fetchone()
        if row:
            return {
                'notes': row['notes'],
                'date_created': row['date_created'],
                'date_updated': row['date_updated']
            }
        return None

    @staticmethod
    def delete_notes(player_id: str, course_id: str) -> Tuple[bool, str]:
        """Delete player's notes for a course"""
        db = get_db()
        conn = db.get_connection()

        try:
            conn.execute(
                "DELETE FROM course_notes WHERE player_id = ? AND course_id = ?",
                (player_id, course_id)
            )
            return True, "Notes deleted successfully"
        except Exception as e:
            return False, f"Error deleting notes: {str(e)}"
