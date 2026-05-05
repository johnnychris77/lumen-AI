from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Header

from backend.app.services.capa_service import (
    build_capa_from_quality_event,
    update_capa_status,
    add_capa_update,
    add_capa_evidence,
)

from backend.app.services.capa_store import (
    init_capa_db,
    save_capa,
    get_capa as store_get_capa,
    list_capas as store_list_capas,
)


router = APIRouter(prefix="/api/capa", tags=["CAPA / Quality Actions"])

def validate_capa_closure_ready(capa: Dict):
    missing = []

    if not capa.get("root_cause"):
        missing.append("root_cause")

    if not capa.get("corrective_action"):
        missing.append("corrective_action")

    if not capa.get("preventive_action"):
        missing.append("preventive_action")

    if not capa.get("closure_summary"):
        missing.append("closure_summary")

    if not capa.get("evidence_links"):
        missing.append("evidence_links")

    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "CAPA cannot be closed until required verification fields are complete.",
                "missing_fields": missing,
                "required_for_closure": [
                    "root_cause",
                    "corrective_action",
                    "preventive_action",
                    "closure_summary",
                    "at least one evidence item",
                ],
            },
        )



@router.on_event("startup")
def startup_capa_store():
    init_capa_db()


@router.post("/from-quality-event")
def create_capa_from_quality_event(
    quality_event: Dict,
    owner: Optional[str] = None,
    due_days: int = 7,
    x_tenant_id: str = Header(default="demo"),
    x_tenant_name: str = Header(default="Demo Hospital"),
):
    quality_event["tenant_id"] = quality_event.get("tenant_id") or x_tenant_id
    quality_event["tenant_name"] = quality_event.get("tenant_name") or x_tenant_name

    capa = build_capa_from_quality_event(
        quality_event=quality_event,
        owner=owner,
        due_days=due_days,
    )

    save_capa(capa)
    return capa


@router.get("/")
def list_capas(
    status: Optional[str] = None,
    facility: Optional[str] = None,
    vendor: Optional[str] = None,
):
    results = store_list_capas(status=status, facility=facility, vendor=vendor)

    return {
        "count": len(results),
        "items": results,
    }


@router.get("/dashboard/summary")
def capa_dashboard_summary():
    items = store_list_capas()
    now = datetime.now(timezone.utc)

    open_capas = [item for item in items if item.get("status") == "Open"]
    pending_ip_review = [
        item for item in items if item.get("status") == "Pending IP Review"
    ]
    vendor_pending = [
        item for item in items if item.get("status") == "Pending Vendor Response"
    ]
    high_risk = [item for item in items if item.get("risk_level") == "High"]

    overdue = []
    due_soon = []
    days_to_due_values = []

    for item in items:
        due_date_raw = item.get("due_date")

        if not due_date_raw:
            continue

        try:
            due_date = datetime.fromisoformat(due_date_raw.replace("Z", "+00:00"))
            days_to_due = (due_date - now).days
            days_to_due_values.append(days_to_due)

            if days_to_due < 0 and item.get("status") != "Closed":
                overdue.append(item)

            if 0 <= days_to_due <= 3 and item.get("status") != "Closed":
                due_soon.append(item)

        except Exception:
            continue

    avg_days_to_due = (
        round(sum(days_to_due_values) / len(days_to_due_values), 1)
        if days_to_due_values
        else None
    )

    recent_items = sorted(
        items,
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )[:10]

    return {
        "total_capas": len(items),
        "open_capas": len(open_capas),
        "pending_ip_review": len(pending_ip_review),
        "vendor_pending": len(vendor_pending),
        "high_risk": len(high_risk),
        "overdue": len(overdue),
        "due_soon": len(due_soon),
        "average_days_to_due": avg_days_to_due,
        "recent_items": recent_items,
    }


@router.get("/summary/metrics")
def capa_summary_metrics():
    items = store_list_capas()

    return {
        "total_capas": len(items),
        "open": len([item for item in items if item.get("status") == "Open"]),
        "pending_ip_review": len(
            [item for item in items if item.get("status") == "Pending IP Review"]
        ),
        "pending_vendor_response": len(
            [item for item in items if item.get("status") == "Pending Vendor Response"]
        ),
        "closed": len([item for item in items if item.get("status") == "Closed"]),
        "high_risk": len([item for item in items if item.get("risk_level") == "High"]),
    }








