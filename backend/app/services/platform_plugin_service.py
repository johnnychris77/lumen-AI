"""v4.0 — LumenAI OS (Project Genesis), Section 8: Plugin Framework.

`PlatformPlugin` is the registration surface a future module announces
itself into — the routes, menus, permissions, widgets, dashboards, and
reports it wants to contribute, all as descriptive JSON. Registering a
plugin here never imports or executes any code: this is a catalog/
metadata record, not a dynamic plugin-loading engine. "No core
modifications required" is satisfied because registering, activating,
or disabling a plugin is a pure data operation against this table — it
never requires editing `app/main.py` or any existing router.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.platform_core import PLUGIN_ACTIVE, PLUGIN_DISABLED, PLUGIN_DRAFT, PLUGIN_STATUSES, PlatformPlugin


class UnknownPluginError(Exception):
    pass


class DuplicatePluginKeyError(Exception):
    pass


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    for field in ("registered_routes", "registered_menus", "registered_permissions", "registered_widgets", "registered_dashboards", "registered_reports"):
        result[field] = json.loads(result.pop(f"{field}_json") or "[]")
    return result


def register_plugin(
    db: Session, *, plugin_key: str, name: str, version: str = "0.1.0", registered_by: str = "",
    routes: list | None = None, menus: list | None = None, permissions: list | None = None,
    widgets: list | None = None, dashboards: list | None = None, reports: list | None = None,
) -> dict:
    if db.query(PlatformPlugin).filter(PlatformPlugin.plugin_key == plugin_key).first() is not None:
        raise DuplicatePluginKeyError(f"Plugin '{plugin_key}' is already registered.")

    row = PlatformPlugin(
        plugin_key=plugin_key, name=name, version=version, status=PLUGIN_DRAFT, registered_by=registered_by,
        registered_routes_json=json.dumps(routes or []), registered_menus_json=json.dumps(menus or []),
        registered_permissions_json=json.dumps(permissions or []), registered_widgets_json=json.dumps(widgets or []),
        registered_dashboards_json=json.dumps(dashboards or []), registered_reports_json=json.dumps(reports or []),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def _get_or_404(db: Session, plugin_key: str) -> PlatformPlugin:
    row = db.query(PlatformPlugin).filter(PlatformPlugin.plugin_key == plugin_key).first()
    if row is None:
        raise UnknownPluginError(f"Plugin '{plugin_key}' not found.")
    return row


def set_plugin_status(db: Session, plugin_key: str, status: str) -> dict:
    if status not in PLUGIN_STATUSES:
        raise ValueError(f"status must be one of {PLUGIN_STATUSES}")
    row = _get_or_404(db, plugin_key)
    row.status = status
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def activate_plugin(db: Session, plugin_key: str) -> dict:
    return set_plugin_status(db, plugin_key, PLUGIN_ACTIVE)


def disable_plugin(db: Session, plugin_key: str) -> dict:
    return set_plugin_status(db, plugin_key, PLUGIN_DISABLED)


def list_plugins(db: Session, *, status: str = "") -> list[dict]:
    q = db.query(PlatformPlugin)
    if status:
        q = q.filter(PlatformPlugin.status == status)
    return [_row_to_dict(r) for r in q.order_by(PlatformPlugin.id.desc()).all()]


def get_plugin(db: Session, plugin_key: str) -> dict | None:
    row = db.query(PlatformPlugin).filter(PlatformPlugin.plugin_key == plugin_key).first()
    return _row_to_dict(row) if row else None
