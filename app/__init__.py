from flask import Flask, g, session

from app.auth import get_user_for_session
from app.config import Config
from app.database import migrate_db


def create_app() -> Flask:
    """Create and configure the BurpLab Flask application."""
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(Config)
    migrate_db()

    @app.context_processor
    def inject_navigation_user():
        navigation_user = g.get("current_user")
        if navigation_user is None:
            token = session.get("auth_token")
            if isinstance(token, str):
                navigation_user = get_user_for_session(token)
        return {"nav_user": navigation_user}

    from app.routes import main
    from app.api import api
    from app.admin import admin

    app.register_blueprint(main)
    app.register_blueprint(api)
    app.register_blueprint(admin)
    return app