@router.post("/seed/demo-analytics")
def seed_demo_capa_analytics():
    demo_events = [
        {
            "event_id": "QEV-SEED-001",
            "inspection_id": "INS-SEED-001",
            "tenant_id": "bonsecours",
            "tenant_name": "Bon Secours",
            "facility": "St. Mary’s Hospital",
            "department": "SPD",
            "instrument_name": "Frazier suction",
            "instrument_category": "Cannulated instrument",
            "vendor": "Medtronic",
            "tray_name": "Neuro basic tray",
            "finding_type": "bioburden suspected",
            "finding_detail": "Brown retained debris observed inside lumen",
            "risk_level": "High",
            "target_status": "Pending IP Review",
        },
        {
            "event_id": "QEV-SEED-002",
            "inspection_id": "INS-SEED-002",
            "tenant_id": "bonsecours",
            "tenant_name": "Bon Secours",
            "facility": "St. Francis Medical Center",
            "department": "SPD",
            "instrument_name": "Cannulated drill",
            "instrument_category": "Cannulated instrument",
            "vendor": "Stryker",
            "tray_name": "Ortho power tray",
            "finding_type": "bioburden suspected",
            "finding_detail": "Retained material observed inside cannulation",
            "risk_level": "High",
            "target_status": "Open",
        },
        {
            "event_id": "QEV-SEED-003",
            "inspection_id": "INS-SEED-003",
            "tenant_id": "bonsecours",
            "tenant_name": "Bon Secours",
            "facility": "Memorial Regional Medical Center",
            "department": "SPD",
            "instrument_name": "Rongeur",
            "instrument_category": "Manual instrument",
            "vendor": "DePuy Synthes",
            "tray_name": "Spine vendor tray",
            "finding_type": "structural damage",
            "finding_detail": "Jaw alignment concern identified during inspection",
            "risk_level": "Medium",
            "target_status": "Action in Progress",
        },
        {
            "event_id": "QEV-SEED-004",
            "inspection_id": "INS-SEED-004",
            "tenant_id": "bonsecours",
            "tenant_name": "Bon Secours",
            "facility": "Offsite Reprocessing Center",
            "department": "SPD",
            "instrument_name": "Vendor loaner tray",
            "instrument_category": "Vendor tray",
            "vendor": "Unknown Vendor",
            "tray_name": "Loaner orthopedic tray",
            "finding_type": "vendor documentation issue",
            "finding_detail": "Missing complete vendor tray documentation at intake",
            "risk_level": "Medium",
            "target_status": "Pending Vendor Response",
        },
        {
            "event_id": "QEV-SEED-005",
            "inspection_id": "INS-SEED-005",
            "tenant_id": "bonsecours",
            "tenant_name": "Bon Secours",
            "facility": "St. Mary’s Hospital",
            "department": "SPD",
            "instrument_name": "Robotic accessory",
            "instrument_category": "Robotic instrument",
            "vendor": "Intuitive",
            "tray_name": "Robotic accessory set",
            "finding_type": "count sheet discrepancy",
            "finding_detail": "Count sheet did not match tray contents",
            "risk_level": "Low",
            "target_status": "Closed",
        },
        {
            "event_id": "QEV-SEED-006",
            "inspection_id": "INS-SEED-006",
            "tenant_id": "bonsecours",
            "tenant_name": "Bon Secours",
            "facility": "St. Francis Medical Center",
            "department": "SPD",
            "instrument_name": "Arthroscopic shaver handpiece",
            "instrument_category": "Powered instrument",
            "vendor": "Stryker",
            "tray_name": "Sports medicine tray",
            "finding_type": "cleaning verification concern",
            "finding_detail": "Residual material noted around connection point",
            "risk_level": "High",
            "target_status": "Pending IP Review",
        },
        {
            "event_id": "QEV-SEED-007",
            "inspection_id": "INS-SEED-007",
            "tenant_id": "bonsecours",
            "tenant_name": "Bon Secours",
            "facility": "Memorial Regional Medical Center",
            "department": "SPD",
            "instrument_name": "Neuro suction",
            "instrument_category": "Cannulated instrument",
            "vendor": "Medtronic",
            "tray_name": "Neuro tray",
            "finding_type": "bioburden suspected",
            "finding_detail": "Debris suspected in narrow lumen",
            "risk_level": "High",
            "target_status": "Action in Progress",
        },
        {
            "event_id": "QEV-SEED-008",
            "inspection_id": "INS-SEED-008",
            "tenant_id": "bonsecours",
            "tenant_name": "Bon Secours",
            "facility": "Offsite Reprocessing Center",
            "department": "SPD",
            "instrument_name": "Vendor acetabular reamer",
            "instrument_category": "Vendor instrument",
            "vendor": "DePuy Synthes",
            "tray_name": "Hip vendor tray",
            "finding_type": "vendor quality concern",
            "finding_detail": "Instrument arrived with visible discoloration",
            "risk_level": "Medium",
            "target_status": "Pending Vendor Response",
        },
        {
            "event_id": "QEV-SEED-009",
            "inspection_id": "INS-SEED-009",
            "tenant_id": "bonsecours",
            "tenant_name": "Bon Secours",
            "facility": "St. Mary’s Hospital",
            "department": "SPD",
            "instrument_name": "Laparoscopic grasper",
            "instrument_category": "Minimally invasive instrument",
            "vendor": "Unknown Vendor",
            "tray_name": "Laparoscopic tray",
            "finding_type": "inspection failure",
            "finding_detail": "Insulation concern identified during visual inspection",
            "risk_level": "Medium",
            "target_status": "Open",
        },
        {
            "event_id": "QEV-SEED-010",
            "inspection_id": "INS-SEED-010",
            "tenant_id": "bonsecours",
            "tenant_name": "Bon Secours",
            "facility": "Memorial Regional Medical Center",
            "department": "SPD",
            "instrument_name": "Bone cutter",
            "instrument_category": "Manual instrument",
            "vendor": "Stryker",
            "tray_name": "Trauma tray",
            "finding_type": "resolved inspection concern",
            "finding_detail": "Instrument removed, replacement verified, and follow-up audit completed",
            "risk_level": "Low",
            "target_status": "Closed",
        },
    ]

    created = []
    skipped_existing = []

    for event in demo_events:
        existing = [
            item for item in store_list_capas()
            if item.get("event_id") == event["event_id"]
        ]

        if existing:
            skipped_existing.append(event["event_id"])
            continue

        target_status = event.pop("target_status")

        capa = build_capa_from_quality_event(
            quality_event=event,
            owner="Infection Prevention / SPD Leadership",
            due_days=7,
        )

        # Add RCA / action data for stronger demo analytics
        if target_status in ["Action in Progress", "Closed", "Pending IP Review"]:
            capa = add_capa_update(
                capa,
                "root_cause",
                "Preliminary review identified a process or vendor-related quality gap requiring follow-up.",
                "Seed Demo"
            )

            capa = add_capa_update(
                capa,
                "corrective_action",
                "Instrument or tray was held for review and appropriate leadership notification was completed.",
                "Seed Demo"
            )

            capa = add_capa_update(
                capa,
                "preventive_action",
                "Targeted audit and education assigned to reduce recurrence risk.",
                "Seed Demo"
            )

            capa = add_capa_evidence(
                capa,
                "Demo inspection evidence",
                "image",
                f"/evidence/demo/{event['event_id'].lower()}.png",
                "Seed Demo"
            )

        if target_status == "Closed":
            capa = add_capa_update(
                capa,
                "closure_summary",
                "CAPA reviewed, corrective action verified, and follow-up audit completed.",
                "Seed Demo"
            )

        if target_status != "Open":
            capa = update_capa_status(
                capa,
                target_status,
                f"Seeded demo status set to {target_status}."
            )

        save_capa(capa)
        created.append(capa)

    return {
        "message": "Demo CAPA analytics seed completed.",
        "created_count": len(created),
        "skipped_existing_count": len(skipped_existing),
        "skipped_existing_event_ids": skipped_existing,
        "created_capa_ids": [item.get("capa_id") for item in created],
    }


