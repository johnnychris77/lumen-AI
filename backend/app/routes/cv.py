"""Computer Vision API routes — P4 (enhanced), hardened in P4.7.1.

P4.7.1 contract for EVERY route in this module:

* **Tenant comes from the verified auth context only** (SEC-R2-01). A
  ``tenant_id`` in a request body or query string is ignored; reads, writes,
  annotations, history and single-record retrieval are all scoped to the
  authenticated caller's membership-verified tenant. Another tenant's record is
  indistinguishable from a missing one (404).
* **Authorization precedes work.** Auth + tenant resolution happen before any
  image validation, retrieval, model execution or persistence.
* **Prohibited image inputs are refused (422) and never fetched** (SEC-R2-02).
* **Nothing simulated is operational evidence** (SCI-17). Defect KPIs count
  only integrity-verified model inference; simulated, unavailable, failed and
  legacy-unverified records are reported separately and never added in.
"""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.ai.inference_gate import STATUS_AI_UNAVAILABLE, simulation_permitted
from app.auth.context import AuthContext
from app.cv.evidence import (
    EVIDENCE_AI_UNAVAILABLE,
    EVIDENCE_FAILED,
    EVIDENCE_LEGACY_UNVERIFIED,
    EVIDENCE_MODEL_INFERENCE,
    EVIDENCE_SIMULATED,
    classify_record,
    is_operational_evidence,
)
from app.cv.pipeline import (
    ImageInputRejected,
    assert_image_inputs_allowed,
    build_composite_ranking_request,
    build_ranking_request_from_result,
    run_analysis,
    run_baseline_compare,
)
from app.cv.registry import CVRegistry
from app.cv.safe_fetch import UnsafeImageURLError, assert_image_url_allowed
from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth
from app.limiter import _rate_limit
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

router = APIRouter(prefix="/api/enterprise/cv", tags=["computer-vision"])

# ── R4: In-process async task store ──────────────────────────────────────────
# Production would use Celery/ARQ + Redis. For single-server deployments this
# in-memory dict provides the same polling interface without extra dependencies.
# Every entry records the tenant that submitted it; only that tenant may poll it.
_async_results: dict[str, dict[str, Any]] = {}
_async_lock = threading.Lock()


# ── Authorization helpers ────────────────────────────────────────────────────

def _verified(ctx: AuthContext) -> AuthContext:
    """Require a VERIFIED tenant on an authenticated context, fail-closed.

    Every handler calls ``require_enterprise_auth(request, db=db)`` INLINE (so
    the endpoint-governance scanner in scripts/generate_endpoint_inventory.py
    sees the auth call in the handler body) and passes the result here. With a
    ``db`` session that call enforces enabled tenant membership for every real
    (JWT / OIDC) identity, so ``tenant_id`` is never a bare client value.
    """
    if not (ctx.tenant_id or "").strip():
        raise HTTPException(status_code=403, detail="No verified tenant for this request.")
    return ctx


def _reject(exc: Exception) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


def _tenant_records(db: Session, tenant_id: str):
    from app.models.cv_inference import CVInferenceRecord

    return db.query(CVInferenceRecord).filter(CVInferenceRecord.tenant_id == tenant_id)


def _tenant_record(db: Session, tenant_id: str, inference_id: str):
    """One record, only if it belongs to the caller's tenant. A record owned by
    another tenant returns None — the caller sees a plain 404."""
    from app.models.cv_inference import CVInferenceRecord

    return (
        _tenant_records(db, tenant_id)
        .filter(CVInferenceRecord.inference_id == inference_id)
        .first()
    )


def _presentable_score(value: float | None, evidence_class: str) -> float | None:
    """A stored score is only presented for verified model inference or for an
    explicitly simulated row. Not-evaluated rows never show a number."""
    if evidence_class in (EVIDENCE_MODEL_INFERENCE, EVIDENCE_SIMULATED):
        return value
    return None


