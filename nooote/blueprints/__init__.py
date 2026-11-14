"""Blueprint registration for the application factory."""

from flask import Flask

from . import attachments, auth, console, notes_api, public


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(public.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(console.bp)
    app.register_blueprint(notes_api.bp)
    app.register_blueprint(attachments.bp)
