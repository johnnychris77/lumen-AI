"""Project Sage, Section 2: Competency Taxonomy.

Thin accessor over `app.models.sage_education.COMPETENCY_TAXONOMY` plus a
mapping from real, already-recognized signal (finding_type strings,
SupervisorReview correction fields) onto the taxonomy leaf it evidences --
mirrors `vulcan_failure_taxonomy_service`'s classify-don't-fabricate pattern.
"""
from __future__ import annotations

from app.models.sage_education import (
    COMPETENCY_ANATOMY_ZONE_LABELING_DOC,
    COMPETENCY_BLOOD,
    COMPETENCY_BONE,
    COMPETENCY_CORROSION,
    COMPETENCY_DEBRIS,
    COMPETENCY_DISCOLORATION,
    COMPETENCY_INSPECTION_COVERAGE,
    COMPETENCY_INSTRUMENT_FAMILY_RECOGNITION,
    COMPETENCY_MISSING_COMPONENTS,
    COMPETENCY_ORGANIC_RESIDUE,
    COMPETENCY_RUST,
    COMPETENCY_TAXONOMY,
    COMPETENCY_TISSUE,
)

# Real finding_type strings (the CV pipeline's actual vocabulary, see
# baseline_comparison_scoring_service.KPI_LABELS) mapped onto the contamination/
# condition competency leaf they evidence.
_FINDING_TYPE_TO_COMPETENCY: dict[str, str] = {
    "blood": COMPETENCY_BLOOD,
    "bone": COMPETENCY_BONE,
    "tissue": COMPETENCY_TISSUE,
    "other_organic_residue": COMPETENCY_ORGANIC_RESIDUE,
    "debris": COMPETENCY_DEBRIS,
    "rust": COMPETENCY_RUST,
    "discoloration": COMPETENCY_DISCOLORATION,
    "corrosion": COMPETENCY_CORROSION,
    "missing_component": COMPETENCY_MISSING_COMPONENTS,
}

# SupervisorReview boolean-correction fields mapped onto the competency
# domain a `False` value (a supervisor correction) evidences.
_SUPERVISOR_FIELD_TO_COMPETENCY: dict[str, str] = {
    "zone_correct": COMPETENCY_ANATOMY_ZONE_LABELING_DOC,
    "instrument_family_correct": COMPETENCY_INSTRUMENT_FAMILY_RECOGNITION,
    "image_view_correct": COMPETENCY_INSPECTION_COVERAGE,
}

_LEAF_TO_DOMAIN: dict[str, str] = {
    leaf: domain for domain, leaves in COMPETENCY_TAXONOMY.items() for leaf in leaves
}


def taxonomy_tree() -> dict:
    return {"domains": COMPETENCY_TAXONOMY}


def domain_for_leaf(leaf: str) -> str:
    return _LEAF_TO_DOMAIN.get(leaf, "")


def competency_for_finding_type(finding_type: str) -> str | None:
    return _FINDING_TYPE_TO_COMPETENCY.get((finding_type or "").strip().lower())


def competency_for_supervisor_field(field_name: str) -> str | None:
    return _SUPERVISOR_FIELD_TO_COMPETENCY.get(field_name)
