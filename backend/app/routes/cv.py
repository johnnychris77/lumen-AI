"""Computer Vision API routes — P4."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.cv.pipeline import build_ranking_request_from_result, run_analysis, run_baseline_compare
from app.cv.registry import CVRegistry
from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth
from app.schemas.cv import (
    BaselineCompareRequest,
    CVAnalysisRequest,
    CVInferenceResult,
    CVKPISummary,
)
from app.schemas.ranking import RankingRequest
from app.services.ranking_engine import score_inspection

router = APIRouter(prefix="/api/enterprise/cv", tags=["computer-vision"])


@router.post("/analyze", response_model=CVInferenceResult)
def analyze_image(
    req: CVAnalysisRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Run the full CV pipeline on an inspection image.

    Stages executed (based on requested_capabilities):
    1. Instrument recognition
    2. Identifier reading (barcode / QR / KeyDot)
    3. Contamination detection (blood / bone / tissue / debris / bioburden)
    4. Damage detection (corrosion / crack / insulation / pitting / lumen blockage)
    5. Baseline comparison (if baseline_image_url provided)

    Returns a CVInferenceResult with ranking_inputs ready for
    POST /api/enterprise/ranking/score.
    """
    require_enterprise_auth(request)
    return run_analysis(req, db=db)


@router.post("/baseline-compare", response_model=CVInferenceResult)
def compare_to_baseline(
    req: BaselineCompareRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Compare an inspection image against a manufacturer/vendor baseline."""
    require_enterprise_auth(request)
    return run_baseline_compare(req, db=db)


@router.post("/analyze-and-rank", response_model=dict)
def analyze_and_rank(
    req: CVAnalysisRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Single-call convenience endpoint: CV analysis → P3 ranking score.

    Returns both the CVInferenceResult and the RankingResult so the
    frontend needs only one round-trip to get a complete inspection record.
    """
    require_enterprise_auth(request)
    cv_result = run_analysis(req, db=db)
    ranking_inputs = build_ranking_request_from_result(cv_result)
    ranking_req = RankingRequest(**ranking_inputs)
    ranking_result = score_inspection(ranking_req, db=db)

    return {
        "cv": cv_result.model_dump(),
        "ranking": ranking_result.model_dump(),
    }


@router.get("/inference/{inference_id}", response_model=CVInferenceResult)
def get_inference(
    inference_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Retrieve a stored CV inference result by ID."""
    from app.models.cv_inference import CVInferenceRecord
    require_enterprise_auth(request)
    record = (
        db.query(CVInferenceRecord)
        .filter(CVInferenceRecord.inference_id == inference_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Inference record not found")
    return CVInferenceResult.model_validate(json.loads(record.result_json))


@router.get("/history", response_model=list[dict])
def list_inference_history(
    request: Request,
    tenant_id: str = "demo-tenant",
    limit: int = 25,
    db: Session = Depends(get_db),
):
    """List recent CV inference records for a tenant."""
    from app.models.cv_inference import CVInferenceRecord
    require_enterprise_auth(request)
    limit = max(1, min(limit, 100))
    records = (
        db.query(CVInferenceRecord)
        .filter(CVInferenceRecord.tenant_id == tenant_id)
        .order_by(CVInferenceRecord.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "inference_id": r.inference_id,
            "context": r.context,
            "provider": r.provider,
            "status": r.status,
            "instrument_name": r.instrument_name,
            "instrument_recognized": r.instrument_recognized,
            "barcode_value": r.barcode_value,
            "overall_cleanliness_score": r.overall_cleanliness_score,
            "baseline_compared": r.baseline_compared,
            "baseline_match_pct": r.baseline_match_pct,
            "baseline_verdict": r.baseline_verdict,
            "finding_count": r.finding_count,
            "processing_ms": r.processing_ms,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


@router.get("/kpi-summary", response_model=CVKPISummary)
def cv_kpi_summary(
    request: Request,
    tenant_id: str = "demo-tenant",
    db: Session = Depends(get_db),
):
    """CV findings KPI summary for the dashboard — reads from persisted records."""
    from app.models.cv_inference import CVInferenceRecord
    require_enterprise_auth(request)
    records = (
        db.query(CVInferenceRecord)
        .filter(CVInferenceRecord.tenant_id == tenant_id)
        .all()
    )
    total = len(records)
    if total == 0:
        return CVKPISummary(
            total_analyses=0, recognized_count=0, recognition_rate_pct=0.0,
            barcode_read_count=0, qr_read_count=0, key_dot_read_count=0,
            blood_detections=0, bone_detections=0, tissue_detections=0,
            corrosion_detections=0, crack_detections=0,
            insulation_defect_detections=0, residue_detections=0,
            baseline_comparisons_run=0, baseline_pass_count=0, baseline_fail_count=0,
            avg_confidence=0.0, avg_baseline_match_pct=0.0,
        )

    recognized = sum(1 for r in records if r.instrument_recognized)
    barcode_reads = sum(1 for r in records if r.barcode_value)
    qr_reads = sum(1 for r in records if r.qr_value)
    key_dot_reads = sum(1 for r in records if r.key_dot_value)
    blood = sum(r.blood_count for r in records)
    bone = sum(r.bone_count for r in records)
    tissue = sum(r.tissue_count for r in records)
    corrosion = sum(r.corrosion_count for r in records)
    crack = sum(r.crack_count for r in records)
    insulation = sum(r.insulation_count for r in records)
    residue = sum(r.residue_count for r in records)
    bl_runs = sum(1 for r in records if r.baseline_compared)
    bl_pass = sum(1 for r in records if r.baseline_verdict == "pass")
    bl_fail = sum(1 for r in records if r.baseline_verdict == "fail")
    avg_conf = round(
        sum(r.instrument_confidence for r in records) / total, 3
    )
    bl_pcts = [r.baseline_match_pct for r in records if r.baseline_compared]
    avg_bl_pct = round(sum(bl_pcts) / len(bl_pcts), 1) if bl_pcts else 0.0

    def _pct(n: int) -> float:
        return round(n / total * 100, 1)

    return CVKPISummary(
        total_analyses=total,
        recognized_count=recognized,
        recognition_rate_pct=_pct(recognized),
        barcode_read_count=barcode_reads,
        qr_read_count=qr_reads,
        key_dot_read_count=key_dot_reads,
        blood_detections=blood,
        bone_detections=bone,
        tissue_detections=tissue,
        corrosion_detections=corrosion,
        crack_detections=crack,
        insulation_defect_detections=insulation,
        residue_detections=residue,
        baseline_comparisons_run=bl_runs,
        baseline_pass_count=bl_pass,
        baseline_fail_count=bl_fail,
        avg_confidence=avg_conf,
        avg_baseline_match_pct=avg_bl_pct,
    )


@router.get("/provider/info")
def provider_info(request: Request):
    """Return active CV provider name and model versions."""
    require_enterprise_auth(request)
    provider = CVRegistry.get_provider()
    return {
        "provider": provider.provider_name,
        "model_versions": provider.model_versions,
        "capabilities": [
            "instrument_recognition",
            "identifier_reading",
            "contamination_detection",
            "damage_detection",
            "baseline_comparison",
        ],
        "swap_instructions": "Set CV_PROVIDER env var to: mock | onnx | openai | roboflow | custom",
    }
