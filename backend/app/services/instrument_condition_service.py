"""v1.6 — Instrument Condition Tracker (Deliverable 5).

Trends a physical instrument's condition across its full inspection history —
cleaning findings, damage findings, corrosion history, repair history, and
supervisor comments — grouped by the same honest instrument-identity key
already used by the pre-sterilization readiness engine (barcode/UDI, with an
explicit "untracked" fallback rather than a fabricated re-identification).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.models.inspection_finding import InspectionFinding
from app.models.supervisor_review import SupervisorReview
from app.services.baseline_comparison_scoring_service import CLEANING_KPIS


def instrument_condition_history(db: Session, tenant_id: str, instrument_identity: str) -> dict | None:
    """Full history for one instrument identity (`barcode:...` / `udi:...`)."""
    if instrument_identity.startswith("barcode:"):
        barcode = instrument_identity.removeprefix("barcode:")
        rows = (
            db.query(models.Inspection)
            .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.instrument_barcode == barcode)
            .order_by(models.Inspection.created_at.asc())
            .all()
        )
    elif instrument_identity.startswith("udi:"):
        udi = instrument_identity.removeprefix("udi:")
        rows = (
            db.query(models.Inspection)
            .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.instrument_udi == udi)
            .order_by(models.Inspection.created_at.asc())
            .all()
        )
    else:
        return None

    if not rows:
        return None

    inspection_ids = [r.id for r in rows]
    findings = (
        db.query(InspectionFinding)
        .filter(InspectionFinding.inspection_id.in_(inspection_ids))
        .all()
    ) if inspection_ids else []
    reviews = (
        db.query(SupervisorReview)
        .filter(SupervisorReview.inspection_id.in_(inspection_ids))
        .all()
    ) if inspection_ids else []
    reviews_by_inspection: dict[int, list] = {}
    for r in reviews:
        reviews_by_inspection.setdefault(r.inspection_id, []).append(r)

    findings_by_inspection: dict[int, list] = {}
    for f in findings:
        findings_by_inspection.setdefault(f.inspection_id, []).append(f)

    history = []
    for insp in rows:
        insp_findings = findings_by_inspection.get(insp.id, [])
        cleaning_findings = [f.finding_type for f in insp_findings if f.finding_type in CLEANING_KPIS]
        damage_findings = [f.finding_type for f in insp_findings if f.finding_type not in CLEANING_KPIS]
        corrosion_present = any(f.finding_type in ("rust", "corrosion", "pitting") for f in insp_findings)
        supervisor_comments = [
            r.rationale for r in reviews_by_inspection.get(insp.id, []) if r.rationale.strip()
        ]

        history.append({
            "inspection_id": insp.id,
            "date": insp.created_at.isoformat() if insp.created_at else None,
            "disposition": insp.disposition,
            "cleaning_findings": cleaning_findings,
            "damage_findings": damage_findings,
            "corrosion_present": corrosion_present,
            "repair_flag": insp.disposition == "REMOVE FROM SERVICE",
            "supervisor_comments": supervisor_comments,
        })

    repair_count = sum(1 for h in history if h["repair_flag"])
    corrosion_count = sum(1 for h in history if h["corrosion_present"])

    # Trend: is condition improving, declining, or stable across this
    # instrument's history? Compare the first half's clean rate to the second.
    def _clean_rate(bucket: list[dict]) -> float | None:
        if not bucket:
            return None
        clean = sum(1 for h in bucket if not h["cleaning_findings"] and not h["damage_findings"])
        return clean / len(bucket)

    mid = len(history) // 2
    older_rate, newer_rate = _clean_rate(history[:mid]), _clean_rate(history[mid:])
    if older_rate is None or newer_rate is None or older_rate == newer_rate:
        trend = "stable" if len(history) > 1 else "insufficient_data"
    else:
        trend = "improving" if newer_rate > older_rate else "declining"

    return {
        "instrument_identity": instrument_identity,
        "instrument_type": rows[-1].instrument_type,
        "inspection_count": len(history),
        "repair_count": repair_count,
        "corrosion_history_count": corrosion_count,
        "condition_trend": trend,
        "history": history,
    }
