"""v4.2 — Project Pulse, Section 3: Enterprise Command Map.

Composes P16's existing enterprise hierarchy (via Genesis's
`platform_org_service.organization_tree`, itself a read-only wrapper over
`app/models/enterprise_hierarchy.py`) with Atlas's existing facility
intelligence scores (`atlas_dashboard_service.get_latest_facility_
intelligence`) — no second hierarchy, no second score. The one genuinely
new piece is `status_color_for_score`: no status-color banding
(green/yellow/orange/red/gray) concept existed anywhere in this codebase
before Pulse (confirmed: Atlas only exposes numeric scores) — this is a
pure derived presentation function over an existing score, never a
fabricated color.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.pulse_operations import STATUS_GRAY, STATUS_GREEN, STATUS_ORANGE, STATUS_RED, STATUS_YELLOW
from app.services import atlas_dashboard_service, platform_org_service


def status_color_for_score(risk_score: float | None) -> str:
    """Higher `risk_score` means worse — banded the same direction every
    other risk score in this codebase already uses (0-100 scale, higher
    is riskier). `None` (no data yet) is `gray`, never guessed."""
    if risk_score is None:
        return STATUS_GRAY
    if risk_score < 25:
        return STATUS_GREEN
    if risk_score < 50:
        return STATUS_YELLOW
    if risk_score < 75:
        return STATUS_ORANGE
    return STATUS_RED


def command_map(db: Session) -> dict:
    tree = platform_org_service.organization_tree(db)
    facility_nodes = []
    for facility in tree["facilities"]:
        snapshot = atlas_dashboard_service.get_latest_facility_intelligence(
            db, facility["system_id"], facility["facility_id"],
        )
        risk_score = snapshot.get("risk_score") if snapshot else None
        facility_nodes.append({
            "facility_id": facility["facility_id"], "facility_name": facility["facility_name"],
            "market_id": facility["market_id"], "region_id": facility["region_id"], "system_id": facility["system_id"],
            "tenant_id": facility["tenant_id"], "risk_score": risk_score,
            "status_color": status_color_for_score(risk_score),
        })

    return {
        "health_systems": tree["health_systems"], "markets": tree["markets"], "regions": tree["regions"],
        "facilities": facility_nodes,
        "status_summary": {
            color: sum(1 for f in facility_nodes if f["status_color"] == color)
            for color in (STATUS_GREEN, STATUS_YELLOW, STATUS_ORANGE, STATUS_RED, STATUS_GRAY)
        },
    }


def facility_detail(db: Session, system_id: str, facility_id: str) -> dict | None:
    """'Clicking a facility opens live operational details' (Section 3)."""
    snapshot = atlas_dashboard_service.get_latest_facility_intelligence(db, system_id, facility_id)
    if snapshot is None:
        snapshot = atlas_dashboard_service.compute_facility_intelligence(db, system_id, facility_id)
    if snapshot is None:
        return None
    return {**snapshot, "status_color": status_color_for_score(snapshot.get("risk_score"))}
