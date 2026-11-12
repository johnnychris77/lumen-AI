"""Research-only provenance gate (reuses the Stage 4 governance contract).

Research experiments may ONLY consume research-authorized data — synthetic,
external non-clinical, or laboratory-controlled — plus (read-only) real clinical
data that has been explicitly approved through the Stage 4 governance path. In no
case may a research artifact be clinically promoted: this gate is one direction of
that guarantee (the serving/promotion gates in ``app`` are the others).

External and laboratory images can never automatically qualify for clinical model
promotion; that is enforced here (``is_clinically_promotable`` is always False for
a research artifact) and in ``app.services.ml`` (clinical promotion requires
verified ``real_clinical`` + approval + reliable grouping).
"""
from __future__ import annotations

from app.models.dataset_governance import (
    PROVENANCE_APPROVAL_APPROVED,
    PROVENANCE_EXTERNAL_NONCLINICAL,
    PROVENANCE_LABORATORY_CONTROLLED,
    PROVENANCE_REAL_CLINICAL,
    PROVENANCE_SYNTHETIC_EXPERIMENTAL,
)
from app.services.ml.provenance_governance import normalize_provenance_class

# Provenance classes a research EXPERIMENT may consume. real_clinical is NOT here:
# clinical data belongs to the governed clinical-validation track, not open
# research experimentation, unless separately approved (see
# ``assert_research_authorized(allow_approved_clinical=...)``).
RESEARCH_AUTHORIZED_CLASSES = frozenset({
    PROVENANCE_SYNTHETIC_EXPERIMENTAL,
    PROVENANCE_EXTERNAL_NONCLINICAL,
    PROVENANCE_LABORATORY_CONTROLLED,
})


class ResearchProvenanceError(PermissionError):
    """A sample whose provenance is not authorized for research use."""


def sample_provenance_class(sample: dict) -> str:
    """Normalized provenance class of a sample (fail-closed to legacy_unverified)."""
    return normalize_provenance_class(sample.get("data_provenance_class"))


def is_research_authorized(sample: dict, *, allow_approved_clinical: bool = False) -> bool:
    """True iff the sample may enter a research experiment.

    Non-clinical research classes are always allowed. Real clinical data is
    allowed only when ``allow_approved_clinical`` is set AND it is actually
    approved — and even then the output is never clinically promotable from here.
    Unknown / legacy / unapproved data is refused (fail-closed).
    """
    cls = sample_provenance_class(sample)
    if cls in RESEARCH_AUTHORIZED_CLASSES:
        return True
    if (
        allow_approved_clinical
        and cls == PROVENANCE_REAL_CLINICAL
        and sample.get("provenance_approval_status") == PROVENANCE_APPROVAL_APPROVED
    ):
        return True
    return False


def assert_research_authorized(samples, *, allow_approved_clinical: bool = False) -> None:
    """Raise ``ResearchProvenanceError`` if any sample is not research-authorized."""
    for idx, s in enumerate(samples):
        if not is_research_authorized(s, allow_approved_clinical=allow_approved_clinical):
            raise ResearchProvenanceError(
                f"Sample {idx} (provenance_class='{sample_provenance_class(s)}') is not "
                "authorized for research use. Only synthetic / external_nonclinical / "
                "laboratory_controlled — or explicitly approved real_clinical — may be used."
            )


def is_clinically_promotable(_artifact: dict | None = None) -> bool:
    """A research artifact is NEVER clinically promotable, regardless of inputs.

    This is a hard, constant guarantee for the research track; clinical promotion
    is only ever decided by the governed clinical pipeline on verified
    real_clinical + approved + reliably-grouped cohorts.
    """
    return False
