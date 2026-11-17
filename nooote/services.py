"""Shared domain logic for users, notes, and attachments."""

import mimetypes
import os
import secrets
from pathlib import Path
from urllib.parse import urlparse

from flask import (
    abort,
    current_app,
    request,
    session,
    url_for,
)
from sqlalchemy import func, select

from .config import (
    ATTACHMENT_ID_BYTES,
    ATTACHMENT_ID_RE,
    CONTENT_TYPE_RE,
    DEFAULT_ROLE,
    FILENAME_MAX_LENGTH,
    ID_GENERATION_ATTEMPTS,
    IMAGE_CONTENT_TYPES,
    INLINE_IMAGE_TYPES,
    NOTE_ID_BYTES,
    NOTE_ID_RE,
    ROLE_PERMISSIONS,
)
from .extensions import db
from .i18n import t
from .models import Attachment, Note, User, utcnow


class UploadError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


def is_valid_note_id(note_id: str) -> bool:
    return bool(NOTE_ID_RE.fullmatch(note_id)) and note_id not in {".", ".."}


def safe_redirect_target(value: str | None) -> str | None:
    """Return a same-site relative path, or ``None`` for anything external."""
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc:
        return None
    if not value.startswith("/") or value[1:2] in ("/", "\\"):
        return None
    return value


def current_user() -> User | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def login_user(user: User) -> None:
    session.clear()
    session["user_id"] = user.id
    session.permanent = True


def logout_user() -> None:
    session.clear()


def get_owned_note(note_id: str) -> Note:
    if not is_valid_note_id(note_id):
        abort(404)

    user = current_user()
    note = db.session.get(Note, note_id)
    if user is None or note is None or note.owner_id != user.id:
        abort(404)
    return note


def get_public_note(note_id: str) -> Note:
    if not is_valid_note_id(note_id):
        abort(404)

    note = db.session.get(Note, note_id)
    if note is None or not note.is_public:
        abort(404)
    return note


def generate_note_id() -> str:
    for _ in range(ID_GENERATION_ATTEMPTS):
        candidate = secrets.token_urlsafe(NOTE_ID_BYTES)
        if is_valid_note_id(candidate) and db.session.get(Note, candidate) is None:
            return candidate
    raise RuntimeError("Unable to generate a unique note id")


def create_owned_note(owner_id: str, is_public: bool = False) -> Note:
    note = Note(
        id=generate_note_id(),
        owner_id=owner_id,
        content="",
        is_public=is_public,
    )
    db.session.add(note)
    db.session.commit()
    return note


def save_owned_note(note: Note, content: str) -> Note:
    note.content = content
    note.updated_at = utcnow()
    db.session.commit()
    return note


def read_json_object():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def too_large(value: str) -> bool:
    return len(value.encode("utf-8")) > current_app.config["MAX_NOTE_BYTES"]


def console_stats(user_id: str) -> dict[str, int]:
    total = db.session.scalar(
        select(func.count()).select_from(Note).where(Note.owner_id == user_id)
    ) or 0
    public = db.session.scalar(
        select(func.count())
        .select_from(Note)
        .where(Note.owner_id == user_id, Note.is_public.is_(True))
    ) or 0
    attachments = db.session.scalar(
        select(func.count())
        .select_from(Attachment)
        .where(Attachment.owner_id == user_id)
    ) or 0
    return {
        "total": total,
        "public": public,
        "private": total - public,
        "attachments": attachments,
    }


