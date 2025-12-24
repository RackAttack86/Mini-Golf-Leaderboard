from flask import Flask
from datetime import datetime
from config import Config
from models.data_store import init_data_store
from flask_login import LoginManager
from flask_dance.contrib.google import make_google_blueprint
from dotenv import load_dotenv

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

    # Initialize Flask-Login
    login_manager = LoginManager()
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

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5001)
