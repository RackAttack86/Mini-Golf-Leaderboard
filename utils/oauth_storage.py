"""
Custom OAuth storage backend with debugging
"""
from flask_dance.consumer.storage import BaseStorage
from flask import session
from utils.error_tracker import error_tracker


class DebugSessionStorage(BaseStorage):
    """Session storage with error tracking"""

    def __init__(self, key='flask_dance_token', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.key = key

    def get(self, blueprint):
        """Get token from session"""
        try:
            token = session.get(f"{self.key}.{blueprint.name}")
            error_tracker.log_error('oauth_storage_get', f"Retrieved token for {blueprint.name}", None, {
                'blueprint': blueprint.name,
                'has_token': bool(token)
            })
            return token
        except Exception as e:
            error_tracker.log_error('oauth_storage_get_error', str(e), e, {
                'blueprint': blueprint.name
            })
            raise

    def set(self, blueprint, token):
        """Store token in session"""
        try:
            error_tracker.log_error('oauth_storage_set', f"Storing token for {blueprint.name}", None, {
                'blueprint': blueprint.name,
                'has_token': bool(token)
            })
            session[f"{self.key}.{blueprint.name}"] = token
        except Exception as e:
            error_tracker.log_error('oauth_storage_set_error', str(e), e, {
                'blueprint': blueprint.name,
                'token_type': str(type(token)) if token else None
            })
            raise

    def delete(self, blueprint):
        """Delete token from session"""
        try:
            key = f"{self.key}.{blueprint.name}"
            if key in session:
                del session[key]
            error_tracker.log_error('oauth_storage_delete', f"Deleted token for {blueprint.name}", None, {
                'blueprint': blueprint.name
            })
        except Exception as e:
            error_tracker.log_error('oauth_storage_delete_error', str(e), e, {
                'blueprint': blueprint.name
            })
            raise
