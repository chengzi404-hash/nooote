"""Registration, login, and logout."""

import secrets

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from ..config import (
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
    USERNAME_RE,
    USER_ID_BYTES,
)
from ..extensions import db
from ..i18n import t
from ..models import User
from ..permissions import initial_role, permission_require
from ..services import (
    current_user,
    login_user,
    logout_user,
    safe_redirect_target,
)

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
@permission_require(["auth.access"])
def login():
    if current_user() is not None:
        return redirect(url_for("console.index"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        user = db.session.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

        if (
            user is None
            or not user.password_hash
            or not check_password_hash(user.password_hash, password)
        ):
            flash(t("auth.error_credentials"), "error")
            return render_template("login.html", username=username), 200

        login_user(user)
        return redirect(
            safe_redirect_target(request.args.get("next")) or url_for("console.index")
        )

    return render_template("login.html", username="")


@bp.route("/register", methods=["GET", "POST"])
@permission_require(["auth.access"])
def register():
    if current_user() is not None:
        return redirect(url_for("console.index"))

    username = ""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""

        error = None
        if not USERNAME_RE.fullmatch(username):
            error = t(
                "auth.error_username_rule",
                min_length=USERNAME_MIN_LENGTH,
                max_length=USERNAME_MAX_LENGTH,
            )
        elif len(password) < PASSWORD_MIN_LENGTH:
            error = t("auth.error_password_min", min_length=PASSWORD_MIN_LENGTH)
        elif len(password) > PASSWORD_MAX_LENGTH:
            error = t("auth.error_password_max", max_length=PASSWORD_MAX_LENGTH)
        elif password != confirm:
            error = t("auth.error_password_mismatch")

        if error is None:
            user = User(
                id=secrets.token_urlsafe(USER_ID_BYTES),
                username=username,
                password_hash=generate_password_hash(password),
                role=initial_role(username),
            )
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                error = t("auth.error_username_taken")
            else:
                login_user(user)
                return redirect(url_for("console.index"))

        flash(error, "error")
        return render_template("register.html", username=username), 200

    return render_template("register.html", username=username)


@bp.post("/logout")
@permission_require(["auth.logout"])
def logout():
    logout_user()
    return redirect(url_for("public.index"))
