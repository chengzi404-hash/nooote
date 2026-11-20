"""Feature flags for core features and plugins.

Every flag is declared once through :func:`register_feature`; the admin
``/manage`` page persists overrides in the ``feature_flags`` table. Routes and
sidebar entries declare the flags they need, so toggling a flag takes effect
immediately without a restart.

Core flags live in :data:`DEFAULT_FEATURES`. Plugins declare a ``features``
tuple and get a master flag (``plugin.<name>``) plus one namespaced flag per
entry (``plugin.<name>.<key>``); see :func:`plugin_feature_key`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from flask import (
    Flask,
    current_app,
    g,
    has_app_context,
    jsonify,
    render_template,
    request,
)
from sqlalchemy import select

from .config import FEATURE_KEY_MAX_LENGTH
from .extensions import db
from .i18n import t
from .models import FeatureFlag, utcnow

FEATURE_REGISTRY = "features"
FEATURE_GROUPS = "feature_groups"
PLUGIN_BLUEPRINT_FEATURES = "plugin_blueprint_features"
CORE_GROUP = "core"
FEATURE_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class FeatureError(ValueError):
    """Raised for invalid feature definitions."""


@dataclass(frozen=True)
class Feature:
    """One switchable product capability.

    ``label`` and ``description`` go through the i18n catalog, so core flags
    use message keys while plugin flags can pass plain text.
    """

    key: str
    label: str
    description: str = ""
    default: bool = True
    group: str = CORE_GROUP


DEFAULT_FEATURES = (
    Feature(
        "notes",
        "features.notes.label",
        "features.notes.description",
    ),
    Feature(
        "attachments",
        "features.attachments.label",
        "features.attachments.description",
    ),
    Feature(
        "public_shares",
        "features.public_shares.label",
        "features.public_shares.description",
    ),
    Feature(
        "registration",
        "features.registration.label",
        "features.registration.description",
    ),
)


def plugin_feature_key(plugin_name: str, key: str | None = None) -> str:
    """Return the namespaced flag key for a plugin or one of its sub-features."""
    base = f"plugin.{plugin_name}"
    return base if key is None else f"{base}.{key}"


def register_feature_group(app: Flask, key: str, label: str) -> None:
    """Register a display group (``core`` or a plugin name)."""
    if not key or not FEATURE_KEY_RE.fullmatch(key):
        raise FeatureError(f"invalid feature group: {key!r}")
    app.extensions.setdefault(FEATURE_GROUPS, {}).setdefault(key, label)


def register_feature(app: Flask, feature: Feature) -> Feature:
    """Add ``feature`` to the application registry, validating it first."""
    if not isinstance(feature, Feature):
        raise FeatureError("feature must be a Feature instance")
    if (
        not feature.key
        or len(feature.key) > FEATURE_KEY_MAX_LENGTH
        or not FEATURE_KEY_RE.fullmatch(feature.key)
    ):
        raise FeatureError(f"invalid feature key: {feature.key!r}")

    groups = app.extensions.get(FEATURE_GROUPS, {})
    if feature.group not in groups:
        raise FeatureError(f"unknown feature group: {feature.group!r}")

    registry = app.extensions.setdefault(FEATURE_REGISTRY, {})
    if feature.key in registry:
        raise FeatureError(f"duplicate feature key: {feature.key}")
    registry[feature.key] = feature
    return feature


def register_default_features(app: Flask) -> None:
    """Register the feature flags shipped with the application."""
    register_feature_group(app, CORE_GROUP, "manage.features_core")
    for feature in DEFAULT_FEATURES:
        register_feature(app, feature)


def feature_require(keys):
    """Declare the feature flags a view needs, e.g. ``feature_require("notes")``."""
    required = frozenset((keys,) if isinstance(keys, str) else keys)

    def decorator(view):
        existing = getattr(view, "required_features", frozenset())
        view.required_features = frozenset(existing) | required
        return view

    return decorator


def get_feature(key: str) -> Feature | None:
    return current_app.extensions.get(FEATURE_REGISTRY, {}).get(key)


def feature_states() -> dict[str, bool]:
    """Effective flag values: registry defaults plus persisted overrides."""
    registry = current_app.extensions.get(FEATURE_REGISTRY, {})
    states = {key: feature.default for key, feature in registry.items()}

    if has_app_context():
        cached = getattr(g, "_feature_states", None)
        if cached is not None:
            return cached

        for row in db.session.execute(select(FeatureFlag)).scalars():
            if row.key in states:
                states[row.key] = row.enabled
        g._feature_states = states

    return states


def feature_enabled(key: str) -> bool:
    """Whether ``key`` is enabled; unknown flags stay enabled."""
    return feature_states().get(key, True)


def set_feature_enabled(key: str, enabled: bool) -> None:
    """Persist an override and invalidate the per-request cache."""
    row = db.session.get(FeatureFlag, key)
    if row is None:
        db.session.add(FeatureFlag(key=key, enabled=enabled))
    else:
        row.enabled = enabled
        row.updated_at = utcnow()
    db.session.commit()

    if has_app_context():
        g.pop("_feature_states", None)


def feature_groups_view() -> list[dict[str, object]]:
    """Groups and flags for the admin UI, with translated labels."""
    registry = current_app.extensions.get(FEATURE_REGISTRY, {})
    groups = current_app.extensions.get(FEATURE_GROUPS, {})
    states = feature_states()

    result = []
    for group_key, group_label in groups.items():
        features = [
            {
                "key": feature.key,
                "label": t(feature.label),
                "description": t(feature.description)
                if feature.description
                else "",
                "default": feature.default,
                "enabled": states.get(feature.key, feature.default),
            }
            for feature in registry.values()
            if feature.group == group_key
        ]
        if features:
            result.append(
                {
                    "key": group_key,
                    "label": t(group_label),
                    "features": features,
                }
            )
    return result


def enforce_features():
    """Reject requests for views whose feature flags are disabled."""
    endpoint = request.endpoint
    if (
        endpoint is None
        or endpoint == "static"
        or endpoint.endswith(".static")
    ):
        return None

    view = current_app.view_functions.get(endpoint)
    required = set(getattr(view, "required_features", ()))
    master = current_app.extensions.get(PLUGIN_BLUEPRINT_FEATURES, {}).get(
        request.blueprint
    )
    if master is not None:
        required.add(master)
    if not required:
        return None

    states = feature_states()
    if all(states.get(key, True) for key in required):
        return None
    return _feature_disabled()


def validate_feature_wiring(app: Flask) -> None:
    """Log views that reference flags which were never registered."""
    known = set(app.extensions.get(FEATURE_REGISTRY, {}))
    unknown = set()
    for rule in app.url_map.iter_rules():
        view = app.view_functions.get(rule.endpoint)
        for key in getattr(view, "required_features", ()):
            if key not in known:
                unknown.add((key, rule.endpoint))

    for key, endpoint in sorted(unknown):
        app.logger.warning(
            "endpoint %s requires unregistered feature %s", endpoint, key
        )


def _feature_disabled():
    if request.path.startswith("/api/"):
        return jsonify(error=t("error.feature_disabled")), 403
    return (
        render_template(
            "error.html",
            error_title=t("error.feature_disabled_title"),
            error_heading=t("error.feature_disabled_heading"),
            error_body=t("error.feature_disabled_body"),
        ),
        403,
    )
