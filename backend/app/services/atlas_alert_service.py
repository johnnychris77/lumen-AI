"""v3.1 — Project Atlas, Section 8: Enterprise Alerts.

Explainable, cross-facility alerts derived from what
`atlas_watchlist_service`/`atlas_analytics_service` already found — never a
bare severity number. Idempotent per underlying entry so re-running
generation doesn't spam duplicates for an already-alerted, still-open
finding.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.atlas_enterprise import ENTERPRISE_WATCHLIST_EMERGING_TREND, ENTERPRISE_WATCHLIST_HOSPITAL, EnterpriseAlert
from app.services import atlas_analytics_service, atlas_watchlist_service


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _new_ref() -> str:
    return f"EA-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}"


def _already_alerted(db: Session, system_id: str, title: str) -> bool:
    return (
        db.query(EnterpriseAlert.id)
        .filter(EnterpriseAlert.system_id == system_id, EnterpriseAlert.title == title, EnterpriseAlert.resolved_at.is_(None))
        .first()
        is not None
    )


def generate_enterprise_alerts(db: Session, system_id: str) -> list[dict]:
    created: list[EnterpriseAlert] = []

    watchlist = atlas_watchlist_service.list_active_watchlist(db, system_id)
    for entry in watchlist:
        if entry["entity_type"] == ENTERPRISE_WATCHLIST_EMERGING_TREND:
            title = f"Emerging trend: {entry['entity_value'].replace('_', ' ')}"
            if _already_alerted(db, system_id, title):
                continue
            facility_count = entry["reason"].count(",") + 1
            row = EnterpriseAlert(
                system_id=system_id, alert_ref=_new_ref(), title=title, narrative=entry["reason"],
                recommendation="Review whether a shared root cause (vendor, IFU, training gap) spans these facilities.",
                reasoning=f"The same recurring pattern was independently detected at {facility_count} separate facilities — "
                          f"a market-wide or system-wide cause is more likely than {facility_count} unrelated local causes.",
                severity="high" if facility_count >= 3 else "medium", affected_facility_count=facility_count,
            )
            db.add(row)
            created.append(row)

        if entry["entity_type"] == ENTERPRISE_WATCHLIST_HOSPITAL and entry["score"] >= 0.8:
            title = f"Highest-risk hospital: {entry['entity_value']}"
            if _already_alerted(db, system_id, title):
                continue
            row = EnterpriseAlert(
                system_id=system_id, alert_ref=_new_ref(), title=title, narrative=entry["reason"],
                recommendation=f"Escalate {entry['entity_value']} for a system-level quality review.",
                reasoning=f"{entry['entity_value']}'s enterprise risk score places it in the highest-risk tier system-wide.",
                severity="critical", affected_facility_count=1,
            )
            db.add(row)
            created.append(row)

    agreement_trend = atlas_analytics_service.enterprise_trend(db, system_id, metric="supervisor_agreement_rate")["series"]
    if len(agreement_trend) >= 2:
        latest, prior = agreement_trend[-1], agreement_trend[-2]
        delta = latest["value"] - prior["value"]
        if delta <= -5:
            title = "Supervisor agreement decreased this month"
            if not _already_alerted(db, system_id, title):
                row = EnterpriseAlert(
                    system_id=system_id, alert_ref=_new_ref(), title=title,
                    narrative=f"Supervisor agreement rate fell from {prior['value']}% to {latest['value']}% "
                              f"({prior['period']} to {latest['period']}) system-wide.",
                    recommendation="Review recent AI model changes and recent supervisor onboarding/turnover across facilities.",
                    reasoning="A system-wide drop in supervisor agreement (not isolated to one facility) suggests a "
                              "model-level or process-level cause rather than a single facility's practice.",
                    severity="high", affected_facility_count=0,
                )
                db.add(row)
                created.append(row)

    db.commit()
    for row in created:
        db.refresh(row)

    return list_alerts(db, system_id)


def list_alerts(db: Session, system_id: str, *, severity: str = "", unresolved_only: bool = True) -> list[dict]:
    q = db.query(EnterpriseAlert).filter(EnterpriseAlert.system_id == system_id)
    if unresolved_only:
        q = q.filter(EnterpriseAlert.resolved_at.is_(None))
    if severity:
        q = q.filter(EnterpriseAlert.severity == severity)
    rows = q.order_by(EnterpriseAlert.created_at.desc()).all()
    return [_row_to_dict(r) for r in rows]


def acknowledge_alert(db: Session, system_id: str, alert_id: int, *, acknowledged_by: str) -> dict | None:
    row = db.query(EnterpriseAlert).filter(EnterpriseAlert.id == alert_id, EnterpriseAlert.system_id == system_id).first()
    if row is None:
        return None
    row.acknowledged = True
    row.acknowledged_by = acknowledged_by
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def resolve_alert(db: Session, system_id: str, alert_id: int) -> dict | None:
    row = db.query(EnterpriseAlert).filter(EnterpriseAlert.id == alert_id, EnterpriseAlert.system_id == system_id).first()
    if row is None:
        return None
    row.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)
