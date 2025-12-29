"""
Flask extensions initialization module

This module initializes Flask extensions to avoid circular imports.
Extensions are initialized here and then imported by app.py and routes.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    headers_enabled=True
)

# Initialize CSRF protection
csrf = CSRFProtect()

# Initialize login manager
login_manager = LoginManager()
