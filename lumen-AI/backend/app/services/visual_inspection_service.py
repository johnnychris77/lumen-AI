from datetime import datetime, timezone
from typing import Dict, List
from uuid import uuid4


DEBRIS_TYPES = [
    "Suspected blood residue",
    "Suspected tissue residue",
    "Suspected bone fragment",
    "Suspected detergent or chemical residue",
    "Water spot or mineral deposit",
    "Fiber or lint contamination",
    "Unknown retained foreign material",
    "No debris observed",
]

QUALITY_ISSUE_TYPES = [
    "Bioburden / retained debris",
    "Stain / discoloration",
    "Rust / corrosion",
    "Pitting",
    "Crack / structural defect",
    "Surface damage",
    "Moisture / wetness",
    "Lumen obstruction",
    "Documentation concern",
    "No quality issue observed",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def calculate_severity_score(payload: Dict) -> int:
    score = 0

    issue_type = (payload.get("quality_issue_type") or "").lower()
    debris_type = (payload.get("suspected_debris_type") or "").lower()
    lumen_visibility = payload.get("lumen_visibility_score", 0)
    coverage = payload.get("estimated_affected_area_percent", 0)
    repeated = payload.get("repeat_finding", False)
    obstruction = payload.get("lumen_obstruction", False)
    organic = payload.get("organic_material_suspected", False)

    if "bioburden" in issue_type or "retained debris" in issue_type:
        score += 35

    if any(term in debris_type for term in ["blood", "tissue", "bone", "foreign"]):
        score += 25

    if organic:
        score += 15

    if obstruction:
        score += 20

    if repeated:
        score += 10

    if coverage:
        if coverage >= 50:
            score += 25
        elif coverage >= 25:
            score += 15
        elif coverage >= 10:
            score += 8

    if lumen_visibility:
        if lumen_visibility < 40:
            score += 15
        elif lumen_visibility < 70:
            score += 8

    if "rust" in issue_type or "corrosion" in issue_type or "pitting" in issue_type:
        score += 30

    if "crack" in issue_type or "structural" in issue_type:
        score += 45

    if "no quality issue" in issue_type or "no debris" in debris_type:
        score = min(score, 15)

    return max(0, min(score, 100))


def calculate_confidence_score(payload: Dict) -> int:
    score = 60

    image_quality = payload.get("image_quality_score", 70)
    lumen_visibility = payload.get("lumen_visibility_score", 70)
    evidence_present = bool(payload.get("evidence_url"))
    technician_certainty = payload.get("technician_certainty_score", 70)

    if image_quality >= 80:
        score += 10
    elif image_quality < 50:
        score -= 20

    if lumen_visibility >= 80:
        score += 10
    elif lumen_visibility < 50:
        score -= 15

    if evidence_present:
        score += 10

    if technician_certainty >= 80:
        score += 10
    elif technician_certainty < 50:
        score -= 15

    return max(0, min(score, 100))


def recommended_actions(severity: int, confidence: int, payload: Dict) -> Dict:
    issue_type = (payload.get("quality_issue_type") or "").lower()
    debris_type = (payload.get("suspected_debris_type") or "").lower()

    reclean_required = False
    second_inspection_required = False
    quarantine_required = False
    ip_review_recommended = False
    vendor_escalation_recommended = False
    capa_recommended = False
    disposition = "Pass"

    if severity <= 20:
        disposition = "Pass"
    elif severity <= 40:
        disposition = "Monitor / Document Observation"
    elif severity <= 60:
        disposition = "Reclean Required"
        reclean_required = True
    elif severity <= 80:
        disposition = "Reclean + Second Inspection Required"
        reclean_required = True
        second_inspection_required = True
    else:
        disposition = "Quarantine / Remove From Service + Escalate"
        reclean_required = True
        second_inspection_required = True
        quarantine_required = True
        capa_recommended = True

    if confidence < 50 and severity >= 40:
        second_inspection_required = True

    if any(term in issue_type for term in ["bioburden", "retained debris", "lumen obstruction"]):
        if severity >= 50:
            ip_review_recommended = True
            capa_recommended = True

    if any(term in debris_type for term in ["blood", "tissue", "bone", "foreign"]):
        if severity >= 50:
            ip_review_recommended = True

    if any(term in issue_type for term in ["rust", "corrosion", "pitting", "crack", "structural"]):
        quarantine_required = True
        vendor_escalation_recommended = bool(payload.get("vendor"))
        capa_recommended = severity >= 60

    if payload.get("repeat_finding"):
        capa_recommended = True

    return {
        "recommended_disposition": disposition,
        "reclean_required": reclean_required,
        "second_inspection_required": second_inspection_required,
        "quarantine_required": quarantine_required,
        "ip_review_recommended": ip_review_recommended,
        "vendor_escalation_recommended": vendor_escalation_recommended,
        "capa_recommended": capa_recommended,
    }


def build_visual_inspection_review(payload: Dict) -> Dict:
    now = utc_now_iso()
    severity = calculate_severity_score(payload)
    confidence = calculate_confidence_score(payload)
    actions = recommended_actions(severity, confidence, payload)

    review_id = payload.get("review_id") or f"VIR-{uuid4()}"

    return {
        "review_id": review_id,
        "inspection_id": payload.get("inspection_id", ""),
        "event_id": payload.get("event_id", ""),
        "facility": payload.get("facility", ""),
        "department": payload.get("department", "SPD"),
        "instrument_name": payload.get("instrument_name", ""),
        "instrument_category": payload.get("instrument_category", ""),
        "vendor": payload.get("vendor", "Unknown Vendor"),
        "tray_name": payload.get("tray_name", ""),
        "evidence_url": payload.get("evidence_url", ""),
        "suspected_debris_type": payload.get("suspected_debris_type", "Unknown retained foreign material"),
        "quality_issue_type": payload.get("quality_issue_type", "Bioburden / retained debris"),
        "image_quality_score": payload.get("image_quality_score", 70),
        "lumen_visibility_score": payload.get("lumen_visibility_score", 70),
        "estimated_affected_area_percent": payload.get("estimated_affected_area_percent", 25),
        "organic_material_suspected": payload.get("organic_material_suspected", False),
        "lumen_obstruction": payload.get("lumen_obstruction", False),
        "repeat_finding": payload.get("repeat_finding", False),
        "technician_certainty_score": payload.get("technician_certainty_score", 70),
        "severity_score": severity,
        "confidence_score": confidence,
        **actions,
        "technician_decision": "",
        "override_reason": "",
        "review_status": "Recommendation Generated",
        "created_at": now,
        "updated_at": now,
        "audit_trail": [
            {
                "timestamp": now,
                "action": "Visual Inspection Review Created",
                "details": f"Severity {severity}, confidence {confidence}, disposition {actions['recommended_disposition']}."
            }
        ],
    }


def finalize_review(review: Dict, payload: Dict) -> Dict:
    now = utc_now_iso()

    technician_decision = payload.get("technician_decision")
    override_reason = payload.get("override_reason", "")

    if not technician_decision:
        raise ValueError("technician_decision is required.")

    recommendation = review.get("recommended_disposition")

    if technician_decision != recommendation and not override_reason:
        raise ValueError("override_reason is required when technician decision differs from LumenAI recommendation.")

    review["technician_decision"] = technician_decision
    review["override_reason"] = override_reason
    review["review_status"] = "Finalized"
    review["updated_at"] = now

    review.setdefault("audit_trail", []).append({
        "timestamp": now,
        "action": "Visual Inspection Review Finalized",
        "details": f"Technician decision: {technician_decision}. Override reason: {override_reason or 'None'}."
    })

    return review
