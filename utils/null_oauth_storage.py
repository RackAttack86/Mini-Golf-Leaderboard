"""
Null OAuth storage backend - doesn't store tokens since we only use OAuth for login
"""
from flask_dance.consumer.storage import BaseStorage


class NullStorage(BaseStorage):
    """Storage backend that doesn't actually store tokens"""

    def get(self, blueprint):
        """Always return None - no stored token"""
        return None

    def set(self, blueprint, token):
        """Don't store the token - we handle login in the signal handler"""
        pass

    def delete(self, blueprint):
        """Nothing to delete"""
        pass
