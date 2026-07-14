"""Genesis — Section 11: the Candidate promotion ladder.

A model CANNOT advance beyond "Candidate" unless every one of the 8
checklist items is satisfied. This ladder (Experimental -> Candidate ->
Validated Candidate -> Pilot -> Production) is DISTINCT from, and does not
modify, the pre-existing ``app.services.ml.deployment_gates`` ladder
(experimental/pilot/validated/deprecated), which governs whether a model
may drive a clinical recommendation at all. This ladder governs where a
model sits in its own training -> validation -> deployment lifecycle.
Models are never auto-promoted here either — every advance requires an
explicit approver.

Shadow (Phase 6 — Prospective Shadow-Mode Clinical Validation) §14 adds a
SECOND, stage-scoped checklist that only applies once a model is moving
*beyond* Candidate (to Validated Candidate or later) — the original 8-item
``CHECKLIST_ITEMS`` above is left completely unchanged so the
Experimental -> Candidate transition Genesis's own tests exercise is
unaffected. Every new item reuses an existing, real evidence source rather
than reimplementing one: inspection volume/performance targets from
``shadow_validation_metrics.shadow_go_no_go()``, drift from
``sentinel_ai_health_service._detect_drift()``, and clinical sign-off from
``shadow_clinical_review_board.board_approved()``.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.dataset_governance import DatasetRegistryEntry, DatasetVersion
from app.models.model_registry import ModelRegistryEntry
from app.models.shadow_prediction import ShadowPrediction
from app.models.supervisor_review import SupervisorReview
from app.services.advisory_safety_service import safety_objectives_achieved
from app.services.advisory_workflow_impact_service import adoption_rate
from app.services.ml.pilot_validation import go_no_go as advisory_go_no_go
from app.services.ml.shadow_clinical_review_board import board_approved
from app.services.ml.shadow_validation_metrics import shadow_go_no_go
from app.services.sentinel_ai_health_service import _detect_drift

CANDIDATE_STAGES = ["Experimental", "Candidate", "Validated Candidate", "Pilot", "Production"]

CHECKLIST_ITEMS = [
    "dataset_frozen",
    "annotation_complete",
    "evaluation_complete",
    "model_card_generated",
    "registry_updated",
    "reproducible_training_confirmed",
    "error_analysis_reviewed",
    "governance_review_completed",
]

# Shadow §14 — additional items required only for Validated Candidate and
# beyond, on top of (never instead of) the 8 items above.
VALIDATED_CANDIDATE_CHECKLIST_ITEMS = [
    "inspection_volume_achieved",
    "performance_targets_met",
    "model_drift_acceptable",
    "clinical_review_board_approved",
]

_STAGES_REQUIRING_SHADOW_EVIDENCE = {"Validated Candidate", "Pilot", "Production"}

# Advisor (Phase 7) §13 — additional items required only to advance to
# Production, on top of (never instead of) the base 8 + Shadow's 4.
# governance_approval and clinical_review_board_approved are already
# covered by the cumulative checklists above (CHECKLIST_ITEMS's
# governance_review_completed, and Shadow's clinical_review_board_approved
# respectively) — this adds only what those don't already check.
PRODUCTION_CHECKLIST_ITEMS = [
    "safety_objectives_achieved",
    "performance_thresholds_met",
    "user_adoption_targets_met",
    "customer_approval",
]

_STAGES_REQUIRING_PILOT_EVIDENCE = {"Production"}
_MIN_ADOPTION_RATE = 0.6


def _dataset_frozen(db: Session, model: ModelRegistryEntry) -> bool:
    if model.dataset_version_id is None:
        return False
    version = db.query(DatasetVersion).filter(DatasetVersion.id == model.dataset_version_id).first()
    return bool(version and version.frozen)


def _annotation_complete(db: Session, model: ModelRegistryEntry) -> bool:
    """Every image registered against this model's dataset version must be
    in a terminal annotation state (APPROVED or ARCHIVED) — none left
    UNLABELED/LABELED/SECOND_REVIEW/DISAGREEMENT/ADJUDICATED."""
    if model.dataset_version_id is None:
        return False
    entries = (
        db.query(DatasetRegistryEntry)
        .filter(DatasetRegistryEntry.dataset_version_id == model.dataset_version_id)
        .all()
    )
    if not entries:
        return False
    return all(e.review_status in ("APPROVED", "ARCHIVED") for e in entries)


def evaluate_candidate_checklist(db: Session, model: ModelRegistryEntry) -> dict[str, bool]:
    return {
        "dataset_frozen": _dataset_frozen(db, model),
        "annotation_complete": _annotation_complete(db, model),
        "evaluation_complete": bool(model.evaluation_metrics and model.evaluation_metrics != "{}"),
        "model_card_generated": bool(model.model_card_markdown),
        "registry_updated": model.id is not None,
        "reproducible_training_confirmed": model.reproducible_training_confirmed,
        "error_analysis_reviewed": model.error_analysis_reviewed,
        "governance_review_completed": model.governance_review_completed,
    }


def _shadow_rows(db: Session, model: ModelRegistryEntry) -> list[ShadowPrediction]:
    return (
        db.query(ShadowPrediction)
        .filter(ShadowPrediction.tenant_id == model.tenant_id, ShadowPrediction.model_id == model.model_id)
        .all()
    )


def evaluate_validated_candidate_checklist(db: Session, model: ModelRegistryEntry) -> dict[str, bool]:
    """Shadow §14 — the 4 additional items required to advance beyond
    Candidate, each read from a real, already-computed evidence source."""
    gng = shadow_go_no_go(_shadow_rows(db, model))
    drift_detected, _ = _detect_drift(db, model.tenant_id)
    return {
        "inspection_volume_achieved": gng["inspection_volume_achieved"],
        "performance_targets_met": gng["performance_targets_met"],
        "model_drift_acceptable": not drift_detected,
        "clinical_review_board_approved": board_approved(
            db, tenant_id=model.tenant_id, model_id=model.model_id, model_version=model.model_version
        ),
    }


def evaluate_production_checklist(db: Session, model: ModelRegistryEntry) -> dict[str, bool]:
    """Advisor §13 — the 4 additional items required to advance from Pilot
    to Production. ``performance_thresholds_met`` reuses
    ``pilot_validation.go_no_go()`` over real ``SupervisorReview`` rows
    (the Advisory-pilot's real, visible-recommendation evidence) —
    distinct from Shadow's ``shadow_go_no_go()`` over silent shadow
    predictions, since by the Pilot stage the model's recommendations are
    actually visible and generating real supervisor reviews."""
    reviews = db.query(SupervisorReview).filter(SupervisorReview.tenant_id == model.tenant_id).all()
    gng = advisory_go_no_go(reviews)
    adoption = adoption_rate(db, model.tenant_id, model_id=model.model_id)
    return {
        "safety_objectives_achieved": safety_objectives_achieved(db, model.tenant_id),
        "performance_thresholds_met": gng["decision"] == "GO",
        "user_adoption_targets_met": (
            adoption["adoption_rate"] is not None and adoption["adoption_rate"] >= _MIN_ADOPTION_RATE
        ),
        "customer_approval": model.customer_approved,
    }


def evaluate_candidate_promotion(
    db: Session, *, model: ModelRegistryEntry, target_stage: str, approver: str | None = None,
) -> dict[str, Any]:
    """Decide whether ``model`` may advance to ``target_stage`` on this
    ladder. Never auto-promotes: returns ``allowed`` plus the unmet
    checklist items. The caller only writes the new stage when ``allowed``
    is True and an approver is recorded."""
    if target_stage not in CANDIDATE_STAGES:
        return {"allowed": False, "reason": f"Unknown candidate stage '{target_stage}'.", "unmet": []}

    current = model.candidate_stage if model.candidate_stage in CANDIDATE_STAGES else "Experimental"
    cur_i = CANDIDATE_STAGES.index(current)
    tgt_i = CANDIDATE_STAGES.index(target_stage)
    if tgt_i <= cur_i:
        return {"allowed": False, "reason": f"Cannot move from '{current}' to '{target_stage}' (not forward).", "unmet": []}
    if tgt_i > cur_i + 1:
        return {"allowed": False, "reason": "Promotion must advance one stage at a time (no skipping).", "unmet": []}

    # The full 8-item checklist gates every advance beyond "Candidate" —
    # a model already at "Candidate" moving to "Validated Candidate" (and
    # beyond) must still satisfy every item, since none of them are
    # inherently one-time; e.g. governance review must cover the specific
    # stage being entered. Validated Candidate and beyond additionally
    # require Shadow §14's 4-item pilot-evidence checklist (unchanged for
    # Experimental -> Candidate, so Genesis's own promotion tests are
    # unaffected).
    checklist = evaluate_candidate_checklist(db, model)
    if target_stage in _STAGES_REQUIRING_SHADOW_EVIDENCE:
        checklist.update(evaluate_validated_candidate_checklist(db, model))
    if target_stage in _STAGES_REQUIRING_PILOT_EVIDENCE:
        checklist.update(evaluate_production_checklist(db, model))
    unmet = [item for item, ok in checklist.items() if not ok]
    if not approver:
        unmet.append("approver_required")

    return {
        "allowed": not unmet,
        "current_stage": current,
        "target_stage": target_stage,
        "checklist": checklist,
        "unmet": unmet,
        "auto_promoted": False,
        "note": "No model advances beyond Candidate without every checklist item satisfied and a recorded human approver.",
    }


def promote_candidate(
    db: Session, *, model: ModelRegistryEntry, target_stage: str, approver: str,
) -> dict[str, Any]:
    decision = evaluate_candidate_promotion(db, model=model, target_stage=target_stage, approver=approver)
    if not decision["allowed"]:
        return decision
    model.candidate_stage = target_stage
    model.approved_by = approver
    db.commit()
    db.refresh(model)
    return {**decision, "promoted": True, "candidate_stage": model.candidate_stage}
