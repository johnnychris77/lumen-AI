"""Project Council, Sections 2 & 15: Leadership Team Registry & Governance.

Provisions the six default AI leadership teams for a tenant on first use,
and supports organization-level configuration changes -- always
append-only/versioned (mirrors Veritas's baseline governance action
pattern) so every configuration change is itself auditable. Organizations
may reconfigure membership but the safety-veto specialists
(`SAFETY_VETO_SPECIALISTS`) can never be dropped from a required list --
mandatory safety/evidence review can't be configured away.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.council_leadership import (
    COUNCIL_TEAM_KEYS,
    DEFAULT_TEAM_DEFINITIONS,
    KNOWN_SPECIALISTS,
    SAFETY_VETO_SPECIALISTS,
    CouncilTeamConfig,
)


def to_dict(row: CouncilTeamConfig) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "team_key": row.team_key,
        "team_name": row.team_name,
        "required_specialists": json.loads(row.required_specialists_json or "[]"),
        "optional_specialists": json.loads(row.optional_specialists_json or "[]"),
        "decision_scope": row.decision_scope,
        "escalation_rules": row.escalation_rules,
        "quorum_requirement": row.quorum_requirement,
        "safety_veto_enabled": row.safety_veto_enabled,
        "evidence_requirements": row.evidence_requirements,
        "review_frequency": row.review_frequency,
        "version": row.version,
        "approval_status": row.approval_status,
        "owner": row.owner,
        "is_current": row.is_current,
    }


def ensure_default_teams(db: Session, tenant_id: str) -> list[CouncilTeamConfig]:
    """Provisions the six default teams for a tenant the first time
    Council is used there. Idempotent -- does nothing if any current team
    config already exists for the tenant."""
    existing = (
        db.query(CouncilTeamConfig)
        .filter(CouncilTeamConfig.tenant_id == tenant_id, CouncilTeamConfig.is_current.is_(True))
        .count()
    )
    if existing:
        return list_teams(db, tenant_id, as_rows=True)

    rows = []
    for team_key in COUNCIL_TEAM_KEYS:
        definition = DEFAULT_TEAM_DEFINITIONS[team_key]
        row = CouncilTeamConfig(
            tenant_id=tenant_id,
            team_key=team_key,
            team_name=definition["team_name"],
            required_specialists_json=json.dumps(definition["required_specialists"]),
            optional_specialists_json=json.dumps(definition["optional_specialists"]),
            decision_scope=definition["decision_scope"],
            quorum_requirement=max(2, len(definition["required_specialists"]) - 1),
            evidence_requirements="Each required specialist must submit an independent assessment before consensus is classified.",
            owner="SPD Leadership",
        )
        db.add(row)
        rows.append(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def list_teams(db: Session, tenant_id: str, *, as_rows: bool = False):
    rows = (
        db.query(CouncilTeamConfig)
        .filter(CouncilTeamConfig.tenant_id == tenant_id, CouncilTeamConfig.is_current.is_(True))
        .order_by(CouncilTeamConfig.team_key.asc())
        .all()
    )
    return rows if as_rows else [to_dict(r) for r in rows]


def get_team_config(db: Session, tenant_id: str, team_key: str) -> CouncilTeamConfig | None:
    return (
        db.query(CouncilTeamConfig)
        .filter(
            CouncilTeamConfig.tenant_id == tenant_id, CouncilTeamConfig.team_key == team_key,
            CouncilTeamConfig.is_current.is_(True),
        )
        .first()
    )


def update_team_config(
    db: Session, tenant_id: str, team_key: str, *, required_specialists: list[str] | None = None,
    optional_specialists: list[str] | None = None, decision_scope: str | None = None,
    escalation_rules: str | None = None, quorum_requirement: int | None = None,
    evidence_requirements: str | None = None, review_frequency: str | None = None, owner: str = "",
) -> CouncilTeamConfig:
    """Inserts a new, incremented-version row rather than mutating the
    current one -- the full configuration history stays queryable."""
    current = get_team_config(db, tenant_id, team_key)
    if current is None:
        raise ValueError(f"Unknown Council team '{team_key}' for this tenant")

    current_required = json.loads(current.required_specialists_json)
    new_required = required_specialists if required_specialists is not None else current_required

    unknown_specialists = set(new_required) - KNOWN_SPECIALISTS
    if unknown_specialists:
        raise ValueError(
            f"Unknown specialist key(s) {sorted(unknown_specialists)} -- Council has no assessor for "
            "these and cases requiring them could never reach a human decision",
        )

    # Only the safety specialists that were actually required by the
    # *current* config can be "removed" -- checking against the full
    # SAFETY_VETO_SPECIALISTS set regardless of what was previously
    # required would wrongly block edits to teams (Operations, Executive,
    # Education) that only ever required one of the two.
    previously_required_safety = SAFETY_VETO_SPECIALISTS & set(current_required)
    missing_safety = previously_required_safety - set(new_required)
    if missing_safety:
        raise ValueError(
            f"Cannot remove mandatory safety/evidence specialist(s) {sorted(missing_safety)} from a required Council review",
        )

    current.is_current = False
    db.add(current)

    new_row = CouncilTeamConfig(
        tenant_id=tenant_id,
        team_key=team_key,
        team_name=current.team_name,
        required_specialists_json=json.dumps(new_required),
        optional_specialists_json=json.dumps(optional_specialists if optional_specialists is not None else json.loads(current.optional_specialists_json)),
        decision_scope=decision_scope if decision_scope is not None else current.decision_scope,
        escalation_rules=escalation_rules if escalation_rules is not None else current.escalation_rules,
        quorum_requirement=quorum_requirement if quorum_requirement is not None else current.quorum_requirement,
        safety_veto_enabled=current.safety_veto_enabled,
        evidence_requirements=evidence_requirements if evidence_requirements is not None else current.evidence_requirements,
        review_frequency=review_frequency if review_frequency is not None else current.review_frequency,
        version=current.version + 1,
        approval_status="pending_review",
        owner=owner or current.owner,
        is_current=True,
    )
    db.add(new_row)
    db.commit()
    db.refresh(new_row)
    return new_row


def team_config_history(db: Session, tenant_id: str, team_key: str) -> list[dict]:
    rows = (
        db.query(CouncilTeamConfig)
        .filter(CouncilTeamConfig.tenant_id == tenant_id, CouncilTeamConfig.team_key == team_key)
        .order_by(CouncilTeamConfig.version.asc())
        .all()
    )
    return [to_dict(r) for r in rows]
