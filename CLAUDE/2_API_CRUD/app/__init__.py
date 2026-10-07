from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    # Registrar el Blueprint con las rutas
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    # Crear tablas automáticamente antes de la primera petición
    with app.app_context():
        db.create_all()

    return app