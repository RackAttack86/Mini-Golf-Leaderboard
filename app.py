from flask import Flask, render_template, request
from datetime import datetime
from config import Config
from models.data_store import init_data_store
from flask_login import current_user
from flask_dance.contrib.google import make_google_blueprint
from flask_talisman import Talisman
from flask_session import Session
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import os

# Import Flask extensions from extensions module to avoid circular imports
from extensions import limiter, csrf, login_manager

# Load environment variables from .env file
load_dotenv()

# Import route blueprints
from routes import main_routes, player_routes, course_routes, round_routes, stats_routes, auth_routes
from services.auth_service import AuthService


def create_app():
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize data store
    init_data_store(app.config['DATA_DIR'])

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

    # Initialize security headers (Talisman) - only in non-debug mode
    if not app.debug:
        Talisman(
            app,
            force_https=app.config['TALISMAN_FORCE_HTTPS'],
            strict_transport_security=True,
            strict_transport_security_max_age=31536000,  # 1 year
            content_security_policy=app.config['CONTENT_SECURITY_POLICY'],
            feature_policy=app.config['FEATURE_POLICY'],
            referrer_policy='strict-origin-when-cross-origin',
            x_content_type_options=True,
            x_frame_options='SAMEORIGIN',
            x_xss_protection=True
        )

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
            'current_year': datetime.now().year
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
    from flask import flash

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


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5001)
