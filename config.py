import os
from pathlib import Path
from datetime import timedelta

class Config:
    """Application configuration"""

    # Application settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_ENV') != 'production'

    # Data storage
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / 'data'

    # Pagination
    ROUNDS_PER_PAGE = 20

    # Date formats
    DATE_FORMAT = '%Y-%m-%d'
    DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

    # Google OAuth Configuration
    GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
    GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
    # Only allow insecure transport in development (disable HTTPS requirement for OAuth)
    OAUTHLIB_INSECURE_TRANSPORT = '1' if DEBUG else '0'
    OAUTHLIB_RELAX_TOKEN_SCOPE = '1'

    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = not DEBUG  # True in production with HTTPS, False in development
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
