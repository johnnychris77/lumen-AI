from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.customer_health import build_customer_health_summary, create_health_snapshot, latest_snapshot, recommendations
from app.db import models


DEFAULT_PLAYBOOKS = [
    {
        "playbook_key": "low_health_recovery",
        "title": "Low Health Recovery Plan",
        "trigger_type": "health_score",
        "trigger_threshold": 60,
        "recommended_actions": [
            "Schedule executive adoption review",
            "Run leadership packet workflow",
            "Resolve open governance exceptions",
            "Review implementation blockers",
        ],
        "owner_role": "customer_success",
        "notes": "Triggered for low health score tenants",
    },
    {
        "playbook_key": "governance_stabilization",
        "title": "Governance Stabilization Plan",
        "trigger_type": "risk_flag",
        "trigger_threshold": 1,
        "recommended_actions": [
            "Review release governance exception queue",
            "Resolve open SLA events",
            "Clear or document packet holds",
            "Validate distribution list governance",
        ],
        "owner_role": "customer_success",
        "notes": "Triggered for open governance issues",
    },
    {
        "playbook_key": "adoption_acceleration",
        "title": "Adoption Acceleration Plan",
        "trigger_type": "usage_score",
        "trigger_threshold": 40,
        "recommended_actions": [
            "Create and run saved reports",
            "Generate executive scorecards",
            "Configure templates and digests",
            "Train tenant admins on packet workflows",
        ],
        "owner_role": "customer_success",
        "notes": "Triggered for weak adoption signals",
    },
]


def _compact(value: Any) -> str:
    return json.dumps(value, default=str)[:4000]


def _safe_json_list(value: str | None) -> list:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def ensure_default_playbooks(db: Session, tenant_id: str, tenant_name: str) -> None:
    existing = (
        db.query(models.CustomerSuccessPlaybook)
        .filter(models.CustomerSuccessPlaybook.tenant_id == tenant_id)
        .count()
    )
    if existing:
        return

    for item in DEFAULT_PLAYBOOKS:
        db.add(models.CustomerSuccessPlaybook(
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            playbook_key=item["playbook_key"],
            title=item["title"],
            trigger_type=item["trigger_type"],
            trigger_threshold=item["trigger_threshold"],
            recommended_actions_json=_compact(item["recommended_actions"]),
            owner_role=item["owner_role"],
            is_enabled=True,
            notes=item["notes"],
        ))
    db.commit()


def evaluate_playbook_trigger(playbook: models.CustomerSuccessPlaybook, health_summary: dict) -> tuple[bool, str, str]:
    if playbook.trigger_type == "health_score":
        score = int(health_summary.get("health_score", 0))
        if score <= int(playbook.trigger_threshold):
            risk = "critical" if score < 40 else "high" if score < 60 else "watch"
            return True, f"Health score {score} is at or below threshold {playbook.trigger_threshold}", risk
        return False, "", ""

    if playbook.trigger_type == "usage_score":
        score = int(health_summary.get("usage_score", 0))
        if score <= int(playbook.trigger_threshold):
            risk = "high" if score < 30 else "watch"
            return True, f"Usage score {score} is at or below threshold {playbook.trigger_threshold}", risk
        return False, "", ""

    if playbook.trigger_type == "risk_flag":
        flags = set(health_summary.get("risk_flags", []))
        governance_flags = {"release_exceptions_open", "sla_events_open", "go_live_not_ready"}
        matched = flags.intersection(governance_flags)
        if matched:
            return True, f"Governance-related risk flags present: {', '.join(sorted(matched))}", "high"
        return False, "", ""

    return False, "", ""


