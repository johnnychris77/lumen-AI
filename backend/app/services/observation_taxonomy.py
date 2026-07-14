"""LumenAI Observation Doctrine — Sections 1 & 2.

Defines the exactly-10 initial observation taxonomy categories and the
probability-based, visually-descriptive language LumenAI is permitted to
use. This module is the single source of truth other services import from
— it never fabricates a probability for a category the deployed model does
not evaluate, and it never describes a finding as a confirmed substance.

Maps the existing KPI vocabulary already computed by
`baseline_comparison_scoring_service` (CONTAMINATION_KPIS + CONDITION_KPIS)
onto this taxonomy — it does not re-detect anything itself.
"""
from __future__ import annotations

# ── Section 2 — the exactly-10 initial observation categories ──────────────
OBSERVATION_BLOOD_LIKE = "probable_blood_like_residue"
OBSERVATION_BONE_LIKE = "probable_bone_like_fragment"
OBSERVATION_TISSUE_OR_ORGANIC = "probable_tissue_or_organic_residue"
OBSERVATION_RETAINED_DEBRIS = "probable_retained_debris"
OBSERVATION_CORROSION_LIKE = "probable_corrosion_like_degradation"
OBSERVATION_LINT_OR_FIBER = "probable_lint_or_fiber"
OBSERVATION_PLASTIC_OR_INSULATION = "probable_plastic_or_insulation_fragment"
OBSERVATION_UNKNOWN_FOREIGN = "probable_unknown_foreign_material"
OBSERVATION_NO_ABNORMALITY = "no_observable_abnormality"
OBSERVATION_INSUFFICIENT_IMAGE = "insufficient_image_quality"

OBSERVATION_TAXONOMY = [
    OBSERVATION_BLOOD_LIKE, OBSERVATION_BONE_LIKE, OBSERVATION_TISSUE_OR_ORGANIC,
    OBSERVATION_RETAINED_DEBRIS, OBSERVATION_CORROSION_LIKE, OBSERVATION_LINT_OR_FIBER,
    OBSERVATION_PLASTIC_OR_INSULATION, OBSERVATION_UNKNOWN_FOREIGN,
    OBSERVATION_NO_ABNORMALITY, OBSERVATION_INSUFFICIENT_IMAGE,
]

# Categories the current model has no real detection signal for at all
# (no KPI in the existing scoring engine maps to them). Never scored —
# always reported as NOT_EVALUATED_BY_CURRENT_MODEL, never a fabricated
# zero probability.
NOT_EVALUATED_BY_CURRENT_MODEL = "NOT_EVALUATED_BY_CURRENT_MODEL"
UNSUPPORTED_OBSERVATION_CATEGORIES = [OBSERVATION_LINT_OR_FIBER]

# Section 1 — required display labels (probability language only, never a
# confirmed-substance claim).
DISPLAY_LABELS = {
    OBSERVATION_BLOOD_LIKE: "Probable blood-like organic residue",
    OBSERVATION_BONE_LIKE: "Probable bone-like fragment",
    OBSERVATION_TISSUE_OR_ORGANIC: "Probable tissue-like organic residue",
    OBSERVATION_RETAINED_DEBRIS: "Probable retained debris",
    OBSERVATION_CORROSION_LIKE: "Probable corrosion-like surface degradation",
    OBSERVATION_LINT_OR_FIBER: "Probable lint or fiber",
    OBSERVATION_PLASTIC_OR_INSULATION: "Probable plastic or insulation fragment",
    OBSERVATION_UNKNOWN_FOREIGN: "Probable unknown foreign material",
    OBSERVATION_NO_ABNORMALITY: "No observable abnormality within the model's validated scope",
    OBSERVATION_INSUFFICIENT_IMAGE: "Image insufficient for evaluation",
}

# Section 2 — maps the existing KPI vocabulary onto the taxonomy above. KPIs
# not listed here (crack, missing_component) are structural-integrity
# findings handled by the existing readiness/disposition engine, not the
# contamination observation taxonomy.
_KPI_TO_OBSERVATION = {
    "blood": OBSERVATION_BLOOD_LIKE,
    "bone": OBSERVATION_BONE_LIKE,
    "tissue": OBSERVATION_TISSUE_OR_ORGANIC,
    "other_organic_residue": OBSERVATION_TISSUE_OR_ORGANIC,
    "debris": OBSERVATION_RETAINED_DEBRIS,
    "rust": OBSERVATION_CORROSION_LIKE,
    "corrosion": OBSERVATION_CORROSION_LIKE,
    "discoloration": OBSERVATION_CORROSION_LIKE,
    "pitting": OBSERVATION_CORROSION_LIKE,
    "insulation_damage": OBSERVATION_PLASTIC_OR_INSULATION,
}

# "Contamination-like" observation categories the Section 4 safety rule
# applies to — a high baseline similarity must never cancel one of these.
CONTAMINATION_LIKE_CATEGORIES = {
    OBSERVATION_BLOOD_LIKE, OBSERVATION_BONE_LIKE, OBSERVATION_TISSUE_OR_ORGANIC,
    OBSERVATION_RETAINED_DEBRIS, OBSERVATION_UNKNOWN_FOREIGN,
}

# Structural-integrity KPIs — outside the contamination taxonomy above,
# these still flow into the Decision Engine's recommendation via the
# existing readiness/disposition engine's own honest vocabulary.
STRUCTURAL_KPIS = {"crack", "missing_component"}

# Section 1 — permitted visual appearance attributes (descriptive only,
# never a laboratory conclusion or an age estimate).
PERMITTED_APPEARANCE_ATTRIBUTES = [
    "red", "dark red", "red-brown", "dark brown", "dried-appearing",
    "crusted", "smeared", "particulate", "fibrous", "adherent",
]

# Section 17 — preferred vs. avoided legal/safety language.
PREFERRED_TERMS = [
    "probable", "observed", "visually consistent with", "suspected",
    "requires review", "recommended", "baseline similarity",
    "baseline deviation", "image insufficient",
]
AVOIDED_TERMS = [
    "confirmed blood", "definitely contaminated", "sterile",
    "safe for patient use", "clinically cleared", "guaranteed clean",
    "diagnosis", "exact age of residue",
]


# LCID Sprint 1 (Clinical Image Dataset) specified this same taxonomy using
# slightly different identifiers for two categories. Rather than run a
# second, competing taxonomy for dataset annotation, this maps those
# spec-literal names onto the canonical categories above — annotation tools
# should accept either spelling and always store the canonical one.
LCID_SPEC_ALIASES = {
    "probable_bone_fragment": OBSERVATION_BONE_LIKE,
    "probable_plastic_fragment": OBSERVATION_PLASTIC_OR_INSULATION,
}


def canonical_observation_category(name: str) -> str:
    """Resolve either the canonical category name or an LCID-spec alias to
    the canonical `OBSERVATION_*` value. Unknown names are returned
    unchanged so callers can decide how to handle them (never silently
    dropped)."""
    return LCID_SPEC_ALIASES.get(name, name)


def kpi_to_observation_category(kpi: str) -> str | None:
    """Map an existing scoring-engine KPI key onto the observation taxonomy.

    Returns None for KPIs that are structural (crack, missing_component) —
    those are not contamination observations and are handled separately."""
    return _KPI_TO_OBSERVATION.get(kpi)


def is_unsupported_category(category: str) -> bool:
    return category in UNSUPPORTED_OBSERVATION_CATEGORIES


def display_label(category: str | None) -> str:
    if category is None:
        return NOT_EVALUATED_BY_CURRENT_MODEL
    return DISPLAY_LABELS.get(category, category)
