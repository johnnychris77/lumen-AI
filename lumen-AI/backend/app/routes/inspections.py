from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Header

from backend.app.services.inspection_service import build_inspection_record
from backend.app.services.inspection_store import (
    init_inspection_db,
    save_inspection,
    get_inspection as store_get_inspection,
    list_inspections as store_list_inspections,
)
from backend.app.services.capa_service import build_capa_from_quality_event
from backend.app.services.capa_store import save_capa


router = APIRouter(prefix="/api/inspections", tags=["Inspection Intake"])


@router.on_event("startup")
def startup_inspection_store():
    init_inspection_db()


@router.post("/intake")
def create_inspection_intake(
    payload: Dict,
    x_tenant_id: str = Header(default="demo"),
    x_tenant_name: str = Header(default="Demo Hospital"),
):
    payload["tenant_id"] = payload.get("tenant_id") or x_tenant_id
    payload["tenant_name"] = payload.get("tenant_name") or x_tenant_name

    required = [
        "facility",
        "instrument_name",
        "instrument_category",
        "finding_type",
        "finding_detail",
    ]

    missing = [field for field in required if not payload.get(field)]

    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Missing required inspection intake fields.",
                "missing_fields": missing,
            },
        )

    inspection = build_inspection_record(payload)
    save_inspection(inspection)

    return inspection


@router.get("/")
def list_inspection_intakes(
    facility: Optional[str] = None,
    vendor: Optional[str] = None,
    risk_level: Optional[str] = None,
    capa_required: Optional[bool] = None,
):
    items = store_list_inspections(
        facility=facility,
        vendor=vendor,
        risk_level=risk_level,
        capa_required=capa_required,
    )

    return {
        "count": len(items),
        "items": items,
    }


@router.get("/{inspection_id}")
def get_inspection_intake(inspection_id: str):
    inspection = store_get_inspection(inspection_id)

    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    return inspection


@router.post("/{inspection_id}/create-capa")
def create_capa_from_inspection(
    inspection_id: str,
    payload: Dict = {},
):
    inspection = store_get_inspection(inspection_id)

    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    if inspection.get("capa_id"):
        existing_capa_id = inspection.get("capa_id")
        raise HTTPException(
            status_code=409,
            detail={
                "message": "CAPA already exists for this inspection.",
                "capa_id": existing_capa_id,
            },
        )

    if not inspection.get("capa_required"):
        allow_override = payload.get("allow_override", False)

        if not allow_override:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "This inspection was not classified as requiring CAPA.",
                    "recommendation": inspection.get("recommended_routing"),
                    "override_option": "Send allow_override=true to create CAPA anyway.",
                },
            )

    quality_event = {
        "event_id": inspection.get("event_id"),
        "inspection_id": inspection.get("inspection_id"),
        "tenant_id": inspection.get("tenant_id"),
        "tenant_name": inspection.get("tenant_name"),
        "facility": inspection.get("facility"),
        "department": inspection.get("department"),
        "instrument_name": inspection.get("instrument_name"),
        "instrument_category": inspection.get("instrument_category"),
        "vendor": inspection.get("vendor"),
        "tray_name": inspection.get("tray_name"),
        "finding_type": inspection.get("finding_type"),
        "finding_detail": inspection.get("finding_detail"),
        "risk_level": inspection.get("risk_level"),
    }

    capa = build_capa_from_quality_event(
        quality_event=quality_event,
        owner=payload.get("owner", "Infection Prevention / SPD Leadership"),
        due_days=payload.get("due_days", 7),
    )

    if inspection.get("evidence_url"):
        capa.setdefault("evidence_links", []).append({
            "evidence_id": f"EVID-{inspection.get('inspection_id')}",
            "name": "Inspection intake evidence",
            "type": "inspection_evidence",
            "url": inspection.get("evidence_url"),
            "added_by": inspection.get("inspector", "Dashboard User"),
            "added_at": datetime.now(timezone.utc).isoformat(),
        })

        capa.setdefault("audit_trail", []).append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "Inspection Evidence Linked",
            "details": "Evidence from inspection intake was linked to CAPA."
        })

    save_capa(capa)

    inspection["capa_id"] = capa.get("capa_id")
    inspection["status"] = "CAPA Created"
    inspection["updated_at"] = datetime.now(timezone.utc).isoformat()
    inspection.setdefault("audit_trail", []).append({
        "timestamp": inspection["updated_at"],
        "action": "CAPA Created From Inspection",
        "details": f"CAPA {capa.get('capa_id')} created from inspection intake."
    })

    save_inspection(inspection)

    return {
        "message": "CAPA created from inspection intake.",
        "inspection": inspection,
        "capa": capa,
    }
