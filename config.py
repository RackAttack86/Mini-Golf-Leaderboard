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

    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # No expiration (uses session lifetime instead)
    WTF_CSRF_SSL_STRICT = not DEBUG  # Require Referer header to match in production
    WTF_CSRF_CHECK_DEFAULT = True

    # Security Headers (Talisman)
    TALISMAN_FORCE_HTTPS = not DEBUG  # Only force HTTPS in production

    # Content Security Policy
    CONTENT_SECURITY_POLICY = {
        'default-src': ['\'self\''],
        'script-src': [
            '\'self\'',
            'https://cdn.jsdelivr.net',  # Bootstrap JS
        ],
        'style-src': [
            '\'self\'',
            '\'unsafe-inline\'',  # Required for Bootstrap inline styles
            'https://cdn.jsdelivr.net',  # Bootstrap CSS
        ],
        'font-src': [
            '\'self\'',
            'https://cdn.jsdelivr.net',  # Bootstrap Icons
        ],
        'img-src': [
            '\'self\'',
            'data:',  # For data URIs
            'https:',  # Allow external course images
        ],
        'connect-src': ['\'self\''],
        'object-src': ['\'none\''],
        'base-uri': ['\'self\''],
        'form-action': ['\'self\''],
        'frame-ancestors': ['\'self\''],
    }

    # Feature Policy (Permissions Policy)
    FEATURE_POLICY = {
        'geolocation': '\'none\'',
        'microphone': '\'none\'',
        'camera': '\'none\'',
        'payment': '\'none\'',
    }
