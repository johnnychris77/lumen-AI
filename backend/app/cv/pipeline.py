"""Multi-stage CV pipeline with persistence and P3 ranking integration."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.cv.image_validator import validate_image_url, validate_b64_payload
from app.cv.image_store import archive_image
from app.cv.registry import CVRegistry
from app.schemas.cv import BaselineCompareRequest, CVAnalysisRequest, CVInferenceResult


def run_analysis(req: CVAnalysisRequest, db: Session | None = None) -> CVInferenceResult:
    """Run full CV pipeline and persist result."""
    # R1: Validate image inputs at the API boundary
    warnings = list(validate_image_url(req.image_url))
    warnings += validate_b64_payload(req.image_data_b64)

    provider = CVRegistry.get_provider()
    result = provider.analyze(req)

    # Merge pipeline validation warnings into result
    if warnings:
        result = result.model_copy(update={"warnings": list(result.warnings) + warnings})

    # R7: Archive image for audit trail (noop unless IMAGE_STORE_BACKEND is set)
    archive = archive_image(
        image_bytes=None,
        image_url=req.image_url,
        inference_id=result.inference_id,
        tenant_id=req.tenant_id,
    )
    if archive.object_key:
        result = result.model_copy(update={"archived_image_key": archive.object_key})

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
    """Extract P3-compatible ranking request from CV inference result (single-finding)."""
    return result.ranking_inputs


def build_composite_ranking_request(result: CVInferenceResult) -> dict[str, Any] | None:
    """R3: Build a CompositeRankingRequest dict from all detected regions.

    Returns None when there are fewer than 2 regions (single-finding path
    is more appropriate in that case).
    """
    if not result.regions:
        return None

    base = result.ranking_inputs
    findings = [
        {
            "finding_category": r.finding_category,
            "severity": r.severity,
            "confidence_score": round(r.confidence, 4),
            "barcode_value": base.get("barcode_value", ""),
            "qr_code_value": base.get("qr_code_value", ""),
            "key_dot_value": base.get("key_dot_value", ""),
            "baseline_status": base.get("baseline_status", ""),
            "instrument_match_status": base.get("instrument_match_status", ""),
        }
        for r in result.regions
    ]
    return {
        "instrument_id": base.get("instrument_id"),
        "instrument_name": base.get("instrument_name", ""),
        "findings": findings,
        "tenant_id": result.tenant_id,
    }


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
        facility_id=getattr(result, "facility_id", ""),
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
        # R12: provider cost (populated by provider if known)
        provider_cost_usd=getattr(result, "provider_cost_usd", 0.0),
    )
    db.add(record)
    db.commit()