def site_stats() -> dict[str, object]:
    """Site-wide aggregates shown on the management dashboard."""
    total_notes = db.session.scalar(
        select(func.count()).select_from(Note)
    ) or 0
    public_notes = db.session.scalar(
        select(func.count()).select_from(Note).where(Note.is_public.is_(True))
    ) or 0
    total_attachments = db.session.scalar(
        select(func.count()).select_from(Attachment)
    ) or 0
    attachment_bytes = db.session.scalar(
        select(func.coalesce(func.sum(Attachment.size), 0))
    ) or 0
    note_bytes = db.session.scalar(
        select(func.coalesce(func.sum(func.length(Note.content)), 0))
    ) or 0
    total_users = db.session.scalar(
        select(func.count()).select_from(User)
    ) or 0

    role_counts = {role: 0 for role in ROLE_PERMISSIONS}
    for role, count in db.session.execute(
        select(User.role, func.count()).group_by(User.role)
    ).all():
        role_counts[role if role in ROLE_PERMISSIONS else DEFAULT_ROLE] += count

    return {
        "users": total_users,
        "role_counts": role_counts,
        "notes": total_notes,
        "public_notes": public_notes,
        "private_notes": total_notes - public_notes,
        "attachments": total_attachments,
        "attachment_bytes": attachment_bytes,
        "note_bytes": note_bytes,
    }


def random_public_note_id() -> str | None:
    ids = (
        db.session.execute(select(Note.id).where(Note.is_public.is_(True)))
        .scalars()
        .all()
    )
    return secrets.choice(ids) if ids else None


def is_inline_image(content_type: str) -> bool:
    return content_type in INLINE_IMAGE_TYPES


def sanitize_filename(raw: str) -> str:
    name = os.path.basename((raw or "").replace("\\", "/")).strip()
    name = "".join(ch for ch in name if ch.isprintable())
    return name[:FILENAME_MAX_LENGTH] or "file"


def guess_content_type(filename: str, provided: str | None) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in IMAGE_CONTENT_TYPES:
        return IMAGE_CONTENT_TYPES[suffix]

    guessed, _ = mimetypes.guess_type(filename)
    if guessed:
        return guessed

    candidate = (provided or "").lower()
    if CONTENT_TYPE_RE.fullmatch(candidate):
        return candidate
    return "application/octet-stream"


def attachment_path(attachment_id: str) -> Path:
    return Path(current_app.config["UPLOAD_FOLDER"]) / attachment_id


def generate_attachment_id() -> str:
    for _ in range(ID_GENERATION_ATTEMPTS):
        candidate = secrets.token_urlsafe(ATTACHMENT_ID_BYTES)
        if (
            ATTACHMENT_ID_RE.fullmatch(candidate)
            and db.session.get(Attachment, candidate) is None
        ):
            return candidate
    raise RuntimeError("Unable to generate a unique attachment id")


def save_upload(file) -> Attachment:
    if file is None or not file.filename:
        raise UploadError(t("upload.file_required"))

    limit = current_app.config["MAX_UPLOAD_BYTES"]
    data = file.read(limit + 1)
    if len(data) > limit:
        raise UploadError(t("upload.file_too_large"), 413)
    if not data:
        raise UploadError(t("upload.file_empty"))

    user = current_user()
    if user is None:
        raise UploadError(t("upload.login_required"), 401)

    attachment = Attachment(
        id=generate_attachment_id(),
        owner_id=user.id,
        filename=sanitize_filename(file.filename),
        content_type=guess_content_type(file.filename, file.mimetype),
        size=len(data),
    )

    path = attachment_path(attachment.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.part")
    temp_path.write_bytes(data)
    os.replace(temp_path, path)

    db.session.add(attachment)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        path.unlink(missing_ok=True)
        raise
    return attachment


def attachment_markdown(attachment: Attachment) -> str:
    label = (
        attachment.filename.replace("\\", "\\\\")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )
    url = url_for("attachments.serve_attachment", attachment_id=attachment.id)
    if is_inline_image(attachment.content_type):
        return f"![{label}]({url})"
    return f"[{label}]({url})"


def get_owned_attachment(attachment_id: str) -> Attachment:
    if not ATTACHMENT_ID_RE.fullmatch(attachment_id):
        abort(404)

    user = current_user()
    attachment = db.session.get(Attachment, attachment_id)
    if user is None or attachment is None or attachment.owner_id != user.id:
        abort(404)
    return attachment
