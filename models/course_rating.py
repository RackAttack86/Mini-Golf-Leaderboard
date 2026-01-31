"""Course rating model for player ratings"""
from datetime import datetime, UTC
from typing import List, Dict, Any, Tuple, Optional
from models.database import get_db


class CourseRating:
    """Course rating model with CRUD operations using SQLite"""

    @staticmethod
    def rate_course(player_id: str, course_id: str, rating: int) -> Tuple[bool, str]:
        """
        Rate a course (1-5 stars)

        Args:
            player_id: Player ID
            course_id: Course ID
            rating: Rating (1-5 stars)

        Returns:
            Tuple of (success, message)
        """
        # Validate rating
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return False, "Rating must be between 1 and 5 stars"

        db = get_db()
        conn = db.get_connection()

        date_rated = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')

        try:
            # Check if rating already exists
            existing = conn.execute(
                "SELECT COUNT(*) FROM course_ratings WHERE player_id = ? AND course_id = ?",
                (player_id, course_id)
            ).fetchone()[0]

            # Insert or update rating
            conn.execute("""
                INSERT INTO course_ratings (player_id, course_id, rating, date_rated)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(player_id, course_id) DO UPDATE SET
                    rating = excluded.rating,
                    date_rated = excluded.date_rated
            """, (player_id, course_id, rating, date_rated))

            message = "Rating updated successfully" if existing else "Rating added successfully"
            return True, message

        except Exception as e:
            return False, f"Error saving rating: {str(e)}"

    @staticmethod
    def get_player_rating(player_id: str, course_id: str) -> Optional[int]:
        """
        Get a player's rating for a specific course

        Args:
            player_id: Player ID
            course_id: Course ID

        Returns:
            Rating (1-5) or None if not rated
        """
        db = get_db()
        conn = db.get_connection()

        cursor = conn.execute(
            "SELECT rating FROM course_ratings WHERE player_id = ? AND course_id = ?",
            (player_id, course_id)
        )
        row = cursor.fetchone()

        return row['rating'] if row else None

    @staticmethod
    def get_course_average_rating(course_id: str) -> Tuple[Optional[float], int]:
        """
        Get average rating for a course

        Args:
            course_id: Course ID

        Returns:
            Tuple of (average_rating, count)
        """
        db = get_db()
        conn = db.get_connection()

        cursor = conn.execute(
            "SELECT AVG(rating) as avg_rating, COUNT(*) as count FROM course_ratings WHERE course_id = ?",
            (course_id,)
        )
        row = cursor.fetchone()

        if row['count'] == 0:
            return None, 0

        return round(row['avg_rating'], 1), row['count']

    @staticmethod
    def get_all() -> Dict[str, Tuple[Optional[float], int]]:
        """
        Get average ratings for all courses

        Returns:
            Dictionary of {course_id: (average_rating, count)}
        """
        db = get_db()
        conn = db.get_connection()

        cursor = conn.execute("""
            SELECT course_id, AVG(rating) as avg_rating, COUNT(*) as count
            FROM course_ratings
            GROUP BY course_id
        """)

        result = {}
        for row in cursor.fetchall():
            result[row['course_id']] = (round(row['avg_rating'], 1), row['count'])

        return result

    @staticmethod
    def get_all_player_ratings(player_id: str) -> Dict[str, int]:
        """
        Get all ratings by a specific player

        Args:
            player_id: Player ID

        Returns:
            Dictionary of {course_id: rating}
        """
        db = get_db()
        conn = db.get_connection()

        cursor = conn.execute(
            "SELECT course_id, rating FROM course_ratings WHERE player_id = ?",
            (player_id,)
        )

        return {row['course_id']: row['rating'] for row in cursor.fetchall()}

    @staticmethod
    def delete_rating(player_id: str, course_id: str) -> Tuple[bool, str]:
        """
        Delete a player's rating for a course

        Args:
            player_id: Player ID
            course_id: Course ID

        Returns:
            Tuple of (success, message)
        """
        db = get_db()
        conn = db.get_connection()

        cursor = conn.execute(
            "DELETE FROM course_ratings WHERE player_id = ? AND course_id = ?",
            (player_id, course_id)
        )

        if cursor.rowcount > 0:
            return True, "Rating deleted successfully"
        else:
            return False, "Rating not found"