@router.get("/analytics/trends")
def capa_analytics_trends(
    status: Optional[str] = None,
    facility: Optional[str] = None,
    vendor: Optional[str] = None,
    risk_level: Optional[str] = None,
):
    items = store_list_capas()

    def matches_filters(item):
        if status and item.get("status") != status:
            return False
        if facility and item.get("facility") != facility:
            return False
        if vendor and item.get("vendor") != vendor:
            return False
        if risk_level and item.get("risk_level") != risk_level:
            return False
        return True

    filtered_items = [item for item in items if matches_filters(item)]

    now = datetime.now(timezone.utc)

    def days_to_due(item):
        due_date_raw = item.get("due_date")
        if not due_date_raw:
            return None
        try:
            due_date = datetime.fromisoformat(due_date_raw.replace("Z", "+00:00"))
            return (due_date - now).days
        except Exception:
            return None

    def is_overdue(item):
        days = days_to_due(item)
        return days is not None and days < 0 and item.get("status") != "Closed"

    def is_due_soon(item):
        days = days_to_due(item)
        return days is not None and 0 <= days <= 3 and item.get("status") != "Closed"

    def group_by(field):
        result = {}
        for item in filtered_items:
            key = item.get(field) or "Unknown"
            if key not in result:
                result[key] = {
                    "name": key,
                    "total": 0,
                    "open": 0,
                    "closed": 0,
                    "high_risk": 0,
                    "pending_ip_review": 0,
                    "vendor_pending": 0,
                    "overdue": 0,
                }

            result[key]["total"] += 1

            if item.get("status") == "Open":
                result[key]["open"] += 1
            if item.get("status") == "Closed":
                result[key]["closed"] += 1
            if item.get("risk_level") == "High":
                result[key]["high_risk"] += 1
            if item.get("status") == "Pending IP Review":
                result[key]["pending_ip_review"] += 1
            if item.get("status") == "Pending Vendor Response":
                result[key]["vendor_pending"] += 1
            if is_overdue(item):
                result[key]["overdue"] += 1

        return sorted(result.values(), key=lambda row: row["total"], reverse=True)

    days_values = [
        days_to_due(item)
        for item in filtered_items
        if days_to_due(item) is not None
    ]

    average_days_to_due = (
        round(sum(days_values) / len(days_values), 1)
        if days_values
        else None
    )

    return {
        "filters_applied": {
            "status": status,
            "facility": facility,
            "vendor": vendor,
            "risk_level": risk_level,
        },
        "summary": {
            "total_capas": len(filtered_items),
            "open_capas": len([item for item in filtered_items if item.get("status") == "Open"]),
            "closed_capas": len([item for item in filtered_items if item.get("status") == "Closed"]),
            "pending_ip_review": len([item for item in filtered_items if item.get("status") == "Pending IP Review"]),
            "vendor_pending": len([item for item in filtered_items if item.get("status") == "Pending Vendor Response"]),
            "high_risk": len([item for item in filtered_items if item.get("risk_level") == "High"]),
            "overdue": len([item for item in filtered_items if is_overdue(item)]),
            "due_soon": len([item for item in filtered_items if is_due_soon(item)]),
            "average_days_to_due": average_days_to_due,
        },
        "facility_trends": group_by("facility"),
        "vendor_trends": group_by("vendor"),
        "status_trends": group_by("status"),
        "risk_trends": group_by("risk_level"),
        "recent_items": sorted(
            filtered_items,
            key=lambda item: item.get("updated_at", item.get("created_at", "")),
            reverse=True,
        )[:10],
    }


