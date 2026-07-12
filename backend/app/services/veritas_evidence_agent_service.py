"""Project Veritas, Sections 1, 10 & 12: Evidence Assurance Agent
orchestrator + Evidence Gate + Inspection Evidence Panel data.

Composes baseline resolution, matching, image quality, coverage, and
conflict detection into one persisted `VeritasEvidenceReadinessAssessment` +
a recommended (never self-finalized) evidence gate. Veritas does not
independently approve an instrument -- `recommended_gate` is always
advisory; only a supervisor-gated `VeritasFeedback` action
(`override_evidence_gate`) can set `final_gate_override`.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.db import models
from app.models.veritas_evidence import (
    BASELINE_STATUS_APPROVED,
    BASELINE_STATUS_DRAFT,
    BASELINE_STATUS_PENDING_REVIEW,
    COVERAGE_INSUFFICIENT,
    GATE_ADDITIONAL_IMAGE_REQUIRED,
    GATE_ANALYSIS_BLOCKED,
    GATE_BASELINE_REVIEW_REQUIRED,
    GATE_EVIDENCE_CONFLICT,
    GATE_PROCEED_WITH_ANALYSIS,
    GATE_PROCEED_WITH_LIMITATIONS,
    GATE_SUPERVISOR_REVIEW_REQUIRED,
    IMAGE_QUALITY_INSUFFICIENT,
    READINESS_INSUFFICIENT,
    READINESS_LIMITED,
    READINESS_MODERATE,
    RESOLUTION_STATUS_SUPERVISOR_REVIEW_REQUIRED,
    VeritasEvidenceConflict,
    VeritasEvidenceReadinessAssessment,
)
from app.services.veritas_baseline_governance_service import effective_status
from app.services.veritas_baseline_matching_service import classify_match
from app.services.veritas_baseline_resolution_service import resolve_governed_baseline
from app.services.veritas_conflict_detection_service import detect_conflicts
from app.services.veritas_coverage_service import assess_coverage
from app.services.veritas_image_quality_service import assess_image_quality
from app.services.veritas_readiness_score_service import compute_evidence_readiness_score


def _recommend_gate(*, has_conflicts: bool, baseline_resolution_status: str, baseline_governance_status: str,
                     image_quality_status: str, coverage_status: str, readiness_category_value: str) -> str:
    if has_conflicts:
        return GATE_EVIDENCE_CONFLICT
    if baseline_resolution_status == RESOLUTION_STATUS_SUPERVISOR_REVIEW_REQUIRED:
        return GATE_SUPERVISOR_REVIEW_REQUIRED
    if baseline_governance_status in (BASELINE_STATUS_DRAFT, BASELINE_STATUS_PENDING_REVIEW):
        return GATE_BASELINE_REVIEW_REQUIRED
    if image_quality_status == IMAGE_QUALITY_INSUFFICIENT or coverage_status == COVERAGE_INSUFFICIENT:
        return GATE_ADDITIONAL_IMAGE_REQUIRED
    if readiness_category_value == READINESS_INSUFFICIENT:
        return GATE_ANALYSIS_BLOCKED
    if readiness_category_value in (READINESS_LIMITED, READINESS_MODERATE):
        return GATE_PROCEED_WITH_LIMITATIONS
    return GATE_PROCEED_WITH_ANALYSIS


_NEXT_ACTION = {
    GATE_PROCEED_WITH_ANALYSIS: "No additional evidence required; proceed with analysis.",
    GATE_PROCEED_WITH_LIMITATIONS: "Proceed, but address the documented limitation before final disposition if possible.",
    GATE_ADDITIONAL_IMAGE_REQUIRED: "Capture the missing anatomy zone image(s) before final disposition.",
    GATE_BASELINE_REVIEW_REQUIRED: "Route this baseline for governance review before it can support a final score.",
    GATE_SUPERVISOR_REVIEW_REQUIRED: "No approved baseline is available -- request supervisor review before final disposition.",
    GATE_EVIDENCE_CONFLICT: "Resolve the detected evidence conflict(s) before final disposition.",
    GATE_ANALYSIS_BLOCKED: "Evidence is insufficient -- do not issue a final AI conclusion from this inspection as-is.",
}


def run_evidence_assessment(
    db: Session, tenant_id: str, inspection_id: int, *, model_version: str = "", dataset_version: str = "",
) -> VeritasEvidenceReadinessAssessment:
    """Section 1: run the full Veritas pipeline and persist one assessment."""
    inspection = db.query(models.Inspection).filter(models.Inspection.id == inspection_id, models.Inspection.tenant_id == tenant_id).first()
    if inspection is None:
        raise ValueError(f"Inspection {inspection_id} not found for this tenant")

    instrument_identity = (
        f"barcode:{inspection.instrument_barcode}" if inspection.instrument_barcode
        else f"udi:{inspection.instrument_udi}" if inspection.instrument_udi
        else f"untracked:{inspection.instrument_type}:{inspection.id}"
    )

    baseline_resolution = resolve_governed_baseline(
        db, tenant_id, inspection.instrument_type, instrument_identity=instrument_identity,
    )

    if baseline_resolution.baseline_source_id is not None:
        baseline_governance_status = effective_status(
            db, tenant_id, baseline_resolution.baseline_source_type, baseline_resolution.baseline_source_id,
        )
        # A freshly-resolved approved baseline with no explicit Veritas governance
        # history yet is treated as approved (it already passed the real
        # resolve_baseline() approval filter) rather than defaulting to
        # pending_review, which would understate a genuinely approved baseline.
        if baseline_governance_status == BASELINE_STATUS_PENDING_REVIEW and baseline_resolution.approval_status.lower() in (
            "approved", "active", "vendor_approved", "hospital_approved",
        ):
            baseline_governance_status = BASELINE_STATUS_APPROVED
        match = classify_match(
            instrument_type=inspection.instrument_type, baseline_instrument_category=inspection.instrument_type,
            baseline_manufacturer=baseline_resolution.manufacturer, instrument_manufacturer=baseline_resolution.manufacturer,
        )
    else:
        baseline_governance_status = ""
        match = {"match_classification": "unavailable", "reason": baseline_resolution.message}

    image_quality = assess_image_quality(has_image=inspection.has_image, ai_confidence=inspection.ai_confidence)

    inspected_zones = json.loads(inspection.inspected_zones_json) if inspection.inspected_zones_json not in (None, "null") else None
    coverage = assess_coverage(inspection.instrument_type, inspected_zones)

    conflicts = detect_conflicts(match_classification=match["match_classification"])

    score_result = compute_evidence_readiness_score(
        match_classification=match["match_classification"],
        baseline_governance_status=baseline_governance_status or "unresolved",
        image_quality_status=image_quality["quality_status"],
        coverage_status=coverage["coverage_status"],
        instrument_identity_confidence="high" if instrument_identity.startswith(("barcode:", "udi:")) else "low",
        provenance_complete=True,
        supervisor_validated=False,
        model_compatible=True,
        has_conflicts=bool(conflicts),
    )

    gate = _recommend_gate(
        has_conflicts=bool(conflicts), baseline_resolution_status=baseline_resolution.resolution_status,
        baseline_governance_status=baseline_governance_status, image_quality_status=image_quality["quality_status"],
        coverage_status=coverage["coverage_status"], readiness_category_value=score_result["readiness_category"],
    )

    limitations = []
    if coverage["missing_zones"]:
        limitations.append(f"Missing zone(s): {', '.join(coverage['missing_zones'])}.")
    if image_quality["detected_issues"]:
        limitations.append(f"Image quality issue(s): {', '.join(image_quality['detected_issues'])}.")
    if baseline_resolution.resolution_status == RESOLUTION_STATUS_SUPERVISOR_REVIEW_REQUIRED:
        limitations.append(baseline_resolution.message)

    narrative = _build_narrative(
        baseline_resolution=baseline_resolution, match=match, image_quality=image_quality, coverage=coverage,
        score_result=score_result, gate=gate,
    )

    row = VeritasEvidenceReadinessAssessment(
        tenant_id=tenant_id, inspection_id=inspection_id, instrument_identity=instrument_identity,
        baseline_resolution_id=baseline_resolution.id,
        match_classification=match["match_classification"], image_quality_status=image_quality["quality_status"],
        coverage_status=coverage["coverage_status"], coverage_pct=coverage["coverage_pct"],
        missing_zones_json=json.dumps(coverage["missing_zones"]),
        readiness_score=score_result["readiness_score"], readiness_category=score_result["readiness_category"],
        score_breakdown_json=json.dumps(score_result["score_breakdown"]), limitations_json=json.dumps(limitations),
        recommended_gate=gate, next_action=_NEXT_ACTION[gate], reasoning_narrative=narrative,
        confidence=baseline_resolution.confidence, model_version=model_version, dataset_version=dataset_version,
        human_review_required=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    for conflict in conflicts:
        db.add(VeritasEvidenceConflict(
            tenant_id=tenant_id, assessment_id=row.id, conflict_type=conflict["conflict_type"],
            severity=conflict["severity"], affected_evidence_json=json.dumps(conflict["affected_evidence"]),
            recommended_resolution=conflict["recommended_resolution"], responsible_reviewer_role=conflict["responsible_reviewer_role"],
        ))
    db.commit()

    return row


def _build_narrative(*, baseline_resolution, match, image_quality, coverage, score_result, gate) -> str:
    if baseline_resolution.resolution_status == RESOLUTION_STATUS_SUPERVISOR_REVIEW_REQUIRED:
        return baseline_resolution.message

    baseline_text = (
        f"An approved {baseline_resolution.baseline_tier.replace('_', ' ')} baseline (v{baseline_resolution.baseline_version or '?'}) "
        f"was resolved for this instrument." if baseline_resolution.baseline_source_id else "No baseline was resolved for this instrument."
    )
    quality_text = f"Image quality is {image_quality['quality_status']}."
    coverage_text = (
        f"Coverage is {coverage['coverage_status']}"
        + (f" ({coverage['coverage_pct']}%)" if coverage["coverage_pct"] is not None else "")
        + (f"; missing: {', '.join(coverage['missing_zones'])}." if coverage["missing_zones"] else ".")
    )
    readiness_text = (
        f"Evidence readiness is {score_result['readiness_category'].replace('_', ' ')} at "
        f"{int(score_result['readiness_score'])}/100."
    )
    action_text = _NEXT_ACTION[gate]

    return f"{baseline_text} {quality_text} {coverage_text} {readiness_text} {action_text}"


def to_dict(row: VeritasEvidenceReadinessAssessment) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "tenant_id": row.tenant_id,
        "inspection_id": row.inspection_id,
        "instrument_identity": row.instrument_identity,
        "baseline_resolution_id": row.baseline_resolution_id,
        "match_classification": row.match_classification,
        "image_quality_status": row.image_quality_status,
        "coverage_status": row.coverage_status,
        "coverage_pct": row.coverage_pct,
        "missing_zones": json.loads(row.missing_zones_json or "[]"),
        "readiness_score": row.readiness_score,
        "readiness_category": row.readiness_category,
        "score_breakdown": json.loads(row.score_breakdown_json or "{}"),
        "limitations": json.loads(row.limitations_json or "[]"),
        "recommended_gate": row.recommended_gate,
        "next_action": row.next_action,
        "reasoning_narrative": row.reasoning_narrative,
        "confidence": row.confidence,
        "model_version": row.model_version,
        "dataset_version": row.dataset_version,
        "agent_version": row.agent_version,
        "human_review_required": row.human_review_required,
        "final_gate_override": row.final_gate_override,
        "overridden_by": row.overridden_by,
        "overridden_at": row.overridden_at.isoformat() if row.overridden_at else None,
        "disclaimer": row.disclaimer,
    }
