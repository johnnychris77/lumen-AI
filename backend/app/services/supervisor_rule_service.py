"""v2.5 — Supervisor Rule Builder service (Project Cortex, Section 7).

CRUD + evidence matching for supervisor-authored `ClinicalDecisionRule` rows.
Governed and versioned: `update_rule` never edits a row in place — it creates
a new row at `version + 1`, links the old row to it via `superseded_by_id`,
and deactivates the old row, so the full history of what a rule used to say
is never lost.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.clinical_decision_rule import RULE_TYPES, ClinicalDecisionRule


def rule_to_dict(row: ClinicalDecisionRule) -> dict:
    try:
        recommendation = json.loads(row.recommendation or "[]")
    except (TypeError, ValueError):
        recommendation = []
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "created_by": row.created_by,
        "rule_type": row.rule_type,
        "title": row.title,
        "description": row.description,
        "evidence": {
            "finding_types": [row.finding_type] if row.finding_type else [],
            "zone_keywords": [row.zone_keyword] if row.zone_keyword else [],
            "requires_high_risk_zone": row.requires_high_risk_zone,
            "requires_repeat_finding": row.requires_repeat_finding,
            "min_repeat_occurrences": row.min_repeat_occurrences,
        },
        "severity": row.severity,
        "spd_risk": row.spd_risk,
        "recommendation": recommendation,
        "is_active": row.is_active,
        "version": row.version,
        "superseded_by_id": row.superseded_by_id,
        "source": "supervisor_rule_builder",
    }


def create_rule(
    db: Session, tenant_id: str, *, created_by: str, rule_type: str, title: str, description: str = "",
    finding_type: str = "", zone_keyword: str = "", requires_high_risk_zone: bool = False,
    requires_repeat_finding: bool = False, min_repeat_occurrences: int = 0,
    severity: str = "Moderate", spd_risk: str = "Moderate", recommendation: list[str] | None = None,
) -> ClinicalDecisionRule:
    if rule_type not in RULE_TYPES:
        raise ValueError(f"rule_type must be one of {RULE_TYPES}")
    row = ClinicalDecisionRule(
        tenant_id=tenant_id, created_by=created_by, rule_type=rule_type, title=title, description=description,
        finding_type=(finding_type or "").strip().lower(), zone_keyword=(zone_keyword or "").strip().lower(),
        requires_high_risk_zone=requires_high_risk_zone, requires_repeat_finding=requires_repeat_finding,
        min_repeat_occurrences=min_repeat_occurrences, severity=severity, spd_risk=spd_risk,
        recommendation=json.dumps(recommendation or []),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_rules(db: Session, tenant_id: str, *, active_only: bool = True) -> list[dict]:
    q = db.query(ClinicalDecisionRule).filter(ClinicalDecisionRule.tenant_id == tenant_id)
    if active_only:
        q = q.filter(ClinicalDecisionRule.is_active.is_(True))
    rows = q.order_by(ClinicalDecisionRule.id.desc()).all()
    return [rule_to_dict(r) for r in rows]


def get_rule(db: Session, tenant_id: str, rule_id: int) -> ClinicalDecisionRule | None:
    return (
        db.query(ClinicalDecisionRule)
        .filter(ClinicalDecisionRule.id == rule_id, ClinicalDecisionRule.tenant_id == tenant_id)
        .first()
    )


def update_rule(db: Session, tenant_id: str, rule_id: int, *, updated_by: str, **changes) -> ClinicalDecisionRule | None:
    """Governed edit: creates a new row at `version + 1` rather than mutating
    the existing row, and deactivates + links the prior version."""
    current = get_rule(db, tenant_id, rule_id)
    if current is None:
        return None

    next_version = create_rule(
        db, tenant_id,
        created_by=updated_by,
        rule_type=changes.get("rule_type", current.rule_type),
        title=changes.get("title", current.title),
        description=changes.get("description", current.description),
        finding_type=changes.get("finding_type", current.finding_type),
        zone_keyword=changes.get("zone_keyword", current.zone_keyword),
        requires_high_risk_zone=changes.get("requires_high_risk_zone", current.requires_high_risk_zone),
        requires_repeat_finding=changes.get("requires_repeat_finding", current.requires_repeat_finding),
        min_repeat_occurrences=changes.get("min_repeat_occurrences", current.min_repeat_occurrences),
        severity=changes.get("severity", current.severity),
        spd_risk=changes.get("spd_risk", current.spd_risk),
        recommendation=changes.get("recommendation", json.loads(current.recommendation or "[]")),
    )
    next_version.version = current.version + 1
    current.is_active = False
    current.superseded_by_id = next_version.id
    db.commit()
    db.refresh(next_version)
    return next_version


def deactivate_rule(db: Session, tenant_id: str, rule_id: int) -> ClinicalDecisionRule | None:
    row = get_rule(db, tenant_id, rule_id)
    if row is None:
        return None
    row.is_active = False
    db.commit()
    db.refresh(row)
    return row


def evaluate_supervisor_rules(db: Session, tenant_id: str, evidence: dict) -> list[dict]:
    """Every active supervisor-authored rule whose conditions the evidence
    bundle satisfies — same matching semantics as `spd_rule_library`."""
    rows = (
        db.query(ClinicalDecisionRule)
        .filter(ClinicalDecisionRule.tenant_id == tenant_id, ClinicalDecisionRule.is_active.is_(True))
        .all()
    )
    finding_type = (evidence.get("finding_type") or "").strip().lower()
    zone = (evidence.get("zone") or "").strip().lower()
    matched = []
    for row in rows:
        if row.finding_type and row.finding_type != finding_type:
            continue
        if row.zone_keyword and row.zone_keyword not in zone:
            continue
        if row.requires_high_risk_zone and not evidence.get("high_risk_zone"):
            continue
        if row.requires_repeat_finding and not evidence.get("repeat_finding"):
            continue
        if evidence.get("repeat_occurrences", 0) < row.min_repeat_occurrences:
            continue
        matched.append(rule_to_dict(row))
    return matched