@router.get("/{capa_id}/report")
def get_capa_report(capa_id: str):
    capa = store_get_capa(capa_id)

    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found.")

    generated_at = datetime.now(timezone.utc).isoformat()

    evidence_links = capa.get("evidence_links") or []
    audit_trail = capa.get("audit_trail") or []

    status = capa.get("status", "Unknown")
    risk_level = capa.get("risk_level", "Unknown")

    documentation_complete = all([
        bool(capa.get("root_cause")),
        bool(capa.get("corrective_action")),
        bool(capa.get("preventive_action")),
        len(evidence_links) > 0,
    ])

    if status == "Closed":
        recommended_next_action = "CAPA is closed. Retain record for audit, trend review, and quality committee reporting."
    elif not capa.get("root_cause"):
        recommended_next_action = "Document root cause analysis before closure consideration."
    elif not capa.get("corrective_action"):
        recommended_next_action = "Document corrective action and responsible follow-up."
    elif not capa.get("preventive_action"):
        recommended_next_action = "Document preventive action to reduce recurrence risk."
    elif len(evidence_links) == 0:
        recommended_next_action = "Attach supporting evidence such as image, audit, inspection record, or vendor response."
    elif status in ["Open", "Pending IP Review", "Pending Vendor Response", "Action in Progress"]:
        recommended_next_action = "Continue workflow review and move toward closure once actions are verified."
    else:
        recommended_next_action = "Review CAPA status and confirm next operational action."

    executive_summary = (
        f"{risk_level} risk CAPA for {capa.get('instrument_name')} at "
        f"{capa.get('facility')} related to {capa.get('finding_type')}. "
        f"Current status: {status}. Documentation complete: "
        f"{'Yes' if documentation_complete else 'No'}."
    )

    return {
        "report_type": "LumenAI CAPA Quality Action Report",
        "generated_at": generated_at,
        "executive_summary": executive_summary,
        "documentation_complete": documentation_complete,
        "recommended_next_action": recommended_next_action,
        "capa": {
            "capa_id": capa.get("capa_id"),
            "tenant_id": capa.get("tenant_id"),
            "tenant_name": capa.get("tenant_name"),
            "facility": capa.get("facility"),
            "department": capa.get("department", "SPD"),
            "owner": capa.get("owner"),
            "status": status,
            "risk_level": risk_level,
            "capa_type": capa.get("capa_type"),
            "due_date": capa.get("due_date"),
            "created_at": capa.get("created_at"),
            "updated_at": capa.get("updated_at"),
        },
        "quality_event": {
            "event_id": capa.get("event_id"),
            "inspection_id": capa.get("inspection_id"),
            "instrument_name": capa.get("instrument_name"),
            "instrument_category": capa.get("instrument_category"),
            "vendor": capa.get("vendor"),
            "finding_type": capa.get("finding_type"),
            "problem_statement": capa.get("problem_statement"),
            "containment_action": capa.get("containment_action"),
        },
        "capa_documentation": {
            "root_cause": capa.get("root_cause"),
            "corrective_action": capa.get("corrective_action"),
            "preventive_action": capa.get("preventive_action"),
            "closure_summary": capa.get("closure_summary"),
        },
        "evidence": evidence_links,
        "audit_trail": audit_trail,
    }


