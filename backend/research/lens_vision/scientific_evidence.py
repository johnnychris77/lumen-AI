"""Scientific evidence contract (Stage 5C).

Captures independently-verified LABORATORY evidence for a research observation and
links it to an AI-detected anomaly WITHOUT ever letting the anomaly become a
confirmed material identity or a clinical disposition. Four layers are kept
strictly separate:

  1. AI-detected anomaly          (research-only, uncalibrated spatial signal)
  2. Human visual interpretation  (a reviewer's opinion; not confirmation)
  3. Laboratory-confirmed identity (independently verified material/condition)
  4. Clinical instrument disposition (NEVER produced here)

An image anomaly never automatically becomes confirmed corrosion / blood / tissue
/ pitting. Category-appropriate laboratory evidence is REQUIRED before a material
identity may be recorded, and even then the AI↔material relationship defaults to
``indeterminate`` until an authorized reviewer links them. No oxidation-color
staging or biological-age inference from RGB appearance is permitted.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict

# ── Evidence categories (research mapping; NOT clinical taxonomy classes) ────
CORROSION_LIKE = "corrosion_like_surface"
PITTING_LOCALIZED = "localized_pitting"
BLOOD_LIKE_RESIDUE = "blood_like_residue"
BONE_TISSUE_LIKE = "bone_or_tissue_like_particle"
VERIFIED_NORMAL_SURFACE = "verified_normal_surface"
CONFOUNDING_SURFACE = "confounding_surface"

EVIDENCE_CATEGORIES = frozenset({
    CORROSION_LIKE, PITTING_LOCALIZED, BLOOD_LIKE_RESIDUE, BONE_TISSUE_LIKE,
    VERIFIED_NORMAL_SURFACE, CONFOUNDING_SURFACE,
})

# The four separated evidence layers.
LAYER_AI_ANOMALY = "ai_detected_anomaly"
LAYER_HUMAN_INTERPRETATION = "human_visual_interpretation"
LAYER_LAB_IDENTITY = "laboratory_confirmed_identity"
LAYER_CLINICAL_DISPOSITION = "clinical_instrument_disposition"

# Relationship between an AI anomaly region and laboratory evidence.
REL_INDETERMINATE = "indeterminate"
REL_SUPPORTED = "supported_by_reviewer"   # set ONLY by an authorized human link
REL_CONTRADICTED = "contradicted_by_reviewer"


class EvidenceValidationError(ValueError):
    """Laboratory evidence is missing a category-appropriate requirement."""


class ForbiddenInferenceError(RuntimeError):
    """An attempt to infer material identity/age from RGB appearance alone."""


@dataclass
class LaboratoryEvidence:
    """Independently-verified laboratory evidence for one research image/region."""

    # Image + physical identity
    image_id: object
    image_sha256: str
    instrument_id: str
    specimen_id: str
    imaging_session_id: str

    # Material / anatomy
    evidence_category: str
    material_type: str
    instrument_anatomy: str

    # Source + method
    source_laboratory: str
    study_id: str
    reference_method: str

    # Independently verified identity / condition + measurement
    verified_material_identity: str = ""
    physical_condition: str = ""
    measurement_value: float | None = None
    measurement_units: str = ""
    measurement_uncertainty: float | str | None = None  # number, "unknown", or None — never fabricated 0

    # Spatial linkage
    mask_ref: str = ""
    spatial_annotation_ref: str = ""

    # Review + approval
    reviewer_id: str = ""
    verification_status: str = "pending"   # pending | verified | rejected
    approval_evidence_ref: str = ""

    # Governance
    data_rights: str = ""
    retention_status: str = ""
    provenance_class: str = ""

    # Honesty
    limitations: list[str] = field(default_factory=list)
    unresolved_ambiguities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# Category-appropriate requirements. Each entry lists required reference methods
# (any-of) and whether a quantitative measurement is required.
_METHODS = {
    CORROSION_LIKE: {"methods": {"eds", "xrd", "sem_eds", "material_characterization"}, "needs_measurement": True,
                     "measurement": "affected_area"},
    PITTING_LOCALIZED: {"methods": {"optical_microscopy", "sem", "profilometry", "confocal_microscopy"},
                        "needs_measurement": True, "measurement": "pit_geometry"},
    BLOOD_LIKE_RESIDUE: {"methods": {"protein_assay", "hemoglobin_assay", "elisa", "soil_identity_confirmation"},
                         "needs_measurement": False, "needs_identity": True},
    BONE_TISSUE_LIKE: {"methods": {"histology", "composition_analysis", "ftir", "independently_verified_particle_id"},
                       "needs_measurement": False, "needs_identity": True},
    VERIFIED_NORMAL_SURFACE: {"methods": {"independent_review", "reference_standard", "material_characterization"},
                              "needs_measurement": False},
    CONFOUNDING_SURFACE: {"methods": {"independent_review", "reference_standard", "material_characterization"},
                          "needs_measurement": False},
}


def _uncertainty_ok(u) -> bool:
    """Uncertainty must be present and NOT fabricated: a finite non-negative
    number, or the explicit strings 'unknown'/'not_measured', or None."""
    if u is None:
        return True
    if isinstance(u, str):
        return u.strip().lower() in {"unknown", "not_measured"}
    if isinstance(u, (int, float)):
        return math.isfinite(u) and u >= 0
    return False


def validate_evidence(evidence: LaboratoryEvidence) -> list[str]:
    """Return a list of reasons the evidence is not category-appropriate (empty =
    valid). Does not raise — callers decide."""
    reasons: list[str] = []
    cat = evidence.evidence_category
    if cat not in EVIDENCE_CATEGORIES:
        return [f"unknown_evidence_category:{cat}"]
    spec = _METHODS[cat]

    for fld in ("image_sha256", "instrument_id", "specimen_id", "source_laboratory", "study_id", "reference_method"):
        if not str(getattr(evidence, fld) or "").strip():
            reasons.append(f"missing_{fld}")

    if (evidence.reference_method or "").strip().lower() not in spec["methods"]:
        reasons.append(f"reference_method_not_appropriate_for_{cat}")

    if spec.get("needs_measurement"):
        if evidence.measurement_value is None or not str(evidence.measurement_units or "").strip():
            reasons.append(f"missing_quantitative_{spec.get('measurement', 'measurement')}")
        elif not (isinstance(evidence.measurement_value, (int, float)) and math.isfinite(evidence.measurement_value)):
            reasons.append("measurement_value_not_finite")
    if spec.get("needs_identity") and not str(evidence.verified_material_identity or "").strip():
        reasons.append("missing_verified_material_identity")

    if not _uncertainty_ok(evidence.measurement_uncertainty):
        reasons.append("uncertainty_missing_or_nonfinite_or_fabricated")

    if evidence.verification_status not in {"pending", "verified", "rejected"}:
        reasons.append("invalid_verification_status")
    return reasons


def is_lab_confirmed(evidence: LaboratoryEvidence) -> bool:
    """True only when evidence is category-appropriate AND verified by a reviewer
    with approval evidence. This is the ONLY route to a confirmed material identity
    — never the AI anomaly."""
    return (
        not validate_evidence(evidence)
        and evidence.verification_status == "verified"
        and bool((evidence.reviewer_id or "").strip())
        and bool((evidence.approval_evidence_ref or "").strip())
    )


@dataclass
class ScientificObservation:
    """Keeps the four evidence layers separate for one research observation."""

    ai_anomaly: dict                      # layer 1 (a research-only AnomalyResult dict)
    human_interpretation: str = ""        # layer 2 (reviewer opinion; not confirmation)
    laboratory_evidence: dict | None = None   # layer 3 (verified lab identity, if any)
    ai_to_material_relationship: str = REL_INDETERMINATE
    confirmed_material_identity: str | None = None   # ONLY from verified lab evidence
    clinical_disposition: None = None     # layer 4 — NEVER produced here
    research_only: bool = True
    clinical_promotion_eligible: bool = False
    confirmed_diagnosis: None = None
    human_review_required: bool = True
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def link_observation(
    ai_anomaly: dict, *, laboratory_evidence: LaboratoryEvidence | None = None,
    human_interpretation: str = "", reviewer_linked: bool = False,
) -> ScientificObservation:
    """Assemble a scientific observation that keeps the four layers separate.

    The AI↔material relationship defaults to ``indeterminate``. A confirmed
    material identity is recorded ONLY when (a) the lab evidence is verified AND
    (b) an authorized reviewer explicitly links it (``reviewer_linked``). The AI
    anomaly alone can never confirm an identity or produce a disposition.
    """
    obs = ScientificObservation(ai_anomaly=dict(ai_anomaly), human_interpretation=human_interpretation)
    if laboratory_evidence is not None:
        obs.laboratory_evidence = laboratory_evidence.to_dict()
        obs.limitations = list(laboratory_evidence.limitations) + list(laboratory_evidence.unresolved_ambiguities)
        if reviewer_linked and is_lab_confirmed(laboratory_evidence):
            obs.ai_to_material_relationship = REL_SUPPORTED
            obs.confirmed_material_identity = (
                laboratory_evidence.verified_material_identity or laboratory_evidence.physical_condition or None
            )
        else:
            obs.ai_to_material_relationship = REL_INDETERMINATE
    return obs


def infer_identity_from_rgb(*_args, **_kwargs):
    """FORBIDDEN: material identity, oxidation stage, or biological age may never be
    inferred from RGB appearance. This exists to document and enforce the ban."""
    raise ForbiddenInferenceError(
        "Material identity / oxidation stage / biological age must not be inferred from RGB "
        "appearance. Use independently-verified laboratory evidence (validate_evidence)."
    )
