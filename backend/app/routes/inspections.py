import hashlib
from datetime import datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.db import models
from app.enterprise_auth import get_request_tenant_id, require_enterprise_auth
from app.analytics.risk_engine import calculate_risk
from app.services.baseline_comparison_scoring_service import analyze_inspection

router = APIRouter(tags=["inspections"])

_ALLOWED_INSTRUMENT_TYPES = {
    "laparoscopic_grasper", "retractor", "scissors", "needle_holder",
    "forceps", "trocar", "electrosurgical", "suction_irrigation",
    "clip_applier", "stapler", "other",
}
_ALLOWED_MATERIAL_TYPES = {"stainless_steel", "titanium", "polymer", "tungsten_carbide", "other"}
_ALLOWED_DETECTED_ISSUES = {
    "blood", "bone", "tissue", "debris", "corrosion",
    "crack", "insulation_damage", "other", "none",
}
_ALLOWED_STATUSES = {"pending", "reviewed", "flagged", "closed", "invalidated"}

_MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB per file
_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/tiff"}


# ---------------------------------------------------------------------------
# DQ-01..DQ-14: Pydantic schema enforced at submission boundary
# ---------------------------------------------------------------------------

_ALLOWED_BASELINE_SOURCES = {
    "manufacturer", "vendor", "hospital", "none", "manual_review",
}


class InspectionCreate(BaseModel):
    instrument_type: str = Field(..., description="Must be an approved instrument type")
    material_type: Optional[str] = Field(None, description="Must be an approved material type; optional when image present")
    stain_detected: Optional[bool] = Field(None)
    detected_issue: Optional[str] = Field(None, description="Must be an approved issue type; optional when image present")
    site_name: str = Field(..., min_length=1, max_length=100)
    vendor_name: str = Field("", max_length=100)
    confidence: Optional[float] = Field(None, ge=0.0, le=100.0)  # DQ-11
    file_name: str = Field("", max_length=255)
    tenant_name: str = Field("", max_length=255)
    has_image: bool = Field(False)
    image_sha256: Optional[str] = Field(None, max_length=64)
    # Sprint 7 additions — facility/department/tray/instrument identity
    facility_name: Optional[str] = Field(None, max_length=255)
    department: Optional[str] = Field(None, max_length=255)
    tray_id: Optional[str] = Field(None, max_length=100)
    instrument_barcode: Optional[str] = Field(None, max_length=255)
    instrument_udi: Optional[str] = Field(None, max_length=255)
    keydot_id: Optional[str] = Field(None, max_length=255)
    # Technician-declared finding categories (optional — AI determines findings)
    finding_categories: Optional[List[str]] = Field(None)

    @field_validator("instrument_type")
    @classmethod
    def validate_instrument_type(cls, v: str) -> str:
        if v not in _ALLOWED_INSTRUMENT_TYPES:
            raise ValueError(f"instrument_type '{v}' not in approved list: {sorted(_ALLOWED_INSTRUMENT_TYPES)}")
        return v

    @field_validator("material_type")
    @classmethod
    def validate_material_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _ALLOWED_MATERIAL_TYPES:
            raise ValueError(f"material_type '{v}' not in approved list: {sorted(_ALLOWED_MATERIAL_TYPES)}")
        return v

    @field_validator("detected_issue")
    @classmethod
    def validate_detected_issue(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _ALLOWED_DETECTED_ISSUES:
            raise ValueError(f"detected_issue '{v}' not in approved list: {sorted(_ALLOWED_DETECTED_ISSUES)}")
        return v

    @model_validator(mode="after")
    def validate_findings_and_image(self) -> "InspectionCreate":
        # DQ-10: stain_detected=true must have a non-"none" detected_issue (when findings provided)
        if self.stain_detected and self.detected_issue == "none":
            raise ValueError("detected_issue must not be 'none' when stain_detected is true")
        # When no image, findings are required
        if not self.has_image:
            if self.material_type is None:
                raise ValueError("material_type is required when no image is uploaded")
            if self.detected_issue is None:
                raise ValueError("detected_issue is required when no image is uploaded")
            if self.stain_detected is None:
                raise ValueError("stain_detected is required when no image is uploaded")
        return self


class BaselineOverride(BaseModel):
    baseline_source: str = Field(..., description="Alternate baseline source")
    override_reason: str = Field(..., min_length=10, max_length=1000)

    @field_validator("baseline_source")
    @classmethod
    def validate_baseline_source(cls, v: str) -> str:
        if v not in _ALLOWED_BASELINE_SOURCES:
            raise ValueError(f"baseline_source '{v}' not in allowed list: {sorted(_ALLOWED_BASELINE_SOURCES)}")
        return v


def inspection_response(row: models.Inspection) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "file_name": row.file_name,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "stain_detected": row.stain_detected,
        "confidence": row.confidence,
        "material_type": row.material_type,
        "status": row.status,
        "model_name": row.model_name,
        "model_version": row.model_version,
        "inference_timestamp": row.inference_timestamp.isoformat() if row.inference_timestamp else None,
        "instrument_type": row.instrument_type,
        "detected_issue": row.detected_issue,
        "inference_mode": row.inference_mode,
        "risk_score": row.risk_score,
        "vendor_name": row.vendor_name,
        "site_name": row.site_name,
        "facility_name": row.facility_name,
        "department": row.department,
        "tray_id": row.tray_id,
        "instrument_barcode": row.instrument_barcode,
        "instrument_udi": row.instrument_udi,
        # Phase 14 baseline governance fields
        "has_image": row.has_image,
        "image_sha256": row.image_sha256,
        "baseline_status": row.baseline_status,
        "baseline_source": row.baseline_source,
        "score_status": row.score_status,
        "supervisor_review_required": row.supervisor_review_required,
        "override_reason": row.override_reason,
        "override_by": row.override_by,
        "override_at": row.override_at.isoformat() if row.override_at else None,
    }


