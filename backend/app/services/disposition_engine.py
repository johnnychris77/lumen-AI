"""v1.6 — Instrument Disposition Engine (Deliverable 2).

Generates a standardized disposition recommendation from the readiness
classification plus signals the readiness engine doesn't itself distinguish
(coverage completeness, manufacturer-attributable wear) — every disposition
carries a required, non-generic explanation grounded in the actual inputs.
"""
from __future__ import annotations

from app.services.readiness_engine import (
    PENDING_ANALYSIS_STATUS,
    PENDING_SUPERVISOR_REVIEW,
    READY,
    READY_WITH_SUPERVISOR_APPROVAL,
    REMOVE_FROM_SERVICE_STATUS,
    REQUIRES_RECLEANING_STATUS,
    REQUIRES_REPAIR_STATUS,
)

PROCEED_TO_PACKAGING = "Proceed to Packaging"
RECLEAN = "Reclean"
REPEAT_INSPECTION = "Repeat Inspection"
SUPERVISOR_REVIEW_REQUIRED = "Supervisor Review Required"
REPAIR_EVALUATION = "Repair Evaluation"
MANUFACTURER_EVALUATION = "Manufacturer Evaluation"
REMOVE_FROM_SERVICE = "Remove From Service"

DISPOSITIONS = [
    PROCEED_TO_PACKAGING, RECLEAN, REPEAT_INSPECTION, SUPERVISOR_REVIEW_REQUIRED,
    REPAIR_EVALUATION, MANUFACTURER_EVALUATION, REMOVE_FROM_SERVICE,
]

# Condition findings attributable to manufacturing/material quality rather
# than SPD process — routed to Manufacturer Evaluation instead of a generic
# repair queue when they recur on the same instrument.
_MANUFACTURER_ATTRIBUTABLE = {"corrosion", "pitting", "insulation_damage"}
_COVERAGE_INSUFFICIENT_THRESHOLD = 50


def recommend_disposition(
    readiness: dict, insp, *, coverage_pct: int | None, primary_finding_type: str | None = None,
) -> dict:
    """Deliverable 2 — one of the seven standardized dispositions, with a
    required, grounded explanation.

    `primary_finding_type` should be the real detected finding (see
    `readiness_engine.get_primary_finding_type`) — `insp.detected_issue` is
    only used as a fallback for the no-image manual-entry path."""
    status = readiness["status"]
    detected_issue = (
        primary_finding_type if primary_finding_type is not None
        else (insp.detected_issue or "").strip().lower()
    )

    # Coverage too incomplete to trust any disposition — ask for a repeat
    # inspection before anything else, regardless of what was found.
    if coverage_pct is not None and coverage_pct < _COVERAGE_INSUFFICIENT_THRESHOLD:
        return {
            "disposition": REPEAT_INSPECTION,
            "explanation": (
                f"Inspection coverage was only {coverage_pct}%, below the "
                f"{_COVERAGE_INSUFFICIENT_THRESHOLD}% threshold needed to trust a disposition. "
                "Capture the missing required zones and repeat the inspection."
            ),
        }

    if status in (PENDING_ANALYSIS_STATUS, PENDING_SUPERVISOR_REVIEW):
        return {
            "disposition": SUPERVISOR_REVIEW_REQUIRED,
            "explanation": (
                "No approved baseline or completed scoring exists yet for this inspection — "
                "a supervisor must review before any disposition can be recommended."
            ),
        }

    if status == REMOVE_FROM_SERVICE_STATUS:
        return {
            "disposition": REMOVE_FROM_SERVICE,
            "explanation": (
                f"{detected_issue.capitalize() or 'A structural finding'} escalated to remove-from-service "
                "and is not a repairable condition — the instrument should not re-enter circulation."
            ),
        }

    if status == REQUIRES_REPAIR_STATUS:
        if detected_issue in _MANUFACTURER_ATTRIBUTABLE and readiness.get("repair_history"):
            return {
                "disposition": MANUFACTURER_EVALUATION,
                "explanation": (
                    f"This instrument has a prior remove-from-service history and a recurring "
                    f"{detected_issue} finding — a manufacturer-attributable material or design "
                    "issue should be evaluated, not just a one-off repair."
                ),
            }
        return {
            "disposition": REPAIR_EVALUATION,
            "explanation": (
                f"{detected_issue.capitalize() or 'A structural finding'} was detected and classified "
                "as repairable — route to repair evaluation before returning to service."
            ),
        }

    if status == REQUIRES_RECLEANING_STATUS:
        return {
            "disposition": RECLEAN,
            "explanation": (
                f"{detected_issue.capitalize() or 'Residual contamination'} was detected — the "
                "instrument should be recleaned and re-inspected before packaging."
            ),
        }

    if status == READY_WITH_SUPERVISOR_APPROVAL:
        return {
            "disposition": PROCEED_TO_PACKAGING,
            "explanation": (
                "No actionable findings, and a supervisor has confirmed the AI's assessment — "
                "the instrument may proceed to packaging."
            ),
        }

    if status == READY:
        return {
            "disposition": SUPERVISOR_REVIEW_REQUIRED,
            "explanation": (
                "No actionable findings were detected, but no supervisor has confirmed this "
                "assessment yet — review is required before proceeding to packaging."
            ),
        }

    # Defensive fallback — never silently proceed on an unrecognized status.
    return {
        "disposition": SUPERVISOR_REVIEW_REQUIRED,
        "explanation": f"Unrecognized readiness status '{status}' — routed to supervisor review as a safe default.",
    }