def _run_async_task(inference_id: str, req: CVAnalysisRequest, tenant_id: str) -> None:
    """Background thread target for async analysis."""
    try:
        result = run_analysis(req)
        payload = {
            "status": "complete",
            "result": result.model_dump(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        payload = {
            "status": "failed",
            # Class name only: an exception message may contain paths or URLs.
            "error": type(exc).__name__,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    payload["tenant_id"] = tenant_id
    with _async_lock:
        _async_results[inference_id] = payload


# ── Core endpoints ────────────────────────────────────────────────────────────

@router.post("/analyze", response_model=CVInferenceResult)
@_rate_limit("30/minute")
def analyze_image(
    req: CVAnalysisRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Full synchronous CV pipeline (instrument recognition → finding detection → scoring)."""
    ctx = _verified(require_enterprise_auth(request, db=db))
    req = req.model_copy(update={"tenant_id": ctx.tenant_id})
    try:
        return run_analysis(req, db=db)
    except ImageInputRejected as exc:
        raise _reject(exc) from exc


@router.post("/baseline-compare", response_model=CVInferenceResult)
def compare_to_baseline(
    req: BaselineCompareRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Dedicated baseline comparison: structural similarity + anomaly regions."""
    ctx = _verified(require_enterprise_auth(request, db=db))
    req = req.model_copy(update={"tenant_id": ctx.tenant_id})
    try:
        return run_baseline_compare(req, db=db)
    except ImageInputRejected as exc:
        raise _reject(exc) from exc


@router.post("/analyze-and-rank", response_model=dict)
def analyze_and_rank(
    req: CVAnalysisRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """R3: CV analysis → composite P3 ranking in one round-trip.

    P4.7.1 (SCI-17): ranking is produced only from findings that exist. A
    not-evaluated result is NOT ranked. A simulated result may be ranked in the
    dev/test simulation, and the ranking is then stamped ``simulated``.
    """
    ctx = _verified(require_enterprise_auth(request, db=db))
    req = req.model_copy(update={"tenant_id": ctx.tenant_id})
    try:
        cv_result = run_analysis(req, db=db)
    except ImageInputRejected as exc:
        raise _reject(exc) from exc

    evidence_class = cv_result.evidence_class
    rankable = (
        bool(cv_result.regions)
        and evidence_class in (EVIDENCE_MODEL_INFERENCE, EVIDENCE_SIMULATED)
    )
    if not rankable:
        ranking_dict: dict[str, Any] = {
            "ranking_mode": "not_ranked",
            "evidence_class": evidence_class,
            "reason": (
                "No model-detected findings to rank."
                if evidence_class == EVIDENCE_MODEL_INFERENCE
                else "CV analysis did not evaluate the image; nothing to rank."
            ),
        }
    else:
        composite_req = build_composite_ranking_request(cv_result)
        if composite_req and len(composite_req.get("findings", [])) > 1:
            ranking_result = score_composite(CompositeRankingRequest(**composite_req), db=db)
            ranking_dict = ranking_result.model_dump()
            ranking_dict["ranking_mode"] = "composite"
        else:
            ranking_inputs = build_ranking_request_from_result(cv_result)
            ranking_result_single = score_inspection(RankingRequest(**ranking_inputs), db=db)
            ranking_dict = ranking_result_single.model_dump()
            ranking_dict["ranking_mode"] = "single"
        ranking_dict["evidence_class"] = evidence_class
        ranking_dict["simulated"] = evidence_class == EVIDENCE_SIMULATED

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
    db: Session = Depends(get_db),
):
    """R4: Submit inference job and return immediately with inference_id.

    Poll GET /inference/{inference_id}/status for completion.
    """
    ctx = _verified(require_enterprise_auth(request, db=db))
    req = req.model_copy(update={"tenant_id": ctx.tenant_id})
    try:
        assert_image_inputs_allowed(req)  # refuse before a job is ever queued
    except ImageInputRejected as exc:
        raise _reject(exc) from exc

    inference_id = f"inf-{uuid.uuid4().hex[:12]}"
    with _async_lock:
        _async_results[inference_id] = {
            "status": "processing",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "tenant_id": ctx.tenant_id,
        }
    background_tasks.add_task(_run_async_task, inference_id, req, ctx.tenant_id)
    return {"inference_id": inference_id, "status": "processing"}


@router.get("/inference/{inference_id}/status", response_model=dict)
def get_inference_status(inference_id: str, request: Request, db: Session = Depends(get_db)):
    """R4: Poll async inference task status (own tenant's jobs only)."""
    ctx = _verified(require_enterprise_auth(request, db=db))
    with _async_lock:
        entry = _async_results.get(inference_id)
    if entry is None or entry.get("tenant_id") != ctx.tenant_id:
        # Unknown id and another tenant's id are indistinguishable.
        return {"inference_id": inference_id, "status": "not_found"}
    public = {k: v for k, v in entry.items() if k != "tenant_id"}
    return {"inference_id": inference_id, **public}


# ── R11: Video analysis endpoint ──────────────────────────────────────────────

@router.post("/analyze-video", response_model=CVVideoAnalysisResult)
def analyze_video(
    req: CVVideoAnalysisRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """R11: Borescope video frame sampling and aggregated finding detection.

    No video decoder exists in this build. Outside the dev/test simulation the
    result is an explicit ``ai_unavailable`` with zero frames analysed — never
    a synthesized timeline.
    """
    ctx = _verified(require_enterprise_auth(request, db=db))
    import time as _time

    try:
        assert_image_url_allowed(req.video_url)
    except UnsafeImageURLError as exc:
        raise HTTPException(status_code=422, detail=f"video_url rejected: {exc}") from exc

    t0 = _time.monotonic()
    provider = CVRegistry.get_provider()

    if provider.provider_name != "mock" or not simulation_permitted():
        reason = (
            "Video analysis is not available: no video decoder or approved "
            "computer-vision model is installed on this deployment."
        )
        return CVVideoAnalysisResult(
            video_url=req.video_url,
            frames_analyzed=0,
            total_duration_sec=0.0,
            worst_contamination_score=None,
            worst_damage_score=None,
            finding_timeline=[],
            composite_regions=[],
            provider=provider.provider_name,
            processing_ms=int((_time.monotonic() - t0) * 1000),
            warnings=[reason],
            status=STATUS_AI_UNAVAILABLE,
            simulated=False,
            evidence_class=EVIDENCE_AI_UNAVAILABLE,
            unavailable_reason=reason,
        )

    # ── dev/test SIMULATION only (mock provider, explicitly permitted) ───────
    warnings: list[str] = [
        "SIMULATED RESULT: frame count, duration and findings are generated from "
        "the video URL by the development/test mock provider. Not a detection."
    ]
    frames: list[CVVideoFrame] = []
    estimated_duration = _mock_video_duration(req.video_url)
    n_frames = max(1, int(estimated_duration * req.sample_fps))

    contamination_scores: list[float] = []
    damage_scores: list[float] = []
    all_regions = []

    for i in range(n_frames):
        ts = i / req.sample_fps
        frame_req = CVAnalysisRequest(
            image_url=f"{req.video_url}#frame={i}",
            instrument_name=req.instrument_name,
            instrument_category=req.instrument_category,
            tenant_id=ctx.tenant_id,
            requested_capabilities=req.requested_capabilities,
        )
        frame_result = run_analysis(frame_req)
        if frame_result.contamination_score is not None:
            contamination_scores.append(frame_result.contamination_score)
        if frame_result.damage_score is not None:
            damage_scores.append(frame_result.damage_score)
        all_regions.extend(frame_result.regions)
        frames.append(CVVideoFrame(
            frame_index=i,
            timestamp_sec=round(ts, 2),
            inference_id=frame_result.inference_id,
            regions=frame_result.regions,
            contamination_score=frame_result.contamination_score,
            damage_score=frame_result.damage_score,
            status=frame_result.status,
        ))

    # Deduplicate composite regions by finding_category
    seen: set[str] = set()
    composite: list = []
    for r in all_regions:
        if r.finding_category not in seen:
            composite.append(r)
            seen.add(r.finding_category)

    return CVVideoAnalysisResult(
        video_url=req.video_url,
        frames_analyzed=len(frames),
        total_duration_sec=estimated_duration,
        worst_contamination_score=round(min(contamination_scores), 1) if contamination_scores else None,
        worst_damage_score=round(min(damage_scores), 1) if damage_scores else None,
        finding_timeline=frames,
        composite_regions=composite,
        provider=provider.provider_name,
        processing_ms=int((_time.monotonic() - t0) * 1000),
        warnings=warnings,
        status="success",
        simulated=True,
        evidence_class=EVIDENCE_SIMULATED,
    )


def _mock_video_duration(video_url: str) -> float:
    """Return a deterministic mock duration for a video URL (simulation only)."""
    import hashlib
    seed = int(hashlib.md5(video_url.encode()).hexdigest()[:4], 16)  # noqa: S324
    import random
    return round(random.Random(seed).uniform(8.0, 45.0), 1)


# ── R10: Active learning review queue ────────────────────────────────────────

@router.get("/review-queue", response_model=list[dict])
def get_review_queue(
    request: Request,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """R10: Return low-confidence inferences pending human annotation (own tenant)."""
    from app.models.cv_inference import CVInferenceRecord
    ctx = _verified(require_enterprise_auth(request, db=db))
    limit = max(1, min(limit, 200))
    records = (
        _tenant_records(db, ctx.tenant_id)
        .filter(
            CVInferenceRecord.review_required.is_(True),
            CVInferenceRecord.review_completed_at.is_(None),
        )
        .order_by(CVInferenceRecord.created_at.asc())
        .limit(limit)
        .all()
    )
    out = []
    for r in records:
        evidence_class = classify_record(r)
        out.append({
            "inference_id": r.inference_id,
            "instrument_name": r.instrument_name,
            "instrument_confidence": r.instrument_confidence,
            "finding_count": r.finding_count,
            "overall_cleanliness_score": _presentable_score(r.overall_cleanliness_score, evidence_class),
            "image_url": r.image_url,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "evidence_class": evidence_class,
            "simulated": evidence_class == EVIDENCE_SIMULATED,
        })
    return out


@router.post("/inference/{inference_id}/annotate", response_model=dict)
def annotate_inference(
    inference_id: str,
    annotation: AnnotationRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """R10: Submit human annotation for a low-confidence inference (own tenant)."""
    ctx = _verified(require_enterprise_auth(request, db=db))
    record = _tenant_record(db, ctx.tenant_id, inference_id)
    if not record:
        raise HTTPException(status_code=404, detail="Inference record not found")
    record.review_annotation = json.dumps({
        "annotator_id": annotation.annotator_id,
        # The authenticated identity, recorded independently of the
        # caller-declared annotator_id.
        "authenticated_actor": ctx.actor,
        "confirmed_regions": annotation.confirmed_regions,
        "rejected_region_ids": annotation.rejected_region_ids,
        "corrected_severity": annotation.corrected_severity,
        "notes": annotation.notes,
        # An annotation on a simulated / unverified record is not ground truth.
        "evidence_class": classify_record(record),
    })
    record.review_annotator_id = annotation.annotator_id
    record.review_completed_at = datetime.now(timezone.utc)
    db.commit()
    return {"inference_id": inference_id, "annotation_saved": True}


# ── R12: Provider metrics endpoint ────────────────────────────────────────────

@router.get("/provider/metrics", response_model=dict)
def provider_metrics(
    request: Request,
    db: Session = Depends(get_db),
):
    """R12: Provider cost and latency telemetry aggregated from persisted records.

    Operational telemetry only — it describes what ran, not what was detected.
    ``evidence_breakdown`` shows how many records are simulated / unavailable.
    """
    ctx = _verified(require_enterprise_auth(request, db=db))
    records = _tenant_records(db, ctx.tenant_id).all()
    if not records:
        return {
            "total_inferences": 0,
            "avg_processing_ms": 0.0,
            "p95_processing_ms": 0.0,
            "total_cost_usd": 0.0,
            "avg_cost_per_inference_usd": 0.0,
            "provider_breakdown": {},
            "evidence_breakdown": {},
        }

    latencies = sorted(r.processing_ms for r in records)
    p95_idx = max(0, int(len(latencies) * 0.95) - 1)
    total_cost = sum(r.provider_cost_usd for r in records)

    provider_counts: dict[str, int] = {}
    provider_costs: dict[str, float] = {}
    evidence_counts: dict[str, int] = {}
    for r in records:
        provider_counts[r.provider] = provider_counts.get(r.provider, 0) + 1
        provider_costs[r.provider] = provider_costs.get(r.provider, 0.0) + r.provider_cost_usd
        cls = classify_record(r)
        evidence_counts[cls] = evidence_counts.get(cls, 0) + 1

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
        "evidence_breakdown": evidence_counts,
    }


# ── Existing retrieval / history / KPI endpoints ──────────────────────────────

@router.get("/inference/{inference_id}", response_model=CVInferenceResult)
def get_inference(
    inference_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Retrieve a stored CV inference result by ID (own tenant only)."""
    ctx = _verified(require_enterprise_auth(request, db=db))
    record = _tenant_record(db, ctx.tenant_id, inference_id)
    if not record:
        raise HTTPException(status_code=404, detail="Inference record not found")
    result = CVInferenceResult.model_validate(json.loads(record.result_json))
    evidence_class = classify_record(record)
    updates: dict[str, Any] = {
        "evidence_class": evidence_class,
        "simulated": evidence_class == EVIDENCE_SIMULATED,
        "human_review_required": True,
    }
    if evidence_class not in (EVIDENCE_MODEL_INFERENCE, EVIDENCE_SIMULATED):
        # A legacy / not-evaluated record never re-surfaces a stored score.
        updates.update(contamination_score=None, damage_score=None, overall_cleanliness_score=None)
    return result.model_copy(update=updates)


@router.get("/history", response_model=list[dict])
def list_inference_history(
    request: Request,
    limit: int = 25,
    db: Session = Depends(get_db),
):
    """List recent CV inference records for the caller's tenant."""
    from app.models.cv_inference import CVInferenceRecord
    ctx = _verified(require_enterprise_auth(request, db=db))
    limit = max(1, min(limit, 100))
    records = (
        _tenant_records(db, ctx.tenant_id)
        .order_by(CVInferenceRecord.id.desc())
        .limit(limit)
        .all()
    )
    out = []
    for r in records:
        evidence_class = classify_record(r)
        out.append({
            "inference_id": r.inference_id,
            "context": r.context,
            "provider": r.provider,
            "status": r.status,
            "instrument_name": r.instrument_name,
            "instrument_recognized": r.instrument_recognized,
            "barcode_value": r.barcode_value,
            "overall_cleanliness_score": _presentable_score(r.overall_cleanliness_score, evidence_class),
            "baseline_compared": r.baseline_compared,
            "baseline_match_pct": r.baseline_match_pct,
            "baseline_verdict": r.baseline_verdict,
            "finding_count": r.finding_count,
            "processing_ms": r.processing_ms,
            "provider_cost_usd": r.provider_cost_usd,
            "review_required": r.review_required,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            # P4.7.1: every row states what it is.
            "evidence_class": evidence_class,
            "simulated": evidence_class == EVIDENCE_SIMULATED,
            "operational_evidence": is_operational_evidence(evidence_class),
        })
    return out


@router.get("/kpi-summary", response_model=CVKPISummary)
def cv_kpi_summary(
    request: Request,
    include_simulated: bool = False,
    db: Session = Depends(get_db),
):
    """CV findings KPI summary — reads from persisted records (own tenant).

    P4.7.1 (SCI-17): the defect, recognition and baseline KPIs count ONLY
    records produced by integrity-verified model inference. Simulated,
    unavailable, failed and legacy-unverified records are reported in their own
    counters and are never added in.

    ``include_simulated=true`` is honoured ONLY where simulation is explicitly
    permitted (dev/test); the response then says so in ``evidence_basis``. It
    is ignored everywhere else.
    """
    ctx = _verified(require_enterprise_auth(request, db=db))
    all_records = _tenant_records(db, ctx.tenant_id).all()

    by_class: dict[str, list] = {
        EVIDENCE_MODEL_INFERENCE: [], EVIDENCE_SIMULATED: [], EVIDENCE_AI_UNAVAILABLE: [],
        EVIDENCE_FAILED: [], EVIDENCE_LEGACY_UNVERIFIED: [],
    }
    for r in all_records:
        by_class.setdefault(classify_record(r), []).append(r)

    with_simulated = bool(include_simulated) and simulation_permitted()
    records = list(by_class[EVIDENCE_MODEL_INFERENCE])
    if with_simulated:
        records += by_class[EVIDENCE_SIMULATED]

    accounting = {
        "genuine_analyses": len(by_class[EVIDENCE_MODEL_INFERENCE]),
        "simulated_excluded_count": 0 if with_simulated else len(by_class[EVIDENCE_SIMULATED]),
        "unavailable_or_failed_count": len(by_class[EVIDENCE_AI_UNAVAILABLE]) + len(by_class[EVIDENCE_FAILED]),
        "legacy_unverified_excluded_count": len(by_class[EVIDENCE_LEGACY_UNVERIFIED]),
        "evidence_basis": "includes_simulated_dev_test_only" if with_simulated else "model_inference_only",
    }

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
            **accounting,
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
        **accounting,
    )


@router.get("/provider/info")
def provider_info(request: Request, db: Session = Depends(get_db)):
    """Return the active CV provider and whether it is real, simulated or unavailable."""
    _verified(require_enterprise_auth(request, db=db))
    provider = CVRegistry.get_provider()
    name = provider.provider_name
    available = name not in ("unavailable",)
    return {
        "provider": name,
        "model_versions": provider.model_versions,
        "available": available,
        "simulated": name == "mock",
        "status": "simulated" if name == "mock" else ("available" if available else STATUS_AI_UNAVAILABLE),
        "unavailable_reason": getattr(provider, "reason", "") if not available else "",
        # Capabilities that can actually run right now — empty when unavailable.
        "capabilities": [
            "instrument_recognition",
            "identifier_reading",
            "contamination_detection",
            "damage_detection",
            "baseline_comparison",
        ] if available else [],
        "swap_instructions": (
            "Set CV_PROVIDER=onnx with SHA-256-pinned local model artifacts. "
            "The mock provider is a dev/test simulation only."
        ),
    }
