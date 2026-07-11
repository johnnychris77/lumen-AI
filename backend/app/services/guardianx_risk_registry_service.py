"""v5.2 — Project GuardianX, Section 5: AI Risk Registry.

One `AIModelRiskEntry` row per identified risk, bias, failure mode, or
clinical boundary for a given `AIModelRegistryEntry` (Olympus, v5.1) --
a model typically has several, so this is a many-rows-per-model table,
distinct from the single-value `approved_use_cases_json`/
`out_of_scope_uses_json` scope declarations already on the model itself
(`docs/guardianx/model-governance.md`).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.guardianx_assurance import RISK_SEVERITIES, RISK_STATUSES, RISK_TYPES, AIModelRiskEntry
from app.services.olympus_model_registry_service import get_model_or_404


class UnknownRiskEntryError(Exception):
    pass


def _to_dict(entry: AIModelRiskEntry) -> dict:
    return {
        "id": entry.id,
        "model_id": entry.model_id,
        "risk_type": entry.risk_type,
        "description": entry.description,
        "mitigation": entry.mitigation,
        "severity": entry.severity,
        "status": entry.status,
        "identified_by": entry.identified_by,
        "created_at": entry.created_at.isoformat(),
    }


def record_risk(
    db: Session, model_id: int, *, risk_type: str, description: str, mitigation: str = "",
    severity: str = "medium", identified_by: str = "",
) -> dict:
    get_model_or_404(db, model_id)  # 404s if the model doesn't exist
    if risk_type not in RISK_TYPES:
        raise ValueError(f"risk_type must be one of {RISK_TYPES}")
    if severity not in RISK_SEVERITIES:
        raise ValueError(f"severity must be one of {RISK_SEVERITIES}")
    row = AIModelRiskEntry(
        model_id=model_id, risk_type=risk_type, description=description, mitigation=mitigation,
        severity=severity, identified_by=identified_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def _get_or_404(db: Session, risk_id: int) -> AIModelRiskEntry:
    row = db.query(AIModelRiskEntry).filter(AIModelRiskEntry.id == risk_id).first()
    if row is None:
        raise UnknownRiskEntryError(f"Risk entry {risk_id} not found.")
    return row


def update_risk_status(db: Session, risk_id: int, *, status: str) -> dict:
    if status not in RISK_STATUSES:
        raise ValueError(f"status must be one of {RISK_STATUSES}")
    row = _get_or_404(db, risk_id)
    row.status = status
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def list_risks_for_model(db: Session, model_id: int) -> list[dict]:
    rows = db.query(AIModelRiskEntry).filter(AIModelRiskEntry.model_id == model_id).order_by(AIModelRiskEntry.created_at.desc()).all()
    return [_to_dict(r) for r in rows]


def risk_registry_summary(db: Session) -> dict:
    rows = db.query(AIModelRiskEntry).all()
    by_severity: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for r in rows:
        by_severity[r.severity] = by_severity.get(r.severity, 0) + 1
        by_status[r.status] = by_status.get(r.status, 0) + 1
    return {
        "total_risks": len(rows),
        "by_severity": by_severity,
        "by_status": by_status,
        "open_critical_or_high": sum(
            1 for r in rows if r.status == "open" and r.severity in ("critical", "high")
        ),
    }
