# Standard library
import uuid
from datetime import datetime, UTC
from typing import List, Optional, Dict, Any, Tuple

# Local
from models.database import get_db
from utils.validators import validate_course_name, validate_holes, validate_par, sanitize_html


class Course:
    """Course model with CRUD operations using SQLite"""

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        """Convert SQLite Row to dictionary"""
        return {
            'id': row['id'],
            'name': row['name'],
            'location': row['location'] or '',
            'holes': row['holes'],
            'par': row['par'],
            'image_url': row['image_url'] or '',
            'created_at': row['created_at'],
            'active': bool(row['active'])
        }

    @staticmethod
    def create(name: str, location: Optional[str] = None, holes: Optional[int] = None,
               par: Optional[int] = None, image_url: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Create a new course

        Args:
            name: Course name
            location: Course location (optional)
            holes: Number of holes (optional)
            par: Par score (optional)
            image_url: Course image URL or filename (optional)

        Returns:
            Tuple of (success, message, course_dict)
        """
        db = get_db()
        conn = db.get_connection()

        # Get all courses for validation
        all_courses = Course.get_all(active_only=False)

        # Validate name
        is_valid, error = validate_course_name(name, all_courses)
        if not is_valid:
            return False, error, None

        # Validate holes
        if holes is not None:
            is_valid, error = validate_holes(holes)
            if not is_valid:
                return False, error, None

        # Validate par
        if par is not None:
            is_valid, error = validate_par(par)
            if not is_valid:
                return False, error, None

        # Create course
        course_id = str(uuid.uuid4())
        created_at = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')

        try:
            conn.execute("""
                INSERT INTO courses (
                    id, name, location, holes, par, image_url, created_at, active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                course_id,
                sanitize_html(name),
                sanitize_html(location) if location else None,
                int(holes) if holes else None,
                int(par) if par else None,
                image_url or None,
                created_at,
                1  # active
            ))

            # Return the created course
            course = Course.get_by_id(course_id)
            return True, "Course created successfully", course

        except Exception as e:
            return False, f"Error creating course: {str(e)}", None

    @staticmethod
    def get_all(active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all courses

        Args:
            active_only: If True, return only active courses

        Returns:
            List of course dictionaries
        """
        db = get_db()
        conn = db.get_connection()

        if active_only:
            cursor = conn.execute(
                "SELECT * FROM courses WHERE active = 1 ORDER BY name"
            )
        else:
            cursor = conn.execute("SELECT * FROM courses ORDER BY name")

        return [Course._row_to_dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_by_id(course_id: str) -> Optional[Dict[str, Any]]:
        """
        Get course by ID

        Args:
            course_id: Course ID

        Returns:
            Course dictionary or None
        """
        db = get_db()
        conn = db.get_connection()

        cursor = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
        row = cursor.fetchone()

        return Course._row_to_dict(row) if row else None

    @staticmethod
    def update(course_id: str, name: Optional[str] = None, location: Optional[str] = None,
               holes: Optional[int] = None, par: Optional[int] = None, image_url: Optional[str] = None) -> Tuple[bool, str]:
        """
        Update course

        Args:
            course_id: Course ID
            name: New name (optional)
            location: New location (optional)
            holes: New number of holes (optional)
            par: New par (optional)
            image_url: New image URL or filename (optional)

        Returns:
            Tuple of (success, message)
        """
        db = get_db()
        conn = db.get_connection()

        # Find course
        course = Course.get_by_id(course_id)
        if not course:
            return False, "Course not found"

        # Validate and update name
        if name is not None:
            all_courses = Course.get_all(active_only=False)
            is_valid, error = validate_course_name(name, all_courses, exclude_id=course_id)
            if not is_valid:
                return False, error

            old_name = course['name']
            new_name = sanitize_html(name)

            conn.execute("UPDATE courses SET name = ? WHERE id = ?", (new_name, course_id))

            # Update denormalized data in rounds
            if old_name != new_name:
                Course._update_name_in_rounds(course_id, new_name)

        # Update location
        if location is not None:
            conn.execute("UPDATE courses SET location = ? WHERE id = ?",
                        (sanitize_html(location), course_id))

        # Validate and update holes
        if holes is not None:
            is_valid, error = validate_holes(holes)
            if not is_valid:
                return False, error
            conn.execute("UPDATE courses SET holes = ? WHERE id = ?", (int(holes), course_id))

        # Validate and update par
        if par is not None:
            is_valid, error = validate_par(par)
            if not is_valid:
                return False, error
            conn.execute("UPDATE courses SET par = ? WHERE id = ?", (int(par), course_id))

        # Update image URL
        if image_url is not None:
            conn.execute("UPDATE courses SET image_url = ? WHERE id = ?", (image_url, course_id))

        return True, "Course updated successfully"

    @staticmethod
    def delete(course_id: str, force: bool = False) -> Tuple[bool, str]:
        """
        Delete course (soft delete by default, hard delete if force=True)

        Args:
            course_id: Course ID
            force: If True, permanently delete the course

        Returns:
            Tuple of (success, message)
        """
        db = get_db()
        conn = db.get_connection()

        # Find course
        course = Course.get_by_id(course_id)
        if not course:
            return False, "Course not found"

        # Check if course has rounds
        has_rounds = Course._has_rounds(course_id)

        if has_rounds and not force:
            # Soft delete
            conn.execute("UPDATE courses SET active = 0 WHERE id = ?", (course_id,))
            return True, "Course deactivated (has existing rounds)"
        else:
            # Hard delete
            conn.execute("DELETE FROM courses WHERE id = ?", (course_id,))
            return True, "Course deleted successfully"

    @staticmethod
    def _has_rounds(course_id: str) -> bool:
        """Check if course has any rounds"""
        from models.round import Round
        rounds = Round.get_by_course(course_id)
        return len(rounds) > 0

    @staticmethod
    def _update_name_in_rounds(course_id: str, new_name: str):
        """Update denormalized course name in all rounds"""
        db = get_db()
        conn = db.get_connection()

        # Update in rounds table
        conn.execute(
            "UPDATE rounds SET course_name = ? WHERE course_id = ?",
            (new_name, course_id)
        )
