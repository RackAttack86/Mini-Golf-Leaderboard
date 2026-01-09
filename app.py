# Standard library
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Third-party
from dotenv import load_dotenv
from flask import Flask, render_template, flash, request
from flask_dance.contrib.google import make_google_blueprint
from flask_login import current_user
from flask_session import Session
# from flask_talisman import Talisman  # Disabled for Fly.io - not needed

# Local
from config import Config
from extensions import limiter, csrf, login_manager
from routes import main_routes, player_routes, course_routes, round_routes, stats_routes, auth_routes
from services.auth_service import AuthService

# Load environment variables from .env file
load_dotenv()


def create_app():
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Trust proxy headers from Fly.io (fixes HTTPS detection for OAuth)
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Initialize database
    from models.database import init_database
    init_database(app.config['DATABASE_PATH'])

    # Set max upload size
    app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH

    # Ensure session directory exists
    session_dir = app.config.get('SESSION_FILE_DIR')
    if session_dir and not os.path.exists(session_dir):
        os.makedirs(session_dir, exist_ok=True)

    # Initialize server-side sessions
    Session(app)

    # Initialize rate limiter
    limiter.init_app(app)

    # Initialize CSRF protection
    csrf.init_app(app)

    # Note: Talisman disabled for Fly.io deployment
    # Fly.io handles HTTPS at the load balancer level (force_https=true in fly.toml)
    # We keep CSRF protection and rate limiting for security
    # If you need Talisman for local production, uncomment below:
    # if not app.debug:
    #     Talisman(app, force_https=False, content_security_policy=app.config['CONTENT_SECURITY_POLICY'])

    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(player_id):
        """Load user by player ID"""
        return AuthService.load_user(player_id)

    # Initialize Google OAuth
    google_bp = make_google_blueprint(
        client_id=app.config['GOOGLE_OAUTH_CLIENT_ID'],
        client_secret=app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
        scope=['profile', 'email'],
        redirect_to='auth.google_callback'
    )
    app.register_blueprint(google_bp, url_prefix='/login')

    # OAuth error handler
    from flask_dance.consumer import oauth_authorized, oauth_error
    from flask import flash, redirect, url_for, request
    from utils.error_tracker import error_tracker
    import traceback as tb

    @oauth_error.connect_via(google_bp)
    def google_error(blueprint, message, response):
        app.logger.error(f"OAuth error from {blueprint.name}: {message}")
        app.logger.error(f"OAuth error response: {response}")
        error_tracker.log_error('flask_dance_oauth_error', message, None, {
            'blueprint': blueprint.name,
            'response': str(response)
        })
        flash(f"OAuth error: {message}", "danger")
        return redirect(url_for('auth.login'))

    @oauth_authorized.connect_via(google_bp)
    def google_logged_in(blueprint, token):
        """Called when OAuth flow completes successfully"""
        try:
            app.logger.info(f"OAuth authorized signal received. Token: {bool(token)}")
            error_tracker.log_error('oauth_signal_fired', f"Token received: {bool(token)}", None, {
                'has_token': bool(token),
                'token_type': str(type(token)) if token else None
            })

            if not token:
                app.logger.error("No token received from Google")
                error_tracker.log_error('flask_dance_no_token', 'No token received', None, {})
                flash("Failed to receive authentication token from Google.", "danger")
                return False

            # Store token in session manually
            from flask import session
            session['google_oauth_token'] = token

            # Return False to prevent Flask-Dance from storing token again
            return False
        except Exception as e:
            app.logger.error(f"Error in oauth_authorized handler: {str(e)}")
            app.logger.error(tb.format_exc())
            error_tracker.log_error('flask_dance_handler_exception', str(e), e, {})
            flash(f"Authentication error: {str(e)}", "danger")
            return False

    # Track OAuth-related requests
    @app.before_request
    def track_oauth_requests():
        """Track OAuth callback requests for debugging"""
        if '/login/google' in request.path or '/auth/google' in request.path:
            error_tracker.log_error('oauth_request_received', f"{request.method} {request.path}", None, {
                'url': request.url,
                'path': request.path,
                'method': request.method,
                'args': dict(request.args)
            })

    # Global exception handler
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Catch all exceptions"""
        app.logger.error(f"Unhandled exception: {str(e)}")
        app.logger.error(tb.format_exc())
        error_tracker.log_error('unhandled_exception', str(e), e, {
            'request_url': request.url if request else None,
            'request_method': request.method if request else None,
            'request_path': request.path if request else None,
            'exception_type': type(e).__name__
        })

        # If it's an HTTP exception, pass it through
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return e

        # For all other exceptions, show error and redirect
        flash(f'An error occurred: {str(e)}', 'danger')
        return redirect(url_for('auth.login')), 500

    # Global error handler for 500 errors
    @app.errorhandler(500)
    def handle_500_error(e):
        """Catch all 500 errors"""
        app.logger.error(f"500 Internal Server Error: {str(e)}")
        app.logger.error(tb.format_exc())
        error_tracker.log_error('500_internal_server_error', str(e), e, {
            'request_url': request.url if request else None,
            'request_method': request.method if request else None,
            'request_path': request.path if request else None
        })
        # Show error message to user
        flash(f'An internal server error occurred: {str(e)}', 'danger')
        return redirect(url_for('auth.login'))

    # Register blueprints
    app.register_blueprint(main_routes.bp)
    app.register_blueprint(player_routes.bp, url_prefix='/players')
    app.register_blueprint(course_routes.bp, url_prefix='/courses')
    app.register_blueprint(round_routes.bp, url_prefix='/rounds')
    app.register_blueprint(stats_routes.bp, url_prefix='/stats')
    app.register_blueprint(auth_routes.auth_bp)

    # Custom Jinja2 filter to format course names with bold "(HARD)"
    @app.template_filter('format_course_name')
    def format_course_name(name):
        """Make '(HARD)' bold in course names"""
        if '(HARD)' in name:
            return name.replace('(HARD)', '<strong>(HARD)</strong>')
        return name

    # Context processor for global template variables
    @app.context_processor
    def inject_globals():
        return {
            'app_name': 'Mini Golf Leaderboard',
            'current_year': datetime.now().year,
            'is_admin': current_user.is_authenticated and current_user.is_admin,
            'is_logged_in': current_user.is_authenticated
        }

    # Setup logging
    setup_logging(app)

    # Register error handlers
    register_error_handlers(app)

    return app


def setup_logging(app):
    """Configure application logging"""
    if not app.debug and not app.testing:
        # Ensure logs directory exists
        if not os.path.exists('logs'):
            os.mkdir('logs')

        # File handler for general logs
        file_handler = RotatingFileHandler(
            'logs/minigolf.log',
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        # File handler for errors
        error_handler = RotatingFileHandler(
            'logs/errors.log',
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        error_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s [%(pathname)s:%(lineno)d]: %(message)s'
        ))
        error_handler.setLevel(logging.ERROR)
        app.logger.addHandler(error_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Mini Golf Leaderboard startup')
    else:
        # In debug/test mode, just use console logging
        app.logger.setLevel(logging.DEBUG)


def register_error_handlers(app):
    """Register global error handlers"""
    from flask_wtf.csrf import CSRFError

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        """Handle CSRF validation errors"""
        app.logger.warning(f'CSRF validation failed: {e.description}')
        flash('Security validation failed. Please try again.', 'danger')
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors"""
        app.logger.warning(f'404 error: {request.url} - User: {current_user.id if current_user.is_authenticated else "anonymous"}')
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server errors"""
        app.logger.error(f'500 error: {error}', exc_info=True)
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 Forbidden errors"""
        app.logger.warning(f'403 error: User {current_user.id if current_user.is_authenticated else "anonymous"} tried to access {request.url}')
        return render_template('errors/403.html'), 403

    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle uncaught exceptions"""
        app.logger.error(f'Unhandled exception: {error}', exc_info=True)
        return render_template('errors/500.html'), 500


# Create app instance for production servers (Gunicorn, etc.)
app = create_app()

if __name__ == '__main__':
    # Development server
    app.run(debug=True, port=5001)
