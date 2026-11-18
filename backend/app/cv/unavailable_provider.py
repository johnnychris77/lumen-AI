"""P4.7.1 — the fail-closed CV provider (SCI-03).

Selected whenever no approved, integrity-verified model can run. It evaluates
nothing and says so: no regions, no scores, no confidence, no severity, no
instrument identity, no baseline verdict. It is never a "clean" result.
"""
from __future__ import annotations

import uuid

from app.ai.inference_gate import STATUS_AI_UNAVAILABLE, STATUS_FAILED
from app.cv.base import BaseCVProvider
from app.cv.evidence import EVIDENCE_AI_UNAVAILABLE, EVIDENCE_FAILED
from app.schemas.cv import (
    BaselineComparisonResult,
    CVAnalysisRequest,
    CVInferenceResult,
    IdentifierReads,
    InstrumentIdentity,
)

DEFAULT_REASON = "No approved computer-vision model is available on this deployment."


def unavailable_result(
    req: CVAnalysisRequest,
    *,
    reason: str,
    status: str = STATUS_AI_UNAVAILABLE,
    provider: str = "unavailable",
    model_versions: dict[str, str] | None = None,
    model_integrity: dict | None = None,
    warnings: list[str] | None = None,
) -> CVInferenceResult:
    """Build the explicit not-evaluated contract shared by every provider."""
    if status not in (STATUS_AI_UNAVAILABLE, STATUS_FAILED):
        raise ValueError("unavailable_result only builds ai_unavailable / failed results")
    return CVInferenceResult(
        inference_id=f"inf-{uuid.uuid4().hex[:12]}",
        status=status,
        context=req.context,
        tenant_id=req.tenant_id,
        facility_id=req.facility_id,
        instrument_identity=InstrumentIdentity(recognized=False, match_method="none"),
        identifier_reads=IdentifierReads(),
        regions=[],
        contamination_score=None,
        damage_score=None,
        overall_cleanliness_score=None,
        baseline_comparison=None,
        ranking_inputs={},
        provider=provider,
        model_versions=model_versions or {},
        processing_ms=0,
        image_url=req.image_url,
        error_message=reason,
        warnings=list(warnings or []),
        review_required=False,
        simulated=False,
        evidence_class=EVIDENCE_FAILED if status == STATUS_FAILED else EVIDENCE_AI_UNAVAILABLE,
        unavailable_reason=reason,
        model_integrity=model_integrity or {"verified": False},
        human_review_required=True,
    )


class UnavailableCVProvider(BaseCVProvider):
    """Never fabricates. Every method returns an explicit not-evaluated value."""

    def __init__(self, reason: str = DEFAULT_REASON, *, status: str = STATUS_AI_UNAVAILABLE):
        self.reason = reason
        self.status = status

    @property
    def provider_name(self) -> str:
        return "unavailable"

    @property
    def model_versions(self) -> dict[str, str]:
        return {}

    def analyze(self, req: CVAnalysisRequest) -> CVInferenceResult:
        return unavailable_result(req, reason=self.reason, status=self.status)

    def identify_instrument(self, image_url: str, instrument_hint: str = "") -> InstrumentIdentity:
        return InstrumentIdentity(recognized=False, match_method="none")

    def read_identifiers(self, image_url: str) -> IdentifierReads:
        return IdentifierReads()

    def compare_baseline(self, inspection_url: str, baseline_url: str) -> BaselineComparisonResult:
        return BaselineComparisonResult(compared=False, verdict="unavailable", comparison_method="unavailable")
