import uuid
from datetime import datetime, UTC
from typing import List, Optional, Dict, Any, Tuple
from models.database import get_db
from utils.validators import validate_player_name, validate_email, sanitize_html


class Player:
    """Player model with CRUD operations using SQLite"""

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        """Convert SQLite Row to dictionary"""
        return {
            'id': row['id'],
            'name': row['name'],
            'email': row['email'] or '',
            'profile_picture': row['profile_picture'] or '',
            'favorite_color': row['favorite_color'] or '#2e7d32',
            'google_id': row['google_id'],
            'role': row['role'] or 'player',
            'last_login': row['last_login'],
            'created_at': row['created_at'],
            'active': bool(row['active']),
            'meta_quest_username': row['meta_quest_username']
        }

    @staticmethod
    def create(name: str, email: Optional[str] = None, profile_picture: Optional[str] = None,
               favorite_color: Optional[str] = None, role: str = 'player') -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Create a new player

        Args:
            name: Player name
            email: Player email (optional)
            profile_picture: Profile picture filename (optional)
            favorite_color: Favorite color hex code (optional)
            role: Player role - 'player' or 'admin' (default: 'player')

        Returns:
            Tuple of (success, message, player_dict)
        """
        db = get_db()
        conn = db.get_connection()

        # Get all players for validation
        all_players = Player.get_all(active_only=False)

        # Validate name
        is_valid, error = validate_player_name(name, all_players)
        if not is_valid:
            return False, error, None

        # Validate email
        is_valid, error = validate_email(email or '')
        if not is_valid:
            return False, error, None

        # Create player
        player_id = str(uuid.uuid4())
        created_at = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')

        try:
            conn.execute("""
                INSERT INTO players (
                    id, name, email, profile_picture, favorite_color,
                    google_id, role, last_login, created_at, active, meta_quest_username
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                player_id,
                sanitize_html(name),
                email.strip() if email else None,
                profile_picture or None,
                favorite_color or '#2e7d32',
                None,  # google_id
                role if role in ['admin', 'player'] else 'player',
                None,  # last_login
                created_at,
                1,  # active
                None  # meta_quest_username
            ))

            # Return the created player
            player = Player.get_by_id(player_id)
            return True, "Player created successfully", player

        except Exception as e:
            return False, f"Error creating player: {str(e)}", None

    @staticmethod
    def get_all(active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all players

        Args:
            active_only: If True, return only active players

        Returns:
            List of player dictionaries
        """
        db = get_db()
        conn = db.get_connection()

        if active_only:
            cursor = conn.execute(
                "SELECT * FROM players WHERE active = 1 ORDER BY name"
            )
        else:
            cursor = conn.execute("SELECT * FROM players ORDER BY name")

        return [Player._row_to_dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_by_id(player_id: str) -> Optional[Dict[str, Any]]:
        """
        Get player by ID

        Args:
            player_id: Player ID

        Returns:
            Player dictionary or None
        """
        db = get_db()
        conn = db.get_connection()

        cursor = conn.execute("SELECT * FROM players WHERE id = ?", (player_id,))
        row = cursor.fetchone()

        return Player._row_to_dict(row) if row else None

    @staticmethod
    def update(player_id: str, name: Optional[str] = None, email: Optional[str] = None,
               profile_picture: Optional[str] = None, favorite_color: Optional[str] = None,
               role: Optional[str] = None) -> Tuple[bool, str]:
        """
        Update player

        Args:
            player_id: Player ID
            name: New name (optional)
            email: New email (optional)
            profile_picture: Profile picture filename (optional)
            favorite_color: Favorite color hex code (optional)
            role: Player role - 'player' or 'admin' (optional)

        Returns:
            Tuple of (success, message)
        """
        db = get_db()
        conn = db.get_connection()

        # Find player
        player = Player.get_by_id(player_id)
        if not player:
            return False, "Player not found"

        # Validate and update name
        if name is not None:
            all_players = Player.get_all(active_only=False)
            is_valid, error = validate_player_name(name, all_players, exclude_id=player_id)
            if not is_valid:
                return False, error

            old_name = player['name']
            new_name = sanitize_html(name)

            conn.execute("UPDATE players SET name = ? WHERE id = ?", (new_name, player_id))

            # Update denormalized data in rounds
            if old_name != new_name:
                Player._update_name_in_rounds(player_id, new_name)

        # Validate and update email
        if email is not None:
            is_valid, error = validate_email(email)
            if not is_valid:
                return False, error
            conn.execute("UPDATE players SET email = ? WHERE id = ?", (email.strip(), player_id))

        # Update profile picture
        if profile_picture is not None:
            conn.execute("UPDATE players SET profile_picture = ? WHERE id = ?", (profile_picture, player_id))

        # Update favorite color
        if favorite_color is not None:
            conn.execute("UPDATE players SET favorite_color = ? WHERE id = ?", (favorite_color, player_id))

        # Update role
        if role is not None and role in ['admin', 'player']:
            conn.execute("UPDATE players SET role = ? WHERE id = ?", (role, player_id))

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
        db = get_db()
        conn = db.get_connection()

        # Find player
        player = Player.get_by_id(player_id)
        if not player:
            return False, "Player not found"

        # Check if player has rounds
        has_rounds = Player._has_rounds(player_id)

        if has_rounds and not force:
            # Soft delete
            conn.execute("UPDATE players SET active = 0 WHERE id = ?", (player_id,))
            return True, "Player deactivated (has existing rounds)"
        else:
            # Hard delete
            conn.execute("DELETE FROM players WHERE id = ?", (player_id,))
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
        db = get_db()
        conn = db.get_connection()

        # Update in round_scores table
        conn.execute(
            "UPDATE round_scores SET player_name = ? WHERE player_id = ?",
            (new_name, player_id)
        )

    @staticmethod
    def get_by_google_id(google_id: str) -> Optional[Dict[str, Any]]:
        """
        Get player by Google ID

        Args:
            google_id: Google user ID

        Returns:
            Player dictionary or None
        """
        db = get_db()
        conn = db.get_connection()

        cursor = conn.execute("SELECT * FROM players WHERE google_id = ?", (google_id,))
        row = cursor.fetchone()

        return Player._row_to_dict(row) if row else None

    @staticmethod
    def link_google_account(player_id: str, google_id: str) -> Tuple[bool, str]:
        """
        Link Google account to player

        Args:
            player_id: Player ID
            google_id: Google user ID

        Returns:
            Tuple of (success, message)
        """
        db = get_db()
        conn = db.get_connection()

        # Check if Google ID is already linked
        existing = Player.get_by_google_id(google_id)
        if existing and existing['id'] != player_id:
            return False, "This Google account is already linked to another player"

        # Find player
        player = Player.get_by_id(player_id)
        if not player:
            return False, "Player not found"

        # Link Google account
        last_login = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
        conn.execute(
            "UPDATE players SET google_id = ?, last_login = ? WHERE id = ?",
            (google_id, last_login, player_id)
        )

        return True, "Google account linked successfully"

    @staticmethod
    def update_last_login(player_id: str) -> Tuple[bool, str]:
        """
        Update player's last login timestamp

        Args:
            player_id: Player ID

        Returns:
            Tuple of (success, message)
        """
        db = get_db()
        conn = db.get_connection()

        # Find player
        player = Player.get_by_id(player_id)
        if not player:
            return False, "Player not found"

        # Update last login
        last_login = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
        conn.execute("UPDATE players SET last_login = ? WHERE id = ?", (last_login, player_id))

        return True, "Last login updated successfully"

    @staticmethod
    def is_admin(player_id: str) -> bool:
        """
        Check if player has admin role

        Args:
            player_id: Player ID

        Returns:
            True if player is admin, False otherwise
        """
        player = Player.get_by_id(player_id)
        if not player:
            return False

        return player.get('role', 'player') == 'admin'

    # New methods for Meta Quest username support

    @staticmethod
    def set_meta_quest_username(player_id: str, username: str) -> Tuple[bool, str]:
        """
        Set Meta Quest username for player

        Args:
            player_id: Player ID
            username: Meta Quest username

        Returns:
            Tuple of (success, message)
        """
        db = get_db()
        conn = db.get_connection()

        # Check if username is already taken
        existing = Player.get_by_meta_quest_username(username)
        if existing and existing['id'] != player_id:
            return False, "This Meta Quest username is already linked to another player"

        # Find player
        player = Player.get_by_id(player_id)
        if not player:
            return False, "Player not found"

        try:
            conn.execute(
                "UPDATE players SET meta_quest_username = ? WHERE id = ?",
                (username.strip() if username else None, player_id)
            )
            return True, "Meta Quest username updated successfully"
        except Exception as e:
            return False, f"Error updating Meta Quest username: {str(e)}"

    @staticmethod
    def get_by_meta_quest_username(username: str) -> Optional[Dict[str, Any]]:
        """
        Get player by Meta Quest username

        Args:
            username: Meta Quest username

        Returns:
            Player dictionary or None
        """
        if not username:
            return None

        db = get_db()
        conn = db.get_connection()

        cursor = conn.execute(
            "SELECT * FROM players WHERE meta_quest_username = ? COLLATE NOCASE",
            (username.strip(),)
        )
        row = cursor.fetchone()

        return Player._row_to_dict(row) if row else None
