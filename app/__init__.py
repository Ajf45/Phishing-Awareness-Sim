import os

from flask import Flask
from flask_login import LoginManager

from .models import AdminUser, db
from .services.logger import setup_logging


def create_app(config_object="config.Config"):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "admin.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return AdminUser.query.get(int(user_id))

    setup_logging(app)

    from .routes import admin, api, tracking
    app.register_blueprint(tracking.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(api.bp)

    with app.app_context():
        db.create_all()
        _bootstrap_admin(app)

    return app


def _bootstrap_admin(app):
    """Create the default admin user on first run if none exists."""
    if AdminUser.query.count() == 0:
        admin = AdminUser(username=app.config["ADMIN_USERNAME"], role="security_analyst")
        admin.set_password(app.config["ADMIN_PASSWORD"])
        db.session.add(admin)
        db.session.commit()