import os
import secrets
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session
from sqlalchemy import inspect, text

from .config import (
    ADMIN_USERNAMES_ENV,
    Config,
    DEFAULT_DATABASE_URI,
    DEFAULT_LOCALE,
    DEFAULT_ROLE,
    LOCALES,
    LOCALE_MAX_LENGTH,
    PLUGIN_REGISTRY_FILE,
    PLUGINS_FOLDER_NAME,
    ROLE_MAX_LENGTH,
    SECRET_KEY_BYTES,
    SECRET_KEY_FILE,
    UPLOAD_FOLDER_NAME,
    USERNAME_MAX_LENGTH,
    USER_ID_MAX_LENGTH,
)
from .extensions import db
from .features import (
    enforce_features,
    feature_states,
    register_default_features,
    validate_feature_wiring,
)
from .i18n import current_locale, html_lang, js_messages, t
from .models import User, iso_utc
from .navigation import console_nav_view, register_default_nav
from .permissions import enforce_permissions, granted_permissions
from .plugins import install_plugins
from .vendor import sync_app as sync_vendor_assets


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
    if "locale" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN locale "
            f"VARCHAR({LOCALE_MAX_LENGTH}) NOT NULL DEFAULT '{DEFAULT_LOCALE}'"
        )
    if "role" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN role "
            f"VARCHAR({ROLE_MAX_LENGTH}) NOT NULL DEFAULT '{DEFAULT_ROLE}'"
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
        PLUGINS_FOLDER=os.path.join(
            os.path.dirname(app.root_path), PLUGINS_FOLDER_NAME
        ),
        PLUGIN_REGISTRY_PATH=os.path.join(
            app.instance_path, PLUGIN_REGISTRY_FILE
        ),
        ADMIN_USERNAMES=frozenset(
            name.strip()
            for name in os.environ.get(ADMIN_USERNAMES_ENV, "").split(",")
            if name.strip()
        ),
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    if not app.config.get("SECRET_KEY"):
        if app.config.get("TESTING"):
            app.config["SECRET_KEY"] = secrets.token_hex(SECRET_KEY_BYTES)
        else:
            app.config["SECRET_KEY"] = _load_or_create_secret(app.instance_path)

    if not app.config.get("TESTING"):
        sync_vendor_assets(app)

    db.init_app(app)

    from .blueprints import register_blueprints

    register_blueprints(app)
    register_default_features(app)
    register_default_nav(app)
    install_plugins(app)
    validate_feature_wiring(app)
    app.before_request(enforce_permissions)
    app.before_request(enforce_features)
    app.add_template_filter(iso_utc)

    @app.context_processor
    def inject_current_user():
        user_id = session.get("user_id")
        user = db.session.get(User, user_id) if user_id else None
        locale = current_locale()
        nav = console_nav_view(user)
        return {
            "current_user": user,
            "theme": user.theme if user else "auto",
            "locale": locale,
            "locales": LOCALES,
            "html_lang": html_lang(locale),
            "t": t,
            "js_messages": js_messages(locale),
            "permissions": granted_permissions(user),
            "feature_states": feature_states(),
            "console_nav": nav["sections"],
            "console_nav_hidden": nav["hidden"],
        }

    @app.errorhandler(403)
    def forbidden(error):
        if request.path.startswith("/api/"):
            return jsonify(error=t("error.forbidden")), 403
        return render_template("error.html"), 403

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline'; font-src 'self'; "
            "script-src 'self'; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'none'",
        )
        return response

    with app.app_context():
        db.create_all()
        _ensure_note_columns()
        _ensure_user_columns()

    return app
