"""Tournament model for multi-round competitions"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from models.data_store import get_data_store
from models.round import Round
from models.player import Player


class Tournament:
    """Tournament model with CRUD operations"""

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

        store = get_data_store()
        data = store.read_tournaments()

        # Create tournament
        tournament = {
            'id': str(uuid.uuid4()),
            'name': name.strip(),
            'description': description.strip() if description else '',
            'start_date': start_date or '',
            'end_date': end_date or '',
            'round_ids': [],
            'created_at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'active': True
        }

        data['tournaments'].append(tournament)
        store.write_tournaments(data)

        return True, "Tournament created successfully", tournament

    @staticmethod
    def get_all(active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all tournaments

        Args:
            active_only: If True, return only active tournaments

        Returns:
            List of tournament dictionaries
        """
        store = get_data_store()
        data = store.read_tournaments()

        if active_only:
            return [t for t in data['tournaments'] if t.get('active', True)]

        return data['tournaments']

    @staticmethod
    def get_by_id(tournament_id: str) -> Optional[Dict[str, Any]]:
        """
        Get tournament by ID

        Args:
            tournament_id: Tournament ID

        Returns:
            Tournament dictionary or None
        """
        store = get_data_store()
        data = store.read_tournaments()

        for tournament in data['tournaments']:
            if tournament['id'] == tournament_id:
                return tournament

        return None

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
        store = get_data_store()
        data = store.read_tournaments()

        # Find tournament
        tournament = None
        for t in data['tournaments']:
            if t['id'] == tournament_id:
                tournament = t
                break

        if not tournament:
            return False, "Tournament not found"

        # Update fields
        if name is not None:
            if not name.strip():
                return False, "Tournament name cannot be empty"
            tournament['name'] = name.strip()

        if description is not None:
            tournament['description'] = description.strip()

        if start_date is not None:
            tournament['start_date'] = start_date

        if end_date is not None:
            tournament['end_date'] = end_date

        store.write_tournaments(data)
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
        store = get_data_store()
        data = store.read_tournaments()

        # Find tournament
        tournament = None
        for t in data['tournaments']:
            if t['id'] == tournament_id:
                tournament = t
                break

        if not tournament:
            return False, "Tournament not found"

        # Check if round exists
        round_data = Round.get_by_id(round_id)
        if not round_data:
            return False, "Round not found"

        # Add round if not already in tournament
        if round_id not in tournament['round_ids']:
            tournament['round_ids'].append(round_id)
            store.write_tournaments(data)
            return True, "Round added to tournament successfully"
        else:
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
        store = get_data_store()
        data = store.read_tournaments()

        # Find tournament
        tournament = None
        for t in data['tournaments']:
            if t['id'] == tournament_id:
                tournament = t
                break

        if not tournament:
            return False, "Tournament not found"

        # Remove round
        if round_id in tournament['round_ids']:
            tournament['round_ids'].remove(round_id)
            store.write_tournaments(data)
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
        store = get_data_store()
        data = store.read_tournaments()

        # Find tournament
        tournament_index = None
        for i, t in enumerate(data['tournaments']):
            if t['id'] == tournament_id:
                tournament_index = i
                break

        if tournament_index is None:
            return False, "Tournament not found"

        tournament = data['tournaments'][tournament_index]

        # Soft delete if has rounds
        if tournament['round_ids']:
            tournament['active'] = False
            store.write_tournaments(data)
            return True, "Tournament deactivated (has rounds)"
        else:
            # Hard delete if no rounds
            data['tournaments'].pop(tournament_index)
            store.write_tournaments(data)
            return True, "Tournament deleted successfully"
