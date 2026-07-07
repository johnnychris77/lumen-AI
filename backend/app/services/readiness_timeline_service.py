"""v1.6 — Readiness Timeline (Deliverable 4).

Image Uploaded -> Instrument Identified -> Coverage Completed -> AI Findings ->
Clinical Reasoning -> Supervisor Review -> Disposition -> Ready for Packaging.

Most of these steps happen synchronously inside one POST /api/inspections
call, so they share a single real timestamp (Inspection.created_at) rather
than fabricating individually-spaced fake timestamps — consistent with the
same honesty principle already applied in app/cios/state_machine.py's
pipeline-monitor timeline. Only steps with their own real, independently-timed
record (Supervisor Review) get a distinct timestamp.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.supervisor_review import SupervisorReview
from app.services.disposition_engine import recommend_disposition
from app.services.readiness_engine import (
    READY, READY_WITH_SUPERVISOR_APPROVAL, compute_readiness, get_primary_finding_type,
)


def build_timeline(db: Session, tenant_id: str, insp) -> dict:
    submitted_at = insp.created_at.isoformat() if insp.created_at else None
    review = (
        db.query(SupervisorReview)
        .filter(SupervisorReview.inspection_id == insp.id)
        .order_by(SupervisorReview.id.desc())
        .first()
    )
    confirmed = review is not None
    readiness = compute_readiness(
        db, tenant_id, insp, confirmed=confirmed,
        override_action=(review.override_action if review else ""),
    )
    disposition = recommend_disposition(
        readiness, insp, coverage_pct=insp.coverage_pct,
        primary_finding_type=get_primary_finding_type(db, insp),
    )
    ready_for_packaging = readiness["status"] in (READY, READY_WITH_SUPERVISOR_APPROVAL)

    steps = [
        {
            "step": "Image Uploaded",
            "completed": bool(insp.has_image),
            "timestamp": submitted_at if insp.has_image else None,
        },
        {
            "step": "Instrument Identified",
            "completed": bool(insp.instrument_type and insp.instrument_type != "unknown"),
            "timestamp": submitted_at,
        },
        {
            "step": "Coverage Completed",
            "completed": insp.coverage_pct is not None,
            "timestamp": submitted_at if insp.coverage_pct is not None else None,
        },
        {
            "step": "AI Findings",
            "completed": insp.score_status in ("scored", "scored_after_override"),
            "timestamp": insp.inference_timestamp.isoformat() if insp.inference_timestamp else submitted_at,
        },
        {
            "step": "Clinical Reasoning",
            "completed": insp.disposition is not None,
            "timestamp": submitted_at if insp.disposition is not None else None,
        },
        {
            "step": "Supervisor Review",
            "completed": confirmed,
            "timestamp": review.created_at.isoformat() if review and review.created_at else None,
        },
        {
            "step": "Disposition",
            "completed": True,
            "timestamp": (review.created_at.isoformat() if review and review.created_at else submitted_at),
            "value": disposition["disposition"],
        },
        {
            "step": "Ready for Packaging",
            "completed": ready_for_packaging,
            "timestamp": (review.created_at.isoformat() if ready_for_packaging and review else None),
        },
    ]

    return {
        "inspection_id": insp.id,
        "steps": steps,
        "note": (
            "Steps that happen synchronously within one analysis call share the "
            "submission timestamp rather than fabricating individually-spaced times; "
            "only Supervisor Review has its own independently-timed record."
        ),
    }
