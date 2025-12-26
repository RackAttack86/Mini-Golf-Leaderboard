import uuid
from datetime import datetime, UTC
from typing import List, Optional, Dict, Any, Tuple
from models.data_store import get_data_store
from utils.validators import validate_course_name, validate_holes, validate_par


class Course:
    """Course model with CRUD operations"""

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
        store = get_data_store()
        data = store.read_courses()

        # Validate name
        is_valid, error = validate_course_name(name, data['courses'])
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
        course = {
            'id': str(uuid.uuid4()),
            'name': name.strip(),
            'location': location.strip() if location else '',
            'holes': int(holes) if holes else None,
            'par': int(par) if par else None,
            'image_url': image_url or '',
            'created_at': datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'active': True
        }

        data['courses'].append(course)
        store.write_courses(data)

        return True, "Course created successfully", course

    @staticmethod
    def get_all(active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all courses

        Args:
            active_only: If True, return only active courses

        Returns:
            List of course dictionaries
        """
        store = get_data_store()
        data = store.read_courses()

        if active_only:
            return [c for c in data['courses'] if c.get('active', True)]

        return data['courses']

    @staticmethod
    def get_by_id(course_id: str) -> Optional[Dict[str, Any]]:
        """
        Get course by ID

        Args:
            course_id: Course ID

        Returns:
            Course dictionary or None
        """
        store = get_data_store()
        data = store.read_courses()

        for course in data['courses']:
            if course['id'] == course_id:
                return course

        return None

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
        store = get_data_store()
        data = store.read_courses()

        # Find course
        course = None
        for c in data['courses']:
            if c['id'] == course_id:
                course = c
                break

        if not course:
            return False, "Course not found"

        # Validate and update name
        if name is not None:
            is_valid, error = validate_course_name(name, data['courses'], exclude_id=course_id)
            if not is_valid:
                return False, error

            old_name = course['name']
            course['name'] = name.strip()

            # Update denormalized data in rounds
            if old_name != course['name']:
                Course._update_name_in_rounds(course_id, course['name'])

        # Update location
        if location is not None:
            course['location'] = location.strip()

        # Validate and update holes
        if holes is not None:
            is_valid, error = validate_holes(holes)
            if not is_valid:
                return False, error
            course['holes'] = int(holes) if holes else None

        # Validate and update par
        if par is not None:
            is_valid, error = validate_par(par)
            if not is_valid:
                return False, error
            course['par'] = int(par) if par else None

        # Update image URL
        if image_url is not None:
            course['image_url'] = image_url

        store.write_courses(data)
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
        store = get_data_store()
        data = store.read_courses()

        # Find course
        course_index = None
        for i, c in enumerate(data['courses']):
            if c['id'] == course_id:
                course_index = i
                break

        if course_index is None:
            return False, "Course not found"

        # Check if course has rounds
        has_rounds = Course._has_rounds(course_id)

        if has_rounds and not force:
            # Soft delete
            data['courses'][course_index]['active'] = False
            store.write_courses(data)
            return True, "Course deactivated (has existing rounds)"
        else:
            # Hard delete
            data['courses'].pop(course_index)
            store.write_courses(data)
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
        store = get_data_store()
        data = store.read_rounds()

        updated = False
        for round_data in data['rounds']:
            if round_data['course_id'] == course_id:
                round_data['course_name'] = new_name
                updated = True

        if updated:
            store.write_rounds(data)
