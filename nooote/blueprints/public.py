"""Public pages: home, read-only shares, and legacy redirects."""

from flask import Blueprint, abort, redirect, render_template, request, url_for
from sqlalchemy import select

from ..config import RECENT_NOTES_LIMIT
from ..extensions import db
from ..features import feature_require
from ..models import Note
from ..permissions import permission_require
from ..services import get_public_note, is_valid_note_id, random_public_note_id

bp = Blueprint("public", __name__)


@bp.get("/")
@permission_require(["public.view"])
def index():
    recent = (
        db.session.execute(
            select(Note)
            .where(Note.is_public.is_(True))
            .order_by(Note.updated_at.desc())
            .limit(RECENT_NOTES_LIMIT)
        )
        .scalars()
        .all()
    )
    return render_template(
        "index.html",
        recent=recent,
        random_public=random_public_note_id(),
    )


@bp.get("/share/<note_id>")
@feature_require("public_shares")
@permission_require(["public.view"])
def share_note(note_id: str):
    note = get_public_note(note_id)
    return render_template("share.html", note=note)


@bp.get("/world")
@feature_require("public_shares")
@permission_require(["public.view"])
def world_lookup():
    note_id = (request.args.get("id") or "").strip()
    if not is_valid_note_id(note_id):
        return redirect(url_for("public.index"))
    return redirect(url_for("public.share_note", note_id=note_id))


@bp.get("/world/<note_id>")
@feature_require("public_shares")
@permission_require(["public.view"])
def world_note(note_id: str):
    if not is_valid_note_id(note_id):
        abort(404)
    return redirect(url_for("public.share_note", note_id=note_id))