@router.get("/inspections/{inspection_id}")
async def get_inspection(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "viewer")),
):
    tenant_id = getattr(current_user, "tenant_id", None)

    query = db.query(models.Inspection).filter(models.Inspection.id == inspection_id)

    # Scope to the caller's tenant unless platform admin
    if tenant_id and getattr(current_user, "role", "") != "admin":
        query = query.filter(models.Inspection.tenant_id == tenant_id)

    row = query.first()
    if not row:
        raise HTTPException(status_code=404, detail="Not Found")

    return inspection_response(row)


@router.post("/inspections", status_code=201)
async def create_inspection(
    body: InspectionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "viewer")),
):
    """Submit a new inspection record. Enforces DQ-01..DQ-14 validation rules."""
    tenant_id = getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)
    tenant_name = body.tenant_name or getattr(current_user, "tenant_name", "") or tenant_id

    conf_val = (body.confidence or 0.0) / 100.0 if body.confidence is not None else 0.0
    detected_issue = body.detected_issue or "unknown"
    material_type = body.material_type or "unknown"
    stain_detected = body.stain_detected if body.stain_detected is not None else False

    # Baseline governance + AI analysis when an image is present.
    supervisor_review_required = False
    baseline_status = "not_checked"
    score_status = "pending"
    risk_score_val = 0
    baseline_source_val: Optional[str] = None
    analysis: Optional[dict] = None

    # Clean declared findings — drop the "pending_ai_analysis" placeholder.
    declared = [
        c for c in (body.finding_categories or [])
        if c and c != "pending_ai_analysis"
    ]

    if body.has_image:
        analysis = analyze_inspection(
            db,
            instrument_type=body.instrument_type,
            tenant_id=tenant_id,
            has_image=True,
            image_sha256=body.image_sha256,
            declared_findings=declared,
            instrument_barcode=body.instrument_barcode,
            instrument_udi=body.instrument_udi,
            keydot_id=body.keydot_id,
        )
        if analysis["analysis_status"] == "completed":
            baseline_status = "approved_baseline_found"
            baseline_source_val = analysis["baseline_source"]
            # inspection_score is 0–100 quality; risk_score is 0–100 risk (inverse).
            risk_score_val = 100 - int(analysis["inspection_score"])
            score_status = "scored"
        else:
            baseline_status = "no_approved_baseline"
            supervisor_review_required = True
            score_status = "supervisor_review_required"
            risk_score_val = 0
    else:
        # No image: score immediately from provided findings
        baseline_status = "not_applicable"
        risk_score_val = calculate_risk(detected_issue, conf_val)
        score_status = "scored"

    row = models.Inspection(
        file_name=body.file_name or "manual-entry",
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        stain_detected=stain_detected,
        confidence=body.confidence if body.confidence is not None else 0.0,
        material_type=material_type,
        status="pending" if not supervisor_review_required else "pending",
        instrument_type=body.instrument_type,
        detected_issue=detected_issue,
        inference_mode="manual" if not body.has_image else "baseline_comparison_scoring",
        risk_score=risk_score_val,
        vendor_name=body.vendor_name or "unknown",
        site_name=body.site_name,
        facility_name=body.facility_name,
        department=body.department,
        tray_id=body.tray_id,
        instrument_barcode=body.instrument_barcode,
        instrument_udi=body.instrument_udi,
        inference_timestamp=datetime.now(timezone.utc),
        has_image=body.has_image,
        image_sha256=body.image_sha256,
        baseline_status=baseline_status,
        baseline_source=baseline_source_val,
        score_status=score_status,
        supervisor_review_required=supervisor_review_required,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    actor = getattr(current_user, "email", None) or getattr(current_user, "username", "unknown")
    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        actor_email=actor,
        actor_role=getattr(current_user, "role", "viewer"),
        action_type="inspection_created",
        resource_type="inspection",
        resource_id=str(row.id),
    )

    response = inspection_response(row)
    if analysis is not None:
        # Attach the full explainable AI analysis output (placeholder scoring).
        response["analysis"] = analysis
    return response


