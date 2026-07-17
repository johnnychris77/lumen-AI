"""Machine-readable inference-engine capability contract (Pilot Zero
Directive 002, Phase 8 — placeholder isolation).

Establishes the structural separation between the current deterministic
placeholder scorer and any future trained model, so a placeholder result
can never be silently treated as validated computer vision, approved as
Ground Truth, or counted in validated performance metrics.

This module is the single source of truth for the capability envelope.
Increment 1 (this change) introduces the contract and the placeholder
declaration; wiring every scoring path to stamp its result with a
capability block is tracked as the next controlled increment (see
docs/pilot-zero/directive-002/PLACEHOLDER_ISOLATION_POLICY.md).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

# Engine maturity ladder (ordered least → most capable).
ENGINE_PLACEHOLDER = "PLACEHOLDER"
ENGINE_EXPERIMENTAL_MODEL = "EXPERIMENTAL_MODEL"
ENGINE_CANDIDATE_MODEL = "CANDIDATE_MODEL"
ENGINE_TECHNICALLY_VALIDATED_MODEL = "TECHNICALLY_VALIDATED_MODEL"
ENGINE_PILOT_ELIGIBLE_MODEL = "PILOT_ELIGIBLE_MODEL"
ENGINE_PRODUCTION_MODEL = "PRODUCTION_MODEL"

VALIDATION_NOT_VALIDATED = "NOT_VALIDATED"


@dataclass(frozen=True)
class EngineCapability:
    """A result's capability envelope. All consumers (Ground Truth
    approval, performance reporting, export, UI) must read these flags
    rather than inferring capability from the presence of a score."""

    engine_type: str
    model_id: str | None
    model_version: str | None
    validation_status: str
    intended_use: str
    human_review_required: bool
    clinical_use_permitted: bool
    ground_truth_eligible: bool
    performance_reporting_eligible: bool

    def to_dict(self) -> dict:
        return asdict(self)


def placeholder_capability() -> EngineCapability:
    """The capability envelope for the deterministic placeholder scorer.

    Fixed, restrictive values — the placeholder is research-only and can
    never be presented as trained computer vision."""
    return EngineCapability(
        engine_type=ENGINE_PLACEHOLDER,
        model_id=None,
        model_version=None,
        validation_status=VALIDATION_NOT_VALIDATED,
        intended_use="research_and_engineering_only",
        human_review_required=True,
        clinical_use_permitted=False,
        ground_truth_eligible=False,
        performance_reporting_eligible=False,
    )


def is_ground_truth_eligible(capability: EngineCapability) -> bool:
    return bool(capability.ground_truth_eligible)


def is_performance_reporting_eligible(capability: EngineCapability) -> bool:
    return bool(capability.performance_reporting_eligible)


def assert_not_placeholder_for_ground_truth(capability: EngineCapability) -> None:
    """Guard for Ground Truth approval paths: refuse a placeholder-derived
    result. Raises ValueError so callers fail closed."""
    if capability.engine_type == ENGINE_PLACEHOLDER or not capability.ground_truth_eligible:
        raise ValueError(
            "Placeholder / non-validated engine output is not eligible to become "
            "approved Ground Truth."
        )
