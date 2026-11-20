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

from .config import PERMISSIONS
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
    order: int = DEFAULT_ORDER


DEFAULT_NAV_ITEMS = (
    NavItem(
        "notes",
        "console.index",
        "console.my_notes",
        "notes",
        order=10,
        count="total",
    ),
    NavItem(
        "attachments",
        "attachments.index",
        "console.attachments",
        "image",
        order=20,
        count="attachments",
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


def console_nav(user=None) -> list[dict[str, object]]:
    """Sidebar sections for ``user``: permission-filtered, ordered, with URLs."""
    granted = granted_permissions(user)
    endpoint = request.endpoint if has_request_context() else None
    sections = [
        {"key": group, "label": t(label), "entries": []}
        for group, label in NAV_GROUPS.items()
    ]
    by_group = {section["key"]: section for section in sections}

    items = sorted(
        current_app.extensions.get(NAV_REGISTRY, ()),
        key=lambda item: item.order,
    )
    for item in items:
        if item.permission is not None and item.permission not in granted:
            continue
        by_group[item.group]["entries"].append(
            {
                "key": item.key,
                "label": t(item.label),
                "icon": item.icon,
                "url": url_for(item.endpoint),
                "count": item.count,
                "active": endpoint == item.endpoint,
            }
        )

    return [section for section in sections if section["entries"]]
