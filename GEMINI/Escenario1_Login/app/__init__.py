from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'main.login'
login_manager.login_message_category = 'info'
login_manager.login_message = 'Por favor, inicia sesión para acceder a esta página.'

def create_app(config_class=Config):
    """
    Application factory format. Ready for production.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    # Registro de blueprints
    from app.routes import main
    app.register_blueprint(main)

    return app
