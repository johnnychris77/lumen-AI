"""Stage 6C — traceable research review records (research-only).

A review record links, for one image, the four distinct Stage 5C layers and whether
the AI prediction matches / misses / conflicts with the approved ground truth. It is a
traceability artifact: it produces no diagnosis, no severity estimate, and no
instrument-release decision.

Four layers (kept distinct, per the contract):
  1. AI anomaly localization (model prediction + spatial mask reference)
  2. Expert visual interpretation (a reviewer's opinion)
  3. Independently-confirmed physical condition / material identity (laboratory)
  4. Clinical disposition — OUTSIDE the research system (never set here)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

# Outcome of comparing a prediction to approved ground truth.
MATCH = "match"
MISS = "miss"            # a real (ground-truth abnormal) finding the model did not flag (false negative)
CONFLICT = "conflict"    # the model flagged an anomaly where ground truth is verified-normal (false positive)
GT_UNAVAILABLE = "ground_truth_unavailable"

# Approved ground-truth labels this comparison understands.
GT_VERIFIED_NORMAL = "verified_normal"
GT_ABNORMAL = "abnormal"


def compare_prediction_to_ground_truth(
    *, predicted_positive: bool, ground_truth_label: str | None, lab_confirmed: bool = False,
) -> str:
    """Return whether a prediction matches / misses / conflicts with approved ground
    truth. Ground truth must be an independently-established label; a label that is not
    ``verified_normal`` or ``abnormal`` (or is absent) yields ``ground_truth_unavailable``
    — the comparison is never guessed. A positive abnormal label is trusted as truth
    only when ``lab_confirmed`` for categories that require it (caller decides)."""
    gt = (ground_truth_label or "").strip()
    if gt not in {GT_VERIFIED_NORMAL, GT_ABNORMAL}:
        return GT_UNAVAILABLE
    gt_positive = gt == GT_ABNORMAL and bool(lab_confirmed) if gt == GT_ABNORMAL else False
    # For abnormal ground truth not yet lab-confirmed, truth is not established.
    if gt == GT_ABNORMAL and not lab_confirmed:
        return GT_UNAVAILABLE
    if bool(predicted_positive) == gt_positive:
        return MATCH
    return MISS if gt_positive else CONFLICT


@dataclass
class ReviewRecord:
    """One traceable research review record (research-only)."""

    # Identity / traceability
    specimen_id: str
    image_id: object
    image_sha256: str
    modality: str = ""

    # Layer 1 — AI anomaly localization
    model_name: str = ""
    predicted_positive: bool = False
    anomaly_score: float | None = None
    spatial_mask_ref: str = ""

    # Layer 2 — expert visual interpretation
    human_visual_interpretation: str = ""
    visual_reviewer_id: str = ""

    # Layer 3 — independently-confirmed physical condition / identity (laboratory)
    laboratory_evidence_ref: str = ""
    lab_confirmed: bool = False
    confirmed_material_identity: str | None = None

    # Approved ground truth + comparison outcome
    approved_ground_truth_label: str | None = None
    outcome: str = GT_UNAVAILABLE

    # Layer 4 — clinical disposition: NEVER produced here
    clinical_disposition: None = None

    # Research invariants
    research_only: bool = True
    confirmed_diagnosis: None = None
    severity_estimate: None = None
    instrument_release_decision: None = None
    human_review_required: bool = True
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def build_review_record(
    *, specimen_id: str, image_id, image_sha256: str, modality: str = "",
    model_name: str, predicted_positive: bool, anomaly_score: float | None = None,
    spatial_mask_ref: str = "", human_visual_interpretation: str = "", visual_reviewer_id: str = "",
    lab_confirmation=None, approved_ground_truth_label: str | None = None,
    limitations: list[str] | None = None,
) -> ReviewRecord:
    """Assemble a traceable review record and compute the match/miss/conflict outcome.

    Laboratory confirmation must be a **resolved** object (an object with ``.confirmed``
    and ``.identity`` — see ``scientific_authorization.resolve_lab_confirmation``),
    **never an arbitrary boolean**. A confirmed material identity and the evidence
    reference are taken from that resolved object only; the AI prediction never
    establishes them. No diagnosis, severity, or release decision is produced.
    """
    confirmed = bool(getattr(lab_confirmation, "confirmed", False))
    identity = getattr(lab_confirmation, "identity", None) if confirmed else None
    evidence_id = getattr(lab_confirmation, "evidence_record_id", None)
    evidence_ref = f"veritas_evidence:{evidence_id}" if (confirmed and evidence_id is not None) else ""
    outcome = compare_prediction_to_ground_truth(
        predicted_positive=predicted_positive, ground_truth_label=approved_ground_truth_label,
        lab_confirmed=confirmed,
    )
    return ReviewRecord(
        specimen_id=specimen_id, image_id=image_id, image_sha256=image_sha256, modality=modality,
        model_name=model_name, predicted_positive=bool(predicted_positive), anomaly_score=anomaly_score,
        spatial_mask_ref=spatial_mask_ref, human_visual_interpretation=human_visual_interpretation,
        visual_reviewer_id=visual_reviewer_id, laboratory_evidence_ref=evidence_ref,
        lab_confirmed=confirmed, confirmed_material_identity=identity,
        approved_ground_truth_label=approved_ground_truth_label, outcome=outcome,
        limitations=list(limitations or []),
    )


def summarize_outcomes(records: list[ReviewRecord]) -> dict:
    """Aggregate outcomes, surfacing false negatives (misses) prominently. Reports
    counts only — never an accuracy claim or denominator that real data don't support."""
    counts = {MATCH: 0, MISS: 0, CONFLICT: 0, GT_UNAVAILABLE: 0}
    for r in records:
        counts[r.outcome] = counts.get(r.outcome, 0) + 1
    return {
        "n_records": len(records),
        "outcomes": counts,
        "false_negatives": counts[MISS],       # surfaced prominently
        "conflicts": counts[CONFLICT],
        "ground_truth_unavailable": counts[GT_UNAVAILABLE],
        "note": "Outcome counts only; not a scientific accuracy claim. Misses are "
                "potential false negatives for human review.",
    }
