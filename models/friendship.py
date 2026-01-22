# Standard library
from datetime import datetime, UTC
from typing import List, Optional, Dict, Any, Tuple

# Local
from models.database import get_db


class Friendship:
    """Friendship model with CRUD operations for managing friend relationships"""

    # Status constants
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        """Convert SQLite Row to dictionary"""
        return {
            'id': row['id'],
            'requester_id': row['requester_id'],
            'addressee_id': row['addressee_id'],
            'status': row['status'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        }

    @staticmethod
    def send_request(requester_id: str, addressee_id: str) -> Tuple[bool, str]:
        """
        Send a friend request

        Args:
            requester_id: ID of the player sending the request
            addressee_id: ID of the player receiving the request

        Returns:
            Tuple of (success, message)
        """
        if requester_id == addressee_id:
            return False, "Cannot send friend request to yourself"

        db = get_db()
        conn = db.get_connection()

        # Check if a friendship already exists (in either direction)
        existing = Friendship._get_friendship_record(requester_id, addressee_id)
        if existing:
            if existing['status'] == Friendship.STATUS_ACCEPTED:
                return False, "You are already friends"
            elif existing['status'] == Friendship.STATUS_PENDING:
                if existing['requester_id'] == requester_id:
                    return False, "Friend request already sent"
                else:
                    # The other person already sent us a request - accept it
                    return Friendship.accept_request(existing['id'], requester_id)
            elif existing['status'] == Friendship.STATUS_REJECTED:
                # Allow re-requesting after rejection
                now = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
                conn.execute(
                    "UPDATE friendships SET status = ?, requester_id = ?, addressee_id = ?, updated_at = ? WHERE id = ?",
                    (Friendship.STATUS_PENDING, requester_id, addressee_id, now, existing['id'])
                )
                return True, "Friend request sent"

        # Create new friendship request
        now = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
        try:
            conn.execute("""
                INSERT INTO friendships (requester_id, addressee_id, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (requester_id, addressee_id, Friendship.STATUS_PENDING, now, now))
            return True, "Friend request sent"
        except Exception as e:
            return False, f"Error sending friend request: {str(e)}"

    @staticmethod
    def accept_request(friendship_id: int, user_id: str) -> Tuple[bool, str]:
        """
        Accept a pending friend request

        Args:
            friendship_id: ID of the friendship record
            user_id: ID of the user accepting (must be the addressee)

        Returns:
            Tuple of (success, message)
        """
        db = get_db()
        conn = db.get_connection()

        # Get the friendship record
        cursor = conn.execute("SELECT * FROM friendships WHERE id = ?", (friendship_id,))
        row = cursor.fetchone()

        if not row:
            return False, "Friend request not found"

        if row['addressee_id'] != user_id:
            return False, "Only the recipient can accept this request"

        if row['status'] != Friendship.STATUS_PENDING:
            return False, "This request is no longer pending"

        # Accept the request
        now = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
        conn.execute(
            "UPDATE friendships SET status = ?, updated_at = ? WHERE id = ?",
            (Friendship.STATUS_ACCEPTED, now, friendship_id)
        )
        return True, "Friend request accepted"

    @staticmethod
    def reject_request(friendship_id: int, user_id: str) -> Tuple[bool, str]:
        """
        Reject a pending friend request

        Args:
            friendship_id: ID of the friendship record
            user_id: ID of the user rejecting (must be the addressee)

        Returns:
            Tuple of (success, message)
        """
        db = get_db()
        conn = db.get_connection()

        # Get the friendship record
        cursor = conn.execute("SELECT * FROM friendships WHERE id = ?", (friendship_id,))
        row = cursor.fetchone()

        if not row:
            return False, "Friend request not found"

        if row['addressee_id'] != user_id:
            return False, "Only the recipient can reject this request"

        if row['status'] != Friendship.STATUS_PENDING:
            return False, "This request is no longer pending"

        # Reject the request
        now = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
        conn.execute(
            "UPDATE friendships SET status = ?, updated_at = ? WHERE id = ?",
            (Friendship.STATUS_REJECTED, now, friendship_id)
        )
        return True, "Friend request rejected"

    @staticmethod
    def remove_friend(player_id: str, friend_id: str) -> Tuple[bool, str]:
        """
        Remove an existing friendship (either party can remove)

        Args:
            player_id: ID of the player initiating removal
            friend_id: ID of the friend to remove

        Returns:
            Tuple of (success, message)
        """
        db = get_db()
        conn = db.get_connection()

        # Find the accepted friendship
        friendship = Friendship._get_friendship_record(player_id, friend_id)

        if not friendship:
            return False, "Friendship not found"

        if friendship['status'] != Friendship.STATUS_ACCEPTED:
            return False, "You are not friends with this player"

        # Delete the friendship
        conn.execute("DELETE FROM friendships WHERE id = ?", (friendship['id'],))
        return True, "Friend removed"

    @staticmethod
    def get_friends(player_id: str) -> List[Dict[str, Any]]:
        """
        Get all accepted friends for a player

        Args:
            player_id: Player ID

        Returns:
            List of friend player dictionaries (with player info)
        """
        db = get_db()
        conn = db.get_connection()

        # Get friends where player is either requester or addressee
        cursor = conn.execute("""
            SELECT p.*
            FROM players p
            JOIN friendships f ON (
                (f.requester_id = ? AND f.addressee_id = p.id) OR
                (f.addressee_id = ? AND f.requester_id = p.id)
            )
            WHERE f.status = ?
            AND p.active = 1
            ORDER BY p.name
        """, (player_id, player_id, Friendship.STATUS_ACCEPTED))

        friends = []
        for row in cursor.fetchall():
            friends.append({
                'id': row['id'],
                'name': row['name'],
                'email': row['email'] or '',
                'profile_picture': row['profile_picture'] or '',
                'favorite_color': row['favorite_color'] or '#2e7d32'
            })
        return friends

    @staticmethod
    def get_friend_ids(player_id: str) -> List[str]:
        """
        Get just the IDs of accepted friends

        Args:
            player_id: Player ID

        Returns:
            List of friend player IDs
        """
        db = get_db()
        conn = db.get_connection()

        cursor = conn.execute("""
            SELECT
                CASE
                    WHEN requester_id = ? THEN addressee_id
                    ELSE requester_id
                END as friend_id
            FROM friendships
            WHERE status = ?
            AND (requester_id = ? OR addressee_id = ?)
        """, (player_id, Friendship.STATUS_ACCEPTED, player_id, player_id))

        return [row['friend_id'] for row in cursor.fetchall()]

    @staticmethod
    def get_friends_and_self(player_id: str) -> List[str]:
        """
        Get friend IDs + the player's own ID (for inclusive filtering)

        Args:
            player_id: Player ID

        Returns:
            List containing the player's ID and all friend IDs
        """
        friend_ids = Friendship.get_friend_ids(player_id)
        return [player_id] + friend_ids

    @staticmethod
    def get_pending_requests_received(player_id: str) -> List[Dict[str, Any]]:
        """
        Get pending friend requests sent TO this player

        Args:
            player_id: Player ID

        Returns:
            List of pending request dictionaries with requester info
        """
        db = get_db()
        conn = db.get_connection()

        cursor = conn.execute("""
            SELECT f.*, p.name as requester_name, p.profile_picture as requester_profile_picture,
                   p.favorite_color as requester_favorite_color
            FROM friendships f
            JOIN players p ON f.requester_id = p.id
            WHERE f.addressee_id = ?
            AND f.status = ?
            AND p.active = 1
            ORDER BY f.created_at DESC
        """, (player_id, Friendship.STATUS_PENDING))

        requests = []
        for row in cursor.fetchall():
            requests.append({
                'id': row['id'],
                'requester_id': row['requester_id'],
                'requester_name': row['requester_name'],
                'requester_profile_picture': row['requester_profile_picture'] or '',
                'requester_favorite_color': row['requester_favorite_color'] or '#2e7d32',
                'created_at': row['created_at']
            })
        return requests

    @staticmethod
    def get_pending_requests_sent(player_id: str) -> List[Dict[str, Any]]:
        """
        Get pending friend requests sent BY this player

        Args:
            player_id: Player ID

        Returns:
            List of pending request dictionaries with addressee info
        """
        db = get_db()
        conn = db.get_connection()

        cursor = conn.execute("""
            SELECT f.*, p.name as addressee_name, p.profile_picture as addressee_profile_picture,
                   p.favorite_color as addressee_favorite_color
            FROM friendships f
            JOIN players p ON f.addressee_id = p.id
            WHERE f.requester_id = ?
            AND f.status = ?
            AND p.active = 1
            ORDER BY f.created_at DESC
        """, (player_id, Friendship.STATUS_PENDING))

        requests = []
        for row in cursor.fetchall():
            requests.append({
                'id': row['id'],
                'addressee_id': row['addressee_id'],
                'addressee_name': row['addressee_name'],
                'addressee_profile_picture': row['addressee_profile_picture'] or '',
                'addressee_favorite_color': row['addressee_favorite_color'] or '#2e7d32',
                'created_at': row['created_at']
            })
        return requests

    @staticmethod
    def get_friendship_status(player_id: str, other_id: str) -> Optional[Dict[str, Any]]:
        """
        Get friendship status between two players

        Args:
            player_id: First player ID
            other_id: Second player ID

        Returns:
            Dictionary with status info or None if no relationship exists
        """
        friendship = Friendship._get_friendship_record(player_id, other_id)
        if not friendship:
            return None

        return {
            'id': friendship['id'],
            'status': friendship['status'],
            'is_requester': friendship['requester_id'] == player_id,
            'is_addressee': friendship['addressee_id'] == player_id
        }

    @staticmethod
    def are_friends(player_id: str, other_id: str) -> bool:
        """
        Check if two players are friends

        Args:
            player_id: First player ID
            other_id: Second player ID

        Returns:
            True if they are accepted friends, False otherwise
        """
        friendship = Friendship._get_friendship_record(player_id, other_id)
        return friendship is not None and friendship['status'] == Friendship.STATUS_ACCEPTED

    @staticmethod
    def get_pending_request_count(player_id: str) -> int:
        """
        Get count of pending requests for a player (for notification badge)

        Args:
            player_id: Player ID

        Returns:
            Count of pending friend requests received
        """
        db = get_db()
        conn = db.get_connection()

        cursor = conn.execute("""
            SELECT COUNT(*) as count
            FROM friendships f
            JOIN players p ON f.requester_id = p.id
            WHERE f.addressee_id = ?
            AND f.status = ?
            AND p.active = 1
        """, (player_id, Friendship.STATUS_PENDING))

        row = cursor.fetchone()
        return row['count'] if row else 0

    @staticmethod
    def _get_friendship_record(player_id: str, other_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the friendship record between two players (internal helper)

        Args:
            player_id: First player ID
            other_id: Second player ID

        Returns:
            Friendship dictionary or None
        """
        db = get_db()
        conn = db.get_connection()

        cursor = conn.execute("""
            SELECT * FROM friendships
            WHERE (requester_id = ? AND addressee_id = ?)
            OR (requester_id = ? AND addressee_id = ?)
        """, (player_id, other_id, other_id, player_id))

        row = cursor.fetchone()
        return Friendship._row_to_dict(row) if row else None
