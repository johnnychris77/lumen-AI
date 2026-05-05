from typing import Dict

from fastapi import APIRouter, HTTPException

from backend.app.services.visual_inspection_service import (
    build_visual_inspection_review,
    calculate_severity_score,
    calculate_confidence_score,
    recommended_actions,
    finalize_review,
)
from backend.app.services.visual_inspection_store import (
    init_visual_inspection_db,
    save_visual_review,
    get_visual_review,
    list_visual_reviews,
)


router = APIRouter(prefix="/api/inspection-review", tags=["Visual Inspection Intelligence"])


@router.on_event("startup")
def startup_visual_inspection_store():
    init_visual_inspection_db()


@router.post("/analyze")
def analyze_visual_inspection(payload: Dict):
    review = build_visual_inspection_review(payload)
    save_visual_review(review)
    return review


@router.post("/score")
def score_visual_inspection(payload: Dict):
    severity = calculate_severity_score(payload)
    confidence = calculate_confidence_score(payload)
    actions = recommended_actions(severity, confidence, payload)

    return {
        "severity_score": severity,
        "confidence_score": confidence,
        **actions,
    }


@router.post("/decision")
def decision_support(payload: Dict):
    severity = payload.get("severity_score")
    confidence = payload.get("confidence_score")

    if severity is None:
        severity = calculate_severity_score(payload)

    if confidence is None:
        confidence = calculate_confidence_score(payload)

    actions = recommended_actions(severity, confidence, payload)

    return {
        "severity_score": severity,
        "confidence_score": confidence,
        **actions,
    }


@router.get("/")
def list_reviews():
    items = list_visual_reviews()
    return {
        "count": len(items),
        "items": items,
    }


@router.get("/{review_id}")
def get_review(review_id: str):
    review = get_visual_review(review_id)

    if not review:
        raise HTTPException(status_code=404, detail="Visual inspection review not found.")

    return review




@router.post("/{review_id}/create-inspection")
def create_inspection_from_visual_review(review_id: str, payload: Dict = {}):
    review = get_visual_review(review_id)

    if not review:
        raise HTTPException(status_code=404, detail="Visual inspection review not found.")

    from backend.app.services.inspection_service import build_inspection_record
    from backend.app.services.inspection_store import save_inspection, get_inspection as store_get_inspection

    existing_inspection_id = review.get("inspection_id")
    if existing_inspection_id:
        existing = store_get_inspection(existing_inspection_id)
        if existing:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Inspection intake already exists for this visual review.",
                    "inspection_id": existing_inspection_id,
                },
            )

    finding_type = review.get("quality_issue_type") or "visual inspection finding"
    suspected_debris = review.get("suspected_debris_type") or "Unknown"
    disposition = review.get("recommended_disposition") or "Review required"

    finding_detail = payload.get("finding_detail") or (
        f"Visual inspection review identified {suspected_debris}. "
        f"Quality issue: {finding_type}. "
        f"Severity score: {review.get('severity_score')}. "
        f"Confidence score: {review.get('confidence_score')}. "
        f"Recommended disposition: {disposition}."
    )

    inspection_payload = {
        "event_id": review.get("event_id") or payload.get("event_id"),
        "tenant_id": payload.get("tenant_id", "bonsecours"),
        "tenant_name": payload.get("tenant_name", "Bon Secours"),
        "facility": review.get("facility"),
        "department": review.get("department", "SPD"),
        "instrument_name": review.get("instrument_name"),
        "instrument_category": review.get("instrument_category"),
        "vendor": review.get("vendor"),
        "tray_name": review.get("tray_name"),
        "finding_type": finding_type,
        "finding_detail": finding_detail,
        "evidence_url": review.get("evidence_url", ""),
        "inspector": payload.get("inspector", "Dashboard User"),
        "risk_level": "High" if review.get("severity_score", 0) >= 70 else "Medium" if review.get("severity_score", 0) >= 40 else "Low",
    }

    inspection = build_inspection_record(inspection_payload)

    inspection["source_visual_review_id"] = review_id
    inspection.setdefault("audit_trail", []).append({
        "timestamp": inspection["created_at"],
        "action": "Inspection Created From Visual Review",
        "details": f"Inspection intake created from visual review {review_id}."
    })

    save_inspection(inspection)

    review["inspection_id"] = inspection.get("inspection_id")
    review["updated_at"] = inspection["created_at"]
    review.setdefault("audit_trail", []).append({
        "timestamp": inspection["created_at"],
        "action": "Inspection Intake Created",
        "details": f"Inspection intake {inspection.get('inspection_id')} created from visual review."
    })

    save_visual_review(review)

    return {
        "message": "Inspection intake created from visual review.",
        "visual_review": review,
        "inspection": inspection,
    }




