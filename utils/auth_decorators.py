from functools import wraps
from flask import redirect, url_for, flash, abort
from flask_login import current_user


def login_required(f):
    """
    Decorator to require user to be logged in

    Usage:
        @login_required
        def protected_route():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator to require user to be admin

    Usage:
        @admin_required
        def admin_only_route():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))

        if not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            abort(403)

        return f(*args, **kwargs)
    return decorated_function


def player_or_admin_required(f):
    """
    Decorator to require user to be the player themselves or an admin

    Usage:
        @player_or_admin_required
        def edit_profile(player_id):
            # player_id must be a parameter in the route
            ...

    Note: The decorated function must have a 'player_id' parameter
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))

        # Get player_id from kwargs
        player_id = kwargs.get('player_id')

        if not player_id:
            flash('Invalid request.', 'danger')
            abort(400)

        # Check if user is admin or the player themselves
        if not current_user.is_admin and current_user.id != player_id:
            flash('You do not have permission to access this page.', 'danger')
            abort(403)

        return f(*args, **kwargs)
    return decorated_function
