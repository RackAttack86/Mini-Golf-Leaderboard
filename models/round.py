import uuid
from datetime import datetime, UTC
from typing import List, Optional, Dict, Any, Tuple
from models.data_store import get_data_store
from models.player import Player
from models.course import Course
from utils.validators import validate_date, validate_score


class Round:
    """Round model with CRUD operations and filtering"""

    @staticmethod
    def create(course_id: str, date_played: str, scores: List[Dict[str, Any]],
               notes: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Create a new round

        Args:
            course_id: Course ID
            date_played: Date in YYYY-MM-DD format
            scores: List of dicts with player_id and score
            notes: Optional notes

        Returns:
            Tuple of (success, message, round_dict)
        """
        store = get_data_store()

        # Validate date
        is_valid, error = validate_date(date_played)
        if not is_valid:
            return False, error, None

        # Validate course exists
        course = Course.get_by_id(course_id)
        if not course:
            return False, "Course not found", None

        # Validate scores
        if not scores or len(scores) == 0:
            return False, "At least one player score is required", None

        validated_scores = []
        player_ids_seen = set()

        for score_data in scores:
            player_id = score_data.get('player_id')
            score = score_data.get('score')

            # Check for duplicate players
            if player_id in player_ids_seen:
                return False, f"Duplicate player in round", None
            player_ids_seen.add(player_id)

            # Validate player exists
            player = Player.get_by_id(player_id)
            if not player:
                return False, f"Player not found: {player_id}", None

            # Validate score
            is_valid, error = validate_score(score)
            if not is_valid:
                return False, f"Invalid score for {player['name']}: {error}", None

            validated_scores.append({
                'player_id': player_id,
                'player_name': player['name'],  # Denormalized
                'score': int(score)
            })

        # Create round
        round_data = {
            'id': str(uuid.uuid4()),
            'course_id': course_id,
            'course_name': course['name'],  # Denormalized
            'date_played': date_played,
            'timestamp': datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'scores': validated_scores,
            'notes': notes.strip() if notes else ''
        }

        data = store.read_rounds()
        data['rounds'].append(round_data)
        store.write_rounds(data)

        return True, "Round created successfully", round_data

    @staticmethod
    def update(round_id: str, course_id: str, date_played: str,
               scores: List[Dict[str, Any]], notes: Optional[str] = None) -> Tuple[bool, str]:
        """
        Update an existing round

        Args:
            round_id: Round ID to update
            course_id: Course ID
            date_played: Date in YYYY-MM-DD format
            scores: List of dicts with player_id and score
            notes: Optional notes

        Returns:
            Tuple of (success, message)
        """
        store = get_data_store()

        # Find the round
        data = store.read_rounds()
        round_index = None
        for i, r in enumerate(data['rounds']):
            if r['id'] == round_id:
                round_index = i
                break

        if round_index is None:
            return False, "Round not found"

        # Validate date
        is_valid, error = validate_date(date_played)
        if not is_valid:
            return False, error

        # Validate course exists
        course = Course.get_by_id(course_id)
        if not course:
            return False, "Course not found"

        # Validate scores
        if not scores or len(scores) == 0:
            return False, "At least one player score is required"

        validated_scores = []
        player_ids_seen = set()

        for score_data in scores:
            player_id = score_data.get('player_id')
            score = score_data.get('score')

            # Check for duplicate players
            if player_id in player_ids_seen:
                return False, f"Duplicate player in round", None
            player_ids_seen.add(player_id)

            # Validate player exists
            player = Player.get_by_id(player_id)
            if not player:
                return False, f"Player not found: {player_id}"

            # Validate score
            is_valid, error = validate_score(score)
            if not is_valid:
                return False, f"Invalid score for {player['name']}: {error}"

            validated_scores.append({
                'player_id': player_id,
                'player_name': player['name'],  # Denormalized
                'score': int(score)
            })

        # Update the round
        data['rounds'][round_index]['course_id'] = course_id
        data['rounds'][round_index]['course_name'] = course['name']  # Update denormalized
        data['rounds'][round_index]['date_played'] = date_played
        data['rounds'][round_index]['scores'] = validated_scores
        data['rounds'][round_index]['notes'] = notes.strip() if notes else ''

        store.write_rounds(data)

        return True, "Round updated successfully"

    @staticmethod
    def get_all(filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get all rounds with optional filtering

        Args:
            filters: Optional dict with keys:
                - player_id: Filter by player
                - course_id: Filter by course
                - start_date: Filter by date >= start_date
                - end_date: Filter by date <= end_date

        Returns:
            List of round dictionaries, sorted by date (newest first)
        """
        store = get_data_store()
        data = store.read_rounds()
        rounds = data['rounds']

        # Apply filters
        if filters:
            if 'player_id' in filters:
                player_id = filters['player_id']
                rounds = [r for r in rounds if any(s['player_id'] == player_id for s in r['scores'])]

            if 'course_id' in filters:
                course_id = filters['course_id']
                rounds = [r for r in rounds if r['course_id'] == course_id]

            if 'start_date' in filters:
                start_date = filters['start_date']
                rounds = [r for r in rounds if r['date_played'] >= start_date]

            if 'end_date' in filters:
                end_date = filters['end_date']
                rounds = [r for r in rounds if r['date_played'] <= end_date]

        # Sort by date (newest first)
        rounds.sort(key=lambda r: r['date_played'], reverse=True)

        return rounds

    @staticmethod
    def get_by_id(round_id: str) -> Optional[Dict[str, Any]]:
        """
        Get round by ID

        Args:
            round_id: Round ID

        Returns:
            Round dictionary or None
        """
        store = get_data_store()
        data = store.read_rounds()

        for round_data in data['rounds']:
            if round_data['id'] == round_id:
                return round_data

        return None

    @staticmethod
    def get_by_player(player_id: str) -> List[Dict[str, Any]]:
        """
        Get all rounds for a specific player

        Args:
            player_id: Player ID

        Returns:
            List of round dictionaries
        """
        return Round.get_all({'player_id': player_id})

    @staticmethod
    def get_by_course(course_id: str) -> List[Dict[str, Any]]:
        """
        Get all rounds for a specific course

        Args:
            course_id: Course ID

        Returns:
            List of round dictionaries
        """
        return Round.get_all({'course_id': course_id})

    @staticmethod
    def delete(round_id: str) -> Tuple[bool, str]:
        """
        Delete round

        Args:
            round_id: Round ID

        Returns:
            Tuple of (success, message)
        """
        store = get_data_store()
        data = store.read_rounds()

        # Find round
        round_index = None
        for i, r in enumerate(data['rounds']):
            if r['id'] == round_id:
                round_index = i
                break

        if round_index is None:
            return False, "Round not found"

        # Delete round
        data['rounds'].pop(round_index)
        store.write_rounds(data)

        return True, "Round deleted successfully"

    @staticmethod
    def get_player_score_in_round(round_data: Dict[str, Any], player_id: str) -> Optional[int]:
        """
        Get a player's score in a specific round

        Args:
            round_data: Round dictionary
            player_id: Player ID

        Returns:
            Player's score or None
        """
        for score in round_data['scores']:
            if score['player_id'] == player_id:
                return score['score']
        return None
