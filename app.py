from flask import Flask
from datetime import datetime
from config import Config
from models.data_store import init_data_store

# Import route blueprints
from routes import main_routes, player_routes, course_routes, round_routes, stats_routes


def create_app():
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize data store
    init_data_store(app.config['DATA_DIR'])

    # Register blueprints
    app.register_blueprint(main_routes.bp)
    app.register_blueprint(player_routes.bp, url_prefix='/players')
    app.register_blueprint(course_routes.bp, url_prefix='/courses')
    app.register_blueprint(round_routes.bp, url_prefix='/rounds')
    app.register_blueprint(stats_routes.bp, url_prefix='/stats')

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
