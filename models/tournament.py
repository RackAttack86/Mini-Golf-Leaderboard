"""Tournament model for multi-round competitions"""
import uuid
from datetime import datetime, UTC
from typing import List, Optional, Dict, Any, Tuple
from models.database import get_db
from models.round import Round
from models.player import Player


class Tournament:
    """Tournament model with CRUD operations using SQLite"""

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        """Convert SQLite Row to dictionary"""
        return {
            'id': row['id'],
            'name': row['name'],
            'description': row['description'] or '',
            'start_date': row['start_date'] or '',
            'end_date': row['end_date'] or '',
            'created_at': row['created_at'],
            'active': bool(row['active'])
        }

    @staticmethod
    def create(name: str, description: Optional[str] = None,
               start_date: Optional[str] = None, end_date: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Create a new tournament

        Args:
            name: Tournament name
            description: Tournament description (optional)
            start_date: Start date (YYYY-MM-DD) (optional)
            end_date: End date (YYYY-MM-DD) (optional)

        Returns:
            Tuple of (success, message, tournament_dict)
        """
        if not name or not name.strip():
            return False, "Tournament name is required", None

        db = get_db()
        conn = db.get_connection()

        tournament_id = str(uuid.uuid4())
        created_at = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')

        try:
            conn.execute("""
                INSERT INTO tournaments (
                    id, name, description, start_date, end_date, created_at, active
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                tournament_id,
                name.strip(),
                description.strip() if description else None,
                start_date or None,
                end_date or None,
                created_at,
                1  # active
            ))

            tournament = Tournament.get_by_id(tournament_id)
            return True, "Tournament created successfully", tournament

        except Exception as e:
            return False, f"Error creating tournament: {str(e)}", None

    @staticmethod
    def get_all(active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all tournaments

        Args:
            active_only: If True, return only active tournaments

        Returns:
            List of tournament dictionaries
        """
        db = get_db()
        conn = db.get_connection()

        if active_only:
            cursor = conn.execute(
                "SELECT * FROM tournaments WHERE active = 1 ORDER BY created_at DESC"
            )
        else:
            cursor = conn.execute("SELECT * FROM tournaments ORDER BY created_at DESC")

        return [Tournament._row_to_dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_by_id(tournament_id: str) -> Optional[Dict[str, Any]]:
        """
        Get tournament by ID

        Args:
            tournament_id: Tournament ID

        Returns:
            Tournament dictionary or None (includes round_ids for compatibility)
        """
        db = get_db()
        conn = db.get_connection()

        cursor = conn.execute("SELECT * FROM tournaments WHERE id = ?", (tournament_id,))
        row = cursor.fetchone()

        if not row:
            return None

        tournament = Tournament._row_to_dict(row)

        # Get round IDs for this tournament (for backward compatibility)
        cursor = conn.execute(
            "SELECT round_id FROM tournament_rounds WHERE tournament_id = ? ORDER BY rowid",
            (tournament_id,)
        )
        tournament['round_ids'] = [r['round_id'] for r in cursor.fetchall()]

        return tournament

    @staticmethod
    def update(tournament_id: str, name: Optional[str] = None, description: Optional[str] = None,
               start_date: Optional[str] = None, end_date: Optional[str] = None) -> Tuple[bool, str]:
        """
        Update tournament

        Args:
            tournament_id: Tournament ID
            name: New name (optional)
            description: New description (optional)
            start_date: New start date (optional)
            end_date: New end date (optional)

        Returns:
            Tuple of (success, message)
        """
        db = get_db()
        conn = db.get_connection()

        # Find tournament
        tournament = Tournament.get_by_id(tournament_id)
        if not tournament:
            return False, "Tournament not found"

        # Update fields
        if name is not None:
            if not name.strip():
                return False, "Tournament name cannot be empty"
            conn.execute("UPDATE tournaments SET name = ? WHERE id = ?", (name.strip(), tournament_id))

        if description is not None:
            conn.execute("UPDATE tournaments SET description = ? WHERE id = ?", (description.strip(), tournament_id))

        if start_date is not None:
            conn.execute("UPDATE tournaments SET start_date = ? WHERE id = ?", (start_date, tournament_id))

        if end_date is not None:
            conn.execute("UPDATE tournaments SET end_date = ? WHERE id = ?", (end_date, tournament_id))

        return True, "Tournament updated successfully"

    @staticmethod
    def add_round(tournament_id: str, round_id: str) -> Tuple[bool, str]:
        """
        Add a round to a tournament

        Args:
            tournament_id: Tournament ID
            round_id: Round ID

        Returns:
            Tuple of (success, message)
        """
        db = get_db()
        conn = db.get_connection()

        # Find tournament
        tournament = Tournament.get_by_id(tournament_id)
        if not tournament:
            return False, "Tournament not found"

        # Check if round exists
        round_data = Round.get_by_id(round_id)
        if not round_data:
            return False, "Round not found"

        try:
            # Try to insert, will fail if already exists (primary key constraint)
            conn.execute(
                "INSERT INTO tournament_rounds (tournament_id, round_id) VALUES (?, ?)",
                (tournament_id, round_id)
            )
            return True, "Round added to tournament successfully"
        except Exception:
            return False, "Round already in tournament"

    @staticmethod
    def remove_round(tournament_id: str, round_id: str) -> Tuple[bool, str]:
        """
        Remove a round from a tournament

        Args:
            tournament_id: Tournament ID
            round_id: Round ID

        Returns:
            Tuple of (success, message)
        """
        db = get_db()
        conn = db.get_connection()

        # Find tournament
        tournament = Tournament.get_by_id(tournament_id)
        if not tournament:
            return False, "Tournament not found"

        # Remove round
        cursor = conn.execute(
            "DELETE FROM tournament_rounds WHERE tournament_id = ? AND round_id = ?",
            (tournament_id, round_id)
        )

        if cursor.rowcount > 0:
            return True, "Round removed from tournament successfully"
        else:
            return False, "Round not in tournament"

    @staticmethod
    def get_standings(tournament_id: str) -> List[Dict[str, Any]]:
        """
        Calculate tournament standings

        Args:
            tournament_id: Tournament ID

        Returns:
            List of player standings with scores
        """
        tournament = Tournament.get_by_id(tournament_id)
        if not tournament:
            return []

        # Get all rounds in tournament
        rounds = []
        for round_id in tournament['round_ids']:
            round_data = Round.get_by_id(round_id)
            if round_data:
                rounds.append(round_data)

        if not rounds:
            return []

        # Calculate standings
        player_stats = {}  # {player_id: {'name': ..., 'total_score': ..., 'rounds': ..., 'wins': ...}}

        for round_data in rounds:
            # Find winner of this round
            winner_score = min(s['score'] for s in round_data['scores']) if round_data['scores'] else None

            for score_data in round_data['scores']:
                player_id = score_data['player_id']
                player_name = score_data['player_name']
                score = score_data['score']

                if player_id not in player_stats:
                    player_stats[player_id] = {
                        'player_id': player_id,
                        'player_name': player_name,
                        'total_score': 0,
                        'rounds_played': 0,
                        'wins': 0,
                        'avg_score': 0
                    }

                player_stats[player_id]['total_score'] += score
                player_stats[player_id]['rounds_played'] += 1

                # Check if player won this round
                if winner_score and score == winner_score:
                    player_stats[player_id]['wins'] += 1

        # Calculate averages and sort
        standings = []
        for stats in player_stats.values():
            if stats['rounds_played'] > 0:
                stats['avg_score'] = round(stats['total_score'] / stats['rounds_played'], 2)
            standings.append(stats)

        # Sort by lowest average score (better in golf)
        standings.sort(key=lambda x: (x['avg_score'], -x['wins']))

        return standings

    @staticmethod
    def delete(tournament_id: str) -> Tuple[bool, str]:
        """
        Delete tournament (soft delete if has rounds)

        Args:
            tournament_id: Tournament ID

        Returns:
            Tuple of (success, message)
        """
        db = get_db()
        conn = db.get_connection()

        # Find tournament
        tournament = Tournament.get_by_id(tournament_id)
        if not tournament:
            return False, "Tournament not found"

        # Check if has rounds
        cursor = conn.execute(
            "SELECT COUNT(*) as count FROM tournament_rounds WHERE tournament_id = ?",
            (tournament_id,)
        )
        has_rounds = cursor.fetchone()['count'] > 0

        if has_rounds:
            # Soft delete
            conn.execute("UPDATE tournaments SET active = 0 WHERE id = ?", (tournament_id,))
            return True, "Tournament deactivated (has rounds)"
        else:
            # Hard delete
            conn.execute("DELETE FROM tournaments WHERE id = ?", (tournament_id,))
            return True, "Tournament deleted successfully"
