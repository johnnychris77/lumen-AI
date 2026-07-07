"""v1.8 — Clinical Case Library (Deliverable 2).

Automatically preserves significant inspections — a real critical finding,
a supervisor override, or a repair/remove-from-service outcome — as a
reusable case: what was found, what the AI said, what the supervisor
corrected, the final disposition, and any educational notes. One case per
inspection; later events (a disposition action after the AI's initial
save) update the same case rather than creating a duplicate.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.knowledge import ClinicalCase


def is_significant(*, risk_tier: str, is_critical_finding: bool, has_override: bool, finding_type: str = "") -> bool:
    """A real trigger, never a heuristic guess: any actionable finding was
    actually detected (matching the spec's own examples — blood, bone,
    corrosion, missing insulation, a crack are all ordinary findings, not
    just remove-from-service-tier ones), a critical risk tier, a critical
    finding on the readiness engine's own classification, or a supervisor
    has already acted on this inspection."""
    has_finding = bool((finding_type or "").strip()) and finding_type not in ("none", "unknown")
    return has_finding or risk_tier == "Critical" or bool(is_critical_finding) or has_override


def _ai_findings_snapshot(db: Session, inspection_id: int) -> str:
    from app.models.inspection_finding import InspectionFinding

    rows = (
        db.query(InspectionFinding)
        .filter(InspectionFinding.inspection_id == inspection_id)
        .order_by(InspectionFinding.severity_index.desc())
        .all()
    )
    return json.dumps([
        {"finding_type": r.finding_type, "zone": r.zone, "severity_index": r.severity_index}
        for r in rows
    ])


def get_case(db: Session, tenant_id: str, inspection_id: int) -> ClinicalCase | None:
    return (
        db.query(ClinicalCase)
        .filter(ClinicalCase.tenant_id == tenant_id, ClinicalCase.inspection_id == inspection_id)
        .first()
    )


def save_or_update_case(
    db: Session, tenant_id: str, insp, *, finding_type: str,
    supervisor_corrections: str = "", final_disposition: str = "",
    clinical_reasoning: str = "", educational_notes: str = "", outcome: str = "",
) -> ClinicalCase:
    existing = get_case(db, tenant_id, insp.id)
    finding_label = (finding_type or "unspecified finding").replace("_", " ")
    title = f"{finding_label.capitalize()} — {insp.instrument_type}"

    if existing is not None:
        if supervisor_corrections:
            existing.supervisor_corrections = supervisor_corrections
        if final_disposition:
            existing.final_disposition = final_disposition
        if clinical_reasoning:
            existing.clinical_reasoning = clinical_reasoning
        if educational_notes:
            existing.educational_notes = educational_notes
        if outcome:
            existing.outcome = outcome
        existing.ai_findings = _ai_findings_snapshot(db, insp.id)
        return existing

    row = ClinicalCase(
        tenant_id=tenant_id, inspection_id=insp.id, instrument_type=insp.instrument_type,
        finding_type=finding_type or "", title=title,
        ai_findings=_ai_findings_snapshot(db, insp.id),
        supervisor_corrections=supervisor_corrections, final_disposition=final_disposition,
        clinical_reasoning=clinical_reasoning, educational_notes=educational_notes, outcome=outcome,
    )
    db.add(row)
    return row


def case_to_dict(row: ClinicalCase) -> dict:
    try:
        ai_findings = json.loads(row.ai_findings or "[]")
    except (TypeError, ValueError):
        ai_findings = []
    return {
        "id": row.id, "inspection_id": row.inspection_id, "instrument_type": row.instrument_type,
        "finding_type": row.finding_type, "title": row.title, "ai_findings": ai_findings,
        "supervisor_corrections": row.supervisor_corrections, "final_disposition": row.final_disposition,
        "clinical_reasoning": row.clinical_reasoning, "educational_notes": row.educational_notes,
        "outcome": row.outcome, "view_count": row.view_count,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def list_cases(db: Session, tenant_id: str, *, instrument: str = "", finding: str = "") -> list[dict]:
    q = db.query(ClinicalCase).filter(ClinicalCase.tenant_id == tenant_id)
    if instrument:
        q = q.filter(ClinicalCase.instrument_type.ilike(f"%{instrument}%"))
    if finding:
        q = q.filter(ClinicalCase.finding_type == finding)
    rows = q.order_by(ClinicalCase.id.desc()).all()
    return [case_to_dict(r) for r in rows]


def record_view(db: Session, tenant_id: str, case_id: int) -> ClinicalCase | None:
    row = (
        db.query(ClinicalCase)
        .filter(ClinicalCase.tenant_id == tenant_id, ClinicalCase.id == case_id)
        .first()
    )
    if row is None:
        return None
    row.view_count += 1
    return row
