from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.app.services.evidence_store import (
    create_evidence_record,
    get_evidence,
    init_evidence_db,
    link_evidence,
    list_evidence,
    save_evidence,
)

from backend.app.services.visual_inspection_store import (
    get_visual_review,
    save_visual_review,
)

from backend.app.services.inspection_store import (
    get_inspection,
    save_inspection,
)

from backend.app.services.capa_store import (
    get_capa,
    save_capa,
)


router = APIRouter(prefix="/api/evidence", tags=["Evidence / Image Upload"])


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


@router.on_event("startup")
def startup_evidence_store():
    init_evidence_db()


@router.post("/upload")
def upload_evidence(
    file: UploadFile = File(...),
    evidence_type: str = Form(default="borescope_image"),
    facility: str = Form(default=""),
    instrument_name: str = Form(default=""),
    vendor: str = Form(default=""),
    finding_category: str = Form(default=""),
):
    record = create_evidence_record(
        file=file,
        evidence_type=evidence_type,
        facility=facility,
        instrument_name=instrument_name,
        vendor=vendor,
        finding_category=finding_category,
    )

    save_evidence(record)

    return {
        "message": "Evidence uploaded successfully.",
        "evidence": record,
    }


@router.get("/")
def list_uploaded_evidence():
    items = list_evidence()
    return {
        "count": len(items),
        "items": items,
    }


@router.get("/{evidence_id}")
def get_uploaded_evidence(evidence_id: str):
    record = get_evidence(evidence_id)

    if not record:
        raise HTTPException(status_code=404, detail="Evidence not found.")

    return record


@router.get("/{evidence_id}/file")
def get_evidence_file(evidence_id: str):
    record = get_evidence(evidence_id)

    if not record:
        raise HTTPException(status_code=404, detail="Evidence not found.")

    file_path = Path(record["file_path"])

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Evidence file not found.")

    return FileResponse(
        path=str(file_path),
        media_type=record.get("mime_type") or "application/octet-stream",
        filename=record.get("original_filename") or file_path.name,
    )


@router.post("/{evidence_id}/link-to-visual-review/{review_id}")
def link_to_visual_review(evidence_id: str, review_id: str):
    evidence = get_evidence(evidence_id)

    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found.")

    review = get_visual_review(review_id)

    if not review:
        raise HTTPException(status_code=404, detail="Visual inspection review not found.")

    evidence = link_evidence(evidence_id, "linked_visual_review_id", review_id)

    review["evidence_url"] = evidence.get("file_url", review.get("evidence_url", ""))
    review["evidence_id"] = evidence_id
    review["updated_at"] = utc_now_iso()
    review.setdefault("audit_trail", []).append({
        "timestamp": review["updated_at"],
        "action": "Evidence Linked",
        "details": f"Evidence {evidence_id} linked to visual inspection review."
    })

    save_visual_review(review)

    return {
        "message": "Evidence linked to visual review.",
        "evidence": evidence,
        "visual_review": review,
    }


@router.post("/{evidence_id}/link-to-inspection/{inspection_id}")
def link_to_inspection(evidence_id: str, inspection_id: str):
    evidence = get_evidence(evidence_id)

    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found.")

    inspection = get_inspection(inspection_id)

    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    evidence = link_evidence(evidence_id, "linked_inspection_id", inspection_id)

    inspection["evidence_url"] = evidence.get("file_url", inspection.get("evidence_url", ""))
    inspection["evidence_id"] = evidence_id
    inspection["updated_at"] = utc_now_iso()
    inspection.setdefault("audit_trail", []).append({
        "timestamp": inspection["updated_at"],
        "action": "Evidence Linked",
        "details": f"Evidence {evidence_id} linked to inspection intake."
    })

    save_inspection(inspection)

    return {
        "message": "Evidence linked to inspection.",
        "evidence": evidence,
        "inspection": inspection,
    }


@router.post("/{evidence_id}/link-to-capa/{capa_id}")
def link_to_capa(evidence_id: str, capa_id: str):
    evidence = get_evidence(evidence_id)

    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found.")

    capa = get_capa(capa_id)

    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found.")

    evidence = link_evidence(evidence_id, "linked_capa_id", capa_id)

    evidence_item = {
        "evidence_id": evidence_id,
        "name": evidence.get("original_filename") or evidence_id,
        "type": evidence.get("evidence_type") or "evidence",
        "url": evidence.get("file_url"),
        "file_url": evidence.get("file_url"),
        "mime_type": evidence.get("mime_type"),
        "added_by": "Dashboard User",
        "added_at": utc_now_iso(),
    }

    existing_links = capa.get("evidence_links") or []
    already_linked = any(item.get("evidence_id") == evidence_id for item in existing_links)

    if not already_linked:
        existing_links.append(evidence_item)

    capa["evidence_links"] = existing_links
    capa["updated_at"] = utc_now_iso()
    capa.setdefault("audit_trail", []).append({
        "timestamp": capa["updated_at"],
        "action": "Evidence Linked",
        "details": f"Evidence {evidence_id} linked to CAPA."
    })

    save_capa(capa)

    return {
        "message": "Evidence linked to CAPA.",
        "evidence": evidence,
        "capa": capa,
    }
