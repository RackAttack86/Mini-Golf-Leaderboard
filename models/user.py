from flask_login import UserMixin
from typing import Optional


class User(UserMixin):
    """User class for Flask-Login integration"""

    def __init__(self, player_id: str, google_id: str, email: str, name: str, role: str):
        """
        Initialize User instance

        Args:
            player_id: Player ID (used as Flask-Login user ID)
            google_id: Google user ID
            email: User email
            name: User name
            role: User role ('admin' or 'player')
        """
        self.id = player_id  # Flask-Login uses 'id' attribute
        self.google_id = google_id
        self.email = email
        self.name = name
        self.role = role

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role"""
        return self.role == 'admin'

    def __repr__(self) -> str:
        return f'<User {self.name} ({self.role})>'
