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
from ..models import User
from ..services import current_user, login_user, logout_user

bp = Blueprint("auth", __name__)


def _safe_next(value: str | None) -> str | None:
    if not value or not value.startswith("/") or value.startswith("//"):
        return None
    return value


@bp.route("/login", methods=["GET", "POST"])
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
            flash("用户名或密码错误", "error")
            return render_template("login.html", username=username), 200

        login_user(user)
        return redirect(_safe_next(request.args.get("next")) or url_for("console.index"))

    return render_template("login.html", username="")


@bp.route("/register", methods=["GET", "POST"])
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
            error = (
                f"用户名需为 {USERNAME_MIN_LENGTH}-{USERNAME_MAX_LENGTH} 位"
                "字母、数字、下划线、点或连字符"
            )
        elif len(password) < PASSWORD_MIN_LENGTH:
            error = f"密码至少需要 {PASSWORD_MIN_LENGTH} 位"
        elif len(password) > PASSWORD_MAX_LENGTH:
            error = f"密码不能超过 {PASSWORD_MAX_LENGTH} 位"
        elif password != confirm:
            error = "两次输入的密码不一致"

        if error is None:
            user = User(
                id=secrets.token_urlsafe(USER_ID_BYTES),
                username=username,
                password_hash=generate_password_hash(password),
            )
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                error = "用户名已被使用"
            else:
                login_user(user)
                return redirect(url_for("console.index"))

        flash(error, "error")
        return render_template("register.html", username=username), 200

    return render_template("register.html", username=username)


@bp.post("/logout")
def logout():
    logout_user()
    return redirect(url_for("public.index"))
