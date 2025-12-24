from typing import Optional, Dict, Any, List, Tuple
from models.player import Player
from models.user import User


class AuthService:
    """Authentication service for handling user authentication and registration"""

    @staticmethod
    def get_user_from_google(google_id: str, email: str, name: str) -> Optional[User]:
        """
        Get or prepare user from Google OAuth data

        Args:
            google_id: Google user ID
            email: User email from Google
            name: User name from Google

        Returns:
            User object if Google account is linked, None if needs registration
        """
        # Check if Google ID is already linked to a player
        player = Player.get_by_google_id(google_id)

        if player:
            # Update last login and return user
            Player.update_last_login(player['id'])
            return User(
                player_id=player['id'],
                google_id=player['google_id'],
                email=player['email'],
                name=player['name'],
                role=player.get('role', 'player')
            )

        # No linked account found - needs registration
        return None

    @staticmethod
    def link_google_to_player(google_id: str, player_id: str) -> Tuple[bool, str, Optional[User]]:
        """
        Link Google account to existing player

        Args:
            google_id: Google user ID
            player_id: Player ID to link to

        Returns:
            Tuple of (success, message, user_object)
        """
        # Link the accounts
        success, message = Player.link_google_account(player_id, google_id)

        if not success:
            return False, message, None

        # Get the updated player
        player = Player.get_by_id(player_id)
        if not player:
            return False, "Player not found after linking", None

        # Create and return user object
        user = User(
            player_id=player['id'],
            google_id=player['google_id'],
            email=player['email'],
            name=player['name'],
            role=player.get('role', 'player')
        )

        return True, message, user

    @staticmethod
    def get_unlinked_players() -> List[Dict[str, Any]]:
        """
        Get all active players without linked Google accounts

        Returns:
            List of player dictionaries without Google accounts
        """
        players = Player.get_all(active_only=True)
        return [p for p in players if not p.get('google_id')]

    @staticmethod
    def load_user(player_id: str) -> Optional[User]:
        """
        Load user by player ID (for Flask-Login user_loader)

        Args:
            player_id: Player ID

        Returns:
            User object or None
        """
        player = Player.get_by_id(player_id)

        if not player or not player.get('google_id'):
            return None

        return User(
            player_id=player['id'],
            google_id=player['google_id'],
            email=player['email'],
            name=player['name'],
            role=player.get('role', 'player')
        )

    @staticmethod
    def get_player_for_user(user: User) -> Optional[Dict[str, Any]]:
        """
        Get full player data for a user

        Args:
            user: User object

        Returns:
            Player dictionary or None
        """
        return Player.get_by_id(user.id)
