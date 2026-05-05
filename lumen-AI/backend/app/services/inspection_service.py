from datetime import datetime, timezone
from typing import Dict
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify_finding(payload: Dict) -> Dict:
    finding_type = (payload.get("finding_type") or "").lower()
    finding_detail = (payload.get("finding_detail") or "").lower()
    instrument_category = (payload.get("instrument_category") or "").lower()
    vendor = payload.get("vendor") or "Unknown Vendor"

    combined_text = f"{finding_type} {finding_detail} {instrument_category}".lower()

    risk_level = "Low"
    classification = "Quality Observation"
    recommended_routing = "SPD Leadership Review"
    capa_required = False
    recommended_containment = "Document finding and continue routine quality monitoring."

    if any(term in combined_text for term in ["bioburden", "retained debris", "blood", "tissue", "brown debris"]):
        risk_level = "High"
        classification = "Suspected Retained Bioburden"
        recommended_routing = "Infection Prevention Review + CAPA"
        capa_required = True
        recommended_containment = "Remove instrument from service, preserve evidence, notify SPD leadership and Infection Prevention."

    elif any(term in combined_text for term in ["crack", "broken", "structural", "damaged", "jaw alignment"]):
        risk_level = "Medium"
        classification = "Instrument Integrity Concern"
        recommended_routing = "SPD Leadership Review + Vendor / Repair Review"
        capa_required = True
        recommended_containment = "Remove instrument from service and route for repair or replacement review."

    elif any(term in combined_text for term in ["vendor", "loaner", "missing documentation", "late tray", "incorrect tray"]):
        risk_level = "Medium"
        classification = "Vendor Quality / Documentation Concern"
        recommended_routing = "Vendor Escalation + SPD Leadership Review"
        capa_required = True
        recommended_containment = "Hold tray or instrument as appropriate and request vendor documentation or response."

    elif any(term in combined_text for term in ["count sheet", "preference card", "documentation", "label"]):
        risk_level = "Low"
        classification = "Documentation / Process Observation"
        recommended_routing = "SPD Manager Review"
        capa_required = False
        recommended_containment = "Correct documentation discrepancy and trend for recurrence."

    if "cannulated" in instrument_category and risk_level in ["Medium", "High"]:
        recommended_containment += " Consider borescope inspection for similar cannulated instruments."

    return {
        "classification": classification,
        "risk_level": payload.get("risk_level") or risk_level,
        "recommended_routing": recommended_routing,
        "recommended_containment": recommended_containment,
        "capa_required": capa_required,
        "vendor_escalation_recommended": vendor != "Unknown Vendor" and capa_required,
        "ip_review_recommended": risk_level == "High" or "bioburden" in combined_text,
    }


def build_inspection_record(payload: Dict) -> Dict:
    now = utc_now_iso()
    decision = classify_finding(payload)

    inspection_id = payload.get("inspection_id") or f"INS-{uuid4()}"

    return {
        "inspection_id": inspection_id,
        "event_id": payload.get("event_id") or f"QEV-{uuid4()}",
        "tenant_id": payload.get("tenant_id", "demo"),
        "tenant_name": payload.get("tenant_name", "Demo Hospital"),
        "facility": payload.get("facility"),
        "department": payload.get("department", "SPD"),
        "instrument_name": payload.get("instrument_name"),
        "instrument_category": payload.get("instrument_category"),
        "vendor": payload.get("vendor", "Unknown Vendor"),
        "tray_name": payload.get("tray_name"),
        "finding_type": payload.get("finding_type"),
        "finding_detail": payload.get("finding_detail"),
        "evidence_url": payload.get("evidence_url", ""),
        "inspector": payload.get("inspector", "Dashboard User"),
        "classification": decision["classification"],
        "risk_level": decision["risk_level"],
        "recommended_routing": decision["recommended_routing"],
        "recommended_containment": decision["recommended_containment"],
        "capa_required": decision["capa_required"],
        "vendor_escalation_recommended": decision["vendor_escalation_recommended"],
        "ip_review_recommended": decision["ip_review_recommended"],
        "capa_id": "",
        "status": "Intake Reviewed",
        "created_at": now,
        "updated_at": now,
        "audit_trail": [
            {
                "timestamp": now,
                "action": "Inspection Intake Created",
                "details": f"Inspection intake created and classified as {decision['classification']}."
            }
        ],
    }
