"""JSON API for private notes and public read-only shares."""

from flask import Blueprint, jsonify, url_for

from ..models import iso_utc
from ..services import (
    api_login_required,
    get_owned_note,
    get_public_note,
    is_valid_note_id,
    read_json_object,
    save_owned_note,
    too_large,
)

bp = Blueprint("notes_api", __name__)


@bp.get("/api/console/notes/<note_id>")
@api_login_required
def api_get_owned_note(note_id: str):
    if not is_valid_note_id(note_id):
        return jsonify(error="Invalid note id"), 400

    note = get_owned_note(note_id)
    return jsonify(
        id=note.id,
        content=note.content,
        is_public=note.is_public,
        created_at=iso_utc(note.created_at),
        updated_at=iso_utc(note.updated_at),
        share_url=url_for("public.share_note", note_id=note.id),
    )


@bp.put("/api/console/notes/<note_id>")
@api_login_required
def api_save_owned_note(note_id: str):
    if not is_valid_note_id(note_id):
        return jsonify(error="Invalid note id"), 400

    note = get_owned_note(note_id)

    data = read_json_object()
    if data is None or not isinstance(data.get("content"), str):
        return jsonify(error='Expected JSON body with a "content" string'), 400

    content = data["content"]
    if too_large(content):
        return jsonify(error="Note content is too large"), 413

    note = save_owned_note(note, content)
    return jsonify(
        id=note.id,
        is_public=note.is_public,
        updated_at=iso_utc(note.updated_at),
        length=len(note.content),
    )


@bp.get("/api/share/<note_id>")
def api_get_public_note(note_id: str):
    if not is_valid_note_id(note_id):
        return jsonify(error="Invalid note id"), 400

    note = get_public_note(note_id)
    return jsonify(
        id=note.id,
        content=note.content,
        created_at=iso_utc(note.created_at),
        updated_at=iso_utc(note.updated_at),
    )
