"""Project Sentinel-X, Section 1: Risk Intelligence Agent orchestrator.

Composes real, already-built specialist outputs -- Vulcan (instrument
reliability + progression), Aegis (process variation), Veritas (evidence
readiness), the Knowledge Graph (confidence), and the real per-instrument
Digital Twin condition trend (`instrument_condition_service`) -- into one
explainable, persisted `SentinelXRiskAssessment`. Never replaces human
clinical judgment; `human_review_required` is always True and there is no
supervisor-override path except through `sentinelx_override_service`.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.db import models
from app.models.sentinelx_risk import SentinelXRiskAssessment
from app.models.supervisor_review import SupervisorReview
from app.services.instrument_anatomy import get_anatomy
from app.services.instrument_condition_service import instrument_condition_history
from app.services.knowledge_graph_service import learning_confidence
from app.services.sentinelx_risk_scoring_service import compute_risk_score
from app.services.sentinelx_risk_taxonomy_service import classify_categories
from app.services.vulcan_aegis_integration_service import compute_process_variation_signal
from app.services.vulcan_progression_service import _inspections_for_identity, findings_timeline
from app.services.vulcan_reliability_agent_service import run_reliability_assessment
from app.services.vulcan_repair_effectiveness_service import repair_history_for_instrument
from app.services.veritas_evidence_agent_service import run_evidence_assessment

_SEVERITY_LABELS = {0: "none", 1: "minor", 2: "moderate", 3: "severe"}


def _recent_supervisor_concern(db: Session, tenant_id: str, instrument_identity: str) -> bool:
    inspections = _inspections_for_identity(db, tenant_id, instrument_identity)
    ids = [i.id for i in inspections]
    if not ids:
        return False
    return (
        db.query(SupervisorReview)
        .filter(SupervisorReview.tenant_id == tenant_id, SupervisorReview.inspection_id.in_(ids), SupervisorReview.agreement == "disagree")
        .first()
        is not None
    )


def _build_narrative(*, severity_label: str, finding_type: str, anatomy_zone: str, instrument_family: str,
                      recurrence_count: int, evidence_readiness_score: float | None, digital_twin_condition_trend: str,
                      repair_recurrence: bool, risk_level_value: str) -> str:
    if not finding_type:
        return (
            "Insufficient inspection evidence is available for this instrument to produce a clinical risk "
            "narrative. Supervisor review is recommended before the instrument proceeds further in the "
            "pre-sterilization workflow."
        )

    zone_text = anatomy_zone.replace("_", " ") if anatomy_zone else "an unspecified anatomy zone"
    family_text = instrument_family.replace("_", " ") if instrument_family else "this instrument"
    subject = f"{severity_label.capitalize()} {finding_type.replace('_', ' ')}"

    recurrence_clause = (
        f" The instrument has demonstrated recurring {finding_type.replace('_', ' ')} over {recurrence_count} inspections."
        if recurrence_count >= 2 else ""
    )
    evidence_clause = (
        f" Evidence quality is {'high' if evidence_readiness_score is not None and evidence_readiness_score >= 75 else 'limited'}."
        if evidence_readiness_score is not None else " Evidence readiness has not been separately assessed for this inspection."
    )
    twin_clause = (
        " The Digital Twin shows declining reliability."
        if digital_twin_condition_trend == "declining" else
        f" The Digital Twin trend is {digital_twin_condition_trend.replace('_', ' ')}."
    )
    repair_clause = " Similar instruments have required repair for this issue." if repair_recurrence else ""

    return (
        f"{subject} has been identified on the {zone_text}, a monitored anatomy zone for {family_text}."
        f"{recurrence_clause}{evidence_clause}{twin_clause}{repair_clause} "
        f"Clinical risk is {risk_level_value.replace('_', ' ').upper()}. Supervisor review is recommended "
        "before the instrument proceeds further in the pre-sterilization workflow."
    )


def run_risk_assessment(
    db: Session, tenant_id: str, instrument_identity: str, *, instrument_type: str = "", inspection_id: int | None = None,
) -> SentinelXRiskAssessment:
    """Section 1: run the full Sentinel-X risk pipeline and persist one
    assessment."""
    vulcan_row = run_reliability_assessment(db, tenant_id, instrument_identity, instrument_type=instrument_type)

    timeline = findings_timeline(db, tenant_id, instrument_identity, zone=vulcan_row.anatomy_zone or None)
    latest = timeline[-1] if timeline else None
    finding_type = latest["finding_type"] if latest else ""
    severity_index = latest["severity_index"] if latest else 0
    severity_label = _SEVERITY_LABELS.get(max(0, min(3, severity_index)), "none")

    anatomy = get_anatomy(instrument_type) if instrument_type else {"high_risk_zones": []}
    anatomy_zone_high_risk = vulcan_row.anatomy_zone in anatomy.get("high_risk_zones", [])

    aegis_signal = compute_process_variation_signal(db, tenant_id, instrument_identity, zone=vulcan_row.anatomy_zone or None)

    veritas_row = None
    if inspection_id is not None:
        veritas_row = run_evidence_assessment(db, tenant_id, inspection_id)

    condition = instrument_condition_history(db, tenant_id, instrument_identity)
    digital_twin_condition_trend = condition["condition_trend"] if condition else "insufficient_data"

    repairs = repair_history_for_instrument(db, tenant_id, instrument_identity)
    repair_recurrence = any(r["repair_outcome"] == "failure_recurred" for r in repairs)

    confidence_signals = learning_confidence(db, tenant_id)
    knowledge_confidence = confidence_signals.get("clinical_recommendation_confidence")

    supervisor_concern = _recent_supervisor_concern(db, tenant_id, instrument_identity)

    score_result = compute_risk_score(
        finding_type=finding_type, severity_index=severity_index, anatomy_zone_high_risk=anatomy_zone_high_risk,
        recurrence_count=vulcan_row.recurrence_count, digital_twin_condition_trend=digital_twin_condition_trend,
        evidence_readiness_score=veritas_row.readiness_score if veritas_row else None,
        repair_recurrence=repair_recurrence, supervisor_concern=supervisor_concern,
        knowledge_confidence=knowledge_confidence, process_variation_detected=aegis_signal["process_variation_detected"],
    )

    categories = classify_categories(
        finding_type=finding_type, evidence_readiness_score=veritas_row.readiness_score if veritas_row else None,
        digital_twin_condition_trend=digital_twin_condition_trend, recurrence_count=vulcan_row.recurrence_count,
        repair_recurrence=repair_recurrence, process_variation_detected=aegis_signal["process_variation_detected"],
        knowledge_confidence=knowledge_confidence,
    )

    narrative = _build_narrative(
        severity_label=severity_label, finding_type=finding_type, anatomy_zone=vulcan_row.anatomy_zone,
        instrument_family=vulcan_row.instrument_family, recurrence_count=vulcan_row.recurrence_count,
        evidence_readiness_score=veritas_row.readiness_score if veritas_row else None,
        digital_twin_condition_trend=digital_twin_condition_trend, repair_recurrence=repair_recurrence,
        risk_level_value=score_result["risk_level"],
    )

    facility_name, department, service_line = "", "", ""
    if inspection_id is not None:
        inspection = db.query(models.Inspection).filter(models.Inspection.id == inspection_id, models.Inspection.tenant_id == tenant_id).first()
        if inspection is not None:
            facility_name = inspection.facility_name or ""
            department = inspection.department or ""
            if inspection.case_id is not None:
                from app.models.or_connect import SurgicalCase
                case = db.query(SurgicalCase).filter(SurgicalCase.id == inspection.case_id, SurgicalCase.tenant_id == tenant_id).first()
                service_line = case.service_line if case else ""

    row = SentinelXRiskAssessment(
        tenant_id=tenant_id, inspection_id=inspection_id, instrument_identity=instrument_identity,
        instrument_family=vulcan_row.instrument_family, manufacturer_name=vulcan_row.manufacturer_name,
        anatomy_zone=vulcan_row.anatomy_zone, facility_name=facility_name, department=department, service_line=service_line,
        risk_categories_json=json.dumps(categories), risk_score=score_result["risk_score"], risk_level=score_result["risk_level"],
        score_breakdown_json=json.dumps(score_result["score_breakdown"]),
        contamination_severity=severity_label, finding_type=finding_type, recurrence_count=vulcan_row.recurrence_count,
        digital_twin_condition_trend=digital_twin_condition_trend,
        vulcan_assessment_id=vulcan_row.id, veritas_assessment_id=veritas_row.id if veritas_row else None,
        reasoning_narrative=narrative, confidence="high" if knowledge_confidence and knowledge_confidence >= 0.75 else "moderate",
        evidence_json=json.dumps({
            "aegis_signal": aegis_signal, "repair_history_count": len(repairs),
            "confidence_signals": confidence_signals, "supervisor_concern": supervisor_concern,
        }),
        human_review_required=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def to_dict(row: SentinelXRiskAssessment) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "tenant_id": row.tenant_id,
        "inspection_id": row.inspection_id,
        "instrument_identity": row.instrument_identity,
        "instrument_family": row.instrument_family,
        "manufacturer_name": row.manufacturer_name,
        "anatomy_zone": row.anatomy_zone,
        "facility_name": row.facility_name,
        "department": row.department,
        "service_line": row.service_line,
        "risk_categories": json.loads(row.risk_categories_json or "[]"),
        "risk_score": row.risk_score,
        "risk_level": row.risk_level,
        "score_breakdown": json.loads(row.score_breakdown_json or "{}"),
        "contamination_severity": row.contamination_severity,
        "finding_type": row.finding_type,
        "recurrence_count": row.recurrence_count,
        "digital_twin_condition_trend": row.digital_twin_condition_trend,
        "vulcan_assessment_id": row.vulcan_assessment_id,
        "veritas_assessment_id": row.veritas_assessment_id,
        "reasoning_narrative": row.reasoning_narrative,
        "confidence": row.confidence,
        "evidence": json.loads(row.evidence_json or "{}"),
        "human_review_required": row.human_review_required,
        "agent_version": row.agent_version,
        "disclaimer": row.disclaimer,
    }
