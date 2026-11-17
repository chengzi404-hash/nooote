"""JSON API for private notes and public read-only shares."""

from flask import Blueprint, jsonify, url_for

from ..i18n import t
from ..models import iso_utc
from ..permissions import permission_require
from ..services import (
    get_owned_note,
    get_public_note,
    is_valid_note_id,
    read_json_object,
    save_owned_note,
    too_large,
)

bp = Blueprint("notes_api", __name__)


@bp.get("/api/console/notes/<note_id>")
@permission_require(["note.read"])
def api_get_owned_note(note_id: str):
    if not is_valid_note_id(note_id):
        return jsonify(error=t("error.invalid_note_id")), 400

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
@permission_require(["note.write"])
def api_save_owned_note(note_id: str):
    if not is_valid_note_id(note_id):
        return jsonify(error=t("error.invalid_note_id")), 400

    note = get_owned_note(note_id)

    data = read_json_object()
    if data is None or not isinstance(data.get("content"), str):
        return jsonify(error=t("error.content_required")), 400

    content = data["content"]
    if too_large(content):
        return jsonify(error=t("error.content_too_large")), 413

    note = save_owned_note(note, content)
    return jsonify(
        id=note.id,
        is_public=note.is_public,
        updated_at=iso_utc(note.updated_at),
        length=len(note.content),
    )


@bp.get("/api/share/<note_id>")
@permission_require(["public.view"])
def api_get_public_note(note_id: str):
    if not is_valid_note_id(note_id):
        return jsonify(error=t("error.invalid_note_id")), 400

    note = get_public_note(note_id)
    return jsonify(
        id=note.id,
        content=note.content,
        created_at=iso_utc(note.created_at),
        updated_at=iso_utc(note.updated_at),
    )