@router.post("/{review_id}/create-capa")
def create_capa_from_visual_review(review_id: str, payload: Dict = {}):
    review = get_visual_review(review_id)

    if not review:
        raise HTTPException(status_code=404, detail="Visual inspection review not found.")

    from backend.app.services.inspection_service import build_inspection_record
    from backend.app.services.inspection_store import (
        save_inspection,
        get_inspection as store_get_inspection,
    )
    from backend.app.services.capa_service import build_capa_from_quality_event
    from backend.app.services.capa_store import save_capa
    from datetime import datetime, timezone

    inspection = None

    existing_inspection_id = review.get("inspection_id")
    if existing_inspection_id:
        inspection = store_get_inspection(existing_inspection_id)

    if not inspection:
        finding_type = review.get("quality_issue_type") or "visual inspection finding"
        suspected_debris = review.get("suspected_debris_type") or "Unknown"
        disposition = review.get("recommended_disposition") or "Review required"

        severity = review.get("severity_score", 0)
        risk_level = "High" if severity >= 70 else "Medium" if severity >= 40 else "Low"

        finding_detail = payload.get("finding_detail") or (
            f"Visual inspection review identified {suspected_debris}. "
            f"Quality issue: {finding_type}. "
            f"Severity score: {review.get('severity_score')}. "
            f"Confidence score: {review.get('confidence_score')}. "
            f"Recommended disposition: {disposition}."
        )

        inspection_payload = {
            "event_id": review.get("event_id") or payload.get("event_id"),
            "tenant_id": payload.get("tenant_id", "bonsecours"),
            "tenant_name": payload.get("tenant_name", "Bon Secours"),
            "facility": review.get("facility"),
            "department": review.get("department", "SPD"),
            "instrument_name": review.get("instrument_name"),
            "instrument_category": review.get("instrument_category"),
            "vendor": review.get("vendor"),
            "tray_name": review.get("tray_name"),
            "finding_type": finding_type,
            "finding_detail": finding_detail,
            "evidence_url": review.get("evidence_url", ""),
            "inspector": payload.get("inspector", "Dashboard User"),
            "risk_level": risk_level,
        }

        inspection = build_inspection_record(inspection_payload)
        inspection["source_visual_review_id"] = review_id
        inspection.setdefault("audit_trail", []).append({
            "timestamp": inspection["created_at"],
            "action": "Inspection Created From Visual Review",
            "details": f"Inspection intake created from visual review {review_id}."
        })

        save_inspection(inspection)

        review["inspection_id"] = inspection.get("inspection_id")
        review["updated_at"] = inspection["created_at"]
        review.setdefault("audit_trail", []).append({
            "timestamp": inspection["created_at"],
            "action": "Inspection Intake Created",
            "details": f"Inspection intake {inspection.get('inspection_id')} created from visual review."
        })

    if inspection.get("capa_id"):
        raise HTTPException(
            status_code=409,
            detail={
                "message": "CAPA already exists for this visual review inspection.",
                "inspection_id": inspection.get("inspection_id"),
                "capa_id": inspection.get("capa_id"),
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
            "name": "Visual inspection evidence",
            "type": "visual_inspection_evidence",
            "url": inspection.get("evidence_url"),
            "added_by": inspection.get("inspector", "Dashboard User"),
            "added_at": datetime.now(timezone.utc).isoformat(),
        })

        capa.setdefault("audit_trail", []).append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "Visual Inspection Evidence Linked",
            "details": f"Evidence from visual review {review_id} was linked to CAPA."
        })

    save_capa(capa)

    inspection["capa_id"] = capa.get("capa_id")
    inspection["status"] = "CAPA Created"
    inspection["updated_at"] = datetime.now(timezone.utc).isoformat()
    inspection.setdefault("audit_trail", []).append({
        "timestamp": inspection["updated_at"],
        "action": "CAPA Created From Visual Review",
        "details": f"CAPA {capa.get('capa_id')} created from visual review {review_id}."
    })

    save_inspection(inspection)

    review["inspection_id"] = inspection.get("inspection_id")
    review["review_status"] = "CAPA Created"
    review["updated_at"] = inspection["updated_at"]
    review.setdefault("audit_trail", []).append({
        "timestamp": inspection["updated_at"],
        "action": "CAPA Created",
        "details": f"CAPA {capa.get('capa_id')} created through visual review workflow."
    })

    save_visual_review(review)

    return {
        "message": "CAPA created from visual inspection review.",
        "visual_review": review,
        "inspection": inspection,
        "capa": capa,
    }


@router.post("/{review_id}/finalize")
def finalize_visual_review(review_id: str, payload: Dict):
    review = get_visual_review(review_id)

    if not review:
        raise HTTPException(status_code=404, detail="Visual inspection review not found.")

    try:
        updated = finalize_review(review, payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    save_visual_review(updated)

    return {
        "message": "Visual inspection review finalized.",
        "review": updated,
    }
