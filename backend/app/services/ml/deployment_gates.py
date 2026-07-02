"""Phase 17 §7 & §8 — Deployment gates + human-in-the-loop promotion rules.

Encodes what each approval stage may do and what a model must satisfy before a
human may promote it. Models are NEVER auto-promoted: promotion always returns a
requirement checklist and refuses to advance until a human confirms it.
"""
from __future__ import annotations

from typing import Any

# Approval lifecycle (ordered).
APPROVAL_STAGES = ["experimental", "pilot", "validated", "deprecated"]

# Capabilities per stage (§8).
GATE_CAPABILITIES: dict[str, dict[str, Any]] = {
    "experimental": {
        "can_drive_clinical_recommendation": False,
        "can_run_shadow_mode": True,
        "can_provide_advisory": False,
        "requires_human_review_disclaimer": True,
        "usable_for_new_inspection": False,
        "description": "Shadow mode only. Cannot drive or advise a clinical recommendation.",
    },
    "pilot": {
        "can_drive_clinical_recommendation": False,
        "can_run_shadow_mode": True,
        "can_provide_advisory": True,
        "requires_human_review_disclaimer": True,
        "usable_for_new_inspection": True,
        "description": "Advisory only, with a visible human-review disclaimer. Cannot decide.",
    },
    "validated": {
        "can_drive_clinical_recommendation": True,
        "can_run_shadow_mode": True,
        "can_provide_advisory": True,
        "requires_human_review_disclaimer": True,
        "usable_for_new_inspection": True,
        "supervisor_override_allowed": True,
        "description": "May support a workflow decision; supervisor override always allowed.",
    },
    "deprecated": {
        "can_drive_clinical_recommendation": False,
        "can_run_shadow_mode": False,
        "can_provide_advisory": False,
        "requires_human_review_disclaimer": True,
        "usable_for_new_inspection": False,
        "description": "Retired. Cannot be used for new inspections.",
    },
}


def capabilities(stage: str) -> dict[str, Any]:
    return dict(GATE_CAPABILITIES.get(stage, GATE_CAPABILITIES["experimental"]))


def can_drive_clinical_recommendation(stage: str) -> bool:
    return capabilities(stage)["can_drive_clinical_recommendation"]


def requires_human_review_disclaimer(stage: str) -> bool:
    return capabilities(stage)["requires_human_review_disclaimer"]


def usable_for_new_inspection(stage: str) -> bool:
    return capabilities(stage)["usable_for_new_inspection"]


# Human-in-the-loop requirements to leave experimental (§7).
_MIN_VALIDATION_SAMPLES = 200


def promotion_requirements(target_stage: str) -> list[str]:
    if target_stage == "pilot":
        return [
            "supervisor_validation",
            "minimum_sample_size",
            "false_negative_review",
            "edge_case_review",
            "limitations_documented",
        ]
    if target_stage == "validated":
        return [
            "supervisor_validation",
            "minimum_sample_size",
            "false_negative_review",
            "edge_case_review",
            "limitations_documented",
            "shadow_mode_completed",
            "safety_false_negative_within_threshold",
        ]
    return []


def evaluate_promotion(
    current_stage: str,
    target_stage: str,
    *,
    checklist: dict[str, bool] | None = None,
    sample_size: int = 0,
    approver: str | None = None,
) -> dict[str, Any]:
    """Decide whether a *human-initiated* promotion may proceed.

    Never auto-promotes: returns ``allowed`` plus the unmet requirements. The
    caller (route) only writes the new stage when ``allowed`` is True and an
    approver is recorded.
    """
    checklist = checklist or {}
    if target_stage not in APPROVAL_STAGES:
        return {"allowed": False, "reason": f"Unknown target stage '{target_stage}'."}

    # Deprecation is always allowed (retiring a model is safe).
    if target_stage == "deprecated":
        return {"allowed": bool(approver), "unmet": [] if approver else ["approver_required"],
                "requirements": [], "auto_promoted": False}

    cur_i = APPROVAL_STAGES.index(current_stage) if current_stage in APPROVAL_STAGES else 0
    tgt_i = APPROVAL_STAGES.index(target_stage)
    if tgt_i <= cur_i:
        return {"allowed": False, "reason": f"Cannot promote from {current_stage} to {target_stage}."}
    if tgt_i > cur_i + 1:
        return {"allowed": False,
                "reason": "Promotion must advance one stage at a time (no skipping)."}

    reqs = promotion_requirements(target_stage)
    unmet = [r for r in reqs if not checklist.get(r, False)]
    if "minimum_sample_size" in reqs and sample_size < _MIN_VALIDATION_SAMPLES:
        if "minimum_sample_size" not in unmet:
            unmet.append("minimum_sample_size")
    if not approver:
        unmet.append("approver_required")

    return {
        "allowed": len(unmet) == 0,
        "requirements": reqs,
        "unmet": unmet,
        "minimum_sample_size": _MIN_VALIDATION_SAMPLES,
        "auto_promoted": False,
        "note": "Models are never auto-promoted; a human must satisfy every requirement.",
    }
