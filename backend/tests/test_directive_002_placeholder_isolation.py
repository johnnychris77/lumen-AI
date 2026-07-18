"""Pilot Zero Directive 002, Phase 8 — placeholder isolation contract.

Pins the machine-readable capability envelope for the deterministic
placeholder scorer and the guard that keeps placeholder output out of
approved Ground Truth and validated performance reporting.
"""
import pytest

from app.security.engine_capability import (
    ENGINE_PLACEHOLDER,
    VALIDATION_NOT_VALIDATED,
    assert_not_placeholder_for_ground_truth,
    is_ground_truth_eligible,
    is_performance_reporting_eligible,
    placeholder_capability,
)


class TestPlaceholderCapability:
    def test_placeholder_declares_restrictive_capability(self):
        cap = placeholder_capability()
        assert cap.engine_type == ENGINE_PLACEHOLDER
        assert cap.validation_status == VALIDATION_NOT_VALIDATED
        assert cap.clinical_use_permitted is False
        assert cap.ground_truth_eligible is False
        assert cap.performance_reporting_eligible is False
        assert cap.human_review_required is True
        assert cap.intended_use == "research_and_engineering_only"

    def test_capability_is_machine_readable(self):
        d = placeholder_capability().to_dict()
        for field in (
            "engine_type", "model_id", "model_version", "validation_status",
            "intended_use", "human_review_required", "clinical_use_permitted",
            "ground_truth_eligible", "performance_reporting_eligible",
        ):
            assert field in d

    def test_placeholder_cannot_enter_ground_truth(self):
        cap = placeholder_capability()
        assert is_ground_truth_eligible(cap) is False
        with pytest.raises(ValueError):
            assert_not_placeholder_for_ground_truth(cap)

    def test_placeholder_cannot_qualify_for_performance_reporting(self):
        assert is_performance_reporting_eligible(placeholder_capability()) is False
