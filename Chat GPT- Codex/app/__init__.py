from pathlib import Path

from flask import Flask, render_template

from config import Config


def create_app(config_class=Config):
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(config_class)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    from app.db import close_db, init_db
    from app.security import csrf_token, validate_csrf
    from app.auth.routes import auth_bp
    from app.employees.routes import employees_api_bp, employees_bp
    from app.uploads.routes import uploads_bp

    app.teardown_appcontext(close_db)
    init_db(app)

    @app.before_request
    def protect_form_posts():
        validate_csrf()

    @app.context_processor
    def inject_csrf_token():
        return {"csrf_token": csrf_token}

    app.register_blueprint(auth_bp)
    app.register_blueprint(employees_bp)
    app.register_blueprint(employees_api_bp)
    app.register_blueprint(uploads_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def file_too_large(error):
        return render_template("errors/413.html"), 413

    return app
