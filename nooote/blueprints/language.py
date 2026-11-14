"""Interface language switching."""

from flask import Blueprint, abort, redirect, request, url_for

from ..extensions import db
from ..i18n import normalize_locale, set_locale_cookie
from ..services import current_user, safe_redirect_target

bp = Blueprint("language", __name__)


@bp.post("/language")
def switch():
    locale = normalize_locale(request.form.get("locale"))
    if locale is None:
        abort(400)

    user = current_user()
    if user is not None:
        user.locale = locale
        db.session.commit()

    target = safe_redirect_target(request.form.get("next"))
    response = redirect(target or url_for("public.index"))
    return set_locale_cookie(response, locale)
