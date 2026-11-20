"""Permission-group based authorization applied to every route.

Routes declare the permissions they need with
:func:`permission_require`; a single application-level ``before_request``
hook enforces the declarations, and any route without a declaration is
denied by default.
"""

from __future__ import annotations

from collections.abc import Iterable

from flask import (
    abort,
    current_app,
    jsonify,
    redirect,
    request,
    url_for,
)

from .config import (
    DEFAULT_ROLE,
    PERMISSIONS,
    ROLE_ADMIN,
    ROLE_GUEST,
    ROLE_PERMISSIONS,
)
from .i18n import t
from .services import current_user

PUBLIC_ENDPOINTS = frozenset({"static"})


def _is_public_endpoint(endpoint: str) -> bool:
    return endpoint in PUBLIC_ENDPOINTS or endpoint.endswith(".static")


def permission_require(permissions: Iterable[str]):
    """Declare the permissions a view needs, e.g. ``["note.read"]``."""
    required = frozenset(permissions)
    unknown = required - set(PERMISSIONS)
    if unknown:
        raise ValueError(f"unknown permission(s): {', '.join(sorted(unknown))}")

    def decorator(view):
        view.required_permissions = required
        return view

    return decorator


def granted_permissions(user=None) -> frozenset[str]:
    """Permissions available to ``user``; anonymous requests get the guest group."""
    role = getattr(user, "role", None)
    if role not in ROLE_PERMISSIONS:
        role = ROLE_GUEST if user is None else DEFAULT_ROLE
    return ROLE_PERMISSIONS[role]


def initial_role(username: str) -> str:
    """Role assigned to a freshly registered account."""
    return (
        ROLE_ADMIN
        if username in (current_app.config.get("ADMIN_USERNAMES") or ())
        else DEFAULT_ROLE
    )


def _wants_json() -> bool:
    return request.path.startswith("/api/")


def _unauthenticated():
    if _wants_json():
        return jsonify(error=t("error.auth_required")), 401
    if request.method == "GET":
        return redirect(url_for("auth.login", next=request.path))
    return redirect(url_for("auth.login"))


def _forbidden():
    if _wants_json():
        return jsonify(error=t("error.forbidden")), 403
    abort(403)


def enforce_permissions():
    """Default-deny guard: every endpoint must declare its permissions."""
    endpoint = request.endpoint
    if endpoint is None or _is_public_endpoint(endpoint):
        return None

    view = current_app.view_functions.get(endpoint)
    required = getattr(view, "required_permissions", None)
    user = current_user()

    if required is None:
        if user is None:
            return _unauthenticated()
        abort(403)

    if required <= granted_permissions(user):
        return None

    if user is None:
        return _unauthenticated()
    return _forbidden()
