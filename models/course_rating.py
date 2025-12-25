"""Course rating model for player ratings"""
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from models.data_store import get_data_store


class CourseRating:
    """Course rating model with CRUD operations"""

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

        store = get_data_store()
        data = store.read_course_ratings()

        # Check if player already rated this course
        existing_rating = None
        for i, r in enumerate(data['ratings']):
            if r['player_id'] == player_id and r['course_id'] == course_id:
                existing_rating = i
                break

        if existing_rating is not None:
            # Update existing rating
            data['ratings'][existing_rating]['rating'] = rating
            data['ratings'][existing_rating]['date_rated'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            message = "Rating updated successfully"
        else:
            # Create new rating
            new_rating = {
                'player_id': player_id,
                'course_id': course_id,
                'rating': rating,
                'date_rated': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            }
            data['ratings'].append(new_rating)
            message = "Rating added successfully"

        store.write_course_ratings(data)
        return True, message

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
        store = get_data_store()
        data = store.read_course_ratings()

        for rating in data['ratings']:
            if rating['player_id'] == player_id and rating['course_id'] == course_id:
                return rating['rating']

        return None

    @staticmethod
    def get_course_average_rating(course_id: str) -> Tuple[Optional[float], int]:
        """
        Get average rating for a course

        Args:
            course_id: Course ID

        Returns:
            Tuple of (average_rating, count)
        """
        store = get_data_store()
        data = store.read_course_ratings()

        ratings = [r['rating'] for r in data['ratings'] if r['course_id'] == course_id]

        if not ratings:
            return None, 0

        avg_rating = sum(ratings) / len(ratings)
        return round(avg_rating, 1), len(ratings)

    @staticmethod
    def get_all_course_ratings() -> Dict[str, Tuple[Optional[float], int]]:
        """
        Get average ratings for all courses

        Returns:
            Dictionary of {course_id: (average_rating, count)}
        """
        store = get_data_store()
        data = store.read_course_ratings()

        course_ratings = {}
        for rating in data['ratings']:
            course_id = rating['course_id']
            if course_id not in course_ratings:
                course_ratings[course_id] = []
            course_ratings[course_id].append(rating['rating'])

        result = {}
        for course_id, ratings in course_ratings.items():
            avg_rating = sum(ratings) / len(ratings)
            result[course_id] = (round(avg_rating, 1), len(ratings))

        return result

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
        store = get_data_store()
        data = store.read_course_ratings()

        for i, rating in enumerate(data['ratings']):
            if rating['player_id'] == player_id and rating['course_id'] == course_id:
                data['ratings'].pop(i)
                store.write_course_ratings(data)
                return True, "Rating deleted successfully"

        return False, "Rating not found"
