"""Site management: site-wide stats and permission-group configuration."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import select

from ..config import ROLES, ROLE_PERMISSIONS
from ..extensions import db
from ..features import (
    feature_groups_view,
    get_feature,
    set_feature_enabled,
)
from ..i18n import t
from ..models import User
from ..permissions import permission_require
from ..services import current_user, console_stats, site_stats

bp = Blueprint("admin", __name__)


@bp.get("/manage")
@permission_require(["manage.view"])
def manage():
    users = (
        db.session.execute(select(User).order_by(User.created_at.asc()))
        .scalars()
        .all()
    )
    return render_template(
        "manage.html",
        users=users,
        roles=ROLES,
        role_permissions={
            role: sorted(ROLE_PERMISSIONS[role]) for role in ROLES
        },
        stats=console_stats(current_user().id),
        site=site_stats(),
        feature_groups=feature_groups_view(),
    )


@bp.post("/manage/users/<user_id>/role")
@permission_require(["manage.users.write"])
def update_role(user_id: str):
    target = db.session.get(User, user_id)
    if target is None:
        abort(404)

    role = request.form.get("role")
    if role not in ROLES:
        abort(400)

    if target.id == current_user().id:
        flash(t("manage.error_self_role"), "error")
        return redirect(url_for("admin.manage"))

    target.role = role
    db.session.commit()
    flash(t("manage.role_updated", username=target.username), "ok")
    return redirect(url_for("admin.manage"))


@bp.post("/manage/features/<feature_key>")
@permission_require(["manage.features.write"])
def toggle_feature(feature_key: str):
    feature = get_feature(feature_key)
    if feature is None:
        abort(404)

    enabled = request.form.get("enabled") == "1"
    set_feature_enabled(feature.key, enabled)
    flash(
        t(
            "manage.feature_updated",
            name=t(feature.label),
            state=t("manage.feature_on" if enabled else "manage.feature_off"),
        ),
        "ok",
    )
    return redirect(url_for("admin.manage"))
