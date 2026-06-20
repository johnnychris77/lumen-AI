"""Multi-stage CV pipeline with persistence and P3 ranking integration."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.cv.registry import CVRegistry
from app.schemas.cv import BaselineCompareRequest, CVAnalysisRequest, CVInferenceResult


def run_analysis(req: CVAnalysisRequest, db: Session | None = None) -> CVInferenceResult:
    """Run full CV pipeline and persist result."""
    provider = CVRegistry.get_provider()
    result = provider.analyze(req)
    if db is not None:
        _persist(result, db)
    return result


def run_baseline_compare(req: BaselineCompareRequest, db: Session | None = None) -> CVInferenceResult:
    """Convenience wrapper for dedicated baseline comparison."""
    analysis_req = CVAnalysisRequest(
        image_url=req.inspection_image_url,
        context="baseline_comparison",
        instrument_name=req.instrument_name,
        instrument_category=req.instrument_category,
        baseline_image_url=req.baseline_image_url,
        tenant_id=req.tenant_id,
        requested_capabilities=["instrument_recognition", "baseline_comparison"],
    )
    return run_analysis(analysis_req, db=db)


def build_ranking_request_from_result(result: CVInferenceResult) -> dict[str, Any]:
    """Extract P3-compatible ranking request from CV inference result."""
    return result.ranking_inputs


def _persist(result: CVInferenceResult, db: Session) -> None:
    """Write inference result to DB for KPI queries and audit trail."""
    from app.models.cv_inference import CVInferenceRecord  # lazy to avoid circular import
    counts: dict[str, int] = {
        "blood": 0, "bone": 0, "tissue": 0, "corrosion": 0,
        "crack": 0, "insulation": 0, "residue": 0,
    }
    for roi in result.regions:
        cat = roi.finding_category.lower()
        if "blood" in cat:
            counts["blood"] += 1
        elif "bone" in cat:
            counts["bone"] += 1
        elif "tissue" in cat:
            counts["tissue"] += 1
        elif "corrosion" in cat:
            counts["corrosion"] += 1
        elif "crack" in cat:
            counts["crack"] += 1
        elif "insulation" in cat:
            counts["insulation"] += 1
        elif "debris" in cat or "bioburden" in cat or "residue" in cat:
            counts["residue"] += 1

    record = CVInferenceRecord(
        inference_id=result.inference_id,
        tenant_id=result.tenant_id,
        context=result.context,
        provider=result.provider,
        status=result.status,
        image_url=result.image_url,
        baseline_image_url=result.baseline_comparison.baseline_image_url if result.baseline_comparison else "",
        instrument_recognized=result.instrument_identity.recognized,
        instrument_name=result.instrument_identity.instrument_name,
        instrument_category=result.instrument_identity.instrument_category,
        instrument_confidence=result.instrument_identity.confidence,
        match_method=result.instrument_identity.match_method,
        barcode_value=result.identifier_reads.barcode_value,
        qr_value=result.identifier_reads.qr_value,
        key_dot_value=result.identifier_reads.key_dot_value,
        contamination_score=result.contamination_score,
        damage_score=result.damage_score,
        overall_cleanliness_score=result.overall_cleanliness_score,
        baseline_compared=result.baseline_comparison.compared if result.baseline_comparison else False,
        baseline_match_pct=result.baseline_comparison.match_pct if result.baseline_comparison else 0.0,
        baseline_verdict=result.baseline_comparison.verdict if result.baseline_comparison else "",
        finding_count=len(result.regions),
        blood_count=counts["blood"],
        bone_count=counts["bone"],
        tissue_count=counts["tissue"],
        corrosion_count=counts["corrosion"],
        crack_count=counts["crack"],
        insulation_count=counts["insulation"],
        residue_count=counts["residue"],
        result_json=result.model_dump_json(),
        processing_ms=result.processing_ms,
    )
    db.add(record)
    db.commit()
