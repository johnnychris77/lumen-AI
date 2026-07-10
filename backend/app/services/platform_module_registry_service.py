"""v4.0 — LumenAI OS (Project Genesis), Section 3: Modular Application
Framework — the module registry.

`PlatformModule` describes each of the ten named modules the sprint asks
for in terms of what already exists in this codebase: the frontend routes
each module corresponds to (grepped directly from `frontend/src/main.tsx`,
not invented), which roles may access it, and a link to its existing
documentation. This is a mapping/description layer — no existing route,
page, or backend module is moved, renamed, or rewritten. "Independent
release lifecycle" is represented by `release_channel`
(`stable`/`beta`) — a module can be flagged `beta` without touching any
other module's code path.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.platform_core import MODULE_KEYS, PlatformModule

_SEED: dict[str, dict] = {
    "inspect": {
        "name": "Inspect",
        "description": "Instrument inspection capture, findings review, work queue, and readiness dashboards.",
        "category": "clinical_operations",
        "nav_icon": "microscope",
        "routes": [
            "/inspection/new", "/inspection/capture", "/findings", "/inspection-work-queue",
            "/operations-board", "/operations", "/clinical-readiness", "/inspection-readiness", "/inspection-zones",
        ],
        "permissions": ["admin", "spd_manager", "operator", "technician"],
        "documentation_url": "docs/simulation/",
    },
    "twin": {
        "name": "Twin",
        "description": "Digital Twin of SPD operations — instrument flow, station utilization, and twin snapshots.",
        "category": "clinical_operations",
        "nav_icon": "layers",
        "routes": ["/digital-twin"],
        "permissions": ["admin", "spd_manager", "operator"],
        "documentation_url": "",
    },
    "knowledge": {
        "name": "Knowledge",
        "description": "Clinical Knowledge Graph, Knowledge Center, anatomy and instrument reference libraries.",
        "category": "intelligence",
        "nav_icon": "network",
        "routes": ["/knowledge-graph", "/knowledge-center", "/anatomy-library", "/instrument-library", "/baseline-library"],
        "permissions": ["admin", "spd_manager", "operator", "viewer"],
        "documentation_url": "",
    },
    "analytics": {
        "name": "Analytics",
        "description": "Analytics dashboards, quality intelligence, coverage, and predictive forecasting.",
        "category": "intelligence",
        "nav_icon": "chart",
        "routes": ["/analytics", "/quality-intelligence", "/quality-dashboard", "/coverage-dashboard", "/forecast"],
        "permissions": ["admin", "spd_manager", "viewer"],
        "documentation_url": "docs/insight/",
    },
    "command": {
        "name": "Command",
        "description": "Executive/quality/sentinel command centers — enterprise risk, CAPA, and autonomous monitoring.",
        "category": "governance",
        "nav_icon": "shield",
        "routes": [
            "/quality-command-center", "/sentinel", "/executive-command-center",
            "/pre-sterilization-command-center", "/capa", "/autonomous-operations",
        ],
        "permissions": ["admin", "spd_manager"],
        "documentation_url": "docs/sentinel/",
    },
    "connect": {
        "name": "Connect",
        "description": "Perioperative case coordination, enterprise integrations, and industry collaboration.",
        "category": "coordination",
        "nav_icon": "link",
        "routes": ["/case-intelligence", "/integrations", "/collaboration", "/collaboration-governance", "/atlas", "/enterprise"],
        "permissions": ["admin", "spd_manager", "operator", "vendor_user"],
        "documentation_url": "docs/beacon/",
    },
    "academy": {
        "name": "Academy",
        "description": "Training compliance, coaching, and education library.",
        "category": "education",
        "nav_icon": "graduation-cap",
        "routes": ["/training-center", "/training-compliance", "/coaching-dashboard", "/education-library"],
        "permissions": ["admin", "spd_manager", "operator", "viewer"],
        "documentation_url": "",
    },
    "research": {
        "name": "Research",
        "description": "Federated research portal, network intelligence, and global standards collaboration.",
        "category": "intelligence",
        "nav_icon": "flask",
        "routes": ["/research", "/network-intelligence", "/global-intelligence", "/global-standards"],
        "permissions": ["admin", "spd_manager", "viewer"],
        "documentation_url": "docs/horizon/",
    },
    "developer": {
        "name": "Developer",
        "description": "Agent trace viewer, CIOS dashboard, and platform integration diagnostics.",
        "category": "platform",
        "nav_icon": "terminal",
        "routes": ["/agent-trace", "/cios-dashboard"],
        "permissions": ["admin"],
        "documentation_url": "",
    },
    "marketplace": {
        "name": "Marketplace",
        "description": "Vendor baseline portal, vendor intelligence, and third-party plugin catalog.",
        "category": "platform",
        "nav_icon": "store",
        "routes": ["/vendor-baseline-portal", "/vendor-intelligence", "/manufacturer-baselines"],
        "permissions": ["admin", "spd_manager", "vendor_user"],
        "documentation_url": "docs/genesis/plugin-framework.md",
    },
}


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    result["routes"] = json.loads(result.pop("routes_json") or "[]")
    result["permissions"] = json.loads(result.pop("permissions_json") or "[]")
    result["settings"] = json.loads(result.pop("settings_json") or "{}")
    return result


def _seed_modules(db: Session) -> None:
    for key in MODULE_KEYS:
        if db.query(PlatformModule).filter(PlatformModule.module_key == key).first() is not None:
            continue
        spec = _SEED[key]
        db.add(PlatformModule(
            module_key=key, name=spec["name"], description=spec["description"], category=spec["category"],
            nav_icon=spec["nav_icon"], routes_json=json.dumps(spec["routes"]),
            permissions_json=json.dumps(spec["permissions"]), documentation_url=spec["documentation_url"],
            is_core=True, release_channel="stable",
        ))
    db.commit()


def list_modules(db: Session) -> list[dict]:
    _seed_modules(db)
    rows = db.query(PlatformModule).order_by(PlatformModule.module_key.asc()).all()
    return [_row_to_dict(r) for r in rows]


def get_module(db: Session, module_key: str) -> dict | None:
    _seed_modules(db)
    row = db.query(PlatformModule).filter(PlatformModule.module_key == module_key).first()
    return _row_to_dict(row) if row else None


def update_module_settings(db: Session, module_key: str, settings: dict) -> dict | None:
    row = db.query(PlatformModule).filter(PlatformModule.module_key == module_key).first()
    if row is None:
        return None
    row.settings_json = json.dumps(settings)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def set_release_channel(db: Session, module_key: str, release_channel: str) -> dict | None:
    if release_channel not in ("stable", "beta"):
        raise ValueError("release_channel must be 'stable' or 'beta'")
    row = db.query(PlatformModule).filter(PlatformModule.module_key == module_key).first()
    if row is None:
        return None
    row.release_channel = release_channel
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)
