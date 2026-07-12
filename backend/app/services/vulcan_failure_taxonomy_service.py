"""Project Vulcan, Section 2: Instrument Failure Taxonomy.

Maps real `InspectionFinding.finding_type` strings (the actual detection
vocabulary logged by the CV pipeline -- "blood", "corrosion", "crack",
"insulation_damage", etc., see `baseline_comparison_scoring_service.CLEANING_KPIS`
and `KPI_LABELS`) onto Vulcan's more granular taxonomy leaves declared in
`app.models.vulcan_reliability.FAILURE_TAXONOMY`. Where the real detection
vocabulary is coarser than a taxonomy leaf (e.g. a single "corrosion" finding
type maps onto one specific leaf, not several), this is an honest one-to-one
or many-to-one mapping -- never a fabricated finer-grained classification the
CV pipeline never actually produced.
"""
from __future__ import annotations

from app.models.vulcan_reliability import (
    FAIL_ANATOMY_NOT_RECOGNIZED,
    FAIL_BENT_COMPONENT,
    FAIL_CORROSION,
    FAIL_CRACK,
    FAIL_DAMAGED_HINGE,
    FAIL_DAMAGED_O_RING,
    FAIL_DAMAGED_RATCHET,
    FAIL_DEBRIS,
    FAIL_DISCOLORATION,
    FAIL_IMAGE_QUALITY_LIMITATION,
    FAIL_INSUFFICIENT_EVIDENCE,
    FAIL_INSULATION_BREACH,
    FAIL_LOOSE_JOINT,
    FAIL_MISSING_COMPONENT,
    FAIL_ORGANIC_RESIDUE,
    FAIL_PITTING,
    FAIL_RETAINED_BLOOD,
    FAIL_RETAINED_BONE,
    FAIL_RUST,
    FAIL_TISSUE,
    FAILURE_TAXONOMY,
    TAXONOMY_GROUP_CLEANING,
    TAXONOMY_GROUP_CONDITION,
    TAXONOMY_GROUP_MECHANICAL,
    TAXONOMY_GROUP_UNKNOWN,
)

# Real `finding_type` strings actually produced by the CV/scoring pipeline
# (see CLEANING_KPIS/KPI_LABELS) mapped onto the closest Vulcan taxonomy leaf.
_FINDING_TYPE_TO_LEAF: dict[str, str] = {
    "blood": FAIL_RETAINED_BLOOD,
    "bone": FAIL_RETAINED_BONE,
    "tissue": FAIL_TISSUE,
    "other_organic_residue": FAIL_ORGANIC_RESIDUE,
    "debris": FAIL_DEBRIS,
    "rust": FAIL_RUST,
    "discoloration": FAIL_DISCOLORATION,
    "corrosion": FAIL_CORROSION,
    "pitting": FAIL_PITTING,
    "crack": FAIL_CRACK,
    "insulation_damage": FAIL_INSULATION_BREACH,
    "missing_component": FAIL_MISSING_COMPONENT,
    # additional real finding_type values seen elsewhere in the pipeline.
    "loose_joint": FAIL_LOOSE_JOINT,
    "damaged_hinge": FAIL_DAMAGED_HINGE,
    "damaged_ratchet": FAIL_DAMAGED_RATCHET,
    "bent_component": FAIL_BENT_COMPONENT,
    "damaged_o_ring": FAIL_DAMAGED_O_RING,
    "o_ring_wear": FAIL_DAMAGED_O_RING,
}

_LEAF_TO_GROUP: dict[str, str] = {
    leaf: group for group, leaves in FAILURE_TAXONOMY.items() for leaf in leaves
}


def classify_finding_type(finding_type: str) -> dict:
    """Classify a real `finding_type` string into a Vulcan taxonomy leaf/group.

    Falls back to the Unknown group (`insufficient_evidence`) rather than
    guessing at a fabricated classification for a finding_type not in the
    real vocabulary above.
    """
    leaf = _FINDING_TYPE_TO_LEAF.get((finding_type or "").strip().lower())
    if leaf is None:
        return {
            "finding_type": finding_type,
            "taxonomy_leaf": FAIL_INSUFFICIENT_EVIDENCE,
            "taxonomy_group": TAXONOMY_GROUP_UNKNOWN,
            "recognized": False,
        }
    return {
        "finding_type": finding_type,
        "taxonomy_leaf": leaf,
        "taxonomy_group": _LEAF_TO_GROUP.get(leaf, TAXONOMY_GROUP_UNKNOWN),
        "recognized": True,
    }


def taxonomy_tree() -> dict:
    """Full taxonomy for the forensics workspace's filter dropdowns."""
    return {"groups": FAILURE_TAXONOMY}


def is_cleaning_related(finding_type: str) -> bool:
    return classify_finding_type(finding_type)["taxonomy_group"] == TAXONOMY_GROUP_CLEANING


def is_condition_related(finding_type: str) -> bool:
    return classify_finding_type(finding_type)["taxonomy_group"] == TAXONOMY_GROUP_CONDITION


def is_mechanical(finding_type: str) -> bool:
    return classify_finding_type(finding_type)["taxonomy_group"] == TAXONOMY_GROUP_MECHANICAL


def image_quality_unknown(finding_type: str) -> bool:
    leaf = classify_finding_type(finding_type)["taxonomy_leaf"]
    return leaf in (FAIL_INSUFFICIENT_EVIDENCE, FAIL_IMAGE_QUALITY_LIMITATION, FAIL_ANATOMY_NOT_RECOGNIZED)
