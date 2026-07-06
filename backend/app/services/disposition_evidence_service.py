"""v1.6 — Disposition Evidence Panel (Deliverable 3).

Assembles the evidence bundle a supervisor reviews before acting on a
disposition recommendation: coverage, findings, severity, baseline used,
supervisor status, readiness score, recommended disposition, and clinical
rationale. Every field is read from already-computed/persisted data — this
module is pure assembly, not a new analysis.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.models.supervisor_review import SupervisorReview
from app.services.disposition_engine import recommend_disposition
from app.services.pre_sterilization_command_center_service import _instrument_identity
from app.services.readiness_engine import compute_readiness, get_primary_finding_type


def build_evidence_panel(db: Session, tenant_id: str, insp) -> dict:
    reviews = (
        db.query(SupervisorReview)
        .filter(SupervisorReview.inspection_id == insp.id)
        .order_by(SupervisorReview.id.desc())
        .all()
    )
    confirmed = len(reviews) > 0
    latest_review = reviews[0] if reviews else None
    override_action = (insp.override_reason and (latest_review.override_action if latest_review else "")) or ""

    primary_finding_type = get_primary_finding_type(db, insp)
    readiness = compute_readiness(db, tenant_id, insp, confirmed=confirmed, override_action=override_action)
    disposition = recommend_disposition(
        readiness, insp, coverage_pct=insp.coverage_pct, primary_finding_type=primary_finding_type,
    )

    return {
        "inspection_id": insp.id,
        "instrument_identity": _instrument_identity(insp),
        "instrument_type": insp.instrument_type,
        "inspection_coverage_pct": insp.coverage_pct,
        "coverage_quality": insp.coverage_quality,
        "detected_issue": primary_finding_type or None,
        "severity": insp.risk_level,
        "baseline_used": insp.baseline_source,
        "baseline_status": insp.baseline_status,
        "supervisor_status": (
            "reviewed" if confirmed else "pending"
        ),
        "supervisor_agreement": latest_review.agreement if latest_review else None,
        "readiness_score": readiness["readiness_score"],
        "readiness_status": readiness["status"],
        "recommended_disposition": disposition["disposition"],
        "clinical_rationale": disposition["explanation"],
        "human_review_required": True,
    }


def get_evidence_panel(db: Session, tenant_id: str, inspection_id: int) -> dict | None:
    insp = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id, models.Inspection.tenant_id == tenant_id)
        .first()
    )
    if insp is None:
        return None
    return build_evidence_panel(db, tenant_id, insp)
