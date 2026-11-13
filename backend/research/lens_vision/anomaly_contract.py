"""Research-only spatial anomaly output contract (Stage 5B).

Extends the Stage 5A ``AnomalyRegion`` into a full result record for a localized
anomaly experiment, WITHOUT introducing any clinical-interpretation pathway. Every
result is research-only, carries no diagnosis, keeps uncertainty explicit (unknown
when unmeasured — never fabricated as zero), and requires human review. These
outputs must never enter technician-facing recommendations, the Lumen Decision
Engine, model deployment, or OEM intelligence.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

# Re-export the Stage 5A region + guard so callers have one import site.
from research.lens_vision.anomaly_feasibility import (  # noqa: F401
    AnomalyRegion,
    ClinicalDiagnosisForbiddenError,
    describe_region,
)

# Sentinel for an uncertainty that has NOT been measured. It is never 0.0.
UNCERTAINTY_UNKNOWN = "unknown"
CALIBRATION_UNCALIBRATED = "uncalibrated"


@dataclass
class AnomalyResult:
    """A research-only localized-anomaly result for one image."""

    # Source + provenance
    source_image_id: Any
    source_image_sha256: str
    provenance_class: str
    provenance_source_id: str
    tenant_id: str

    # Model identity (reproducibility)
    model_architecture: str
    checkpoint_id: str
    checkpoint_digest: str
    research_run_id: str
    run_version: str              # config fingerprint

    # Scores + spatial output
    image_level_anomaly_score: float
    heatmap_ref: str              # reference/id to the stored heatmap (not embedded)
    heatmap_shape: tuple[int, int]
    proposed_regions: list[dict] = field(default_factory=list)

    # Calibration + uncertainty (explicit; unknown when unmeasured)
    calibration_status: str = CALIBRATION_UNCALIBRATED
    uncertainty_status: str = UNCERTAINTY_UNKNOWN

    # Grouping / validation limitations
    grouping_reliable: bool = False
    validation_limitations: list[str] = field(default_factory=list)

    # Hard, constant research-only guarantees
    research_only: bool = True
    clinical_promotion_eligible: bool = False
    confirmed_diagnosis: None = None
    human_review_required: bool = True

    def to_dict(self) -> dict:
        d = asdict(self)
        d["note"] = (
            "RESEARCH ONLY — an uncertain, uncalibrated spatial anomaly signal. Not a "
            "diagnosis, severity score, or instrument-release decision. Must not enter "
            "clinical recommendations, the Lumen Decision Engine, deployment, or OEM intelligence."
        )
        return d


def build_anomaly_result(
    *, sample: dict, image_score: float, heatmap_shape: tuple[int, int], heatmap_ref: str,
    regions: list, config, record, grouping_reliable: bool,
    validation_limitations: list[str], uncertainty_status: str = UNCERTAINTY_UNKNOWN,
) -> AnomalyResult:
    """Assemble a research-only ``AnomalyResult`` from an experiment's pieces."""
    region_dicts = []
    for r in regions:
        if isinstance(r, AnomalyRegion):
            region_dicts.append(describe_region(r.x, r.y, r.width, r.height, r.anomaly_score, r.uncertainty))
        else:
            region_dicts.append(r)
    return AnomalyResult(
        source_image_id=sample.get("id"),
        source_image_sha256=sample.get("image_sha256", ""),
        provenance_class=sample.get("data_provenance_class", ""),
        provenance_source_id=sample.get("provenance_source_id", "") or sample.get("source_id", ""),
        tenant_id=sample.get("tenant_id", ""),
        model_architecture=getattr(record, "architecture", "") if record else "",
        checkpoint_id=config.checkpoint_id,
        checkpoint_digest=getattr(record, "expected_sha256", "") if record else "",
        research_run_id=config.run_id,
        run_version=config.fingerprint(),
        image_level_anomaly_score=image_score,
        heatmap_ref=heatmap_ref,
        heatmap_shape=heatmap_shape,
        proposed_regions=region_dicts,
        grouping_reliable=grouping_reliable,
        validation_limitations=list(validation_limitations),
        uncertainty_status=uncertainty_status,
    )
