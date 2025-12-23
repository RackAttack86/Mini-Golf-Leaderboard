import os
from pathlib import Path

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
