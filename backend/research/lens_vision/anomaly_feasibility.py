"""PatchCore / PaDiM anomaly-localization feasibility (research-only).

This module carries a *programmatic* feasibility assessment (so it can be asserted
in tests and surfaced in docs) and a hard guard ensuring that any anomaly output
stays research-only, retains uncertainty, and is NEVER auto-converted into a
confirmed clinical diagnosis (rust / blood / pitting / etc.).
"""
from __future__ import annotations

from dataclasses import dataclass

# Methods are implemented in the open-source Anomalib library (Apache-2.0); both
# train on NORMAL images and localize anomalies without per-pixel defect labels —
# a pragmatic fit for stainless-steel instrument surfaces where defect masks are
# scarce. Numbers below are qualitative design notes, not benchmarked claims.
METHOD_ASSESSMENT = {
    "patchcore": {
        "supervision": "normal-only (unsupervised)",
        "localization": "pixel-level anomaly map via nearest-neighbour to a coreset memory bank",
        "strengths": "strong pixel localization; few-normal-shot friendly via coreset subsampling",
        "costs": "memory bank storage; inference nearest-neighbour cost grows with bank size",
        "library": "Anomalib (Apache-2.0)",
    },
    "padim": {
        "supervision": "normal-only (unsupervised)",
        "localization": "per-location multivariate-Gaussian Mahalanobis distance",
        "strengths": "simple, fast, low-memory; a solid baseline",
        "costs": "position-wise Gaussian can be less accurate than PatchCore on fine defects",
        "library": "Anomalib (Apache-2.0)",
    },
}


def feasibility_assessment() -> dict:
    """Structured recommendation for the Stage 5B anomaly-localization prototype."""
    return {
        "research_only": True,
        "methods": METHOD_ASSESSMENT,
        "recommended_first_prototype": "padim",
        "recommended_target": "patchcore",
        "rationale": (
            "Start with PaDiM as a fast, low-memory normal-only baseline on "
            "laboratory/synthetic stainless-steel images; graduate to PatchCore for "
            "stronger pixel localization. Both avoid the per-pixel defect labels we "
            "do not yet have."
        ),
        "data_status": "awaiting_qualified_image_data",
        "blocking_requirements": [
            "verified commercial/clinical image rights for any external stainless-steel dataset",
            "a governed set of NORMAL (no_observable_abnormality) instrument images",
            "PyTorch + Anomalib installed in an isolated research environment",
        ],
        "guardrails": [
            "anomaly regions are NOT diagnoses; they retain uncertainty",
            "no automatic mapping from an anomaly region to a clinical taxonomy class",
            "research-only; never servable or clinically promotable",
        ],
    }


class ClinicalDiagnosisForbiddenError(RuntimeError):
    """Raised on any attempt to turn a research anomaly region into a clinical finding."""


@dataclass(frozen=True)
class AnomalyRegion:
    """A research-only localized anomaly: a score and bounds, with NO diagnosis."""

    x: float
    y: float
    width: float
    height: float
    anomaly_score: float          # higher = more anomalous (uncalibrated)
    uncertainty: float            # retained, never dropped
    research_only: bool = True
    confirmed_diagnosis: None = None  # always None — never a clinical class

    def to_clinical_label(self) -> str:  # pragma: no cover - must never succeed
        raise ClinicalDiagnosisForbiddenError(
            "A research anomaly region can never be converted to a confirmed clinical "
            "diagnosis (rust/blood/pitting/etc.). It remains an uncertain, research-only signal."
        )


def describe_region(x, y, width, height, anomaly_score, uncertainty) -> dict:
    """Build a research-only region descriptor that keeps uncertainty and carries
    no clinical diagnosis."""
    return {
        "x": x, "y": y, "width": width, "height": height,
        "anomaly_score": anomaly_score,
        "uncertainty": uncertainty,
        "research_only": True,
        "confirmed_diagnosis": None,
        "note": "Research-only anomaly signal; not a clinical finding.",
    }
