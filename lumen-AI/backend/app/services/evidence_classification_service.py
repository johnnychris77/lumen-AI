from datetime import datetime, timezone
from typing import Dict


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify_evidence(record: Dict, payload: Dict) -> Dict:
    filename = (record.get("original_filename") or "").lower()
    finding_category = (record.get("finding_category") or "").lower()
    evidence_type = (record.get("evidence_type") or "").lower()
    instrument_name = (record.get("instrument_name") or "").lower()

    provided_debris = payload.get("suspected_debris_type", "")
    provided_material = payload.get("suspected_material_type", "")
    provided_issue = payload.get("quality_issue_type", "")

    suspected_debris_type = provided_debris or "Unknown retained foreign material"
    suspected_material_type = provided_material or "Unknown material"
    quality_issue_type = provided_issue or "Quality observation"

    image_quality_score = int(payload.get("image_quality_score", 80))
    ai_confidence_score = 65
    severity_score = 30
    recommended_action = "Human review recommended"

    combined = f"{filename} {finding_category} {evidence_type} {instrument_name}".lower()

    if any(term in combined for term in ["bioburden", "blood", "debris", "borescope", "lumen"]):
        suspected_debris_type = provided_debris or "Suspected retained debris"
        suspected_material_type = provided_material or "Possible organic material"
        quality_issue_type = provided_issue or "Bioburden / retained debris"
        ai_confidence_score = 82
        severity_score = 78
        recommended_action = "Reclean required + second inspection recommended"

    if any(term in combined for term in ["rust", "corrosion", "pitting"]):
        suspected_debris_type = provided_debris or "No debris classification"
        suspected_material_type = provided_material or "Corrosion / oxidation"
        quality_issue_type = provided_issue or "Rust / corrosion"
        ai_confidence_score = 78
        severity_score = 72
        recommended_action = "Remove from service and escalate"

    if "vendor" in combined:
        ai_confidence_score = max(ai_confidence_score, 70)
        recommended_action = f"{recommended_action}; consider vendor review"

    if image_quality_score < 50:
        ai_confidence_score = min(ai_confidence_score, 45)
        recommended_action = "Image quality insufficient; repeat image capture and human review required"

    final_classification = quality_issue_type

    return {
        "suspected_debris_type": suspected_debris_type,
        "suspected_material_type": suspected_material_type,
        "quality_issue_type": quality_issue_type,
        "image_quality_score": image_quality_score,
        "ai_confidence_score": ai_confidence_score,
        "severity_score": severity_score,
        "recommended_action": recommended_action,
        "ai_review_status": "Reviewed",
        "human_review_status": "Pending Human Confirmation",
        "final_classification": final_classification,
        "classified_at": utc_now_iso(),
        "classification_method": "rules_based_ai_ready_v1",
    }


def apply_human_review(record: Dict, payload: Dict) -> Dict:
    confirmed = payload.get("human_confirmed_classification")
    override_reason = payload.get("human_override_reason", "")

    if not confirmed:
        raise ValueError("human_confirmed_classification is required.")

    ai_classification = record.get("final_classification", "")

    if ai_classification and confirmed != ai_classification and not override_reason:
        raise ValueError("human_override_reason is required when human classification differs from AI classification.")

    record["human_confirmed_classification"] = confirmed
    record["human_override_reason"] = override_reason
    record["human_review_status"] = "Human Confirmed"
    record["final_classification"] = confirmed
    record["updated_at"] = utc_now_iso()

    metadata = record.get("metadata") or {}
    metadata["human_reviewed_at"] = record["updated_at"]
    metadata["human_reviewer"] = payload.get("reviewer", "Dashboard User")
    record["metadata"] = metadata

    return record
