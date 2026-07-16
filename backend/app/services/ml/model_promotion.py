"""Dataset Registry & AI Model Development Foundation — Section 12.

The full "no model becomes deployable until..." gate. Deliberately additive
to, not a replacement of, ``app.services.ml.deployment_gates`` — that
module's stage-transition mechanics (one stage at a time, human-recorded
approver, existing checklist items) are reused as-is; this module adds the
dataset/documentation checks this program's brief specifically requires
(dataset frozen, model card generated, documentation/clinical-review/
metrics-approval flags) as an outer layer, so existing callers of
``deployment_gates.evaluate_promotion`` are completely unaffected.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.dataset_governance import DatasetVersion
from app.models.model_registry import ModelRegistryEntry
from app.services.ml.deployment_gates import evaluate_promotion

# The Section 12 checklist, on top of whatever deployment_gates already requires.
FULL_PROMOTION_REQUIREMENTS = [
    "dataset_frozen",
    "evaluation_complete",
    "metrics_approved",
    "clinical_review_complete",
    "documentation_complete",
    "model_card_generated",
    "registry_updated",
]


def evaluate_full_promotion_readiness(
    db: Session,
    *,
    model: ModelRegistryEntry,
    target_stage: str,
    checklist: dict[str, bool] | None = None,
    sample_size: int = 0,
    approver: str | None = None,
) -> dict[str, Any]:
    """Combine the existing deployment-gate checklist with this program's
    dataset/documentation requirements. A model can only be promoted when
    BOTH sets of requirements are satisfied."""
    base = evaluate_promotion(
        model.approval_status, target_stage, checklist=checklist, sample_size=sample_size, approver=approver,
    )

    dataset_frozen = False
    if model.dataset_version_id is not None:
        version = db.query(DatasetVersion).filter(DatasetVersion.id == model.dataset_version_id).first()
        dataset_frozen = bool(version and version.frozen)

    evaluation_complete = bool(model.evaluation_metrics and model.evaluation_metrics != "{}")
    registry_updated = model.id is not None

    section12_checks = {
        "dataset_frozen": dataset_frozen,
        "evaluation_complete": evaluation_complete,
        "metrics_approved": model.metrics_approved,
        "clinical_review_complete": model.clinical_review_complete,
        "documentation_complete": model.documentation_complete,
        "model_card_generated": bool(model.model_card_markdown),
        "registry_updated": registry_updated,
    }
    section12_unmet = [name for name, ok in section12_checks.items() if not ok]

    unmet = list(dict.fromkeys([*base.get("unmet", []), *section12_unmet]))
    allowed = base.get("allowed", False) and not section12_unmet

    return {
        "allowed": allowed,
        "deployment_gate_result": base,
        "section12_checks": section12_checks,
        "unmet": unmet,
        "auto_promoted": False,
        "note": (
            "No model becomes deployable until every deployment-gate requirement AND every "
            "Section 12 requirement (dataset frozen, evaluation complete, metrics approved, "
            "clinical review complete, documentation complete, model card generated, registry "
            "updated) is satisfied."
        ),
    }