def create_or_reuse_risk_case(
    db: Session,
    *,
    tenant_id: str,
    tenant_name: str,
    playbook: models.CustomerSuccessPlaybook,
    health_snapshot_id: int,
    risk_level: str,
    trigger_reason: str,
):
    existing = (
        db.query(models.RenewalRiskCase)
        .filter(
            models.RenewalRiskCase.tenant_id == tenant_id,
            models.RenewalRiskCase.playbook_id == playbook.id,
            models.RenewalRiskCase.status == "open",
        )
        .order_by(models.RenewalRiskCase.id.desc())
        .first()
    )
    if existing:
        return existing, False

    row = models.RenewalRiskCase(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        playbook_id=playbook.id,
        health_snapshot_id=health_snapshot_id,
        risk_level=risk_level,
        status="open",
        trigger_reason=trigger_reason,
        recommended_actions_json=playbook.recommended_actions_json,
        owner=playbook.owner_role,
        notes="",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, True


def run_renewal_risk(db: Session, tenant_id: str, tenant_name: str) -> dict:
    ensure_default_playbooks(db, tenant_id, tenant_name)

    latest = latest_snapshot(db, tenant_id)
    if latest:
        health_summary = build_customer_health_summary(db, tenant_id, tenant_name, 30)
        health_snapshot_id = latest.id
    else:
        snapshot_row, health_summary = create_health_snapshot(db, tenant_id, tenant_name, 30)
        health_snapshot_id = snapshot_row.id

    playbooks = (
        db.query(models.CustomerSuccessPlaybook)
        .filter(
            models.CustomerSuccessPlaybook.tenant_id == tenant_id,
            models.CustomerSuccessPlaybook.is_enabled == True,
        )
        .order_by(models.CustomerSuccessPlaybook.id.asc())
        .all()
    )

    results = []
    for playbook in playbooks:
        triggered, reason, risk = evaluate_playbook_trigger(playbook, health_summary)
        if not triggered:
            results.append({
                "playbook_id": playbook.id,
                "playbook_key": playbook.playbook_key,
                "triggered": False,
            })
            continue

        row, created = create_or_reuse_risk_case(
            db,
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            playbook=playbook,
            health_snapshot_id=health_snapshot_id,
            risk_level=risk,
            trigger_reason=reason,
        )
        results.append({
            "playbook_id": playbook.id,
            "playbook_key": playbook.playbook_key,
            "triggered": True,
            "created": created,
            "case_id": row.id,
            "risk_level": row.risk_level,
            "trigger_reason": row.trigger_reason,
        })

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "health_score": health_summary["health_score"],
        "health_status": health_summary["health_status"],
        "risk_flags": health_summary["risk_flags"],
        "results": results,
    }


def renewal_risk_summary(db: Session, tenant_id: str, tenant_name: str) -> dict:
    ensure_default_playbooks(db, tenant_id, tenant_name)

    playbooks = (
        db.query(models.CustomerSuccessPlaybook)
        .filter(models.CustomerSuccessPlaybook.tenant_id == tenant_id)
        .order_by(models.CustomerSuccessPlaybook.id.asc())
        .all()
    )
    cases = (
        db.query(models.RenewalRiskCase)
        .filter(models.RenewalRiskCase.tenant_id == tenant_id)
        .order_by(models.RenewalRiskCase.id.desc())
        .all()
    )
    health = build_customer_health_summary(db, tenant_id, tenant_name, 30)

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "health_score": health["health_score"],
        "health_status": health["health_status"],
        "risk_flags": health["risk_flags"],
        "playbooks": [
            {
                "id": p.id,
                "playbook_key": p.playbook_key,
                "title": p.title,
                "trigger_type": p.trigger_type,
                "trigger_threshold": p.trigger_threshold,
                "recommended_actions": _safe_json_list(p.recommended_actions_json),
                "owner_role": p.owner_role,
                "is_enabled": p.is_enabled,
                "notes": p.notes,
            }
            for p in playbooks
        ],
        "open_case_count": sum(1 for c in cases if c.status == "open"),
        "cases": [
            {
                "id": c.id,
                "playbook_id": c.playbook_id,
                "health_snapshot_id": c.health_snapshot_id,
                "risk_level": c.risk_level,
                "status": c.status,
                "trigger_reason": c.trigger_reason,
                "recommended_actions": _safe_json_list(c.recommended_actions_json),
                "owner": c.owner,
                "notes": c.notes,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in cases
        ],
        "recommendations": recommendations(health),
    }
