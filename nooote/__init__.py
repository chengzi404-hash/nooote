import os
import secrets
from pathlib import Path

from flask import Flask, session
from sqlalchemy import inspect, text

from .config import (
    Config,
    DEFAULT_DATABASE_URI,
    SECRET_KEY_BYTES,
    SECRET_KEY_FILE,
    UPLOAD_FOLDER_NAME,
    USERNAME_MAX_LENGTH,
    USER_ID_MAX_LENGTH,
)
from .extensions import db
from .models import User, iso_utc


def _load_or_create_secret(instance_path: str) -> str:
    path = Path(instance_path) / SECRET_KEY_FILE
    if path.exists():
        value = path.read_text(encoding="utf-8").strip()
        if value:
            return value

    value = secrets.token_hex(SECRET_KEY_BYTES)
    path.write_text(value, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return value


def _ensure_note_columns() -> None:
    inspector = inspect(db.engine)
    if "notes" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("notes")}
    statements = []
    if "owner_id" not in columns:
        statements.append(
            "ALTER TABLE notes ADD COLUMN owner_id "
            f"VARCHAR({USER_ID_MAX_LENGTH}) NOT NULL DEFAULT ''"
        )
    if "is_public" not in columns:
        statements.append(
            "ALTER TABLE notes ADD COLUMN is_public BOOLEAN NOT NULL DEFAULT 1"
        )

    for statement in statements:
        db.session.execute(text(statement))
    if statements:
        db.session.commit()


def _ensure_user_columns() -> None:
    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    statements = []
    if "username" not in columns:
        statements.append(
            f"ALTER TABLE users ADD COLUMN username VARCHAR({USERNAME_MAX_LENGTH})"
        )
    if "password_hash" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"
        )

    for statement in statements:
        db.session.execute(text(statement))
    if statements:
        db.session.commit()

    db.session.execute(
        text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)")
    )
    db.session.commit()


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_object(Config)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URI),
        UPLOAD_FOLDER=os.path.join(app.instance_path, UPLOAD_FOLDER_NAME),
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    if not app.config.get("SECRET_KEY"):
        if app.config.get("TESTING"):
            app.config["SECRET_KEY"] = secrets.token_hex(SECRET_KEY_BYTES)
        else:
            app.config["SECRET_KEY"] = _load_or_create_secret(app.instance_path)

    db.init_app(app)

    from .blueprints import register_blueprints

    register_blueprints(app)
    app.add_template_filter(iso_utc)

    @app.context_processor
    def inject_current_user():
        user_id = session.get("user_id")
        user = db.session.get(User, user_id) if user_id else None
        return {
            "current_user": user,
            "theme": user.theme if user else "auto",
        }

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
        _ensure_note_columns()
        _ensure_user_columns()

    return app
