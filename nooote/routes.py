import re
import secrets

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, url_for
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .extensions import db
from .models import Note, iso_utc, utcnow

bp = Blueprint("notes", __name__)

_NOTE_ID_RE = re.compile(r"^[\w.-]{1,128}$")


def is_valid_note_id(note_id: str) -> bool:
    return bool(_NOTE_ID_RE.fullmatch(note_id)) and note_id not in {".", ".."}


def get_or_create_note(note_id: str) -> Note:
    note = db.session.get(Note, note_id)
    if note is not None:
        return note

    note = Note(id=note_id, content="")
    db.session.add(note)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        note = db.session.get(Note, note_id)
        if note is None:
            raise
    return note


def save_note_content(note_id: str, content: str) -> Note:
    note = db.session.get(Note, note_id)
    if note is None:
        note = Note(id=note_id, content=content)
        db.session.add(note)
    else:
        note.content = content
        note.updated_at = utcnow()

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        note = db.session.get(Note, note_id)
        if note is None:
            raise
        note.content = content
        note.updated_at = utcnow()
        db.session.commit()
    return note


def read_json_object():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def too_large(value: str) -> bool:
    return len(value.encode("utf-8")) > current_app.config["MAX_NOTE_BYTES"]


@bp.get("/")
def index():
    recent = db.session.execute(
        select(Note).order_by(Note.updated_at.desc()).limit(12)
    ).scalars()
    return render_template(
        "index.html",
        recent=recent,
        random_id=secrets.token_urlsafe(6),
    )


@bp.get("/world")
def world_lookup():
    note_id = (request.args.get("id") or "").strip()
    if not is_valid_note_id(note_id):
        return redirect(url_for("notes.index"))
    return redirect(url_for("notes.note", note_id=note_id))


@bp.get("/world/<note_id>")
def note(note_id: str):
    if not is_valid_note_id(note_id):
        abort(404)

    note = get_or_create_note(note_id)
    return render_template("note.html", note=note)


@bp.get("/api/world/<note_id>")
def api_get_note(note_id: str):
    if not is_valid_note_id(note_id):
        return jsonify(error="Invalid note id"), 400

    note = get_or_create_note(note_id)
    return jsonify(
        id=note.id,
        content=note.content,
        created_at=iso_utc(note.created_at),
        updated_at=iso_utc(note.updated_at),
    )


@bp.put("/api/world/<note_id>")
def api_save_note(note_id: str):
    if not is_valid_note_id(note_id):
        return jsonify(error="Invalid note id"), 400

    data = read_json_object()
    if data is None or not isinstance(data.get("content"), str):
        return jsonify(error='Expected JSON body with a "content" string'), 400

    content = data["content"]
    if too_large(content):
        return jsonify(error="Note content is too large"), 413

    note = save_note_content(note_id, content)
    return jsonify(
        id=note.id,
        updated_at=iso_utc(note.updated_at),
        length=len(note.content),
    )