@router.get("/{capa_id}")
def get_capa(capa_id: str):
    capa = store_get_capa(capa_id)

    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found.")

    return capa


@router.patch("/{capa_id}/status")
def patch_capa_status(
    capa_id: str,
    payload: Dict,
):
    capa = store_get_capa(capa_id)

    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found.")

    new_status = payload.get("status")
    note = payload.get("note")

    if not new_status:
        raise HTTPException(status_code=400, detail="status is required.")

    if new_status == "Closed":
        validate_capa_closure_ready(capa)

    try:
        updated = update_capa_status(capa, new_status, note)

        if new_status == "Closed":
            updated.setdefault("audit_trail", []).append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "CAPA Closed With Verification",
                "details": "CAPA closure completed after required RCA, corrective action, preventive action, closure summary, and evidence were verified."
            })

        save_capa(updated)
        return updated
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.patch("/{capa_id}/update")
def patch_capa_update(
    capa_id: str,
    payload: Dict,
):
    capa = store_get_capa(capa_id)

    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found.")

    update_type = payload.get("update_type")
    content = payload.get("content")
    author = payload.get("author", "System/User")

    if not update_type or not content:
        raise HTTPException(
            status_code=400,
            detail="update_type and content are required.",
        )

    try:
        updated = add_capa_update(
            capa=capa,
            update_type=update_type,
            content=content,
            author=author,
        )
        save_capa(updated)
        return updated
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))




@router.post("/{capa_id}/close-with-verification")
def close_capa_with_verification(
    capa_id: str,
    payload: Dict = {},
):
    capa = store_get_capa(capa_id)

    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found.")

    validate_capa_closure_ready(capa)

    note = payload.get(
        "note",
        "CAPA closed after required closure verification was completed."
    )

    updated = update_capa_status(capa, "Closed", note)

    updated.setdefault("audit_trail", []).append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "CAPA Closed With Verification",
        "details": "Required closure fields verified: root cause, corrective action, preventive action, closure summary, and evidence."
    })

    save_capa(updated)
    return {
        "message": "CAPA closed with verification.",
        "capa": updated,
    }


@router.post("/{capa_id}/evidence")
def post_capa_evidence(
    capa_id: str,
    payload: Dict,
):
    capa = store_get_capa(capa_id)

    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found.")

    required = ["evidence_name", "evidence_type", "evidence_url"]

    for field in required:
        if not payload.get(field):
            raise HTTPException(status_code=400, detail=f"{field} is required.")

    updated = add_capa_evidence(
        capa=capa,
        evidence_name=payload["evidence_name"],
        evidence_type=payload["evidence_type"],
        evidence_url=payload["evidence_url"],
        added_by=payload.get("added_by", "System/User"),
    )

    save_capa(updated)
    return updated
