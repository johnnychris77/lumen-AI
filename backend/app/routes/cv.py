"""Computer Vision API routes — P4 (enhanced)."""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.cv.pipeline import (
    build_composite_ranking_request,
    build_ranking_request_from_result,
    run_analysis,
    run_baseline_compare,
)
from app.cv.registry import CVRegistry
from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth
from app.schemas.cv import (
    AnnotationRequest,
    BaselineCompareRequest,
    CVAnalysisRequest,
    CVInferenceResult,
    CVKPISummary,
    CVVideoAnalysisRequest,
    CVVideoAnalysisResult,
    CVVideoFrame,
)
from app.schemas.ranking import CompositeRankingRequest, RankingRequest
from app.services.ranking_engine import score_composite, score_inspection
from app.limiter import _rate_limit

router = APIRouter(prefix="/api/enterprise/cv", tags=["computer-vision"])

# ── R4: In-process async task store ──────────────────────────────────────────
# Production would use Celery/ARQ + Redis. For single-server deployments this
# in-memory dict provides the same polling interface without extra dependencies.
_async_results: dict[str, dict[str, Any]] = {}
_async_lock = threading.Lock()


def _run_async_task(inference_id: str, req: CVAnalysisRequest) -> None:
    """Background thread target for async analysis."""
    try:
        result = run_analysis(req)
        with _async_lock:
            _async_results[inference_id] = {
                "status": "complete",
                "result": result.model_dump(),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
    except Exception as exc:
        with _async_lock:
            _async_results[inference_id] = {
                "status": "failed",
                "error": str(exc),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }


# ── Core endpoints ────────────────────────────────────────────────────────────

@router.post("/analyze", response_model=CVInferenceResult)
@_rate_limit("30/minute")
def analyze_image(
    req: CVAnalysisRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Full synchronous CV pipeline (instrument recognition → finding detection → scoring)."""
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
    """R3: CV analysis → composite P3 ranking in one round-trip.

    Uses score_composite() when multiple findings are detected so that all
    regions contribute to the risk score — not just the dominant finding.
    Falls back to score_inspection() for single-finding results.
    """
    require_enterprise_auth(request)
    cv_result = run_analysis(req, db=db)

    composite_req = build_composite_ranking_request(cv_result)
    if composite_req and len(composite_req.get("findings", [])) > 1:
        ranking_result = score_composite(
            CompositeRankingRequest(**composite_req), db=db
        )
        ranking_dict = ranking_result.model_dump()
        ranking_dict["ranking_mode"] = "composite"
    else:
        ranking_inputs = build_ranking_request_from_result(cv_result)
        ranking_result_single = score_inspection(RankingRequest(**ranking_inputs), db=db)
        ranking_dict = ranking_result_single.model_dump()
        ranking_dict["ranking_mode"] = "single"

    return {
        "cv": cv_result.model_dump(),
        "ranking": ranking_dict,
    }


# ── R4: Async inference endpoints ─────────────────────────────────────────────

@router.post("/analyze-async", response_model=dict, status_code=202)
def analyze_image_async(
    req: CVAnalysisRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """R4: Submit inference job and return immediately with inference_id.

    Poll GET /inference/{inference_id}/status for completion.
    """
    require_enterprise_auth(request)
    inference_id = f"inf-{uuid.uuid4().hex[:12]}"
    with _async_lock:
        _async_results[inference_id] = {
            "status": "processing",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
    background_tasks.add_task(_run_async_task, inference_id, req)
    return {"inference_id": inference_id, "status": "processing"}


@router.get("/inference/{inference_id}/status", response_model=dict)
def get_inference_status(inference_id: str, request: Request):
    """R4: Poll async inference task status."""
    require_enterprise_auth(request)
    with _async_lock:
        entry = _async_results.get(inference_id)
    if entry is None:
        # Not in async store — may be a DB-persisted sync inference
        return {"inference_id": inference_id, "status": "not_found"}
    return {"inference_id": inference_id, **entry}


# ── R11: Video analysis endpoint ──────────────────────────────────────────────

@router.post("/analyze-video", response_model=CVVideoAnalysisResult)
def analyze_video(
    req: CVVideoAnalysisRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """R11: Borescope video frame sampling and aggregated finding detection.

    Samples frames at req.sample_fps, runs CV pipeline on each frame,
    and returns aggregated findings with a per-frame timeline.
    """
    require_enterprise_auth(request)
    import time as _time

    t0 = _time.monotonic()
    warnings: list[str] = []
    frames: list[CVVideoFrame] = []

    # Estimate duration + frame count from mock (real impl uses cv2.VideoCapture)
    estimated_duration = _mock_video_duration(req.video_url)
    n_frames = max(1, int(estimated_duration * req.sample_fps))

    worst_c = 100.0
    worst_d = 100.0
    all_regions = []

    for i in range(n_frames):
        ts = i / req.sample_fps
        # Synthesize a per-frame URL for deterministic mock results
        frame_url = f"{req.video_url}#frame={i}"
        frame_req = CVAnalysisRequest(
            image_url=frame_url,
            instrument_name=req.instrument_name,
            instrument_category=req.instrument_category,
            tenant_id=req.tenant_id,
            requested_capabilities=req.requested_capabilities,
        )
        frame_result = run_analysis(frame_req)
        worst_c = min(worst_c, frame_result.contamination_score)
        worst_d = min(worst_d, frame_result.damage_score)
        all_regions.extend(frame_result.regions)
        frames.append(CVVideoFrame(
            frame_index=i,
            timestamp_sec=round(ts, 2),
            inference_id=frame_result.inference_id,
            regions=frame_result.regions,
            contamination_score=frame_result.contamination_score,
            damage_score=frame_result.damage_score,
        ))

    # Deduplicate composite regions by finding_category
    seen: set[str] = set()
    composite: list = []
    for r in all_regions:
        if r.finding_category not in seen:
            composite.append(r)
            seen.add(r.finding_category)

    provider = CVRegistry.get_provider()
    return CVVideoAnalysisResult(
        video_url=req.video_url,
        frames_analyzed=len(frames),
        total_duration_sec=estimated_duration,
        worst_contamination_score=round(worst_c, 1),
        worst_damage_score=round(worst_d, 1),
        finding_timeline=frames,
        composite_regions=composite,
        provider=provider.provider_name,
        processing_ms=int((_time.monotonic() - t0) * 1000),
        warnings=warnings,
    )


def _mock_video_duration(video_url: str) -> float:
    """Return a deterministic mock duration for a video URL."""
    import hashlib
    seed = int(hashlib.md5(video_url.encode()).hexdigest()[:4], 16)  # noqa: S324
    import random
    return round(random.Random(seed).uniform(8.0, 45.0), 1)


# ── R10: Active learning review queue ────────────────────────────────────────

@router.get("/review-queue", response_model=list[dict])
def get_review_queue(
    request: Request,
    tenant_id: str = "demo-tenant",
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """R10: Return low-confidence inferences pending human annotation."""
    from app.models.cv_inference import CVInferenceRecord
    require_enterprise_auth(request)
    limit = max(1, min(limit, 200))
    records = (
        db.query(CVInferenceRecord)
        .filter(
            CVInferenceRecord.tenant_id == tenant_id,
            CVInferenceRecord.review_required.is_(True),
            CVInferenceRecord.review_completed_at.is_(None),
        )
        .order_by(CVInferenceRecord.created_at.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "inference_id": r.inference_id,
            "instrument_name": r.instrument_name,
            "instrument_confidence": r.instrument_confidence,
            "finding_count": r.finding_count,
            "overall_cleanliness_score": r.overall_cleanliness_score,
            "image_url": r.image_url,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


@router.post("/inference/{inference_id}/annotate", response_model=dict)
def annotate_inference(
    inference_id: str,
    annotation: AnnotationRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """R10: Submit human annotation for a low-confidence inference."""
    from app.models.cv_inference import CVInferenceRecord
    require_enterprise_auth(request)
    record = (
        db.query(CVInferenceRecord)
        .filter(CVInferenceRecord.inference_id == inference_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Inference record not found")
    record.review_annotation = json.dumps({
        "annotator_id": annotation.annotator_id,
        "confirmed_regions": annotation.confirmed_regions,
        "rejected_region_ids": annotation.rejected_region_ids,
        "corrected_severity": annotation.corrected_severity,
        "notes": annotation.notes,
    })
    record.review_annotator_id = annotation.annotator_id
    record.review_completed_at = datetime.now(timezone.utc)
    db.commit()
    return {"inference_id": inference_id, "annotation_saved": True}


# ── R12: Provider metrics endpoint ────────────────────────────────────────────

@router.get("/provider/metrics", response_model=dict)
def provider_metrics(
    request: Request,
    tenant_id: str = "demo-tenant",
    db: Session = Depends(get_db),
):
    """R12: Provider cost and latency telemetry aggregated from persisted records."""
    from app.models.cv_inference import CVInferenceRecord
    require_enterprise_auth(request)
    records = (
        db.query(CVInferenceRecord)
        .filter(CVInferenceRecord.tenant_id == tenant_id)
        .all()
    )
    if not records:
        return {
            "total_inferences": 0,
            "avg_processing_ms": 0.0,
            "p95_processing_ms": 0.0,
            "total_cost_usd": 0.0,
            "avg_cost_per_inference_usd": 0.0,
            "provider_breakdown": {},
        }

    latencies = sorted(r.processing_ms for r in records)
    p95_idx = max(0, int(len(latencies) * 0.95) - 1)
    total_cost = sum(r.provider_cost_usd for r in records)

    # Group by provider
    provider_counts: dict[str, int] = {}
    provider_costs: dict[str, float] = {}
    for r in records:
        provider_counts[r.provider] = provider_counts.get(r.provider, 0) + 1
        provider_costs[r.provider] = provider_costs.get(r.provider, 0.0) + r.provider_cost_usd

    return {
        "total_inferences": len(records),
        "avg_processing_ms": round(sum(latencies) / len(latencies), 1),
        "p95_processing_ms": latencies[p95_idx],
        "total_cost_usd": round(total_cost, 6),
        "avg_cost_per_inference_usd": round(total_cost / len(records), 6),
        "provider_breakdown": {
            p: {"count": provider_counts[p], "total_cost_usd": round(provider_costs[p], 6)}
            for p in provider_counts
        },
    }


# ── Existing retrieval / history / KPI endpoints ──────────────────────────────

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
            "provider_cost_usd": r.provider_cost_usd,
            "review_required": r.review_required,
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
    """CV findings KPI summary — reads from persisted records."""
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
            avg_processing_ms=0.0, total_provider_cost_usd=0.0, review_queue_size=0,
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
    avg_conf = round(sum(r.instrument_confidence for r in records) / total, 3)
    bl_pcts = [r.baseline_match_pct for r in records if r.baseline_compared]
    avg_bl_pct = round(sum(bl_pcts) / len(bl_pcts), 1) if bl_pcts else 0.0
    avg_ms = round(sum(r.processing_ms for r in records) / total, 1)
    total_cost = round(sum(r.provider_cost_usd for r in records), 6)
    review_q = sum(1 for r in records if r.review_required and not r.review_completed_at)

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
        avg_processing_ms=avg_ms,
        total_provider_cost_usd=total_cost,
        review_queue_size=review_q,
    )


@router.get("/provider/info")
def provider_info(request: Request):
    """Return active CV provider name, model versions, and capabilities."""
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
