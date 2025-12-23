import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from models.data_store import get_data_store
from utils.validators import validate_player_name, validate_email


class Player:
    """Player model with CRUD operations"""

    @staticmethod
    def create(name: str, email: Optional[str] = None, profile_picture: Optional[str] = None,
               favorite_color: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Create a new player

        Args:
            name: Player name
            email: Player email (optional)
            profile_picture: Profile picture filename (optional)
            favorite_color: Favorite color hex code (optional)

        Returns:
            Tuple of (success, message, player_dict)
        """
        store = get_data_store()
        data = store.read_players()

        # Validate name
        is_valid, error = validate_player_name(name, data['players'])
        if not is_valid:
            return False, error, None

        # Validate email
        is_valid, error = validate_email(email or '')
        if not is_valid:
            return False, error, None

        # Create player
        player = {
            'id': str(uuid.uuid4()),
            'name': name.strip(),
            'email': email.strip() if email else '',
            'profile_picture': profile_picture or '',
            'favorite_color': favorite_color or '#2e7d32',
            'created_at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'active': True
        }

        data['players'].append(player)
        store.write_players(data)

        return True, "Player created successfully", player

    @staticmethod
    def get_all(active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all players

        Args:
            active_only: If True, return only active players

        Returns:
            List of player dictionaries
        """
        store = get_data_store()
        data = store.read_players()

        if active_only:
            return [p for p in data['players'] if p.get('active', True)]

        return data['players']

    @staticmethod
    def get_by_id(player_id: str) -> Optional[Dict[str, Any]]:
        """
        Get player by ID

        Args:
            player_id: Player ID

        Returns:
            Player dictionary or None
        """
        store = get_data_store()
        data = store.read_players()

        for player in data['players']:
            if player['id'] == player_id:
                return player

        return None

    @staticmethod
    def update(player_id: str, name: Optional[str] = None, email: Optional[str] = None,
               profile_picture: Optional[str] = None, favorite_color: Optional[str] = None) -> Tuple[bool, str]:
        """
        Update player

        Args:
            player_id: Player ID
            name: New name (optional)
            email: New email (optional)
            profile_picture: Profile picture filename (optional)
            favorite_color: Favorite color hex code (optional)

        Returns:
            Tuple of (success, message)
        """
        store = get_data_store()
        data = store.read_players()

        # Find player
        player = None
        for p in data['players']:
            if p['id'] == player_id:
                player = p
                break

        if not player:
            return False, "Player not found"

        # Validate and update name
        if name is not None:
            is_valid, error = validate_player_name(name, data['players'], exclude_id=player_id)
            if not is_valid:
                return False, error

            old_name = player['name']
            player['name'] = name.strip()

            # Update denormalized data in rounds
            if old_name != player['name']:
                Player._update_name_in_rounds(player_id, player['name'])

        # Validate and update email
        if email is not None:
            is_valid, error = validate_email(email)
            if not is_valid:
                return False, error
            player['email'] = email.strip()

        # Update profile picture
        if profile_picture is not None:
            player['profile_picture'] = profile_picture

        # Update favorite color
        if favorite_color is not None:
            player['favorite_color'] = favorite_color

        store.write_players(data)
        return True, "Player updated successfully"

    @staticmethod
    def delete(player_id: str, force: bool = False) -> Tuple[bool, str]:
        """
        Delete player (soft delete by default, hard delete if force=True)

        Args:
            player_id: Player ID
            force: If True, permanently delete the player

        Returns:
            Tuple of (success, message)
        """
        store = get_data_store()
        data = store.read_players()

        # Find player
        player_index = None
        for i, p in enumerate(data['players']):
            if p['id'] == player_id:
                player_index = i
                break

        if player_index is None:
            return False, "Player not found"

        # Check if player has rounds
        has_rounds = Player._has_rounds(player_id)

        if has_rounds and not force:
            # Soft delete
            data['players'][player_index]['active'] = False
            store.write_players(data)
            return True, "Player deactivated (has existing rounds)"
        else:
            # Hard delete
            data['players'].pop(player_index)
            store.write_players(data)
            return True, "Player deleted successfully"

    @staticmethod
    def _has_rounds(player_id: str) -> bool:
        """Check if player has any rounds"""
        from models.round import Round
        rounds = Round.get_by_player(player_id)
        return len(rounds) > 0

    @staticmethod
    def _update_name_in_rounds(player_id: str, new_name: str):
        """Update denormalized player name in all rounds"""
        store = get_data_store()
        data = store.read_rounds()

        updated = False
        for round_data in data['rounds']:
            for score in round_data['scores']:
                if score['player_id'] == player_id:
                    score['player_name'] = new_name
                    updated = True

        if updated:
            store.write_rounds(data)
