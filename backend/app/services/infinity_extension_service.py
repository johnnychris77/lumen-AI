"""v5.0 — Project Infinity, Sections 3 & 6: Plugin SDK & Extension
Framework.

Reuses Genesis's `PlatformPlugin` (v4.0) directly — extended additively
with five new `registered_*_json` columns for the Plugin SDK's own named
artifact types this table didn't yet have. Still metadata-only: no
plugin code is ever imported or executed from this table, matching
Genesis's own documented convention exactly.

Two distinct dimensions, deliberately not conflated:
  * **Extension type** (Section 3 — what kind of artifact): Applications,
    Widgets, Dashboards, Reports, Workflow Nodes, AI Skills,
    Notifications, Commands, Analytics — each maps 1:1 onto one of
    `PlatformPlugin`'s `registered_*_json` columns.
  * **Extension location** (Section 6 — where in the UI it attaches):
    Menu, Navigation, Dashboard, Command Center, Copilot, Reports,
    Digital Twin Panel, Knowledge Graph View, Simulation Model — recorded
    as a `location` key inside each registered item, not a separate
    column, since a single artifact type (e.g. a "dashboard" widget) can
    attach at several different locations.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.platform_core import PLUGIN_ACTIVE, PLUGIN_DISABLED, PlatformPlugin

SDK_EXTENSION_TYPES = [
    "applications", "widgets", "dashboards", "reports", "workflow_nodes",
    "ai_skills", "notifications", "commands", "analytics",
]

_TYPE_TO_COLUMN = {
    "applications": "registered_routes_json",
    "widgets": "registered_widgets_json",
    "dashboards": "registered_dashboards_json",
    "reports": "registered_reports_json",
    "workflow_nodes": "registered_workflow_nodes_json",
    "ai_skills": "registered_ai_skills_json",
    "notifications": "registered_notifications_json",
    "commands": "registered_commands_json",
    "analytics": "registered_analytics_json",
}

EXTENSION_LOCATIONS = [
    "menu", "navigation", "dashboard", "command_center", "copilot",
    "reports", "digital_twin_panel", "knowledge_graph_view", "simulation_model",
]


class PluginNotFoundError(ValueError):
    pass


class InvalidExtensionTypeError(ValueError):
    pass


class InvalidExtensionLocationError(ValueError):
    pass


def _to_dict(row: PlatformPlugin) -> dict:
    result: dict = {
        "id": row.id, "created_at": row.created_at.isoformat(), "plugin_key": row.plugin_key, "name": row.name,
        "version": row.version, "status": row.status, "developer_account_id": row.developer_account_id,
        "marketplace_listing_id": row.marketplace_listing_id, "registered_by": row.registered_by,
    }
    for extension_type, column in _TYPE_TO_COLUMN.items():
        result[extension_type] = json.loads(getattr(row, column) or "[]")
    return result


def register_plugin(
    db: Session, *, plugin_key: str, name: str, version: str = "0.1.0", developer_account_id: int | None = None,
    marketplace_listing_id: int | None = None, registered_by: str = "",
) -> dict:
    row = PlatformPlugin(
        plugin_key=plugin_key, name=name, version=version, developer_account_id=developer_account_id,
        marketplace_listing_id=marketplace_listing_id, registered_by=registered_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def _get_plugin(db: Session, plugin_key: str) -> PlatformPlugin:
    row = db.query(PlatformPlugin).filter(PlatformPlugin.plugin_key == plugin_key).first()
    if row is None:
        raise PluginNotFoundError(f"Plugin '{plugin_key}' not found.")
    return row


def get_plugin(db: Session, plugin_key: str) -> dict:
    return _to_dict(_get_plugin(db, plugin_key))


def list_plugins(db: Session, *, status: str = "") -> list[dict]:
    q = db.query(PlatformPlugin)
    if status:
        q = q.filter(PlatformPlugin.status == status)
    return [_to_dict(r) for r in q.order_by(PlatformPlugin.created_at.desc()).all()]


def register_extension(db: Session, plugin_key: str, *, extension_type: str, location: str, item: dict) -> dict:
    if extension_type not in SDK_EXTENSION_TYPES:
        raise InvalidExtensionTypeError(f"extension_type must be one of {SDK_EXTENSION_TYPES}")
    if location not in EXTENSION_LOCATIONS:
        raise InvalidExtensionLocationError(f"location must be one of {EXTENSION_LOCATIONS}")

    row = _get_plugin(db, plugin_key)
    column = _TYPE_TO_COLUMN[extension_type]
    entries = json.loads(getattr(row, column) or "[]")
    entries.append({**item, "location": location})
    setattr(row, column, json.dumps(entries))
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def activate_plugin(db: Session, plugin_key: str) -> dict:
    row = _get_plugin(db, plugin_key)
    row.status = PLUGIN_ACTIVE
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def disable_plugin(db: Session, plugin_key: str) -> dict:
    row = _get_plugin(db, plugin_key)
    row.status = PLUGIN_DISABLED
    db.commit()
    db.refresh(row)
    return _to_dict(row)
