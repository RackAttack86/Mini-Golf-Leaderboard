# Standard library
import uuid
import json
from datetime import datetime, UTC
from typing import List, Optional, Dict, Any, Tuple

# Local
from models.database import get_db
from models.player import Player
from models.course import Course
from utils.validators import validate_date, validate_score, sanitize_html


class Round:
    """
    Round model with CRUD operations and filtering using SQLite

    Note: This model uses denormalized data (player_name, course_name) for performance.
    The denormalized data is automatically kept in sync when players/courses are updated.
    Scores are stored in a separate round_scores table but are assembled into the
    scores array when returning round data for backward compatibility.
    """

    @staticmethod
    def _validate_date_and_course(date_played: str, course_id: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Validate date and course

        Args:
            date_played: Date in YYYY-MM-DD format
            course_id: Course ID

        Returns:
            Tuple of (is_valid, error_message, course_dict)
        """
        # Validate date
        is_valid, error = validate_date(date_played)
        if not is_valid:
            return False, error, None

        # Validate course exists
        course = Course.get_by_id(course_id)
        if not course:
            return False, "Course not found", None

        return True, "", course

    @staticmethod
    def _validate_and_process_scores(scores: List[Dict[str, Any]]) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        Validate and process player scores

        Args:
            scores: List of dicts with player_id, score, and optional hole_scores

        Returns:
            Tuple of (is_valid, error_message, validated_scores)
        """
        # Validate scores exist
        if not scores or len(scores) == 0:
            return False, "At least one player score is required", []

        validated_scores = []
        player_ids_seen = set()

        for score_data in scores:
            player_id = score_data.get('player_id')
            score = score_data.get('score')
            hole_scores = score_data.get('hole_scores')  # NEW: Optional hole-by-hole scores

            # Check for duplicate players
            if player_id in player_ids_seen:
                return False, "Duplicate player in round", []
            player_ids_seen.add(player_id)

            # Validate player exists
            player = Player.get_by_id(player_id)
            if not player:
                return False, f"Player not found: {player_id}", []

            # Validate score
            is_valid, error = validate_score(score)
            if not is_valid:
                return False, f"Invalid score for {player['name']}: {error}", []

            validated_scores.append({
                'player_id': player_id,
                'player_name': player['name'],  # Denormalized
                'score': int(score),
                'hole_scores': hole_scores  # Will be JSON-encoded when stored
            })

        return True, "", validated_scores

    @staticmethod
    def create(course_id: str, date_played: str, scores: List[Dict[str, Any]],
               notes: Optional[str] = None, round_start_time: Optional[str] = None,
               picture_filename: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Create a new round

        Args:
            course_id: Course ID
            date_played: Date in YYYY-MM-DD format
            scores: List of dicts with player_id, score, and optional hole_scores
            notes: Optional notes
            round_start_time: Optional round start time from game (for duplicate detection)
            picture_filename: Optional filename of uploaded round picture

        Returns:
            Tuple of (success, message, round_dict)
        """
        db = get_db()
        conn = db.get_connection()

        # Validate date and course
        is_valid, error, course = Round._validate_date_and_course(date_played, course_id)
        if not is_valid:
            return False, error, None

        # Validate and process scores
        is_valid, error, validated_scores = Round._validate_and_process_scores(scores)
        if not is_valid:
            return False, error, None

        # Create round
        round_id = str(uuid.uuid4())
        timestamp = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')

        try:
            # Use transaction to ensure round and scores are created atomically
            with db.transaction() as trans_conn:
                # Insert round
                trans_conn.execute("""
                    INSERT INTO rounds (
                        id, course_id, course_name, date_played, timestamp,
                        round_start_time, notes, picture_filename
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    round_id,
                    course_id,
                    course['name'],  # Denormalized
                    date_played,
                    timestamp,
                    round_start_time,
                    sanitize_html(notes) if notes else None,
                    picture_filename
                ))

                # Insert scores
                for score_data in validated_scores:
                    # Encode hole_scores as JSON if present
                    hole_scores_json = None
                    if score_data['hole_scores']:
                        hole_scores_json = json.dumps(score_data['hole_scores'])

                    trans_conn.execute("""
                        INSERT INTO round_scores (
                            round_id, player_id, player_name, score, hole_scores
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        round_id,
                        score_data['player_id'],
                        score_data['player_name'],
                        score_data['score'],
                        hole_scores_json
                    ))

            # Return the created round (transaction committed successfully)
            round_data = Round.get_by_id(round_id)
            return True, "Round created successfully", round_data

        except Exception as e:
            # Transaction automatically rolled back on exception
            return False, f"Error creating round: {str(e)}", None

    @staticmethod
    def update(round_id: str, course_id: str, date_played: str,
               scores: List[Dict[str, Any]], notes: Optional[str] = None) -> Tuple[bool, str]:
        """
        Update an existing round

        Args:
            round_id: Round ID to update
            course_id: Course ID
            date_played: Date in YYYY-MM-DD format
            scores: List of dicts with player_id, score, and optional hole_scores
            notes: Optional notes

        Returns:
            Tuple of (success, message)
        """
        db = get_db()
        conn = db.get_connection()

        # Check if round exists
        if not Round.get_by_id(round_id):
            return False, "Round not found"

        # Validate date and course
        is_valid, error, course = Round._validate_date_and_course(date_played, course_id)
        if not is_valid:
            return False, error

        # Validate and process scores
        is_valid, error, validated_scores = Round._validate_and_process_scores(scores)
        if not is_valid:
            return False, error

        try:
            # Use transaction to ensure round and scores are updated atomically
            with db.transaction() as trans_conn:
                # Update round
                trans_conn.execute("""
                    UPDATE rounds SET
                        course_id = ?,
                        course_name = ?,
                        date_played = ?,
                        notes = ?
                    WHERE id = ?
                """, (
                    course_id,
                    course['name'],  # Update denormalized
                    date_played,
                    sanitize_html(notes) if notes else None,
                    round_id
                ))

                # Delete old scores
                trans_conn.execute("DELETE FROM round_scores WHERE round_id = ?", (round_id,))

                # Insert new scores
                for score_data in validated_scores:
                    # Encode hole_scores as JSON if present
                    hole_scores_json = None
                    if score_data.get('hole_scores'):
                        hole_scores_json = json.dumps(score_data['hole_scores'])

                    trans_conn.execute("""
                        INSERT INTO round_scores (
                            round_id, player_id, player_name, score, hole_scores
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        round_id,
                        score_data['player_id'],
                        score_data['player_name'],
                        score_data['score'],
                        hole_scores_json
                    ))

            # Transaction committed successfully
            return True, "Round updated successfully"

        except Exception as e:
            return False, f"Error updating round: {str(e)}"

    @staticmethod
    def _round_row_to_dict(round_row, score_rows) -> Dict[str, Any]:
        """
        Convert round and score rows to dictionary format

        Args:
            round_row: Round table row
            score_rows: List of score table rows for this round

        Returns:
            Round dictionary with scores array
        """
        scores = []
        for score_row in score_rows:
            score_dict = {
                'player_id': score_row['player_id'],
                'player_name': score_row['player_name'],
                'score': score_row['score']
            }

            # Decode hole_scores JSON if present
            if score_row['hole_scores']:
                try:
                    score_dict['hole_scores'] = json.loads(score_row['hole_scores'])
                except json.JSONDecodeError:
                    score_dict['hole_scores'] = None

            scores.append(score_dict)

        # Handle trophy_up_for_grabs field (may not exist in older data)
        try:
            trophy_up_for_grabs = bool(round_row['trophy_up_for_grabs'])
        except (KeyError, IndexError):
            trophy_up_for_grabs = False

        return {
            'id': round_row['id'],
            'course_id': round_row['course_id'],
            'course_name': round_row['course_name'],
            'date_played': round_row['date_played'],
            'timestamp': round_row['timestamp'],
            'round_start_time': round_row['round_start_time'],
            'notes': round_row['notes'] or '',
            'picture_filename': round_row['picture_filename'],
            'trophy_up_for_grabs': trophy_up_for_grabs,
            'scores': scores
        }

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
        db = get_db()
        conn = db.get_connection()

        # Build query based on filters
        query = "SELECT * FROM rounds"
        params = []
        conditions = []

        if filters:
            if 'course_id' in filters:
                conditions.append("course_id = ?")
                params.append(filters['course_id'])

            if 'start_date' in filters:
                conditions.append("date_played >= ?")
                params.append(filters['start_date'])

            if 'end_date' in filters:
                conditions.append("date_played <= ?")
                params.append(filters['end_date'])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY date_played DESC"

        cursor = conn.execute(query, params)
        round_rows = cursor.fetchall()

        # Get scores for all rounds
        rounds = []
        for round_row in round_rows:
            score_cursor = conn.execute(
                "SELECT * FROM round_scores WHERE round_id = ?",
                (round_row['id'],)
            )
            score_rows = score_cursor.fetchall()

            # Filter by player if needed
            if filters and 'player_id' in filters:
                player_id = filters['player_id']
                if not any(s['player_id'] == player_id for s in score_rows):
                    continue  # Skip rounds where this player didn't play

            rounds.append(Round._round_row_to_dict(round_row, score_rows))

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
        db = get_db()
        conn = db.get_connection()

        cursor = conn.execute("SELECT * FROM rounds WHERE id = ?", (round_id,))
        round_row = cursor.fetchone()

        if not round_row:
            return None

        # Get scores for this round
        score_cursor = conn.execute(
            "SELECT * FROM round_scores WHERE round_id = ?",
            (round_id,)
        )
        score_rows = score_cursor.fetchall()

        return Round._round_row_to_dict(round_row, score_rows)

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
        Delete round (CASCADE deletes scores automatically)

        Args:
            round_id: Round ID

        Returns:
            Tuple of (success, message)
        """
        db = get_db()
        conn = db.get_connection()

        # Check if round exists
        if not Round.get_by_id(round_id):
            return False, "Round not found"

        # Delete round (scores are CASCADE deleted)
        conn.execute("DELETE FROM rounds WHERE id = ?", (round_id,))

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
