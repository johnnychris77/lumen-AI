"""Project Vulcan, Section 1 & 11: Instrument Reliability Agent orchestrator.

Composes every other Vulcan service (taxonomy, progression, anatomy-zone,
repair effectiveness, probable cause, reliability score, Aegis integration)
into one persisted `VulcanReliabilityAssessment`, plus the Section 11
clinical-reasoning narrative. Never finalizes disposition irreversibly --
`recommended_disposition` is always Vulcan's own advisory output;
`final_disposition` stays blank until a supervisor acts via
`vulcan_feedback_service`.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.instrument_knowledge import InstrumentKnowledge
from app.models.vulcan_reliability import (
    DISCLAIMER,
    DISPOSITION_CLINICAL_ENGINEERING_REVIEW,
    DISPOSITION_CONTINUE_ROUTINE_INSPECTION,
    DISPOSITION_INCREASE_INSPECTION_FREQUENCY,
    DISPOSITION_MANUFACTURER_EVALUATION,
    DISPOSITION_QUARANTINE_PENDING_REVIEW,
    DISPOSITION_RECLEAN_AND_REINSPECT,
    DISPOSITION_REMOVE_FROM_SERVICE,
    DISPOSITION_REPAIR_EVALUATION,
    DISPOSITION_SUPERVISOR_REVIEW,
    FAIL_CRACK,
    PROGRESSION_INSUFFICIENT_HISTORY,
    PROGRESSION_RAPIDLY_WORSENING,
    PROGRESSION_SLOWLY_WORSENING,
    PROGRESSION_UNRESOLVED,
    RELIABILITY_ELEVATED_CONCERN,
    RELIABILITY_MONITOR,
    RELIABILITY_RELIABLE,
    RELIABILITY_REPAIR_MANUFACTURER_REVIEW,
    REPAIR_OUTCOME_FAILURE_RECURRED,
    TAXONOMY_GROUP_CLEANING,
    VULCAN_AGENT_VERSION,
    VulcanReliabilityAssessment,
)
from app.services.baseline_comparison_scoring_service import _GENERIC_SCALE, _SEVERITY_SCALES
from app.services.instrument_anatomy import anatomy_profile, get_anatomy
from app.services.vulcan_aegis_integration_service import combine_conclusions, compute_process_variation_signal
from app.services.vulcan_anatomy_zone_service import zone_reliability_analysis
from app.services.vulcan_failure_taxonomy_service import classify_finding_type
from app.services.vulcan_probable_cause_service import classify_probable_causes
from app.services.vulcan_progression_service import compute_progression, findings_timeline
from app.services.vulcan_repair_effectiveness_service import repair_history_for_instrument
from app.services.vulcan_reliability_score_service import compute_reliability_score


def _severity_label(finding_type: str, severity_index: int) -> str:
    scale = _SEVERITY_SCALES.get(finding_type, _GENERIC_SCALE)
    idx = max(0, min(3, severity_index))
    return scale[idx]


def _lookup_manufacturer(db: Session, tenant_id: str, instrument_family: str) -> str:
    row = (
        db.query(InstrumentKnowledge)
        .filter(InstrumentKnowledge.tenant_id == tenant_id, InstrumentKnowledge.instrument_family == instrument_family)
        .first()
    )
    return row.manufacturer if row else ""


def recommend_disposition(
    *, reliability_cat: str, taxonomy_leaf: str, taxonomy_group: str, progression: str, repair_outcome: str | None,
) -> str:
    """Section 8: recommended disposition -- always advisory, never final."""
    if taxonomy_leaf == FAIL_CRACK and progression in (
        PROGRESSION_RAPIDLY_WORSENING, PROGRESSION_SLOWLY_WORSENING, PROGRESSION_UNRESOLVED,
    ):
        return DISPOSITION_REMOVE_FROM_SERVICE

    if reliability_cat == RELIABILITY_RELIABLE:
        return DISPOSITION_CONTINUE_ROUTINE_INSPECTION
    if reliability_cat == RELIABILITY_MONITOR:
        return DISPOSITION_RECLEAN_AND_REINSPECT if taxonomy_group == TAXONOMY_GROUP_CLEANING else DISPOSITION_INCREASE_INSPECTION_FREQUENCY
    if reliability_cat == RELIABILITY_ELEVATED_CONCERN:
        return DISPOSITION_SUPERVISOR_REVIEW
    if reliability_cat == RELIABILITY_REPAIR_MANUFACTURER_REVIEW:
        return DISPOSITION_MANUFACTURER_EVALUATION if repair_outcome == REPAIR_OUTCOME_FAILURE_RECURRED else DISPOSITION_REPAIR_EVALUATION
    # remove_from_service_candidate
    return DISPOSITION_QUARANTINE_PENDING_REVIEW if progression == PROGRESSION_INSUFFICIENT_HISTORY else DISPOSITION_REMOVE_FROM_SERVICE


_DISPOSITION_NEXT_ROLE = {
    DISPOSITION_CONTINUE_ROUTINE_INSPECTION: "SPD technician",
    DISPOSITION_INCREASE_INSPECTION_FREQUENCY: "SPD technician",
    DISPOSITION_RECLEAN_AND_REINSPECT: "SPD technician",
    DISPOSITION_SUPERVISOR_REVIEW: "SPD supervisor",
    DISPOSITION_REPAIR_EVALUATION: "repair vendor",
    DISPOSITION_CLINICAL_ENGINEERING_REVIEW: "clinical engineering",
    DISPOSITION_MANUFACTURER_EVALUATION: "manufacturer",
    DISPOSITION_QUARANTINE_PENDING_REVIEW: "SPD supervisor",
    DISPOSITION_REMOVE_FROM_SERVICE: "SPD supervisor",
}


def _build_narrative(
    *, instrument_family_display: str, zone: str, finding_type: str, severity_index: int,
    recurrence_count: int, days_span: int, progression: str, repair_outcome: str | None, disposition: str,
) -> str:
    if not zone or not finding_type:
        return (
            f"Insufficient inspection history is available for this instrument to produce an "
            f"evidence-based reliability narrative. {DISCLAIMER}"
        )

    severity_label = _severity_label(finding_type, severity_index)
    zone_text = zone.replace("_", " ")
    subject = f"{severity_label.capitalize()} {finding_type.replace('_', ' ')}"

    recurrence_clause = (
        f"The same anatomy zone has been flagged {recurrence_count} times in {days_span} days. "
        if recurrence_count >= 2 else ""
    )
    recurrence_verb = "recurred" if repair_outcome == REPAIR_OUTCOME_FAILURE_RECURRED else "been detected"
    repair_clause = " after repair" if repair_outcome == REPAIR_OUTCOME_FAILURE_RECURRED else ""

    trend_word = {
        PROGRESSION_RAPIDLY_WORSENING: "declining rapidly",
        PROGRESSION_SLOWLY_WORSENING: "declining",
        PROGRESSION_UNRESOLVED: "not improving",
        PROGRESSION_INSUFFICIENT_HISTORY: "not yet established",
    }.get(progression, "stable")

    next_role = _DISPOSITION_NEXT_ROLE.get(disposition, "SPD supervisor")
    disposition_text = disposition.replace("_", " ")

    return (
        f"{subject} has {recurrence_verb} in the {instrument_family_display} {zone_text} region{repair_clause}. "
        f"{recurrence_clause}"
        f"Instrument reliability is {trend_word}. "
        f"Recommend {disposition_text} -- hold for {next_role} evaluation before returning the instrument "
        f"to the pre-sterilization workflow."
    )


def run_reliability_assessment(
    db: Session, tenant_id: str, instrument_identity: str, instrument_type: str = "",
    *, supervisor_concern: bool = False, digital_twin_version: str = "", baseline_version: str = "",
    anatomy_profile_version: str = "",
) -> VulcanReliabilityAssessment:
    """Section 1: run the full Vulcan pipeline and persist one assessment."""
    zone_report = zone_reliability_analysis(db, tenant_id, instrument_identity, instrument_type)
    zones = zone_report["zones"]
    zone_name = zones[0]["anatomy_zone"] if zones else ""

    progression_result = compute_progression(db, tenant_id, instrument_identity, zone=zone_name or None)
    timeline = findings_timeline(db, tenant_id, instrument_identity, zone=zone_name or None)
    latest = timeline[-1] if timeline else None
    finding_type = latest["finding_type"] if latest else ""
    severity_index = latest["severity_index"] if latest else 0
    taxonomy = classify_finding_type(finding_type) if finding_type else {
        "taxonomy_leaf": "insufficient_evidence", "taxonomy_group": "unknown",
    }

    repairs = repair_history_for_instrument(db, tenant_id, instrument_identity)
    zone_repairs = [r for r in repairs if zone_name and r["anatomy_zone"] == zone_name]
    latest_repair = zone_repairs[-1] if zone_repairs else None
    repair_outcome = latest_repair["repair_outcome"] if latest_repair else None

    anatomy = get_anatomy(instrument_type) if instrument_type else {"high_risk_zones": [], "family": "unknown"}
    is_high_risk_zone = zone_name in anatomy.get("high_risk_zones", [])

    probable_causes = classify_probable_causes(
        taxonomy["taxonomy_group"], repair_outcome=repair_outcome, recurrence_count=progression_result["recurrence_count"],
    )

    score_result = compute_reliability_score(
        progression=progression_result["progression"],
        recurrence_count=progression_result["recurrence_count"],
        latest_severity_index=severity_index,
        repair_outcome=repair_outcome,
        is_high_risk_zone=is_high_risk_zone,
        supervisor_concern=supervisor_concern,
        evidence_confidence=progression_result["confidence"],
    )

    disposition = recommend_disposition(
        reliability_cat=score_result["reliability_category"],
        taxonomy_leaf=taxonomy["taxonomy_leaf"],
        taxonomy_group=taxonomy["taxonomy_group"],
        progression=progression_result["progression"],
        repair_outcome=repair_outcome,
    )

    profile = anatomy_profile(instrument_type) if instrument_type else {"instrument_family": "unknown"}
    instrument_family = profile.get("instrument_family", "unknown")
    manufacturer_name = _lookup_manufacturer(db, tenant_id, instrument_family)

    narrative = _build_narrative(
        instrument_family_display=instrument_family.replace("_", " "),
        zone=zone_name, finding_type=finding_type, severity_index=severity_index,
        recurrence_count=progression_result["recurrence_count"], days_span=progression_result["days_span"],
        progression=progression_result["progression"], repair_outcome=repair_outcome, disposition=disposition,
    )

    aegis_conclusion = compute_process_variation_signal(db, tenant_id, instrument_identity, zone=zone_name or None)
    combined_conclusion = combine_conclusions(narrative, aegis_conclusion)

    row = VulcanReliabilityAssessment(
        tenant_id=tenant_id,
        instrument_identity=instrument_identity,
        instrument_family=instrument_family,
        manufacturer_name=manufacturer_name,
        anatomy_zone=zone_name,
        failure_category=taxonomy["taxonomy_leaf"],
        progression=progression_result["progression"],
        recurrence_count=progression_result["recurrence_count"],
        reliability_score=score_result["reliability_score"],
        reliability_category=score_result["reliability_category"],
        score_breakdown_json=json.dumps(score_result["score_breakdown"]),
        probable_causes_json=json.dumps(probable_causes),
        recommended_disposition=disposition,
        reasoning_narrative=narrative,
        confidence=progression_result["confidence"],
        evidence_json=json.dumps({"timeline": [
            {**e, "created_at": e["created_at"].isoformat() if e["created_at"] else None} for e in timeline
        ], "repairs": repairs}),
        rules_applied_json=json.dumps([
            "failure_taxonomy_classification", "progression_model", "anatomy_zone_analysis",
            "repair_effectiveness_analysis", "probable_cause_classification", "reliability_score",
            "recommended_disposition", "aegis_process_variation_signal",
        ]),
        digital_twin_version=digital_twin_version,
        baseline_version=baseline_version,
        anatomy_profile_version=anatomy_profile_version,
        agent_version=VULCAN_AGENT_VERSION,
        aegis_conclusion_json=json.dumps(aegis_conclusion),
        combined_conclusion=combined_conclusion,
        human_review_required=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def to_dict(row: VulcanReliabilityAssessment) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "tenant_id": row.tenant_id,
        "instrument_identity": row.instrument_identity,
        "instrument_family": row.instrument_family,
        "manufacturer_name": row.manufacturer_name,
        "anatomy_zone": row.anatomy_zone,
        "failure_category": row.failure_category,
        "progression": row.progression,
        "recurrence_count": row.recurrence_count,
        "reliability_score": row.reliability_score,
        "reliability_category": row.reliability_category,
        "score_breakdown": json.loads(row.score_breakdown_json or "{}"),
        "probable_causes": json.loads(row.probable_causes_json or "[]"),
        "recommended_disposition": row.recommended_disposition,
        "reasoning_narrative": row.reasoning_narrative,
        "confidence": row.confidence,
        "evidence": json.loads(row.evidence_json or "{}"),
        "rules_applied": json.loads(row.rules_applied_json or "[]"),
        "digital_twin_version": row.digital_twin_version,
        "baseline_version": row.baseline_version,
        "anatomy_profile_version": row.anatomy_profile_version,
        "agent_version": row.agent_version,
        "aegis_conclusion": json.loads(row.aegis_conclusion_json) if row.aegis_conclusion_json else None,
        "combined_conclusion": row.combined_conclusion,
        "human_review_required": row.human_review_required,
        "final_disposition": row.final_disposition,
        "finalized_by": row.finalized_by,
        "finalized_at": row.finalized_at.isoformat() if row.finalized_at else None,
        "disclaimer": row.disclaimer,
    }
