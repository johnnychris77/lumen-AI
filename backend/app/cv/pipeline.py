"""Multi-stage CV pipeline with persistence and P3 ranking integration.

P4.7.1 ordering contract: the calling route authenticates and resolves the
tenant FIRST; this module then rejects prohibited image inputs BEFORE any
provider, fetch or archive step runs. A rejected input is never fetched.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

import logging

from app.ai.inference_gate import STATUS_FAILED
from app.cv.evidence import (
    EVIDENCE_MODEL_INFERENCE,
    EVIDENCE_SIMULATED,
    classify_result,
    is_inference_candidate,
    is_operational_evidence,
)
from app.cv.image_store import archive_image
from app.cv.image_validator import validate_b64_payload
from app.cv.provenance import ProvenanceError, assert_issuable, issue_provenance
from app.cv.registry import CVRegistry
from app.cv.safe_fetch import UnsafeImageURLError, assert_image_url_allowed
from app.cv.unavailable_provider import unavailable_result
from app.schemas.cv import BaselineCompareRequest, CVAnalysisRequest, CVInferenceResult

logger = logging.getLogger(__name__)

_WITHHELD_REASON = (
    "The result was withheld: trusted inference provenance could not be established "
    "for this run, so it cannot be presented as a model finding."
)


class ImageInputRejected(ValueError):
    """An image input is prohibited (unsafe URL or invalid payload). The
    request must be refused; nothing was fetched, analysed or stored."""


def assert_image_inputs_allowed(req: CVAnalysisRequest) -> None:
    """Fail-closed validation of every image reference in a request.

    Raises :class:`ImageInputRejected`. This performs NO network access.
    """
    for label, url in (("image_url", req.image_url), ("baseline_image_url", req.baseline_image_url)):
        if not url:
            continue
        try:
            assert_image_url_allowed(url)
        except UnsafeImageURLError as exc:
            raise ImageInputRejected(f"{label} rejected: {exc}") from exc
    if req.image_data_b64:
        problems = validate_b64_payload(req.image_data_b64)
        if problems:
            raise ImageInputRejected(f"image_data_b64 rejected: {problems[0]}")


def _provider_artifacts(provider: Any) -> dict[str, str]:
    """Integrity-verified artifact digests, taken from the PROVIDER's own server-side
    state — never from the result object, whose fields a provider merely reports."""
    getter = getattr(provider, "verified_artifacts", None)
    try:
        return dict(getter()) if callable(getter) else {}
    except Exception:  # noqa: BLE001 - a provider that cannot report is simply unsealable
        return {}


def _withheld(req: CVAnalysisRequest, provider: Any, exc: Exception) -> CVInferenceResult:
    """A completed run that cannot be sealed is NOT returned as a finding."""
    logger.warning("CV result withheld: provenance not established (%s)", exc)
    return unavailable_result(
        req, reason=_WITHHELD_REASON, status=STATUS_FAILED,
        provider=getattr(provider, "provider_name", "unknown"),
        model_versions=dict(getattr(provider, "model_versions", {}) or {}),
        model_integrity={"verified": False, "reason": "provenance_not_established"},
    )


def _stamp(result: CVInferenceResult, evidence_class: str) -> CVInferenceResult:
    return result.model_copy(update={
        "evidence_class": evidence_class,
        "simulated": evidence_class == EVIDENCE_SIMULATED,
        "human_review_required": True,
    })


def run_analysis(req: CVAnalysisRequest, db: Session | None = None) -> CVInferenceResult:
    """Run full CV pipeline and persist result.

    ``req.tenant_id`` MUST already be the authenticated caller's tenant (set by
    the route from the verified auth context) — it is never taken from the
    client here.

    P4.7.2: a completed run is returned as ``model_inference`` only when this
    function has sealed it with server-issued provenance (``app.cv.provenance``)
    in the same transaction that stores the record. If it cannot be sealed — no
    database session, no provenance key, no approved integrity-verified artifact
    — the result is withheld and an explicit ``failed`` result is returned
    instead. Nothing here trusts what a result says about itself.
    """
    # R1 / SEC-R2-02: reject prohibited inputs before anything else happens.
    assert_image_inputs_allowed(req)

    provider = CVRegistry.get_provider()
    result = provider.analyze(req)

    # Decide, BEFORE archiving or storing anything, whether this run can be sealed.
    artifacts: dict[str, str] | None = None
    if is_inference_candidate(result):
        artifacts = _provider_artifacts(provider)
        try:
            assert_issuable(db, artifacts)
        except ProvenanceError as exc:
            result, artifacts = _withheld(req, provider, exc), None

    sealable = artifacts is not None
    result = _stamp(result, EVIDENCE_MODEL_INFERENCE if sealable else classify_result(result))

    # R7: Archive image for audit trail (noop unless IMAGE_STORE_BACKEND is set).
    # Only a run that is about to be sealed is archived as inspection evidence.
    if sealable:
        archive = archive_image(
            image_bytes=None,
            image_url=req.image_url,
            inference_id=result.inference_id,
            tenant_id=req.tenant_id,
        )
        if archive.object_key:
            result = result.model_copy(update={"archived_image_key": archive.object_key})

    if db is not None:
        try:
            _persist(result, db, authenticated_tenant_id=req.tenant_id, artifacts=artifacts)
        except ProvenanceError as exc:
            # Sealing failed after the pre-flight: store and return the withheld form.
            db.rollback()
            withheld = _withheld(req, provider, exc)
            result = _stamp(withheld, classify_result(withheld))
            _persist(result, db, authenticated_tenant_id=req.tenant_id, artifacts=None)

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
    if not result.regions or not result.ranking_inputs:
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


def _persist(
    result: CVInferenceResult, db: Session, *,
    authenticated_tenant_id: str, artifacts: dict[str, str] | None,
) -> None:
    """Write inference result to DB for KPI queries and audit trail.

    With ``artifacts`` (a sealable run) the record and its provenance row are
    written in ONE transaction: either both exist or neither does."""
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
        # The score columns are NOT NULL. A not-evaluated result stores 0.0 as a
        # placeholder that no read path presents: readers derive the evidence
        # class (app.cv.evidence.classify_record) and return None for anything
        # that is not verified model inference or an explicitly simulated row.
        contamination_score=result.contamination_score if result.contamination_score is not None else 0.0,
        damage_score=result.damage_score if result.damage_score is not None else 0.0,
        overall_cleanliness_score=(
            result.overall_cleanliness_score if result.overall_cleanliness_score is not None else 0.0
        ),
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
        # Only verified model inference may enter the human annotation queue;
        # a simulated or not-evaluated row is not something to "confirm".
        review_required=bool(getattr(result, "review_required", False))
        and is_operational_evidence(result.evidence_class),
    )
    db.add(record)
    if artifacts is not None:
        try:
            db.flush()  # the seal covers the record id
            issue_provenance(
                db, record, authenticated_tenant_id=authenticated_tenant_id,
                artifacts=artifacts, model_versions=dict(result.model_versions or {}),
            )
        except ProvenanceError:
            db.rollback()
            raise
    db.commit()