class StatusUpdate(BaseModel):
    status: Literal["pending", "reviewed", "flagged", "closed", "invalidated"]
    notes: str = Field("", max_length=500)


@router.patch("/inspections/{inspection_id}/status")
async def update_inspection_status(
    inspection_id: int,
    body: StatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Invalidate or update the status of an inspection record (spd_manager or admin only)."""
    tenant_id = getattr(current_user, "tenant_id", None)

    query = db.query(models.Inspection).filter(models.Inspection.id == inspection_id)
    if tenant_id and getattr(current_user, "role", "") != "admin":
        query = query.filter(models.Inspection.tenant_id == tenant_id)

    row = query.first()
    if not row:
        raise HTTPException(status_code=404, detail="Not Found")

    row.status = body.status
    if body.notes:
        row.qa_review_notes = body.notes
        row.qa_reviewer = getattr(current_user, "email", "") or ""
        row.qa_reviewed_at = datetime.now(timezone.utc)

    db.commit()

    actor = getattr(current_user, "email", None) or getattr(current_user, "username", "unknown")
    log_audit_event(
        db,
        tenant_id=tenant_id or row.tenant_id,
        tenant_name=row.tenant_name,
        actor_email=actor,
        actor_role=getattr(current_user, "role", "spd_manager"),
        action_type=f"inspection_status_set_{body.status}",
        resource_type="inspection",
        resource_id=str(row.id),
    )

    return {"id": row.id, "status": row.status, "updated": True}


@router.post("/inspections/{inspection_id}/baseline-override", status_code=200)
async def baseline_override(
    inspection_id: int,
    body: BaselineOverride,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Supervisor/admin can override missing baseline and unlock final scoring (spd_manager or admin only)."""
    tenant_id = getattr(current_user, "tenant_id", None)

    query = db.query(models.Inspection).filter(models.Inspection.id == inspection_id)
    if tenant_id and getattr(current_user, "role", "") != "admin":
        query = query.filter(models.Inspection.tenant_id == tenant_id)

    row = query.first()
    if not row:
        raise HTTPException(status_code=404, detail="Not Found")

    actor = getattr(current_user, "email", None) or getattr(current_user, "username", "unknown")
    now = datetime.now(timezone.utc)

    row.baseline_source = body.baseline_source
    row.override_reason = body.override_reason
    row.override_by = actor
    row.override_at = now
    row.supervisor_review_required = False
    row.baseline_status = f"override_applied_{body.baseline_source}"
    # Unlock scoring using available findings
    conf_val = row.confidence / 100.0 if row.confidence else 0.0
    issue = row.detected_issue if row.detected_issue not in ("unknown", "") else "none"
    row.risk_score = calculate_risk(issue, conf_val)
    row.score_status = "scored_after_override"
    row.inference_mode = "override_scored"

    db.commit()

    log_audit_event(
        db,
        tenant_id=tenant_id or row.tenant_id,
        tenant_name=row.tenant_name,
        actor_email=actor,
        actor_role=getattr(current_user, "role", "spd_manager"),
        action_type="baseline_override_applied",
        resource_type="inspection",
        resource_id=str(row.id),
    )

    return inspection_response(row)


@router.get("/pilot/metrics")
def get_pilot_metrics(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Return live adoption and data quality metrics for the caller's tenant."""
    from datetime import timedelta
    from sqlalchemy import func as sqlfunc

    tenant_id = getattr(current_user, "tenant_id", None)

    base_q = db.query(models.Inspection)
    if tenant_id and getattr(current_user, "role", "") != "admin":
        base_q = base_q.filter(models.Inspection.tenant_id == tenant_id)

    total = base_q.count()

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    this_week = base_q.filter(models.Inspection.created_at >= week_ago).count()

    # Completeness: mandatory fields not at their default placeholder values
    complete = base_q.filter(
        models.Inspection.instrument_type != "unknown",
        models.Inspection.material_type != "unknown",
        models.Inspection.site_name != "default-site",
        models.Inspection.detected_issue != "unknown",
    ).count()
    completeness_pct = round((complete / total * 100) if total > 0 else 0.0, 1)

    # DQ-10 consistency: stain_detected=true with detected_issue != "none"/"unknown"
    stain_true = base_q.filter(models.Inspection.stain_detected == True).count()  # noqa: E712
    consistent = base_q.filter(
        models.Inspection.stain_detected == True,  # noqa: E712
        models.Inspection.detected_issue.notin_(["none", "unknown"]),
    ).count()
    consistency_pct = round((consistent / stain_true * 100) if stain_true > 0 else 100.0, 1)

    # Invalidation rate
    invalidated = base_q.filter(models.Inspection.status == "invalidated").count()
    invalidation_pct = round((invalidated / total * 100) if total > 0 else 0.0, 2)

    # Instrument type coverage (unique types logged)
    unique_types = db.query(sqlfunc.count(sqlfunc.distinct(models.Inspection.instrument_type)))
    if tenant_id and getattr(current_user, "role", "") != "admin":
        unique_types = unique_types.filter(models.Inspection.tenant_id == tenant_id)
    unique_instrument_types = unique_types.scalar() or 0

    return {
        "tenant_id": tenant_id,
        "as_of": now.isoformat(),
        "adoption": {
            "total_inspections": total,
            "inspections_last_7_days": this_week,
            "weekly_target": 25,
            "on_track": this_week >= 25,
        },
        "data_quality": {
            "completeness_pct": completeness_pct,
            "consistency_pct": consistency_pct,
            "invalidation_pct": invalidation_pct,
            "completeness_target": 95.0,
            "meets_completeness_target": completeness_pct >= 95.0,
        },
        "coverage": {
            "unique_instrument_types_logged": unique_instrument_types,
            "instrument_type_target": 5,
        },
        "human_review_required": True,
    }


@router.post("/inspections/upload-images")
async def upload_inspection_images(
    request: Request,
    images: List[UploadFile] = File(...),
):
    """Accept multipart inspection image uploads. Stores SHA-256 hash + metadata only — no raw images in DB."""
    require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    results = []
    for img in images:
        content_type = img.content_type or ""
        if content_type not in _ALLOWED_TYPES:
            raise HTTPException(
                status_code=422,
                detail=f"File '{img.filename}' has unsupported type '{content_type}'. Allowed: {sorted(_ALLOWED_TYPES)}",
            )
        data = await img.read()
        if len(data) > _MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File '{img.filename}' exceeds 10 MB limit ({len(data) // 1024} KB).",
            )
        sha256 = hashlib.sha256(data).hexdigest()
        results.append({
            "filename": img.filename,
            "content_type": content_type,
            "size_bytes": len(data),
            "sha256": sha256,
            "tenant_id": tenant_id,
            "status": "received",
        })

    return {
        "uploaded": len(results),
        "images": results,
        "note": "Image hashes recorded. Raw images are not stored in the database.",
    }


@router.post("/baselines/upload-images")
async def upload_baseline_images(
    request: Request,
    images: List[UploadFile] = File(...),
):
    """Accept multipart baseline reference image uploads."""
    require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    results = []
    for img in images:
        content_type = img.content_type or ""
        if content_type not in _ALLOWED_TYPES:
            raise HTTPException(
                status_code=422,
                detail=f"File '{img.filename}' has unsupported type '{content_type}'.",
            )
        data = await img.read()
        if len(data) > _MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File '{img.filename}' exceeds 10 MB limit.",
            )
        sha256 = hashlib.sha256(data).hexdigest()
        results.append({
            "filename": img.filename,
            "content_type": content_type,
            "size_bytes": len(data),
            "sha256": sha256,
            "tenant_id": tenant_id,
            "status": "received",
        })

    return {
        "uploaded": len(results),
        "images": results,
        "note": "Baseline image hashes recorded for reference integrity.",
    }
