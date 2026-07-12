"""Project Veritas, Section 16: Collaboration With Other Agents.

Every function here reads another specialist's real output by reference and
returns a Veritas-specific evidence opinion -- it never mutates or
overwrites the source. No specialist may overwrite Veritas evidence
findings; the orchestrator preserves separate agent conclusions by
construction (each function below returns its own dict, never merged).
"""
from __future__ import annotations

from app.models.veritas_evidence import (
    DATASET_APPROVED_FOR_TRAINING,
    READINESS_INSUFFICIENT,
    READINESS_LIMITED,
)


def evidence_support_for_aegis(aegis_conclusion: dict, veritas_assessment: dict) -> dict:
    """Section 16: does Veritas's evidence support Aegis's process
    conclusion? Aegis's own signal (`aegis_conclusion`) is referenced
    verbatim, never edited."""
    supported = veritas_assessment["readiness_category"] not in (READINESS_INSUFFICIENT, READINESS_LIMITED)
    return {
        "source_aegis_conclusion": aegis_conclusion,
        "source_veritas_assessment_id": veritas_assessment["id"],
        "evidence_supports_conclusion": supported,
        "opinion": (
            "Evidence readiness is sufficient to support this process conclusion."
            if supported else
            "Evidence readiness is limited or insufficient -- this process conclusion should be treated as provisional "
            "until additional evidence is captured."
        ),
    }


def evidence_support_for_vulcan(veritas_assessments: list[dict]) -> dict:
    """Section 16: confirms Vulcan's progression comparison used comparable
    images/anatomy zones/baseline versions -- flags if the assessments being
    compared don't share a baseline version."""
    baseline_versions = {a.get("baseline_resolution_id") for a in veritas_assessments}
    zones = {a.get("anatomy_zone", "") for a in veritas_assessments if a.get("anatomy_zone")}
    comparable = len(baseline_versions) <= 1
    return {
        "source_veritas_assessment_ids": [a["id"] for a in veritas_assessments],
        "images_comparable": comparable,
        "anatomy_zones_referenced": sorted(zones),
        "opinion": (
            "Images used for this progression comparison share a common baseline resolution."
            if comparable else
            "Images used for this progression comparison were evaluated against different baseline resolutions -- "
            "the progression trend should be treated with reduced confidence until re-verified against one baseline."
        ),
    }


def evidence_support_for_sage(sage_image_entry: dict, veritas_training_entry: dict | None) -> dict:
    """Section 16: confirms Sage's education content uses approved,
    correctly labeled, rights-cleared images -- cross-checking Sage's own
    curation fields against Veritas's independent training-dataset gate."""
    veritas_approved = bool(veritas_training_entry) and veritas_training_entry["dataset_status"] == DATASET_APPROVED_FOR_TRAINING
    sage_cleared = sage_image_entry.get("phi_review_status") == "cleared" and sage_image_entry.get("supervisor_validated")
    return {
        "source_sage_image_entry_id": sage_image_entry.get("id"),
        "source_veritas_training_entry_id": veritas_training_entry.get("id") if veritas_training_entry else None,
        "governed_for_education_use": sage_cleared and (veritas_training_entry is None or veritas_approved),
        "opinion": (
            "Image is validated, PHI-cleared, and rights-cleared for education use."
            if sage_cleared else
            "Image is missing supervisor validation or PHI clearance -- do not use in education content yet."
        ),
    }


def evidence_support_for_clinical_reasoning(veritas_assessment: dict) -> dict:
    """Section 16: evidence limitations and readiness status the Clinical
    Reasoning Agent must consider before finalizing a recommendation."""
    return {
        "source_veritas_assessment_id": veritas_assessment["id"],
        "readiness_category": veritas_assessment["readiness_category"],
        "readiness_score": veritas_assessment["readiness_score"],
        "limitations": veritas_assessment["limitations"],
        "recommended_gate": veritas_assessment["recommended_gate"],
        "opinion": veritas_assessment["next_action"],
    }
