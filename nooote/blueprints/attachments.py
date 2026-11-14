"""Image hosting and attachment management."""

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from sqlalchemy import select

from ..config import ATTACHMENT_CACHE_SECONDS, ATTACHMENT_ID_RE
from ..extensions import db
from ..models import Attachment
from ..services import (
    UploadError,
    api_login_required,
    attachment_markdown,
    attachment_path,
    console_stats,
    current_user,
    get_owned_attachment,
    is_inline_image,
    login_required,
    save_upload,
)

bp = Blueprint("attachments", __name__)


@bp.get("/console/attachments")
@login_required
def index():
    user = current_user()
    items = (
        db.session.execute(
            select(Attachment)
            .where(Attachment.owner_id == user.id)
            .order_by(Attachment.created_at.desc())
        )
        .scalars()
        .all()
    )
    return render_template(
        "attachments.html",
        attachments=items,
        stats=console_stats(user.id),
        active_nav="attachments",
    )


@bp.post("/console/attachments")
@login_required
def upload():
    try:
        attachment = save_upload(request.files.get("file"))
    except UploadError as error:
        flash(error.message, "error")
        return redirect(url_for("attachments.index"))

    flash(f"已上传 {attachment.filename}", "ok")
    return redirect(url_for("attachments.index"))


@bp.post("/console/attachments/<attachment_id>/delete")
@login_required
def delete_attachment(attachment_id: str):
    attachment = get_owned_attachment(attachment_id)
    path = attachment_path(attachment.id)

    db.session.delete(attachment)
    db.session.commit()
    path.unlink(missing_ok=True)

    flash("附件已删除", "ok")
    return redirect(url_for("attachments.index"))


@bp.post("/api/console/attachments")
@api_login_required
def api_upload():
    try:
        attachment = save_upload(request.files.get("file"))
    except UploadError as error:
        return jsonify(error=error.message), error.status

    return (
        jsonify(
            id=attachment.id,
            url=url_for(
                "attachments.serve_attachment", attachment_id=attachment.id
            ),
            filename=attachment.filename,
            content_type=attachment.content_type,
            size=attachment.size,
            markdown=attachment_markdown(attachment),
        ),
        201,
    )


@bp.delete("/api/console/attachments/<attachment_id>")
@api_login_required
def api_delete_attachment(attachment_id: str):
    attachment = get_owned_attachment(attachment_id)
    path = attachment_path(attachment.id)

    db.session.delete(attachment)
    db.session.commit()
    path.unlink(missing_ok=True)

    return "", 204


@bp.get("/files/<attachment_id>")
def serve_attachment(attachment_id: str):
    if not ATTACHMENT_ID_RE.fullmatch(attachment_id):
        abort(404)

    attachment = db.session.get(Attachment, attachment_id)
    if attachment is None:
        abort(404)

    path = attachment_path(attachment.id)
    if not path.is_file():
        abort(404)

    inline = is_inline_image(attachment.content_type)
    return send_file(
        path,
        mimetype=attachment.content_type if inline else "application/octet-stream",
        as_attachment=not inline,
        download_name=attachment.filename,
        conditional=True,
        max_age=ATTACHMENT_CACHE_SECONDS,
    )
