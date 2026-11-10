import os

from flask import Flask

from .extensions import db
from .models import iso_utc


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///notes.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=1024 * 1024,
        MAX_NOTE_BYTES=256 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    from . import routes

    app.register_blueprint(routes.bp)
    app.add_template_filter(iso_utc)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline'; font-src 'self'; "
            "script-src 'self' 'wasm-unsafe-eval'; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'none'",
        )
        return response

    with app.app_context():
        db.create_all()

    return app
