from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_due_date(days: int = 7) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def determine_capa_type(quality_event: Dict) -> str:
    finding_type = (quality_event.get("finding_type") or "").lower()
    risk_level = (quality_event.get("risk_level") or "").lower()
    vendor = quality_event.get("vendor") or "Unknown Vendor"

    if "bioburden" in finding_type or "retained debris" in finding_type:
        return "IP Review / Patient Safety CAPA"

    if "ifu" in finding_type:
        return "Compliance / IFU CAPA"

    if "crack" in finding_type or "structural" in finding_type:
        return "Instrument Removal / Replacement CAPA"

    if "vendor" in finding_type or vendor != "Unknown Vendor":
        return "Vendor Escalation CAPA"

    if risk_level == "high":
        return "High-Risk Quality CAPA"

    return "General Quality CAPA"


def determine_default_owner(quality_event: Dict) -> str:
    finding_type = (quality_event.get("finding_type") or "").lower()
    risk_level = (quality_event.get("risk_level") or "").lower()

    if "bioburden" in finding_type or "retained debris" in finding_type:
        return "Infection Prevention / SPD Leadership"

    if "ifu" in finding_type:
        return "SPD Leadership / Compliance"

    if "vendor" in finding_type:
        return "SPD Leadership / Vendor Representative"

    if risk_level == "high":
        return "SPD Leadership"

    return "SPD Manager"


def build_problem_statement(quality_event: Dict) -> str:
    instrument = quality_event.get("instrument_name", "Unknown instrument")
    facility = quality_event.get("facility", "Unknown facility")
    finding = quality_event.get("finding_type", "quality finding")
    detail = quality_event.get("finding_detail", "")

    statement = f"{finding} identified on {instrument} at {facility}."

    if detail:
        statement += f" Detail: {detail}"

    return statement


def build_containment_action(quality_event: Dict) -> str:
    finding_type = (quality_event.get("finding_type") or "").lower()

    if "bioburden" in finding_type or "retained debris" in finding_type:
        return "Remove instrument from service, preserve evidence, notify SPD leadership, and escalate to Infection Prevention."

    if "crack" in finding_type or "structural" in finding_type:
        return "Remove instrument from service and evaluate for repair, replacement, or vendor review."

    if "ifu" in finding_type:
        return "Hold item from use until IFU requirements are reviewed and compliant reprocessing instructions are confirmed."

    if "rust" in finding_type or "corrosion" in finding_type:
        return "Inspect related instruments, determine if item requires repair/replacement, and trend for recurrence."

    return "Review finding, determine immediate safety impact, and document containment decision."


def build_capa_from_quality_event(
    quality_event: Dict,
    owner: Optional[str] = None,
    due_days: int = 7,
) -> Dict:
    capa = {
        "capa_id": f"CAPA-{uuid4()}",
        "event_id": quality_event.get("event_id"),
        "inspection_id": quality_event.get("inspection_id"),
        "tenant_id": quality_event.get("tenant_id", "demo"),
        "tenant_name": quality_event.get("tenant_name", "Demo Hospital"),
        "facility": quality_event.get("facility", "Unknown Facility"),
        "instrument_name": quality_event.get("instrument_name", "Unknown Instrument"),
        "instrument_category": quality_event.get("instrument_category", "Unknown Category"),
        "vendor": quality_event.get("vendor", "Unknown Vendor"),
        "finding_type": quality_event.get("finding_type", "Unknown Finding"),
        "risk_level": quality_event.get("risk_level", "Medium"),
        "capa_type": determine_capa_type(quality_event),
        "status": "Open",
        "owner": owner or determine_default_owner(quality_event),
        "due_date": default_due_date(due_days),
        "problem_statement": build_problem_statement(quality_event),
        "containment_action": build_containment_action(quality_event),
        "root_cause": "",
        "corrective_action": "",
        "preventive_action": "",
        "closure_summary": "",
        "evidence_links": [],
        "audit_trail": [
            {
                "timestamp": utc_now_iso(),
                "action": "CAPA Created",
                "details": f"CAPA generated from quality event {quality_event.get('event_id')}.",
            }
        ],
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
    }

    return capa


def update_capa_status(
    capa: Dict,
    new_status: str,
    note: Optional[str] = None,
) -> Dict:
    allowed_statuses = {
        "Open",
        "In Review",
        "Pending IP Review",
        "Pending Vendor Response",
        "Pending Manager Review",
        "Action in Progress",
        "Ready for Closure",
        "Closed",
        "Rejected",
    }

    if new_status not in allowed_statuses:
        raise ValueError(f"Invalid CAPA status: {new_status}")

    old_status = capa.get("status", "Unknown")
    capa["status"] = new_status
    capa["updated_at"] = utc_now_iso()

    capa.setdefault("audit_trail", []).append(
        {
            "timestamp": utc_now_iso(),
            "action": "Status Updated",
            "details": f"Status changed from {old_status} to {new_status}.",
            "note": note or "",
        }
    )

    return capa


def add_capa_update(
    capa: Dict,
    update_type: str,
    content: str,
    author: str = "System/User",
) -> Dict:
    valid_fields = {
        "root_cause": "Root Cause Updated",
        "corrective_action": "Corrective Action Updated",
        "preventive_action": "Preventive Action Updated",
        "closure_summary": "Closure Summary Updated",
        "general_note": "General Note Added",
    }

    if update_type not in valid_fields:
        raise ValueError(f"Invalid update type: {update_type}")

    if update_type != "general_note":
        capa[update_type] = content

    capa["updated_at"] = utc_now_iso()

    capa.setdefault("audit_trail", []).append(
        {
            "timestamp": utc_now_iso(),
            "action": valid_fields[update_type],
            "author": author,
            "details": content,
        }
    )

    return capa


def add_capa_evidence(
    capa: Dict,
    evidence_name: str,
    evidence_type: str,
    evidence_url: str,
    added_by: str = "System/User",
) -> Dict:
    evidence = {
        "evidence_id": f"EVID-{uuid4()}",
        "name": evidence_name,
        "type": evidence_type,
        "url": evidence_url,
        "added_by": added_by,
        "added_at": utc_now_iso(),
    }

    capa.setdefault("evidence_links", []).append(evidence)
    capa["updated_at"] = utc_now_iso()

    capa.setdefault("audit_trail", []).append(
        {
            "timestamp": utc_now_iso(),
            "action": "Evidence Added",
            "author": added_by,
            "details": f"{evidence_type}: {evidence_name}",
        }
    )

    return capa
