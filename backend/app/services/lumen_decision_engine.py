"""Section 10 — The Lumen Decision Engine.

The single orchestrator that turns the existing, already-honest
`baseline_comparison_scoring_service.analyze_inspection()` output into the
doctrine-compliant Result Contract (Section 14): a strict separation of
Observation (Section 1-3A), Assessment (3B), Policy (3C), and
Recommendation (3C) layers.

Architectural separation this module enforces, per Section 10:

    "Do not place hospital policy thresholds inside the vision-model code.
    The vision model observes. The baseline service compares. The policy
    engine resolves organizational rules. The Decision Engine recommends."

This module:
  - never re-runs vision inference (that's `app/ai/inference.py`),
  - never re-implements baseline comparison (that's already computed in
    `analysis["baseline_match_score"]`/`baseline_deviation_score`),
  - resolves org policy via `policy_resolution_service` only,
  - is the ONLY place a supervisor-requirement decision is made from an
    observation + policy pair.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.lumen_decision_engine import LumenDecisionRecord
from app.services import observation_taxonomy as taxonomy
from app.services import policy_resolution_service
from app.services import unknown_finding_service
from app.services.enterprise_audit_service import record_enterprise_audit_event

# Recommendation action vocabulary (Section 3C).
ACTION_CONTINUE = "continue_workflow"
ACTION_FOCUSED_REINSPECT = "focused_technician_reinspect"
ACTION_CAPTURE_ADDITIONAL_IMAGE = "capture_additional_image"
ACTION_RECLEAN_REINSPECT = "reclean_and_reinspect"
ACTION_HOLD_SUPERVISOR = "supervisor_attention_required"
ACTION_SUPERVISOR_APPROVAL = "supervisor_approval_required"
ACTION_REPAIR_EVALUATION = "repair_evaluation"
ACTION_MANUFACTURER_EVALUATION = "manufacturer_evaluation"
ACTION_HOLD_FROM_PROCESSING = "hold_from_further_processing"
ACTION_REMOVE_FROM_SERVICE_CONSIDERATION = "remove_from_service_consideration"

_STRUCTURAL_ACTION_BY_RISK = {
    "critical": ACTION_REMOVE_FROM_SERVICE_CONSIDERATION,
    "high": ACTION_REPAIR_EVALUATION,
}


def _present_findings(predicted_findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [f for f in predicted_findings if f.get("probability", 0.0) >= 0.5]


def _pick_primary(findings: list[dict[str, Any]]) -> dict[str, Any]:
    _risk_rank = {"critical": 3, "high": 2, "low": 1, "none": 0}
    return sorted(
        findings,
        key=lambda f: (f.get("severity_index", 0), _risk_rank.get(f.get("spd_risk", "low"), 0), f.get("probability", 0.0)),
        reverse=True,
    )[0]


def _no_baseline_or_failed_contract(analysis: dict[str, Any]) -> dict[str, Any]:
    status = analysis.get("analysis_status")
    reason = (
        "No approved baseline was found for this instrument; supervisor review is "
        "required before any recommendation can be made."
        if status == "supervisor_review_required"
        else "AI analysis was unavailable for this submission; supervisor review is required."
    )
    return {
        "observation": {
            "category": None,
            "display_label": taxonomy.NOT_EVALUATED_BY_CURRENT_MODEL,
            "confidence": None,
            "status": status or "analysis_unavailable",
        },
        "assessment": {
            "image_quality": "not_assessed",
            "instrument_family": "",
            "anatomy_zone": "",
            "anatomy_zone_risk": "",
            "baseline_similarity": None,
            "baseline_deviation": None,
            "baseline_source": None,
            "baseline_version": None,
            "digital_twin_trend": "not_available",
        },
        "policy": {"policy_id": "", "policy_version": "", "scope": "", "minimum_baseline_similarity": None},
        "recommendation": {
            "action": ACTION_HOLD_SUPERVISOR,
            "supervisor_required": True,
            "reason": reason,
            "escalation_condition": "An approved baseline is established and analysis completes successfully.",
        },
        "limitations": analysis.get("model_result", {}).get("limitations", []),
        "human_decision_required": True,
        "unknown_finding": None,
        "guidance": {
            "what_was_observed": taxonomy.NOT_EVALUATED_BY_CURRENT_MODEL,
            "supervisor_help_required": "Yes — no scoreable result exists yet for this inspection.",
        },
    }


def build_decision(
    db: Session,
    *,
    inspection_id: int,
    tenant_id: str,
    facility_name: str,
    department: str,
    instrument_type: str,
    analysis: dict[str, Any],
    persist: bool = True,
) -> dict[str, Any]:
    """Section 10/14 — build (and, by default, persist) the Result Contract
    for one inspection. Idempotent by design: callers should call this once,
    at inspection-submission time; a persisted `LumenDecisionRecord` is never
    recomputed or overwritten afterward (Section 16/18)."""

    if analysis.get("analysis_status") != "completed":
        contract = _no_baseline_or_failed_contract(analysis)
    else:
        contract = _build_completed_contract(
            db, tenant_id=tenant_id, instrument_type=instrument_type,
            department=department, facility_name=facility_name,
            inspection_id=inspection_id, analysis=analysis,
        )

    contract["inspection_id"] = inspection_id

    if persist:
        _persist_record(db, inspection_id=inspection_id, tenant_id=tenant_id, facility_name=facility_name, contract=contract)
        record_enterprise_audit_event(
            db,
            action_type="lumen_decision_recorded",
            resource_type="inspection",
            resource_id=str(inspection_id),
            tenant_id=tenant_id,
            details={
                "observation_category": contract["observation"]["category"],
                "recommendation_action": contract["recommendation"]["action"],
                "supervisor_required": contract["recommendation"]["supervisor_required"],
                "policy_id": contract["policy"]["policy_id"],
                "policy_version": contract["policy"]["policy_version"],
            },
        )

    return contract


def _build_completed_contract(
    db: Session, *, tenant_id: str, instrument_type: str, department: str,
    facility_name: str, inspection_id: int, analysis: dict[str, Any],
) -> dict[str, Any]:
    model_result = analysis.get("model_result", {})
    supported = model_result.get("supported_categories", [])
    predicted_findings = analysis.get("predicted_findings", [])
    present = _present_findings(predicted_findings)

    eligible = [f for f in present if f["type"] in supported and f["type"] not in taxonomy.STRUCTURAL_KPIS]
    unsupported_present = [
        f for f in present
        if f["type"] not in supported and f["type"] not in taxonomy.STRUCTURAL_KPIS
    ]
    structural_present = [f for f in present if f["type"] in taxonomy.STRUCTURAL_KPIS]

    baseline_similarity = analysis.get("baseline_match_score")
    baseline_deviation = analysis.get("baseline_deviation_score")
    anatomy_zone = ""
    anatomy_zone_risk = ""
    resolved_instrument_family = instrument_type

    unknown_finding_record = None

    resolved_policy = policy_resolution_service.resolve_active_policy(
        db, tenant_id=tenant_id, instrument_family=instrument_type,
        anatomy_zone=anatomy_zone, department=department, facility=facility_name,
    )
    policy_out = {
        "policy_id": resolved_policy["policy_id"],
        "policy_version": resolved_policy["version"],
        "scope": resolved_policy["scope"],
        "minimum_baseline_similarity": resolved_policy["pass_threshold"],
    }

    if unsupported_present:
        primary = _pick_primary(unsupported_present)
        anatomy_zone = primary.get("instrument_zone", "")
        anatomy_zone_risk = primary.get("zone_risk", "")
        resolved_instrument_family = primary.get("instrument_family", instrument_type)
        observation = {
            "category": taxonomy.OBSERVATION_UNKNOWN_FOREIGN,
            "display_label": taxonomy.display_label(taxonomy.OBSERVATION_UNKNOWN_FOREIGN),
            "confidence": None,
            "status": "unknown_review_required",
        }
        recommendation = {
            "action": ACTION_HOLD_SUPERVISOR,
            "supervisor_required": True,
            "reason": (
                "A finding was observed in a category the current model is not "
                "validated to evaluate — this requires supervisor classification "
                "before any recommendation can be finalized."
            ),
            "escalation_condition": "Resolved once a supervisor classifies this finding.",
        }
        unknown_finding_record = unknown_finding_service.open_unknown_finding(
            db, inspection_id=inspection_id, tenant_id=tenant_id,
            instrument_family=resolved_instrument_family, anatomy_zone=anatomy_zone,
            model_output={"type": primary["type"], "probability": primary["probability"]},
            model_confidence=primary.get("confidence"),
            baseline_similarity=baseline_similarity,
            evidence_limitations=model_result.get("limitations", []),
            model_version=model_result.get("model_version", ""),
        )
    elif eligible:
        primary = _pick_primary(eligible)
        anatomy_zone = primary.get("instrument_zone", "")
        anatomy_zone_risk = primary.get("zone_risk", "")
        resolved_instrument_family = primary.get("instrument_family", instrument_type)
        category = taxonomy.kpi_to_observation_category(primary["type"])
        observation = {
            "category": category,
            "display_label": taxonomy.display_label(category),
            "confidence": primary.get("confidence"),
            "status": "model_observation",
        }
        if category in taxonomy.CONTAMINATION_LIKE_CATEGORIES:
            # Section 4 — the Contamination Safety Rule: a high baseline
            # similarity must NEVER cancel a probable contamination
            # observation.
            reason = f"{observation['display_label']} was observed."
            if baseline_similarity is not None and baseline_similarity >= resolved_policy["pass_threshold"]:
                reason = (
                    f"A probable retained contaminant was observed even though the "
                    f"overall instrument appearance remains similar to the approved "
                    f"baseline ({round(baseline_similarity * 100)}% baseline similarity)."
                )
            recommendation = {
                "action": ACTION_RECLEAN_REINSPECT,
                "supervisor_required": False,
                "reason": reason,
                "escalation_condition": (
                    "Supervisor review required if this finding remains after "
                    "recleaning, if the material is unknown, or if evidence is conflicting."
                ),
            }
        elif primary.get("spd_risk") in ("critical", "high"):
            recommendation = {
                "action": ACTION_HOLD_SUPERVISOR,
                "supervisor_required": True,
                "reason": f"{observation['display_label']} was observed at a level requiring supervisor attention.",
                "escalation_condition": "Resolved once a supervisor reviews and confirms the disposition.",
            }
        else:
            recommendation = _baseline_policy_recommendation(baseline_similarity, resolved_policy, observation["display_label"])
    elif structural_present:
        primary = _pick_primary(structural_present)
        anatomy_zone = primary.get("instrument_zone", "")
        anatomy_zone_risk = primary.get("zone_risk", "")
        resolved_instrument_family = primary.get("instrument_family", instrument_type)
        observation = {
            "category": None,
            "display_label": f"Probable structural finding: {primary.get('label', primary['type'])}",
            "confidence": primary.get("confidence"),
            "status": "structural_finding",
        }
        risk_tier = primary.get("spd_risk", "high")
        action = _STRUCTURAL_ACTION_BY_RISK.get(risk_tier, ACTION_REPAIR_EVALUATION)
        recommendation = {
            "action": action,
            "supervisor_required": True,
            "reason": analysis.get("recommendation") or f"{observation['display_label']} requires supervisor-directed evaluation.",
            "escalation_condition": "Repair or manufacturer evaluation completed and the instrument re-inspected.",
        }
    else:
        observation = {
            "category": taxonomy.OBSERVATION_NO_ABNORMALITY,
            "display_label": taxonomy.display_label(taxonomy.OBSERVATION_NO_ABNORMALITY),
            "confidence": analysis.get("confidence"),
            "status": "model_observation",
        }
        recommendation = _baseline_policy_recommendation(baseline_similarity, resolved_policy, observation["display_label"])

    contract = {
        "observation": observation,
        "assessment": {
            "image_quality": model_result.get("image_quality_status", "not_assessed"),
            "instrument_family": resolved_instrument_family,
            "anatomy_zone": anatomy_zone,
            "anatomy_zone_risk": anatomy_zone_risk,
            "baseline_similarity": baseline_similarity,
            "baseline_deviation": baseline_deviation,
            "baseline_source": analysis.get("baseline_source"),
            "baseline_version": analysis.get("baseline_version"),
            "digital_twin_trend": "not_available",
        },
        "policy": policy_out,
        "recommendation": recommendation,
        "limitations": model_result.get("limitations", []) + [
            "The observation is visual and has not been laboratory confirmed.",
            "Current model evaluates only supported categories.",
        ],
        "human_decision_required": True,
        "unknown_finding": (
            {"unknown_finding_review_id": unknown_finding_record.id} if unknown_finding_record else None
        ),
        "guidance": _build_guidance(observation, resolved_instrument_family, anatomy_zone, anatomy_zone_risk, baseline_similarity, policy_out, recommendation),
    }
    return contract


def _baseline_policy_recommendation(baseline_similarity: float | None, resolved_policy: dict[str, Any], display_label: str) -> dict[str, Any]:
    pass_threshold = resolved_policy["pass_threshold"]
    tech_threshold = resolved_policy["technician_review_threshold"]
    policy_name = resolved_policy.get("policy_name", "LumenAI Recommended Starting Policy")

    if baseline_similarity is None:
        return {
            "action": ACTION_CAPTURE_ADDITIONAL_IMAGE,
            "supervisor_required": False,
            "reason": "Baseline similarity could not be computed for this submission.",
            "escalation_condition": "Supervisor review required if a usable image cannot be captured.",
        }

    pct = round(baseline_similarity * 100)
    pass_pct = round(pass_threshold * 100)
    tech_pct = round(tech_threshold * 100)

    if baseline_similarity >= pass_threshold:
        return {
            "action": ACTION_CONTINUE,
            "supervisor_required": False,
            "reason": (
                f"{display_label}; baseline similarity {pct}% meets the {policy_name} "
                f"threshold of {pass_pct}%."
            ),
            "escalation_condition": f"Applies only while baseline similarity remains at/above {pass_pct}%.",
        }
    if baseline_similarity >= tech_threshold:
        return {
            "action": ACTION_FOCUSED_REINSPECT,
            "supervisor_required": False,
            "reason": (
                f"Baseline similarity {pct}% is below the {policy_name}'s {pass_pct}% "
                f"pass threshold but at/above its {tech_pct}% technician-review threshold."
            ),
            "escalation_condition": f"Supervisor attention required if similarity remains below {tech_pct}% after reinspection.",
        }
    return {
        "action": ACTION_HOLD_SUPERVISOR,
        "supervisor_required": True,
        "reason": (
            f"Baseline similarity {pct}% is below the {policy_name}'s approved "
            f"review threshold of {tech_pct}%."
        ),
        "escalation_condition": "Resolved once a supervisor reviews and confirms the disposition.",
    }


def _build_guidance(
    observation: dict[str, Any], instrument_family: str, anatomy_zone: str,
    anatomy_zone_risk: str, baseline_similarity: float | None, policy: dict[str, Any],
    recommendation: dict[str, Any],
) -> dict[str, Any]:
    """Section 12 — Technician Guidance content."""
    return {
        "what_was_observed": observation["display_label"],
        "where": anatomy_zone or "not localized to a specific zone",
        "why_this_matters": (
            f"{anatomy_zone or 'This zone'} is a {anatomy_zone_risk or 'standard'}-risk retention area for {instrument_family or 'this instrument family'}."
            if anatomy_zone else "No specific anatomy zone was implicated."
        ),
        "image_quality_feedback": "Acceptable for this evaluation." if baseline_similarity is not None else "Insufficient — consider recapturing.",
        "baseline_comparison": (
            f"{round(baseline_similarity * 100)}% similarity to the approved baseline."
            if baseline_similarity is not None else "Not available."
        ),
        "applicable_policy": f"{policy.get('scope', '')} policy {policy.get('policy_id', '')} v{policy.get('policy_version', '')}".strip(),
        "recommended_action": recommendation["action"],
        "supervisor_help_required": "Yes" if recommendation["supervisor_required"] else "Not required for this step",
        "evidence_limitations": "This is a visual pattern-match; material composition has not been laboratory confirmed.",
        "learning_tip": "Review the anatomy-zone reasoning above before repeating the inspection.",
    }


def _persist_record(db: Session, *, inspection_id: int, tenant_id: str, facility_name: str, contract: dict[str, Any]) -> LumenDecisionRecord:
    obs = contract["observation"]
    asm = contract["assessment"]
    pol = contract["policy"]
    rec = contract["recommendation"]

    record = LumenDecisionRecord(
        inspection_id=inspection_id,
        tenant_id=tenant_id,
        facility_name=facility_name or "",
        observation_category=obs["category"],
        observation_display_label=obs["display_label"],
        observation_confidence=obs["confidence"],
        observation_status=obs["status"],
        model_version=contract.get("model_version", ""),
        image_quality=asm["image_quality"],
        instrument_family=asm["instrument_family"],
        anatomy_zone=asm["anatomy_zone"],
        anatomy_zone_risk=asm["anatomy_zone_risk"],
        baseline_similarity=asm["baseline_similarity"],
        baseline_deviation=asm["baseline_deviation"],
        baseline_source=asm["baseline_source"],
        baseline_version=asm["baseline_version"],
        digital_twin_trend=asm["digital_twin_trend"],
        policy_id=pol["policy_id"],
        policy_version=pol["policy_version"],
        policy_scope=pol["scope"],
        threshold_used=pol["minimum_baseline_similarity"],
        recommended_action=rec["action"],
        supervisor_required=rec["supervisor_required"],
        recommendation_reason=rec["reason"],
        escalation_condition=rec["escalation_condition"],
        limitations_json=json.dumps(contract.get("limitations", [])),
        human_review_required=contract.get("human_decision_required", True),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_record_for_inspection(db: Session, inspection_id: int) -> LumenDecisionRecord | None:
    return (
        db.query(LumenDecisionRecord)
        .filter(LumenDecisionRecord.inspection_id == inspection_id)
        .order_by(LumenDecisionRecord.created_at.desc())
        .first()
    )


def record_human_followthrough(
    db: Session, record: LumenDecisionRecord, *, actor: str, actor_role: str, role_kind: str,
    action_text: str, override_reason: str | None = None, final_decision: str | None = None,
) -> LumenDecisionRecord:
    """Section 16 — records a human's follow-through action WITHOUT ever
    overwriting the original AI observation fields set at creation."""
    now = datetime.now(timezone.utc)
    if role_kind == "technician":
        record.technician_action = action_text
        record.technician_actor = actor
        record.technician_action_at = now
    else:
        record.supervisor_action = action_text
        record.supervisor_actor = actor
        record.supervisor_action_at = now
    if override_reason:
        record.override_reason = override_reason
    if final_decision:
        record.final_human_decision = final_decision
    db.commit()
    db.refresh(record)
    record_enterprise_audit_event(
        db,
        action_type="lumen_decision_human_followthrough",
        resource_type="inspection",
        resource_id=str(record.inspection_id),
        tenant_id=record.tenant_id,
        actor_email=actor,
        actor_role=actor_role,
        details={"role_kind": role_kind, "action_text": action_text, "final_decision": final_decision},
    )
    return record
