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
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.dataset_governance import DatasetRegistryEntry, DatasetVersion
from app.models.model_registry import ModelRegistryEntry

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
    # stage being entered.
    checklist = evaluate_candidate_checklist(db, model)
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
