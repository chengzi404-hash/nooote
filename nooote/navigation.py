"""Console sidebar navigation registry.

The console shell renders whatever is registered here, so a feature (or a
future plugin) can add an entry without touching ``console_base.html``.
:func:`register_default_nav` installs the built-in items from the application
factory; plugins call :func:`register_nav_item` with the application instance
after it has been created.

``NavItem.icon`` is either an ``_icons.html`` macro name (``"notes"``) or a
Font Awesome class list (``"fa-solid fa-puzzle-piece"``).
"""

from __future__ import annotations

from dataclasses import dataclass

from flask import Flask, current_app, has_request_context, request, url_for

from .config import CONSOLE_NAV_VISIBLE_ITEMS, PERMISSIONS
from .features import FEATURE_REGISTRY, feature_enabled
from .i18n import t
from .permissions import granted_permissions

NAV_REGISTRY = "console_nav"
NAV_GROUPS = {
    "workspace": "console.workspace",
    "account": "console.account",
}
DEFAULT_ORDER = 100


@dataclass(frozen=True)
class NavItem:
    """One console sidebar link.

    ``key`` identifies the item and must be unique, ``endpoint`` is a Flask
    endpoint name, ``label`` is an i18n message key, ``group`` picks the
    sidebar section, ``permission`` hides the item unless it is granted, and
    ``count`` names a key in the template ``stats`` mapping to show a badge.
    """

    key: str
    endpoint: str
    label: str
    icon: str
    group: str = "workspace"
    permission: str | None = None
    count: str | None = None
    feature: str | None = None
    order: int = DEFAULT_ORDER


DEFAULT_NAV_ITEMS = (
    NavItem(
        "notes",
        "console.index",
        "console.my_notes",
        "notes",
        order=10,
        count="total",
        feature="notes",
    ),
    NavItem(
        "attachments",
        "attachments.index",
        "console.attachments",
        "image",
        order=20,
        count="attachments",
        feature="attachments",
    ),
    NavItem(
        "manage",
        "admin.manage",
        "console.manage",
        "shield",
        group="account",
        permission="manage.view",
        order=10,
    ),
    NavItem(
        "settings",
        "console.settings",
        "console.settings",
        "settings",
        group="account",
        order=20,
    ),
    NavItem(
        "home",
        "public.index",
        "console.back_home",
        "home",
        group="account",
        order=30,
    ),
)


def register_nav_item(app: Flask, item: NavItem) -> NavItem:
    """Add ``item`` to the console sidebar, validating it first."""
    if item.group not in NAV_GROUPS:
        raise ValueError(f"unknown nav group: {item.group}")
    if item.permission is not None and item.permission not in PERMISSIONS:
        raise ValueError(f"unknown permission: {item.permission}")
    features = app.extensions.get(FEATURE_REGISTRY, {})
    if item.feature is not None and item.feature not in features:
        raise ValueError(f"unknown feature: {item.feature}")
    if item.endpoint not in app.view_functions:
        raise ValueError(f"unknown endpoint: {item.endpoint}")

    registry = app.extensions.setdefault(NAV_REGISTRY, [])
    if any(existing.key == item.key for existing in registry):
        raise ValueError(f"duplicate nav key: {item.key}")

    registry.append(item)
    return item


def register_default_nav(app: Flask) -> None:
    """Register the sidebar items shipped with the application."""
    for item in DEFAULT_NAV_ITEMS:
        register_nav_item(app, item)


def console_nav_view(user=None) -> dict[str, object]:
    """Sidebar view for ``user``: visible sections plus collapsed entries.

    Entries are ordered by :attr:`NavItem.order` and filtered by permission.
    Once more than :data:`CONSOLE_NAV_VISIBLE_ITEMS` are registered, the
    trailing ones move into ``hidden`` so the template can tuck them behind the
    "More apps" disclosure. The entry for the current page is never hidden.
    """
    granted = granted_permissions(user)
    endpoint = request.endpoint if has_request_context() else None

    entries = []
    for item in sorted(
        current_app.extensions.get(NAV_REGISTRY, ()),
        key=lambda item: item.order,
    ):
        if item.permission is not None and item.permission not in granted:
            continue
        if item.feature is not None and not feature_enabled(item.feature):
            continue
        entries.append(
            {
                "key": item.key,
                "label": t(item.label),
                "icon": item.icon,
                "group": item.group,
                "url": url_for(item.endpoint),
                "count": item.count,
                "active": endpoint == item.endpoint,
            }
        )

    visible = 0
    for entry in entries:
        entry["hidden"] = visible >= CONSOLE_NAV_VISIBLE_ITEMS and not entry["active"]
        if not entry["hidden"]:
            visible += 1

    by_group = {group: [] for group in NAV_GROUPS}
    for entry in entries:
        if not entry["hidden"]:
            by_group[entry["group"]].append(entry)

    sections = [
        {"key": group, "label": t(label), "entries": by_group[group]}
        for group, label in NAV_GROUPS.items()
        if by_group[group]
    ]
    return {
        "sections": sections,
        "hidden": [entry for entry in entries if entry["hidden"]],
    }


def console_nav(user=None) -> list[dict[str, object]]:
    """Sidebar sections for ``user``: permission-filtered, ordered, with URLs."""
    return console_nav_view(user)["sections"]
