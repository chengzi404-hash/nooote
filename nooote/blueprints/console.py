"""User console: note management and settings."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import select

from ..config import DEFAULT_THEME, DISPLAY_NAME_MAX_LENGTH, THEMES
from ..extensions import db
from ..models import Note, utcnow
from ..services import (
    console_stats,
    create_owned_note,
    current_user,
    get_owned_note,
)

bp = Blueprint("console", __name__)


@bp.before_request
def require_login():
    if current_user() is None:
        if request.method == "GET":
            return redirect(url_for("auth.login", next=request.path))
        return redirect(url_for("auth.login"))


@bp.get("/console")
def index():
    user = current_user()
    notes = (
        db.session.execute(
            select(Note)
            .where(Note.owner_id == user.id)
            .order_by(Note.updated_at.desc())
        )
        .scalars()
        .all()
    )
    return render_template(
        "console.html",
        notes=notes,
        stats=console_stats(user.id),
        active_nav="notes",
    )


@bp.post("/console/notes")
def create_note():
    user = current_user()
    note = create_owned_note(user.id, is_public=user.default_public)
    return redirect(url_for("console.edit_note", note_id=note.id))


@bp.get("/console/notes/<note_id>")
def edit_note(note_id: str):
    note = get_owned_note(note_id)
    return render_template("note.html", note=note)


@bp.post("/console/notes/<note_id>/publish")
def publish_note(note_id: str):
    note = get_owned_note(note_id)
    if not note.is_public:
        note.is_public = True
        note.updated_at = utcnow()
        db.session.commit()
    return redirect(url_for("console.edit_note", note_id=note.id))


@bp.post("/console/notes/<note_id>/unpublish")
def unpublish_note(note_id: str):
    note = get_owned_note(note_id)
    if note.is_public:
        note.is_public = False
        note.updated_at = utcnow()
        db.session.commit()
    return redirect(url_for("console.edit_note", note_id=note.id))


@bp.post("/console/notes/<note_id>/delete")
def delete_note(note_id: str):
    note = get_owned_note(note_id)
    db.session.delete(note)
    db.session.commit()
    return redirect(url_for("console.index"))


@bp.get("/console/settings")
def settings():
    user = current_user()
    return render_template(
        "settings.html",
        stats=console_stats(user.id),
        active_nav="settings",
    )


@bp.post("/console/settings")
def update_settings():
    user = current_user()
    display_name = (request.form.get("display_name") or "").strip()
    user.display_name = display_name[:DISPLAY_NAME_MAX_LENGTH]

    theme = request.form.get("theme")
    user.theme = theme if theme in THEMES else DEFAULT_THEME
    user.default_public = request.form.get("default_public") == "on"

    db.session.commit()
    flash("设置已保存", "ok")
    return redirect(url_for("console.settings"))
