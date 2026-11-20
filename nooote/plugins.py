"""Local plugin discovery, installation and routing.

A plugin is a Python package inside the project's ``plugins/`` folder. It
must expose ``create_plugin()`` returning a :class:`Plugin`; the factory is
called once per application so every app gets a fresh blueprint.

The first time a plugin is discovered the app generates a persistent
``__id`` (written to ``instance/plugins.json``) and mounts the plugin's
blueprint under ``/plug/<__id>``. Later starts reuse the stored id, so URLs
and sidebar links stay stable across restarts and reinstalls.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import secrets
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, Flask

from .config import (
    PERMISSIONS,
    PLUGIN_ID_BYTES,
    PLUGIN_PERMISSION,
)
from .features import (
    PLUGIN_BLUEPRINT_FEATURES,
    Feature,
    plugin_feature_key,
    register_feature,
    register_feature_group,
)
from .navigation import NavItem, register_nav_item

PLUGIN_EXTENSION = "plugins"
PLUGIN_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
PLUGIN_MODULE_PREFIX = "nooote_plugins"


class PluginError(ValueError):
    """Raised when a discovered plugin does not satisfy the plugin contract."""


@dataclass(frozen=True)
class Plugin:
    """What a plugin package returns from ``create_plugin()``.

    ``blueprint`` is registered at ``/plug/<__id>``; ``endpoint`` names the
    blueprint view used as the landing page and sidebar target (usually the
    ``""`` route). ``label`` doubles as the sidebar text and is passed through
    the i18n catalog, so plain strings and message keys both work.
    """

    name: str
    label: str
    blueprint: Blueprint
    endpoint: str = "index"
    icon: str = "fa-solid fa-puzzle-piece"
    description: str = ""
    order: int = 100
    permission: str | None = PLUGIN_PERMISSION
    nav: bool = True
    features: tuple[Feature, ...] = ()


@dataclass(frozen=True)
class InstalledPlugin:
    """A plugin mounted during this app start."""

    id: str
    name: str
    label: str
    endpoint: str
    folder: Path


def install_plugins(app: Flask) -> list[InstalledPlugin]:
    """Discover, install and mount every plugin; return the loaded plugins."""
    folder = Path(app.config["PLUGINS_FOLDER"])
    registry_path = Path(app.config["PLUGIN_REGISTRY_PATH"])
    registry = _load_registry(registry_path, app)
    used_ids = {
        entry.get("id")
        for entry in registry.values()
        if isinstance(entry, dict) and _valid_id(entry.get("id"))
    }

    installed: list[InstalledPlugin] = []
    changed = False
    if folder.is_dir():
        for path in sorted(folder.iterdir()):
            if not _is_plugin_package(path):
                continue

            previous = (
                dict(registry[path.name]) if path.name in registry else None
            )
            try:
                plugin = _load_plugin(path)
                plugin_id, created = _ensure_plugin_id(
                    registry, path.name, used_ids
                )
                _mount_plugin(app, plugin, plugin_id)
            except Exception:
                app.logger.exception("skipping plugin %s", path.name)
                if previous is None:
                    registry.pop(path.name, None)
                else:
                    registry[path.name] = previous
                continue

            entry = registry[path.name]
            if not entry.get("installed_at"):
                entry["installed_at"] = _now()
                created = True
            changed = changed or created
            used_ids.add(plugin_id)
            installed.append(
                InstalledPlugin(
                    id=plugin_id,
                    name=plugin.name,
                    label=plugin.label,
                    endpoint=f"{plugin.blueprint.name}.{plugin.endpoint}",
                    folder=path,
                )
            )

    if changed:
        _save_registry(registry_path, registry)

    app.extensions[PLUGIN_EXTENSION] = installed
    return installed


def _is_plugin_package(path: Path) -> bool:
    return (
        path.is_dir()
        and path.name.isidentifier()
        and not path.name.startswith("_")
        and (path / "__init__.py").is_file()
    )


def _load_plugin(path: Path) -> Plugin:
    module = _import_plugin_module(path)
    factory = getattr(module, "create_plugin", None)
    if not callable(factory):
        raise PluginError(f"{path.name} does not expose create_plugin()")

    plugin = factory()
    if not isinstance(plugin, Plugin):
        raise PluginError(f"{path.name}.create_plugin() must return a Plugin")
    if plugin.name != path.name:
        raise PluginError(
            f"plugin name {plugin.name!r} does not match folder {path.name!r}"
        )
    if not plugin.name.isidentifier():
        raise PluginError(f"invalid plugin name: {plugin.name!r}")
    if not plugin.label:
        raise PluginError(f"{path.name} is missing a label")
    if not isinstance(plugin.blueprint, Blueprint):
        raise PluginError(f"{path.name} must provide a Flask Blueprint")
    if plugin.blueprint.url_prefix:
        raise PluginError(f"{path.name} must not set a blueprint url_prefix")
    if plugin.permission is not None and plugin.permission not in PERMISSIONS:
        raise PluginError(f"{path.name} declares unknown permission")
    if not all(isinstance(feature, Feature) for feature in plugin.features):
        raise PluginError(f"{path.name} features must be Feature instances")
    local_keys = [feature.key for feature in plugin.features]
    if any(not key for key in local_keys):
        raise PluginError(f"{path.name} declares an empty feature key")
    if len(set(local_keys)) != len(local_keys):
        raise PluginError(f"{path.name} declares duplicate feature keys")
    return plugin


def _import_plugin_module(path: Path):
    module_name = f"{PLUGIN_MODULE_PREFIX}.{path.name}"
    spec = importlib.util.spec_from_file_location(
        module_name,
        path / "__init__.py",
        submodule_search_locations=[str(path)],
    )
    if spec is None or spec.loader is None:
        raise PluginError(f"cannot import plugin {path.name}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def _ensure_plugin_id(
    registry: dict[str, dict], name: str, used_ids: set[str]
) -> tuple[str, bool]:
    """Return the stored id for ``name`` and whether it was generated now."""
    entry = registry.setdefault(name, {})
    plugin_id = entry.get("id")
    if _valid_id(plugin_id) and plugin_id not in (used_ids - {plugin_id}):
        return plugin_id, False

    while True:
        candidate = secrets.token_hex(PLUGIN_ID_BYTES)
        if candidate not in used_ids:
            entry["id"] = candidate
            return candidate, True


def _mount_plugin(app: Flask, plugin: Plugin, plugin_id: str) -> None:
    app.register_blueprint(
        plugin.blueprint,
        url_prefix=f"/plug/{plugin_id}",
        name=plugin.blueprint.name,
    )
    endpoint = f"{plugin.blueprint.name}.{plugin.endpoint}"
    if endpoint not in app.view_functions:
        raise PluginError(
            f"{plugin.name} has no view endpoint {plugin.endpoint!r}"
        )

    master = plugin_feature_key(plugin.name)
    register_feature_group(app, plugin.name, plugin.label)
    register_feature(
        app,
        Feature(master, plugin.label, plugin.description),
    )
    for feature in plugin.features:
        register_feature(
            app,
            Feature(
                plugin_feature_key(plugin.name, feature.key),
                feature.label,
                feature.description,
                feature.default,
                group=plugin.name,
            ),
        )
    app.extensions.setdefault(PLUGIN_BLUEPRINT_FEATURES, {})[
        plugin.blueprint.name
    ] = master

    if not plugin.nav:
        return
    register_nav_item(
        app,
        NavItem(
            key=f"plugin:{plugin_id}",
            endpoint=endpoint,
            label=plugin.label,
            icon=plugin.icon,
            group="workspace",
            permission=plugin.permission,
            feature=master,
            order=plugin.order,
        ),
    )


def _valid_id(value: object) -> bool:
    return isinstance(value, str) and bool(PLUGIN_ID_RE.match(value))


def _load_registry(path: Path, app: Flask) -> dict[str, dict]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        app.logger.warning("ignoring unreadable plugin registry: %s", path)
        return {}

    if not isinstance(raw, dict):
        app.logger.warning("ignoring malformed plugin registry: %s", path)
        return {}

    registry = {}
    seen_ids = set()
    for name, entry in raw.items():
        if isinstance(name, str) and isinstance(entry, dict):
            registry[name] = dict(entry)
            plugin_id = registry[name].get("id")
            if _valid_id(plugin_id):
                if plugin_id in seen_ids:
                    registry[name].pop("id", None)
                else:
                    seen_ids.add(plugin_id)
    return registry


def _save_registry(path: Path, registry: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
