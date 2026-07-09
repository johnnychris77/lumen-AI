"""v2.5 — Decision Replay (Project Cortex, Section 9).

Replays any past inspection's recommendation for audit/education: input,
applied rules, evidence, decision, and the supervisor's actual outcome.
`build_explainable_decision()` is a pure function of already-persisted data
(`Inspection`, `InspectionFinding`, `SupervisorReview`, Clinical Memory), so
replay is done by *reconstruction* rather than reading back a separately
persisted snapshot — the same "replay = re-derive from real rows" approach
`knowledge_graph_service.explain_inspection()` already uses. This keeps the
replay always in sync with the current rule library (a rule fixed or added
since the original inspection is visible on replay, clearly logged as such),
rather than trusting a frozen copy that could drift from what the rules
actually say today.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.models.supervisor_review import SupervisorReview
from app.services.decision_reasoning_service import build_explainable_decision, compute_recommendation_confidence


def _supervisor_outcome(db: Session, inspection_id: int) -> list[dict]:
    reviews = (
        db.query(SupervisorReview)
        .filter(SupervisorReview.inspection_id == inspection_id)
        .order_by(SupervisorReview.id.asc())
        .all()
    )
    return [
        {
            "reviewer_name": r.reviewer_name,
            "reviewer_role": r.reviewer_role,
            "agreement": r.agreement,
            "override_action": r.override_action,
            "final_disposition": r.final_disposition,
            "rationale": r.rationale,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reviews
    ]


def replay_decision(db: Session, tenant_id: str, inspection_id: int) -> dict | None:
    insp = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id, models.Inspection.tenant_id == tenant_id)
        .first()
    )
    if insp is None:
        return None

    decision = build_explainable_decision(db, tenant_id, insp)
    confidence = compute_recommendation_confidence(decision["evidence"], decision["applied_rules"])
    supervisor_outcome = _supervisor_outcome(db, inspection_id)

    return {
        "inspection_id": inspection_id,
        "input": {
            "instrument_type": insp.instrument_type,
            "instrument_identity": decision["evidence"]["instrument_identity"],
            "finding_type": decision["evidence"]["finding_type"],
            "zone": decision["evidence"]["zone"],
            "risk_score": insp.risk_score,
            "risk_level": insp.risk_level,
            "created_at": insp.created_at.isoformat() if insp.created_at else None,
        },
        "reasoning_path": decision["reasoning_path"],
        "applied_rules": decision["applied_rules"],
        "evidence": decision["evidence"],
        "decision": {
            "clinical_rationale": decision["clinical_rationale"],
            "final_recommendation": decision["final_recommendation"],
            "confidence": confidence,
            "persisted_recommended_action": insp.recommended_action,
            "persisted_disposition": insp.disposition,
        },
        "supervisor_outcome": supervisor_outcome,
        "note": (
            "This is a reconstruction from currently-persisted data and the current rule "
            "library, not a frozen snapshot from the original inspection time — a rule added "
            "or corrected since then will be reflected here."
        ),
        "human_review_required": True,
    }
