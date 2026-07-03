"""Phase 23 §4 — Inspection State Machine.

Formal states every inspection passes through, derived honestly from real
persisted fields — never fabricated timestamps for states that happen
synchronously inside one scoring call and therefore have no distinct
historical record. See docs/cios/inspection-state-machine.md for exactly
which states can be individually timestamped vs. which are reported as
"reached" without a separate historical timestamp.
"""
from __future__ import annotations

INSPECTION_STATES = [
    "NEW",
    "IMAGE_CAPTURED",
    "INSTRUMENT_IDENTIFIED",
    "ANATOMY_IDENTIFIED",
    "BASELINE_LOADED",
    "COVERAGE_VALIDATED",
    "ANALYZED",
    "CLINICAL_REVIEW",
    "SUPERVISOR_PENDING",
    "APPROVED",
    "REQUIRES_ACTION",
    "COMPLETE",
]

# Valid forward transitions. APPROVED/REQUIRES_ACTION are the only branch
# point; both lead to COMPLETE.
_TRANSITIONS: dict[str, list[str]] = {
    "NEW": ["IMAGE_CAPTURED"],
    "IMAGE_CAPTURED": ["INSTRUMENT_IDENTIFIED"],
    "INSTRUMENT_IDENTIFIED": ["ANATOMY_IDENTIFIED"],
    "ANATOMY_IDENTIFIED": ["BASELINE_LOADED"],
    "BASELINE_LOADED": ["COVERAGE_VALIDATED"],
    "COVERAGE_VALIDATED": ["ANALYZED"],
    "ANALYZED": ["CLINICAL_REVIEW"],
    "CLINICAL_REVIEW": ["SUPERVISOR_PENDING"],
    "SUPERVISOR_PENDING": ["APPROVED", "REQUIRES_ACTION"],
    "APPROVED": ["COMPLETE"],
    "REQUIRES_ACTION": ["COMPLETE"],
    "COMPLETE": [],
}


def is_valid_transition(from_state: str, to_state: str) -> bool:
    return to_state in _TRANSITIONS.get(from_state, [])


def derive_state(inspection, review=None) -> dict:
    """Derive the current state and the ordered list of states reached so
    far, from real persisted Inspection/SupervisorReview fields.

    Several states (INSTRUMENT_IDENTIFIED / ANATOMY_IDENTIFIED /
    BASELINE_LOADED / COVERAGE_VALIDATED) happen synchronously inside one
    scoring call in the current implementation and have no distinct
    persisted timestamp — they are reported as reached (not skipped) but
    without a fabricated individual timestamp. See
    docs/cios/inspection-state-machine.md.
    """
    branch: str | None = None  # "APPROVED" or "REQUIRES_ACTION", once known

    if not inspection.has_image and inspection.score_status == "pending":
        current = "NEW"
    elif inspection.score_status == "pending":
        current = "IMAGE_CAPTURED"
    elif inspection.score_status in ("scored", "supervisor_review_required"):
        current = "ANALYZED" if review is None else "CLINICAL_REVIEW"
        if inspection.supervisor_review_required or inspection.score_status == "supervisor_review_required":
            if review is None:
                current = "SUPERVISOR_PENDING"
        if review is not None:
            if review.override_action or review.agreement == "disagree":
                branch = "REQUIRES_ACTION"
            else:
                branch = "APPROVED"
            current = branch
        if inspection.status in ("reviewed", "closed") and review is not None:
            current = "COMPLETE"
    else:
        current = "NEW"

    linear_prefix = INSPECTION_STATES[:9]  # NEW .. SUPERVISOR_PENDING
    if current in linear_prefix:
        reached = linear_prefix[: linear_prefix.index(current) + 1]
    elif current == "COMPLETE":
        reached = linear_prefix + [branch or "APPROVED", "COMPLETE"]
    else:  # APPROVED or REQUIRES_ACTION
        reached = linear_prefix + [current]

    return {"current_state": current, "states_reached": reached}
