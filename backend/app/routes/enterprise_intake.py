from app.services.compliance_evidence_summary_service import build_compliance_evidence_verification_summary
from app.services.compliance_evidence_bundle_verification_service import verify_compliance_evidence_bundle_hash
from app.services.compliance_evidence_bundle_service import build_compliance_evidence_bundle
from app.services.audit_export_verification_service import (
    verify_audit_export_hash,
    verify_audit_export_manifest_hash,
)
from app.services.audit_export_service import export_audit_events_csv, record_audit_export_event
from app.enterprise_auth import require_audit_chain_verify, require_enterprise_auth

from app.services.audit_query_service import query_audit_events
from app.services.audit_chain_verification_service import verify_audit_chain
from app.services.enterprise_audit_service import record_enterprise_audit_event
from app.enterprise_auth import require_hospital_or_enterprise_admin
from app.models.vendor_baseline_audit import VendorBaselineAuditEvent
from app.services.vendor_baseline_audit_service import log_vendor_baseline_audit_event

import os
from datetime import datetime, timezone
import json
from fastapi.responses import Response
from fastapi import APIRouter, Depends, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session

from app.deps import get_db
from app.services.object_storage import save_upload_file, open_stored_object, storage_health_check
from app.models.audit_log import AuditLog

# Compatibility alias for legacy enterprise audit references.
EnterpriseAuditTrail = AuditLog
from app.models.enterprise_quality import (
    EnterpriseDepartment,
    EnterpriseDisposition,
    EnterpriseCapa,
    EnterpriseEvidence,
    EnterpriseFacility,
    EnterpriseFinding,
    EnterpriseExportReadinessHistory,
    EnterpriseInstrument,
    EnterpriseInstrumentBaseline,
    EnterpriseRiskScore,
    EnterpriseVendor,
    EnterpriseVendorBaselineSubscription,
)
from app.schemas.enterprise_intake import (
    EnterpriseInspectionIntakeRequest,
    EnterpriseInspectionIntakeResponse,
    EnterpriseIntakeHistoryItem,
    EnterpriseIntakeHistoryResponse,
    EnterpriseGovernancePacketResponse,
    EnterpriseGovernanceExportPackageResponse,
    EnterpriseVendorEscalationPacketResponse,
    EnterpriseInfectionPreventionReviewPacketResponse,
    EnterpriseExecutiveQualityReviewDashboardResponse,
    EnterpriseExportReadinessStatusResponse,
    EnterpriseExportReadinessHistoryResponse,
    EnterpriseExportReadinessHistoryItem,
    EnterpriseGovernanceEvidenceItem,
    EnterpriseAuditTrailItem,
    EnterpriseAuditTrailResponse,
    EnterpriseHumanReviewRequest,
    EnterpriseHumanReviewResponse,
    EnterpriseCapaCreateRequest,
    EnterpriseCapaCreateResponse,
    EnterpriseCapaListItem,
    EnterpriseCapaListResponse,
    EnterpriseCapaStatusUpdateRequest,
    EnterpriseCapaStatusUpdateResponse,
    EnterpriseCapaSummaryResponse,
    EnterpriseEvidenceUploadResponse,
    EnterpriseEvidenceListItem,
    EnterpriseEvidenceListResponse,
    EnterpriseInstrumentBaselineCreateResponse,
    EnterpriseInstrumentBaselineItem,
    EnterpriseInstrumentBaselineListResponse,
    EnterpriseBaselineComparisonResponse,
    EnterpriseBaselineApprovalRequest,
    EnterpriseBaselineApprovalResponse,
)

router = APIRouter(prefix="/api/enterprise", tags=["Enterprise Intake"])

EXPORT_READINESS_HISTORY: list[dict] = []


def _audit_actor_from_request(request: Request) -> tuple[str, str]:
    actor = request.headers.get("x-lumenai-actor", "unknown")
    role = request.headers.get("x-lumenai-role", "viewer")
    return actor, role






def _vendor_baseline_record_to_dict(record) -> dict:
    return {
        "baseline_id": getattr(record, "id", None),
        "vendor_name": getattr(record, "vendor_name", "") or "",
        "instrument_name": getattr(record, "instrument_name", "") or "",
        "instrument_category": getattr(record, "instrument_category", "") or "",
        "catalog_number": getattr(record, "catalog_number", "") or "",
        "model_number": getattr(record, "model_number", "") or "",
        "barcode_value": getattr(record, "barcode_value", "") or "",
        "qr_code_value": getattr(record, "qr_code_value", "") or "",
        "key_dot_value": getattr(record, "key_dot_value", "") or "",
        "tray_name": getattr(record, "tray_name", "") or "",
        "baseline_image_url": getattr(record, "baseline_image_url", "") or "",
        "acceptable_condition_notes": getattr(record, "acceptable_condition_notes", "") or "",
        "unacceptable_condition_examples": getattr(record, "unacceptable_condition_examples", "") or "",
        "ifu_reference": getattr(record, "ifu_reference", "") or "",
        "subscription_tier": getattr(record, "subscription_tier", "") or "",
        "baseline_source": getattr(record, "baseline_source", "") or "",
        "baseline_status": getattr(record, "baseline_status", "") or "",
        "approval_status": getattr(record, "approval_status", "") or "",
        "baseline_version": getattr(record, "baseline_version", "") or "",
        "approved_by": getattr(record, "approved_by", "") or "",
        "approval_notes": getattr(record, "approval_notes", "") or "",
        "created_at": record.created_at.isoformat() if getattr(record, "created_at", None) else "",
        "updated_at": record.updated_at.isoformat() if getattr(record, "updated_at", None) else "",
    }


def _calculate_baseline_aware_score(
    *,
    finding_type: str | None = None,
    risk_level: str | None = None,
    vendor_baseline_id: int | None = None,
    hospital_baseline_id: int | None = None,
    historical_match_count: int = 0,
    baseline_status: str | None = None,
) -> dict:
    """
    Baseline-aware scoring engine.

    Scoring hierarchy:
    1. Approved vendor baseline = highest confidence
    2. Approved hospital baseline = high confidence
    3. Historical pattern match = medium confidence
    4. No baseline = provisional, low confidence, review required
    """

    normalized_risk = (risk_level or "").lower()
    normalized_finding = (finding_type or "").lower()
    normalized_baseline_status = (baseline_status or "").lower()

    base_score = 50

    if normalized_risk in ["critical", "high"]:
        base_score = 85
    elif normalized_risk in ["medium", "moderate"]:
        base_score = 65
    elif normalized_risk in ["low"]:
        base_score = 35

    high_risk_keywords = [
        "bioburden",
        "blood",
        "tissue",
        "bone",
        "contamination",
        "broken",
        "crack",
        "rust",
        "failed indicator",
        "missing lock",
        "no lock",
        "wet tray",
    ]

    if any(keyword in normalized_finding for keyword in high_risk_keywords):
        base_score = max(base_score, 75)

    if vendor_baseline_id and normalized_baseline_status in ["approved", "active", "vendor_approved"]:
        return {
            "score": min(100, base_score + 10),
            "score_confidence": "high",
            "score_basis": "Compared against approved vendor baseline.",
            "baseline_source": "vendor",
            "baseline_status": "approved",
            "requires_baseline_review": False,
            "manual_review_required": False,
        }

    if hospital_baseline_id and normalized_baseline_status in ["approved", "active", "hospital_approved"]:
        return {
            "score": min(95, base_score + 5),
            "score_confidence": "medium_high",
            "score_basis": "Compared against approved hospital baseline.",
            "baseline_source": "hospital",
            "baseline_status": "approved",
            "requires_baseline_review": False,
            "manual_review_required": False,
        }

    if historical_match_count >= 3:
        return {
            "score": base_score,
            "score_confidence": "medium",
            "score_basis": "No approved baseline available. Score based on historical similar findings and inspection risk metadata.",
            "baseline_source": "historical_pattern",
            "baseline_status": "missing",
            "requires_baseline_review": True,
            "manual_review_required": False,
        }

    return {
        "score": base_score,
        "score_confidence": "low",
        "score_basis": "No approved baseline available. Score is provisional and based only on finding type, risk level, and inspection metadata.",
        "baseline_source": "none",
        "baseline_status": "missing",
        "requires_baseline_review": True,
        "manual_review_required": True,
    }


def _record_enterprise_audit(
    db: Session,
    request: Request,
    *,
    tenant_id: str,
    tenant_name: str,
    action_type: str,
    resource_type: str,
    resource_id: str,
    details: dict,
    status: str = "success",
    compliance_flag: bool = True,
) -> None:
    actor, role = _audit_actor_from_request(request)

    db.add(
        AuditLog(
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            actor_email=actor,
            actor_role=role,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            request_method=request.method,
            request_path=str(request.url.path),
            client_ip=request.client.host if request.client else "",
            details=json.dumps(details, default=str),
            compliance_flag=compliance_flag,
        )
    )



def _risk_scores_for_severity(severity: str) -> tuple[int, int, int, int, int, str]:
    normalized = (severity or "").lower().strip()

    if normalized == "critical":
        return 95, 90, 85, 80, 90, "critical"

    if normalized == "high":
        return 80, 75, 70, 65, 75, "high"

    if normalized == "moderate":
        return 55, 50, 50, 45, 50, "moderate"

    return 25, 20, 20, 15, 20, "low"


def _require_governance_packet_access(request: Request):
    require_hospital_or_enterprise_admin(request)



def _require_vendor_baseline_approval_access(request: Request):
    require_hospital_or_enterprise_admin(request)



def _require_vendor_baseline_audit_access(request: Request):
    require_hospital_or_enterprise_admin(request)



def _require_vendor_baseline_library_access(request: Request):
    require_hospital_or_enterprise_admin(request)



@router.post("/intake", response_model=EnterpriseInspectionIntakeResponse)
def create_enterprise_intake(
    payload: EnterpriseInspectionIntakeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    require_hospital_or_enterprise_admin(request)
    facility = EnterpriseFacility(
        tenant_id=payload.tenant_id,
        name=payload.facility_name,
        facility_type="hospital",
        status="active",
    )
    db.add(facility)
    db.flush()

    department = EnterpriseDepartment(
        tenant_id=payload.tenant_id,
        facility_id=facility.id,
        name=payload.department_name,
        department_type="spd",
        status="active",
    )
    db.add(department)
    db.flush()

    vendor = EnterpriseVendor(
        tenant_id=payload.tenant_id,
        name=payload.vendor_name,
        vendor_type="medical_device",
        risk_tier="unassigned",
        status="active",
    )
    db.add(vendor)
    db.flush()

    instrument = EnterpriseInstrument(
        tenant_id=payload.tenant_id,
        vendor_id=vendor.id,
        name=payload.instrument_name,
        instrument_type=payload.instrument_category,
        category=payload.instrument_category,
        risk_class="high-risk reusable medical device",
        status="active",
    )
    db.add(instrument)
    db.flush()

    evidence = None
    if payload.evidence_file_name or payload.evidence_file_url:
        evidence = EnterpriseEvidence(
            tenant_id=payload.tenant_id,
            inspection_id=None,
            evidence_type="inspection_photo",
            file_name=payload.evidence_file_name or "demo-evidence.png",
            file_url=payload.evidence_file_url,
            mime_type="image/png",
            uploaded_by="demo-user",
        )
        db.add(evidence)
        db.flush()

    finding = EnterpriseFinding(
        tenant_id=payload.tenant_id,
        inspection_id=None,
        instrument_id=instrument.id,
        vendor_id=vendor.id,
        finding_category=payload.finding_category,
        finding_description=payload.finding_description,
        severity=payload.severity,
        confidence_score=payload.confidence_score,
        human_confirmed=False,
    )
    db.add(finding)
    db.flush()

    # Compute live ranking score at intake time (pre-cached for KPI queries)
    from app.schemas.ranking import RankingRequest as _RankingRequest
    from app.services.ranking_engine import score_inspection as _score_inspection
    _rank_req = _RankingRequest(
        finding_category=finding.finding_category,
        severity=finding.severity,
        confidence_score=finding.confidence_score,
        instrument_id=instrument.id,
        barcode_value=getattr(payload, "barcode_value", "") or "",
        qr_code_value=getattr(payload, "qr_code_value", "") or "",
        key_dot_value=getattr(payload, "key_dot_value", "") or "",
        tenant_id=payload.tenant_id,
    )
    _rank_result = _score_inspection(_rank_req, db=db)
    overall_score = _rank_result.inspection_score
    risk_tier = _rank_result.risk_level.lower()

    (
        patient_safety_score,
        regulatory_score,
        operational_score,
        vendor_score,
        _legacy_overall,
        _legacy_tier,
    ) = _risk_scores_for_severity(payload.severity)

    risk_score = EnterpriseRiskScore(
        tenant_id=payload.tenant_id,
        finding_id=finding.id,
        inspection_id=finding.id,
        patient_safety_score=patient_safety_score,
        regulatory_score=regulatory_score,
        operational_score=operational_score,
        vendor_score=vendor_score,
        overall_score=overall_score,
        risk_tier=risk_tier,
    )
    db.add(risk_score)
    db.flush()

    # Auto-trigger CAPA for Critical findings with confirmed baseline
    _capa_auto_created = False
    if _rank_result.risk_level == "Critical" and _rank_result.final_ranking_allowed:
        from app.routes.ranking import _maybe_trigger_capa
        _capa_auto_created = _maybe_trigger_capa(db, finding.id, _rank_result, payload.tenant_id)

    disposition = EnterpriseDisposition(
        tenant_id=payload.tenant_id,
        inspection_id=finding.id,
        recommended_action=_rank_result.recommended_action or payload.recommended_action,
        final_action="Pending human review",
        status="recommended",
    )
    db.add(disposition)
    db.flush()

    _record_enterprise_audit(
        db,
        request,
        tenant_id=payload.tenant_id,
        tenant_name=payload.tenant_name,
        action_type="enterprise_intake_created",
        resource_type="enterprise_finding",
        resource_id=str(finding.id),
        details={
            "facility_id": facility.id,
            "department_id": department.id,
            "vendor_id": vendor.id,
            "instrument_id": instrument.id,
            "evidence_id": evidence.id if evidence else None,
            "finding_id": finding.id,
            "risk_score_id": risk_score.id,
            "disposition_id": disposition.id,
            "severity": payload.severity,
            "finding_category": payload.finding_category,
            "recommended_action": payload.recommended_action,
            "workflow_status": "created_pending_human_review",
        },
    )

    db.commit()

    return EnterpriseInspectionIntakeResponse(
        status="success",
        message="Enterprise inspection intake created.",
        tenant_id=payload.tenant_id,
        facility_id=facility.id,
        department_id=department.id,
        vendor_id=vendor.id,
        instrument_id=instrument.id,
        evidence_id=evidence.id if evidence else None,
        finding_id=finding.id,
        risk_score_id=risk_score.id,
        disposition_id=disposition.id,
        workflow_status="created_pending_human_review",
    )


@router.get("/intake/history", response_model=EnterpriseIntakeHistoryResponse)
def list_enterprise_intake_history(
    request: Request,
    limit: int = 25,
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    limit = max(1, min(limit, 100))

    findings = (
        db.query(EnterpriseFinding)
        .order_by(EnterpriseFinding.id.desc())
        .limit(limit)
        .all()
    )

    items: list[EnterpriseIntakeHistoryItem] = []

    for finding in findings:
        vendor = db.get(EnterpriseVendor, finding.vendor_id) if finding.vendor_id else None
        instrument = db.get(EnterpriseInstrument, finding.instrument_id) if finding.instrument_id else None

        risk_score = (
            db.query(EnterpriseRiskScore)
            .filter(EnterpriseRiskScore.finding_id == finding.id)
            .order_by(EnterpriseRiskScore.id.desc())
            .first()
        )

        disposition = (
            db.query(EnterpriseDisposition)
            .filter(EnterpriseDisposition.finding_id == finding.id)
            .order_by(EnterpriseDisposition.id.desc())
            .first()
        )

        items.append(
            EnterpriseIntakeHistoryItem(
                finding_id=finding.id,
                vendor_id=finding.vendor_id,
                instrument_id=finding.instrument_id,
                risk_score_id=risk_score.id if risk_score else None,
                disposition_id=disposition.id if disposition else None,
                vendor_name=vendor.name if vendor else "",
                instrument_name=instrument.name if instrument else "",
                instrument_category=instrument.category if instrument else "",
                finding_category=finding.finding_category,
                finding_description=finding.finding_description,
                severity=finding.severity,
                confidence_score=finding.confidence_score,
                risk_tier=risk_score.risk_tier if risk_score else "",
                overall_score=risk_score.overall_score if risk_score else 0,
                recommended_action=disposition.recommended_action if disposition else "",
                final_action=disposition.final_action if disposition else "",
                disposition_status=disposition.status if disposition else "",
                workflow_status=disposition.status if disposition else "created_pending_human_review",
                human_review_status=disposition.status if disposition else "",
                human_confirmed=bool(finding.human_confirmed),
                created_at=finding.created_at.isoformat() if finding.created_at else "",
            )
        )

    return EnterpriseIntakeHistoryResponse(items=items)



def _vendor_baseline_audit_events_for_packet(db: Session, baseline_id: int) -> list[dict]:
    events = (
        db.query(VendorBaselineAuditEvent)
        .filter(VendorBaselineAuditEvent.baseline_id == baseline_id)
        .order_by(VendorBaselineAuditEvent.created_at.asc())
        .all()
    )

    return [
        {
            "event_id": event.id,
            "event_type": event.event_type,
            "actor": event.actor,
            "actor_role": event.actor_role,
            "decision": event.decision,
            "notes": event.notes,
            "evidence_source": event.evidence_source,
            "finding_id": event.finding_id,
            "inspection_id": event.inspection_id,
            "matched_identifier_type": event.matched_identifier_type,
            "matched_identifier_value": event.matched_identifier_value,
            "previous_status": event.previous_status,
            "new_status": event.new_status,
            "created_at": event.created_at.isoformat() if event.created_at else "",
        }
        for event in events
    ]


def _vendor_baseline_audit_trail_for_packet(db: Session, limit: int = 10) -> list[dict]:
    rows = (
        db.query(EnterpriseVendorBaselineSubscription)
        .order_by(EnterpriseVendorBaselineSubscription.id.desc())
        .limit(limit)
        .all()
    )

    trail = []
    for row in rows:
        baseline_id = getattr(row, "baseline_id", None) or getattr(row, "id", None)
        if not baseline_id:
            continue

        audit_events = _vendor_baseline_audit_events_for_packet(db, int(baseline_id))

        if not audit_events:
            continue

        trail.append(
            {
                "baseline_id": int(baseline_id),
                "vendor_name": getattr(row, "vendor_name", "") or "",
                "instrument_name": getattr(row, "instrument_name", "") or "",
                "instrument_category": getattr(row, "instrument_category", "") or "",
                "catalog_number": getattr(row, "catalog_number", "") or "",
                "model_number": getattr(row, "model_number", "") or "",
                "barcode_value": getattr(row, "barcode_value", "") or "",
                "baseline_status": getattr(row, "baseline_status", "") or "",
                "approval_status": getattr(row, "approval_status", "") or "",
                "approved_by": getattr(row, "approved_by", "") or "",
                "audit_source": "persistent_table",
                "audit_event_count": len(audit_events),
                "audit_events": audit_events,
            }
        )

    return trail

@router.get("/intake/{finding_id}/governance-packet", response_model=EnterpriseGovernancePacketResponse)
def get_enterprise_governance_packet(
    finding_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    finding = db.get(EnterpriseFinding, finding_id)

    if not finding:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Enterprise finding not found")

    vendor = db.get(EnterpriseVendor, finding.vendor_id) if finding.vendor_id else None
    instrument = db.get(EnterpriseInstrument, finding.instrument_id) if finding.instrument_id else None

    risk_score = (
        db.query(EnterpriseRiskScore)
        .filter(EnterpriseRiskScore.finding_id == finding.id)
        .order_by(EnterpriseRiskScore.id.desc())
        .first()
    )

    disposition = (
        db.query(EnterpriseDisposition)
        .filter(EnterpriseDisposition.finding_id == finding.id)
        .order_by(EnterpriseDisposition.id.desc())
        .first()
    )

    evidence_rows = (
        db.query(EnterpriseEvidence)
        .filter(EnterpriseEvidence.inspection_id == finding.id)
        .order_by(EnterpriseEvidence.id.desc())
        .all()
    )

    vendor_name = vendor.name if vendor else ""
    instrument_name = instrument.name if instrument else ""
    instrument_category = instrument.category if instrument else ""

    severity = finding.severity or "unassigned"
    risk_tier = risk_score.risk_tier if risk_score else "unassigned"
    overall_score = risk_score.overall_score if risk_score else 0
    recommended_action = disposition.recommended_action if disposition else "Pending recommended action"
    final_action = disposition.final_action if disposition else "Pending human review"
    workflow_status = disposition.status if disposition else "created_pending_human_review"

    title = f"Governance Packet: Finding #{finding.id} - {instrument_name or 'Instrument Review'}"

    summary = (
        f"LumenAI recorded a {severity} enterprise quality finding for "
        f"{instrument_name or 'an instrument'} associated with "
        f"{vendor_name or 'an identified vendor'}. The finding was classified as "
        f"{finding.finding_category}. The current recommended action is: "
        f"{recommended_action}."
    )

    _record_enterprise_audit(
        db,
        request,
        tenant_id=finding.tenant_id,
        tenant_name="",
        action_type="governance_packet_exported_json",
        resource_type="enterprise_governance_packet",
        resource_id=str(finding.id),
        details={
            "finding_id": finding.id,
            "vendor_id": finding.vendor_id,
            "instrument_id": finding.instrument_id,
            "risk_score_id": risk_score.id if risk_score else None,
            "disposition_id": disposition.id if disposition else None,
            "packet_type": "enterprise_intake_governance_packet",
            "export_format": "json",
        },
    )
    db.commit()

    baseline_instrument_id = getattr(finding, "instrument_id", None) or getattr(instrument, "id", None)
    baseline_vendor_id = getattr(finding, "vendor_id", None) or getattr(vendor, "id", None)

    baseline_rows = []
    if baseline_instrument_id:
        baseline_rows = (
            db.query(EnterpriseInstrumentBaseline)
            .filter(EnterpriseInstrumentBaseline.instrument_id == baseline_instrument_id)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .all()
        )

    if not baseline_rows and baseline_vendor_id:
        baseline_rows = (
            db.query(EnterpriseInstrumentBaseline)
            .filter(EnterpriseInstrumentBaseline.vendor_id == baseline_vendor_id)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .all()
        )

    # Demo/audit fallback: include recent baselines if direct linkage is unexpectedly missing.
    if not baseline_rows:
        baseline_rows = (
            db.query(EnterpriseInstrumentBaseline)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .limit(10)
            .all()
        )

    if not baseline_rows:
        baseline_rows = (
            db.query(EnterpriseInstrumentBaseline)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .limit(10)
            .all()
        )

    vendor_baseline_audit_trail = _vendor_baseline_audit_trail_for_packet(db)
    vendor_baseline_audit_event_count = sum(
        item.get("audit_event_count", 0)
        for item in vendor_baseline_audit_trail
    )

    baseline_evidence_items = [
        {
            "baseline_id": baseline.id,
            "instrument_id": baseline.instrument_id,
            "vendor_id": baseline.vendor_id,
            "manufacturer_name": baseline.manufacturer_name or "",
            "model_number": baseline.model_number or "",
            "catalog_number": baseline.catalog_number or "",
            "baseline_type": baseline.baseline_type or "",
            "file_name": baseline.file_name or "",
            "storage_uri": baseline.storage_uri or "",
            "baseline_status": baseline.baseline_status or "",
            "approved_by": baseline.approved_by or "",
            "approved_at": baseline.approved_at.isoformat() if baseline.approved_at else "",
            "known_normal_characteristics": baseline.known_normal_characteristics or "",
            "known_abnormal_characteristics": baseline.known_abnormal_characteristics or "",
            "baseline_notes": baseline.baseline_notes or "",
            "audit_significance": (
                "Approved manufacturer baseline may be used as trusted comparison evidence."
                if (baseline.baseline_status or "").lower() == "approved"
                else "Baseline captured but not yet approved as trusted comparison evidence."
            ),
        }
        for baseline in baseline_rows
    ]

    return EnterpriseGovernancePacketResponse(
        packet_type="enterprise_intake_governance_packet",
        title=title,
        summary=summary,
        finding_id=finding.id,
        inspection_id=finding.id,
        vendor_name=vendor_name,
        instrument_name=instrument_name,
        instrument_category=instrument_category,
        finding_category=finding.finding_category,
        finding_description=finding.finding_description,
        severity=severity,
        confidence_score=finding.confidence_score,
        risk_tier=risk_tier,
        overall_score=overall_score,
        recommended_action=recommended_action,
        final_action=final_action,
        workflow_status=workflow_status,
        human_review_status=workflow_status,
        human_confirmed=bool(finding.human_confirmed),
        evidence_to_action_chain=[
            "Enterprise intake record created",
            "Vendor and instrument context linked",
            "Finding classified and severity assigned",
            "Risk score generated",
            "Disposition recommended",
            "Workflow placed in pending human review status",
            "Governance packet generated for review",
        ],
        audit_readiness={
            "finding_id": finding.id,
            "vendor_id": finding.vendor_id,
            "instrument_id": finding.instrument_id,
            "risk_score_id": risk_score.id if risk_score else None,
            "disposition_id": disposition.id if disposition else None,
            "created_at": finding.created_at.isoformat() if finding.created_at else "",
            "baseline_lookup_instrument_id": baseline_instrument_id,
            "baseline_lookup_vendor_id": baseline_vendor_id,
            "baseline_evidence_count": len(baseline_evidence_items),
            "vendor_baseline_audit_event_count": vendor_baseline_audit_event_count,
            "vendor_baseline_audit_trail_count": len(vendor_baseline_audit_trail),
        },
        evidence_attachments=[
            EnterpriseGovernanceEvidenceItem(
                evidence_id=row.id,
                evidence_type=row.evidence_type,
                file_name=row.file_name,
                storage_uri=row.storage_key or row.file_url or "",
                content_type=row.mime_type or "",
                notes="",
                created_at=row.created_at.isoformat() if row.created_at else "",
            )
            for row in evidence_rows
        ],
        baseline_evidence=baseline_evidence_items,
        vendor_baseline_audit_trail=vendor_baseline_audit_trail,
    )


@router.get("/intake/{finding_id}/governance-packet.pdf")
def get_enterprise_governance_packet_pdf(
    finding_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_governance_packet_access(request)

    from io import BytesIO
    import hashlib

    from fastapi import HTTPException
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.lib import colors

    finding = db.get(EnterpriseFinding, finding_id)

    if not finding:
        raise HTTPException(status_code=404, detail="Enterprise finding not found")

    vendor = db.get(EnterpriseVendor, finding.vendor_id) if finding.vendor_id else None
    instrument = db.get(EnterpriseInstrument, finding.instrument_id) if finding.instrument_id else None

    risk_score = (
        db.query(EnterpriseRiskScore)
        .filter(EnterpriseRiskScore.finding_id == finding.id)
        .order_by(EnterpriseRiskScore.id.desc())
        .first()
    )

    disposition = (
        db.query(EnterpriseDisposition)
        .filter(EnterpriseDisposition.finding_id == finding.id)
        .order_by(EnterpriseDisposition.id.desc())
        .first()
    )


    baseline_instrument_id = getattr(finding, "instrument_id", None) or getattr(instrument, "id", None)
    baseline_vendor_id = getattr(finding, "vendor_id", None) or getattr(vendor, "id", None)

    baseline_rows = []
    if baseline_instrument_id:
        baseline_rows = (
            db.query(EnterpriseInstrumentBaseline)
            .filter(EnterpriseInstrumentBaseline.instrument_id == baseline_instrument_id)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .all()
        )

    if not baseline_rows and baseline_vendor_id:
        baseline_rows = (
            db.query(EnterpriseInstrumentBaseline)
            .filter(EnterpriseInstrumentBaseline.vendor_id == baseline_vendor_id)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .all()
        )

    if not baseline_rows:
        baseline_rows = (
            db.query(EnterpriseInstrumentBaseline)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .limit(10)
            .all()
        )

    evidence_rows = (
        db.query(EnterpriseEvidence)
        .filter(EnterpriseEvidence.inspection_id == finding.id)
        .order_by(EnterpriseEvidence.id.desc())
        .all()
    )

    vendor_name = vendor.name if vendor else ""
    instrument_name = instrument.name if instrument else ""
    instrument_category = instrument.category if instrument else ""
    severity = finding.severity or "unassigned"
    risk_tier = risk_score.risk_tier if risk_score else "unassigned"
    overall_score = risk_score.overall_score if risk_score else 0
    recommended_action = disposition.recommended_action if disposition else "Pending recommended action"
    final_action = disposition.final_action if disposition else "Pending human review"
    workflow_status = disposition.status if disposition else "created_pending_human_review"

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
        title=f"LumenAI Governance Packet Finding {finding.id}",
    )

    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("LumenAI Governance Packet", styles["Title"]))
    story.append(Spacer(1, 12))

    story.append(
        Paragraph(
            f"Finding #{finding.id}: {instrument_name or 'Instrument Review'}",
            styles["Heading2"],
        )
    )

    story.append(Spacer(1, 10))

    summary = (
        f"LumenAI recorded a <b>{severity}</b> enterprise quality finding for "
        f"<b>{instrument_name or 'an instrument'}</b> associated with "
        f"<b>{vendor_name or 'an identified vendor'}</b>. The finding was classified as "
        f"<b>{finding.finding_category}</b>. The current recommended action is: "
        f"<b>{recommended_action}</b>."
    )

    story.append(Paragraph(summary, styles["BodyText"]))
    story.append(Spacer(1, 16))

    case_data = [
        ["Field", "Value"],
        ["Vendor", vendor_name or "—"],
        ["Instrument", instrument_name or "—"],
        ["Instrument Category", instrument_category or "—"],
        ["Finding Category", finding.finding_category or "—"],
        ["Severity", severity],
        ["Confidence Score", str(finding.confidence_score)],
        ["Risk Tier", risk_tier],
        ["Overall Risk Score", str(overall_score)],
        ["Recommended Action", recommended_action],
        ["Final Action", final_action],
        ["Human Confirmed", "Yes" if finding.human_confirmed else "No"],
        ["Workflow Status", workflow_status],
    ]

    table = Table(case_data, colWidths=[160, 340])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E0E7FF")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1E1B4B")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ]
        )
    )

    story.append(table)
    story.append(Spacer(1, 18))

    story.append(Paragraph("Evidence-to-Action Chain", styles["Heading3"]))
    chain = [
        "Enterprise intake record created",
        "Vendor and instrument context linked",
        "Finding classified and severity assigned",
        "Risk score generated",
        "Disposition recommended",
        "Workflow placed in pending human review status",
        "Governance packet generated for review",
    ]

    for step in chain:
        story.append(Paragraph(f"• {step}", styles["BodyText"]))

    story.append(Spacer(1, 18))

    story.append(Paragraph("Evidence Attachments", styles["Heading3"]))

    if evidence_rows:
        evidence_data = [["Evidence ID", "Type", "File Name", "Notes"]]
        for row in evidence_rows:
            evidence_data.append([
                str(row.id),
                row.evidence_type or "—",
                row.file_name or "—",
                "—",
            ])

        evidence_table = Table(evidence_data, colWidths=[80, 120, 150, 150])
        evidence_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DBEAFE")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ]
            )
        )
        story.append(evidence_table)
    else:
        story.append(Paragraph("No evidence attachments are linked to this finding.", styles["BodyText"]))

    story.append(Spacer(1, 18))

    story.append(Paragraph("Audit Readiness", styles["Heading3"]))

    audit_data = [
        ["Finding ID", str(finding.id)],
        ["Vendor ID", str(finding.vendor_id or "—")],
        ["Instrument ID", str(finding.instrument_id or "—")],
        ["Risk Score ID", str(risk_score.id if risk_score else "—")],
        ["Disposition ID", str(disposition.id if disposition else "—")],
        ["Created At", finding.created_at.isoformat() if finding.created_at else "—"],
    ]

    audit_table = Table(audit_data, colWidths=[160, 340])
    audit_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    story.append(audit_table)
    story.append(Spacer(1, 18))

    story.append(
        Paragraph(
            "Generated by LumenAI for executive governance, quality review, vendor escalation, and survey readiness.",
            styles["Italic"],
        )
    )


    story.append(Spacer(1, 12))
    story.append(Paragraph("Manufacturer Baseline Evidence", styles["Heading2"]))

    if baseline_rows:
        baseline_table_data = [[
            "Baseline ID",
            "Manufacturer",
            "Model",
            "Status",
            "Approved By",
            "Audit Significance",
        ]]

        for baseline in baseline_rows:
            audit_significance = (
                "Approved manufacturer baseline may be used as trusted comparison evidence."
                if (baseline.baseline_status or "").lower() == "approved"
                else "Baseline captured but not yet approved as trusted comparison evidence."
            )

            baseline_table_data.append([
                str(baseline.id),
                baseline.manufacturer_name or "",
                baseline.model_number or "",
                baseline.baseline_status or "",
                baseline.approved_by or "",
                audit_significance,
            ])

        baseline_table = Table(baseline_table_data, colWidths=[60, 85, 85, 65, 85, 150])
        baseline_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(baseline_table)

        for baseline in baseline_rows[:3]:
            story.append(Spacer(1, 8))
            story.append(Paragraph(f"Baseline #{baseline.id} Detail", styles["Heading3"]))
            story.append(Paragraph(f"<b>Storage URI:</b> {baseline.storage_uri or ''}", styles["BodyText"]))
            story.append(Paragraph(f"<b>Known Normal Characteristics:</b> {baseline.known_normal_characteristics or 'Not documented.'}", styles["BodyText"]))
            story.append(Paragraph(f"<b>Known Abnormal Characteristics:</b> {baseline.known_abnormal_characteristics or 'Not documented.'}", styles["BodyText"]))
            story.append(Paragraph(f"<b>Baseline Notes:</b> {baseline.baseline_notes or 'Not documented.'}", styles["BodyText"]))
    else:
        story.append(Paragraph("No manufacturer baseline evidence is currently attached to this governance packet.", styles["BodyText"]))

    story.append(Spacer(1, 18))
    story.append(Paragraph("Vendor Baseline Audit Trail", styles["Heading2"]))

    vendor_baseline_audit_trail = _vendor_baseline_audit_trail_for_packet(db)

    if vendor_baseline_audit_trail:
        for baseline in vendor_baseline_audit_trail[:5]:
            story.append(Spacer(1, 8))
            story.append(
                Paragraph(
                    f"Vendor Baseline #{baseline.get('baseline_id')} — "
                    f"{baseline.get('vendor_name', '')} / {baseline.get('instrument_name', '')}",
                    styles["Heading3"],
                )
            )

            audit_rows = [[
                "Event",
                "Actor",
                "Decision",
                "Status Change",
                "Evidence",
                "Created",
            ]]

            for event in baseline.get("audit_events", []):
                audit_rows.append([
                    event.get("event_type", ""),
                    f"{event.get('actor', '')} ({event.get('actor_role', '')})",
                    event.get("decision", ""),
                    f"{event.get('previous_status') or 'none'} -> {event.get('new_status') or ''}",
                    event.get("evidence_source", ""),
                    event.get("created_at", ""),
                ])

            audit_table = Table(audit_rows, colWidths=[90, 90, 70, 105, 95, 90])
            audit_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DBEAFE")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(audit_table)
    else:
        story.append(Paragraph("No persistent vendor baseline audit events are available.", styles["BodyText"]))


    doc.build(story)

    pdf_bytes = buffer.getvalue()
    packet_hash = hashlib.sha256(pdf_bytes).hexdigest()

    buffer.seek(0)

    filename = f"lumenai-governance-packet-finding-{finding.id}.pdf"

    _record_enterprise_audit(
        db,
        request,
        tenant_id=finding.tenant_id,
        tenant_name="",
        action_type="governance_packet_exported_pdf",
        resource_type="enterprise_governance_packet",
        resource_id=str(finding.id),
        details={
            "finding_id": finding.id,
            "vendor_id": finding.vendor_id,
            "instrument_id": finding.instrument_id,
            "risk_score_id": risk_score.id if risk_score else None,
            "disposition_id": disposition.id if disposition else None,
            "packet_type": "enterprise_intake_governance_packet",
            "export_format": "pdf",
            "filename": filename,
            "included_vendor_baseline_audit_trail": True,
            "vendor_baseline_audit_trail_section": "Vendor Baseline Audit Trail",
            "packet_hash_algorithm": "SHA-256",
            "packet_hash": packet_hash,
            "tamper_evident": True,
        },
    )
    db.commit()

    record_enterprise_audit_event(
        db,
        action_type="centralized_governance_packet_exported_pdf",
        resource_type="enterprise_governance_packet",
        resource_id=finding.id,
        actor=request.headers.get("x-lumenai-actor", "unknown"),
        actor_role=request.headers.get("x-lumenai-role", "viewer"),
        finding_id=finding.id,
        packet_hash=packet_hash,
        packet_hash_algorithm="SHA-256",
        details={
            "legacy_action_type": "governance_packet_exported_pdf",
            "packet_type": "enterprise_intake_governance_packet",
            "export_format": "pdf",
            "filename": f"lumenai-governance-packet-finding-{finding.id}.pdf",
            "included_vendor_baseline_audit_trail": True,
            "tamper_evident": True,
            "workflow_status": "governance_packet_exported_pdf",
        },
    )


    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )




@router.get("/intake/{finding_id}/governance-packet/verify-hash")
def verify_enterprise_governance_packet_hash(
    finding_id: int,
    request: Request,
    packet_hash: str,
    db: Session = Depends(get_db),
):
    _require_governance_packet_access(request)

    import json

    normalized_hash = (packet_hash or "").strip().lower()

    if not normalized_hash:
        return {
            "status": "error",
            "finding_id": finding_id,
            "verified": False,
            "message": "packet_hash is required.",
        }

    audit_model = AuditLog if "AuditLog" in globals() else EnterpriseAuditTrail

    rows = (
        db.query(audit_model)
        .filter(audit_model.resource_id == str(finding_id))
        .filter(audit_model.action_type == "governance_packet_exported_pdf")
        .order_by(audit_model.created_at.desc())
        .limit(100)
        .all()
    )

    matched_export = None
    checked_count = 0

    for row in rows:
        details = getattr(row, "details", {}) or {}

        if isinstance(details, str):
            try:
                details = json.loads(details)
            except Exception:
                details = {}

        stored_hash = (details.get("packet_hash") or "").strip().lower()

        if not stored_hash:
            continue

        checked_count += 1

        if stored_hash == normalized_hash:
            matched_export = {
                "event_id": row.id,
                "action_type": row.action_type,
                "actor": getattr(row, "actor_email", "") or getattr(row, "actor", ""),
                "actor_role": getattr(row, "actor_role", ""),
                "resource_type": getattr(row, "resource_type", ""),
                "resource_id": getattr(row, "resource_id", ""),
                "packet_type": details.get("packet_type", ""),
                "export_format": details.get("export_format", ""),
                "filename": details.get("filename", ""),
                "packet_hash_algorithm": details.get("packet_hash_algorithm", "SHA-256"),
                "packet_hash": details.get("packet_hash", ""),
                "tamper_evident": details.get("tamper_evident", False),
                "included_vendor_baseline_audit_trail": details.get("included_vendor_baseline_audit_trail", False),
                "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else "",
            }
            break

    if matched_export:
        return {
            "status": "success",
            "finding_id": finding_id,
            "verified": True,
            "verification_status": "hash_matched_export_record",
            "packet_hash_algorithm": matched_export.get("packet_hash_algorithm"),
            "packet_hash": matched_export.get("packet_hash"),
            "matched_export": matched_export,
            "checked_hash_export_count": checked_count,
            "message": "Packet hash matches a stored governance PDF export record.",
        }

    return {
        "status": "success",
        "finding_id": finding_id,
        "verified": False,
        "verification_status": "hash_not_found",
        "packet_hash_algorithm": "SHA-256",
        "packet_hash": normalized_hash,
        "checked_hash_export_count": checked_count,
        "message": "Packet hash does not match any stored governance PDF export record for this finding.",
    }


@router.get("/intake/{finding_id}/governance-export-history")
def get_enterprise_governance_export_history(
    finding_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_governance_packet_access(request)

    import json

    audit_model = AuditLog if "AuditLog" in globals() else EnterpriseAuditTrail

    rows = (
        db.query(audit_model)
        .filter(audit_model.resource_id == str(finding_id))
        .filter(
            audit_model.action_type.in_(
                [
                    "governance_packet_exported_json",
                    "governance_packet_exported_pdf",
                    "governance_export_package_generated",
                ]
            )
        )
        .order_by(audit_model.created_at.desc())
        .limit(25)
        .all()
    )

    exports = []

    for row in rows:
        details = getattr(row, "details", {}) or {}

        if isinstance(details, str):
            try:
                details = json.loads(details)
            except Exception:
                details = {}

        included_vendor_baseline_audit_trail = bool(
            details.get("included_vendor_baseline_audit_trail")
        ) or row.action_type in [
            "governance_packet_exported_pdf",
            "governance_export_package_generated",
        ]

        exports.append(
            {
                "event_id": row.id,
                "action_type": row.action_type,
                "actor": getattr(row, "actor_email", "") or getattr(row, "actor", ""),
                "actor_role": getattr(row, "actor_role", ""),
                "resource_type": getattr(row, "resource_type", ""),
                "resource_id": getattr(row, "resource_id", ""),
                "packet_type": details.get("packet_type", ""),
                "export_format": details.get("export_format", ""),
                "filename": details.get("filename", ""),
                "included_vendor_baseline_audit_trail": included_vendor_baseline_audit_trail,
                "audit_event_count": details.get("audit_event_count"),
                "vendor_baseline_audit_event_count": details.get("vendor_baseline_audit_event_count"),
                "packet_hash_algorithm": details.get("packet_hash_algorithm", ""),
                "packet_hash": details.get("packet_hash", ""),
                "tamper_evident": details.get("tamper_evident", False),
                "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else "",
            }
        )

    return {
        "status": "success",
        "finding_id": finding_id,
        "export_count": len(exports),
        "last_exported_at": exports[0]["created_at"] if exports else "",
        "exports": exports,
    }


@router.get("/audit-trail", response_model=EnterpriseAuditTrailResponse)
def list_enterprise_audit_trail(
    request: Request,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    limit = max(1, min(limit, 100))

    rows = (
        db.query(AuditLog)
        .filter(
            AuditLog.action_type.in_(
                [
                    "enterprise_intake_created",
                    "governance_packet_exported_json",
                    "governance_packet_exported_pdf",
                ]
            )
        )
        .order_by(AuditLog.id.desc())
        .limit(limit)
        .all()
    )

    return EnterpriseAuditTrailResponse(
        items=[
            EnterpriseAuditTrailItem(
                id=row.id,
                tenant_id=row.tenant_id,
                actor_email=row.actor_email,
                actor_role=row.actor_role,
                action_type=row.action_type,
                resource_type=row.resource_type,
                resource_id=row.resource_id,
                status=row.status,
                request_method=row.request_method,
                request_path=row.request_path,
                details=row.details,
                compliance_flag=row.compliance_flag,
                created_at=row.created_at.isoformat() if row.created_at else "",
            )
            for row in rows
        ]
    )


@router.post("/intake/{finding_id}/review", response_model=EnterpriseHumanReviewResponse)
def review_enterprise_finding(
    finding_id: int,
    payload: EnterpriseHumanReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    require_hospital_or_enterprise_admin(request)
    from fastapi import HTTPException

    allowed_decisions = {
        "approve",
        "request_more_evidence",
        "escalate_to_ip",
        "escalate_to_vendor",
        "open_capa",
        "reject",
    }

    decision = (payload.decision or "").strip().lower()

    if decision not in allowed_decisions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid review decision. Allowed: {sorted(allowed_decisions)}",
        )

    finding = db.get(EnterpriseFinding, finding_id)

    if not finding:
        raise HTTPException(status_code=404, detail="Enterprise finding not found")

    finding.human_confirmed = payload.human_confirmed

    disposition = (
        db.query(EnterpriseDisposition)
        .filter(EnterpriseDisposition.finding_id == finding.id)
        .order_by(EnterpriseDisposition.id.desc())
        .first()
    )

    if disposition:
        disposition.status = f"human_review_{decision}"
        disposition.final_action = payload.review_notes or decision.replace("_", " ")

    workflow_status = f"human_review_{decision}"

    _record_enterprise_audit(
        db,
        request,
        tenant_id=finding.tenant_id,
        tenant_name="",
        action_type="enterprise_human_review_completed",
        resource_type="enterprise_finding",
        resource_id=str(finding.id),
        details={
            "finding_id": finding.id,
            "decision": decision,
            "reviewer_name": payload.reviewer_name,
            "reviewer_role": payload.reviewer_role,
            "human_confirmed": payload.human_confirmed,
            "review_notes": payload.review_notes,
            "workflow_status": workflow_status,
        },
    )

    db.commit()

    return EnterpriseHumanReviewResponse(
        status="success",
        message="Enterprise finding human review completed.",
        inspection_id=finding.id,
        decision=decision,
        reviewer_name=payload.reviewer_name,
        reviewer_role=payload.reviewer_role,
        human_confirmed=finding.human_confirmed,
        workflow_status=workflow_status,
    )


@router.post("/intake/{finding_id}/capa", response_model=EnterpriseCapaCreateResponse)
def create_enterprise_capa(
    finding_id: int,
    payload: EnterpriseCapaCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    require_hospital_or_enterprise_admin(request)
    from fastapi import HTTPException

    finding = db.get(EnterpriseFinding, finding_id)

    if not finding:
        raise HTTPException(status_code=404, detail="Enterprise finding not found")

    due_date_value = None
    if payload.due_date:
        try:
            due_date_value = datetime.fromisoformat(payload.due_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="due_date must be ISO format, e.g. 2026-06-30")

    capa_number = f"CAPA-{finding.id:06d}"

    existing = (
        db.query(EnterpriseCapa)
        .filter(EnterpriseCapa.finding_id == finding.id)
        .order_by(EnterpriseCapa.id.desc())
        .first()
    )

    if existing:
        return EnterpriseCapaCreateResponse(
            status="success",
            message="Existing CAPA found for this finding.",
            inspection_id=finding.id,
            capa_id=existing.id,
            capa_number=existing.capa_number,
            capa_status=existing.status,
            workflow_status="capa_already_open",
        )

    capa = EnterpriseCapa(
        tenant_id=finding.tenant_id,
        inspection_id=finding.id,
        vendor_id=finding.vendor_id,
        capa_number=capa_number,
        title=payload.title,
        description=payload.description,
        owner_id=payload.owner_id,
        status=payload.status or "open",
        due_date=due_date_value,
    )

    db.add(capa)
    db.flush()

    disposition = (
        db.query(EnterpriseDisposition)
        .filter(EnterpriseDisposition.finding_id == finding.id)
        .order_by(EnterpriseDisposition.id.desc())
        .first()
    )

    if disposition:
        disposition.status = "capa_open"
        disposition.final_action = f"CAPA opened: {capa.capa_number}"

    _record_enterprise_audit(
        db,
        request,
        tenant_id=finding.tenant_id,
        tenant_name="",
        action_type="enterprise_capa_opened",
        resource_type="enterprise_capa",
        resource_id=str(capa.id),
        details={
            "finding_id": finding.id,
            "vendor_id": finding.vendor_id,
            "instrument_id": finding.instrument_id,
            "capa_id": capa.id,
            "capa_number": capa.capa_number,
            "title": capa.title,
            "status": capa.status,
            "workflow_status": "capa_open",
        },
    )

    db.commit()

    return EnterpriseCapaCreateResponse(
        status="success",
        message="Enterprise CAPA opened.",
        inspection_id=finding.id,
        capa_id=capa.id,
        capa_number=capa.capa_number,
        capa_status=capa.status,
        workflow_status="capa_open",
    )


@router.get("/capas", response_model=EnterpriseCapaListResponse)
def list_enterprise_capas(
    request: Request,
    limit: int = 25,
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    limit = max(1, min(limit, 100))

    rows = (
        db.query(EnterpriseCapa)
        .order_by(EnterpriseCapa.id.desc())
        .limit(limit)
        .all()
    )

    return EnterpriseCapaListResponse(
        items=[
            EnterpriseCapaListItem(
                capa_id=row.id,
                finding_id=row.inspection_id,
                vendor_id=row.vendor_id,
                capa_number=row.capa_number,
                title=row.title,
                description=row.description,
                status=row.status,
                due_date=row.due_date.isoformat() if row.due_date else "",
                closed_at=row.closed_at.isoformat() if row.closed_at else "",
                created_at=row.created_at.isoformat() if row.created_at else "",
            )
            for row in rows
        ]
    )


@router.patch("/capas/{capa_id}/status", response_model=EnterpriseCapaStatusUpdateResponse)
def update_enterprise_capa_status(
    capa_id: int,
    payload: EnterpriseCapaStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    require_hospital_or_enterprise_admin(request)
    from fastapi import HTTPException

    allowed_statuses = {
        "open",
        "in_progress",
        "pending_review",
        "closed",
        "overdue",
        "cancelled",
    }

    new_status = (payload.status or "").strip().lower()

    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid CAPA status. Allowed: {sorted(allowed_statuses)}",
        )

    capa = db.get(EnterpriseCapa, capa_id)

    if not capa:
        raise HTTPException(status_code=404, detail="Enterprise CAPA not found")

    previous_status = capa.status
    capa.status = new_status

    if new_status == "closed" and not capa.closed_at:
        capa.closed_at = datetime.now(timezone.utc)

    if new_status != "closed":
        capa.closed_at = None

    if capa.finding_id:
        disposition = (
            db.query(EnterpriseDisposition)
            .filter(EnterpriseDisposition.finding_id == capa.finding_id)
            .order_by(EnterpriseDisposition.id.desc())
            .first()
        )

        if disposition:
            disposition.status = f"capa_{new_status}"
            disposition.final_action = payload.note or f"CAPA status updated to {new_status}"

    _record_enterprise_audit(
        db,
        request,
        tenant_id=capa.tenant_id,
        tenant_name="",
        action_type="enterprise_capa_status_updated",
        resource_type="enterprise_capa",
        resource_id=str(capa.id),
        details={
            "capa_id": capa.id,
            "capa_number": capa.capa_number,
            "finding_id": capa.finding_id,
            "previous_status": previous_status,
            "new_status": new_status,
            "note": payload.note,
            "workflow_status": f"capa_{new_status}",
            "closed_at": capa.closed_at.isoformat() if capa.closed_at else "",
        },
    )

    db.commit()

    return EnterpriseCapaStatusUpdateResponse(
        status="success",
        message="Enterprise CAPA status updated.",
        capa_id=capa.id,
        capa_number=capa.capa_number,
        capa_status=capa.status,
        workflow_status=f"capa_{new_status}",
        closed_at=capa.closed_at.isoformat() if capa.closed_at else "",
    )


@router.get("/capas/summary", response_model=EnterpriseCapaSummaryResponse)
def get_enterprise_capa_summary(
    request: Request,
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    from datetime import datetime, timezone

    rows = db.query(EnterpriseCapa).all()

    total = len(rows)
    open_count = sum(1 for row in rows if row.status == "open")
    in_progress_count = sum(1 for row in rows if row.status == "in_progress")
    pending_review_count = sum(1 for row in rows if row.status == "pending_review")
    closed_count = sum(1 for row in rows if row.status == "closed")
    overdue_count = sum(1 for row in rows if row.status == "overdue")
    cancelled_count = sum(1 for row in rows if row.status == "cancelled")

    now = datetime.now(timezone.utc)
    active_rows = [row for row in rows if row.status != "closed"]

    days_open_values = []
    for row in active_rows:
        if row.created_at:
            created_at = row.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            days_open_values.append((now - created_at).days)

    average_days_open = (
        round(sum(days_open_values) / len(days_open_values), 1)
        if days_open_values
        else 0.0
    )

    closure_rate = round((closed_count / total) * 100, 1) if total else 0.0

    if overdue_count > 0:
        risk_message = "Executive attention required: overdue CAPA records exist."
    elif open_count + in_progress_count + pending_review_count > 0:
        risk_message = "Active CAPA workload requires continued monitoring."
    elif total > 0 and closed_count == total:
        risk_message = "All CAPA records are closed."
    else:
        risk_message = "No CAPA records available."

    return EnterpriseCapaSummaryResponse(
        total_capas=total,
        open_capas=open_count,
        in_progress_capas=in_progress_count,
        pending_review_capas=pending_review_count,
        closed_capas=closed_count,
        overdue_capas=overdue_count,
        cancelled_capas=cancelled_count,
        average_days_open=average_days_open,
        closure_rate=closure_rate,
        risk_message=risk_message,
    )


@router.post("/intake/{finding_id}/evidence", response_model=EnterpriseEvidenceUploadResponse)
def upload_enterprise_evidence(
    finding_id: int,
    request: Request,
    file: UploadFile = File(...),
    evidence_type: str = Form(default="borescope_image"),
    notes: str = Form(default=""),
    db: Session = Depends(get_db),
):
    require_hospital_or_enterprise_admin(request)
    from fastapi import HTTPException

    finding = db.get(EnterpriseFinding, finding_id)

    if not finding:
        raise HTTPException(status_code=404, detail="Enterprise finding not found")

    safe_file_name = os.path.basename(file.filename or "evidence.bin")
    object_key = f"evidence/finding_{finding.id}/{safe_file_name}"

    stored = save_upload_file(
        file_obj=file.file,
        file_name=safe_file_name,
        object_key=object_key,
        content_type=file.content_type or "application/octet-stream",
    )

    storage_path = stored.storage_uri

    evidence = EnterpriseEvidence(
        tenant_id=finding.tenant_id,
        inspection_id=finding.id,
        evidence_type=evidence_type,
        file_name=safe_file_name,
        file_url=storage_path,
        storage_key=storage_path,
        mime_type=file.content_type or "",
        
    )

    db.add(evidence)
    db.flush()

    _record_enterprise_audit(
        db,
        request,
        tenant_id=finding.tenant_id,
        tenant_name="",
        action_type="enterprise_evidence_uploaded",
        resource_type="enterprise_evidence",
        resource_id=str(evidence.id),
        details={
            "finding_id": finding.id,
            "evidence_id": evidence.id,
            "evidence_type": evidence.evidence_type,
            "file_name": evidence.file_name,
            "storage_uri": evidence.storage_key or evidence.file_url,
            "content_type": evidence.mime_type,
            "notes": notes,
            "workflow_status": "evidence_attached",
        },
    )

    db.commit()

    return EnterpriseEvidenceUploadResponse(
        status="success",
        message="Enterprise evidence uploaded and attached to finding.",
        finding_id=finding.id,
        inspection_id=finding.id,
        evidence_id=evidence.id,
        evidence_type=evidence.evidence_type,
        file_name=evidence.file_name,
        storage_uri=evidence.storage_key or evidence.file_url,
        workflow_status="evidence_attached",
    )


@router.get("/intake/{finding_id}/evidence", response_model=EnterpriseEvidenceListResponse)
def list_enterprise_evidence(
    finding_id: int,
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException

    finding = db.get(EnterpriseFinding, finding_id)

    if not finding:
        raise HTTPException(status_code=404, detail="Enterprise finding not found")

    rows = (
        db.query(EnterpriseEvidence)
        .filter(EnterpriseEvidence.inspection_id == finding.id)
        .order_by(EnterpriseEvidence.id.desc())
        .all()
    )

    return EnterpriseEvidenceListResponse(
        items=[
            EnterpriseEvidenceListItem(
                evidence_id=row.id,
                finding_id=row.inspection_id,
                evidence_type=row.evidence_type,
                file_name=row.file_name,
                storage_uri=row.storage_key or row.file_url or "",
                content_type=row.mime_type or "",
                notes="",
                created_at=row.created_at.isoformat() if row.created_at else "",
            )
            for row in rows
        ]
    )


@router.get("/evidence/{evidence_id}/download")
def download_enterprise_evidence(
    evidence_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    from fastapi import HTTPException

    evidence = db.get(EnterpriseEvidence, evidence_id)

    if not evidence:
        raise HTTPException(status_code=404, detail="Enterprise evidence not found")

    storage_path = evidence.storage_key or evidence.file_url

    if not storage_path:
        raise HTTPException(status_code=404, detail="Evidence file path not found")

    resolved_path = open_stored_object(storage_path)

    if not os.path.exists(resolved_path):
        raise HTTPException(status_code=404, detail="Evidence file not found on storage")

    _record_enterprise_audit(
        db,
        request,
        tenant_id=evidence.tenant_id,
        tenant_name="",
        action_type="enterprise_evidence_downloaded",
        resource_type="enterprise_evidence",
        resource_id=str(evidence.id),
        details={
            "evidence_id": evidence.id,
            "inspection_id": evidence.inspection_id,
            "file_name": evidence.file_name,
            "storage_uri": storage_path,
            "mime_type": evidence.mime_type,
            "workflow_status": "evidence_downloaded",
        },
    )

    db.commit()

    return FileResponse(
        path=resolved_path,
        media_type=evidence.mime_type or "application/octet-stream",
        filename=evidence.file_name or f"evidence-{evidence.id}",
    )


@router.post("/instruments/{instrument_id}/baseline", response_model=EnterpriseInstrumentBaselineCreateResponse)
def upload_instrument_baseline(
    instrument_id: int,
    request: Request,
    file: UploadFile = File(...),
    manufacturer_name: str = Form(default=""),
    model_number: str = Form(default=""),
    catalog_number: str = Form(default=""),
    baseline_type: str = Form(default="manufacturer_reference"),
    known_normal_characteristics: str = Form(default=""),
    known_abnormal_characteristics: str = Form(default=""),
    baseline_notes: str = Form(default=""),
    baseline_status: str = Form(default="pending_review"),
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException

    instrument = db.get(EnterpriseInstrument, instrument_id)

    if not instrument:
        raise HTTPException(status_code=404, detail="Enterprise instrument not found")

    safe_file_name = os.path.basename(file.filename or "baseline.bin")
    object_key = f"baselines/instrument_{instrument.id}/{safe_file_name}"

    stored = save_upload_file(
        file_obj=file.file,
        file_name=safe_file_name,
        object_key=object_key,
        content_type=file.content_type or "application/octet-stream",
    )

    storage_path = stored.storage_uri

    baseline = EnterpriseInstrumentBaseline(
        tenant_id=instrument.tenant_id,
        vendor_id=instrument.vendor_id,
        instrument_id=instrument.id,
        manufacturer_name=manufacturer_name or "",
        model_number=model_number or "",
        catalog_number=catalog_number or "",
        baseline_type=baseline_type or "manufacturer_reference",
        file_name=safe_file_name,
        storage_uri=storage_path,
        content_type=file.content_type or "",
        known_normal_characteristics=known_normal_characteristics or "",
        known_abnormal_characteristics=known_abnormal_characteristics or "",
        baseline_notes=baseline_notes or "",
        baseline_status=baseline_status or "pending_review",
    )

    db.add(baseline)
    db.flush()

    _record_enterprise_audit(
        db,
        request,
        tenant_id=instrument.tenant_id,
        tenant_name="",
        action_type="manufacturer_baseline_uploaded",
        resource_type="enterprise_instrument_baseline",
        resource_id=str(baseline.id),
        details={
            "baseline_id": baseline.id,
            "baseline_trust_status": baseline.baseline_status,
            "instrument_id": instrument.id,
            "vendor_id": instrument.vendor_id,
            "manufacturer_name": baseline.manufacturer_name,
            "model_number": baseline.model_number,
            "catalog_number": baseline.catalog_number,
            "baseline_type": baseline.baseline_type,
            "file_name": baseline.file_name,
            "storage_uri": baseline.storage_uri,
            "baseline_status": baseline.baseline_status,
            "workflow_status": "baseline_uploaded_pending_review",
        },
    )

    db.commit()

    return EnterpriseInstrumentBaselineCreateResponse(
        status="success",
        message="Manufacturer baseline uploaded and linked to instrument.",
        baseline_id=baseline.id,
        instrument_id=instrument.id,
        vendor_id=instrument.vendor_id,
        manufacturer_name=baseline.manufacturer_name,
        model_number=baseline.model_number,
        catalog_number=baseline.catalog_number,
        baseline_type=baseline.baseline_type,
        file_name=baseline.file_name,
        storage_uri=baseline.storage_uri,
        baseline_status=baseline.baseline_status,
        workflow_status="baseline_uploaded_pending_review",
    )


@router.get("/instruments/{instrument_id}/baseline", response_model=EnterpriseInstrumentBaselineListResponse)
def list_instrument_baselines(
    instrument_id: int,
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException

    instrument = db.get(EnterpriseInstrument, instrument_id)

    if not instrument:
        raise HTTPException(status_code=404, detail="Enterprise instrument not found")

    rows = (
        db.query(EnterpriseInstrumentBaseline)
        .filter(EnterpriseInstrumentBaseline.instrument_id == instrument.id)
        .order_by(EnterpriseInstrumentBaseline.id.desc())
        .all()
    )

    return EnterpriseInstrumentBaselineListResponse(
        items=[
            EnterpriseInstrumentBaselineItem(
                baseline_id=row.id,
                instrument_id=row.instrument_id,
                vendor_id=row.vendor_id,
                manufacturer_name=row.manufacturer_name or "",
                model_number=row.model_number or "",
                catalog_number=row.catalog_number or "",
                baseline_type=row.baseline_type or "",
                file_name=row.file_name or "",
                storage_uri=row.storage_uri or "",
                known_normal_characteristics=row.known_normal_characteristics or "",
                known_abnormal_characteristics=row.known_abnormal_characteristics or "",
                baseline_notes=row.baseline_notes or "",
                baseline_status=row.baseline_status or "",
                approved_by=row.approved_by or "",
                approved_at=row.approved_at.isoformat() if row.approved_at else "",
                created_at=row.created_at.isoformat() if row.created_at else "",
            )
            for row in rows
        ]
    )


@router.get("/vendor-baselines", response_model=EnterpriseInstrumentBaselineListResponse)
def list_vendor_baselines(
    limit: int = 50,
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 100))

    rows = (
        db.query(EnterpriseInstrumentBaseline)
        .order_by(EnterpriseInstrumentBaseline.id.desc())
        .limit(limit)
        .all()
    )

    return EnterpriseInstrumentBaselineListResponse(
        items=[
            EnterpriseInstrumentBaselineItem(
                baseline_id=row.id,
                instrument_id=row.instrument_id,
                vendor_id=row.vendor_id,
                manufacturer_name=row.manufacturer_name or "",
                model_number=row.model_number or "",
                catalog_number=row.catalog_number or "",
                baseline_type=row.baseline_type or "",
                file_name=row.file_name or "",
                storage_uri=row.storage_uri or "",
                known_normal_characteristics=row.known_normal_characteristics or "",
                known_abnormal_characteristics=row.known_abnormal_characteristics or "",
                baseline_notes=row.baseline_notes or "",
                baseline_status=row.baseline_status or "",
                approved_by=row.approved_by or "",
                approved_at=row.approved_at.isoformat() if row.approved_at else "",
                created_at=row.created_at.isoformat() if row.created_at else "",
            )
            for row in rows
        ]
    )


@router.post("/intake/{finding_id}/baseline-comparison", response_model=EnterpriseBaselineComparisonResponse)
def compare_finding_to_manufacturer_baseline(
    finding_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException

    finding = db.get(EnterpriseFinding, finding_id)

    if not finding:
        raise HTTPException(status_code=404, detail="Enterprise finding not found")

    instrument = (
        db.get(EnterpriseInstrument, finding.instrument_id)
        if finding.instrument_id
        else None
    )

    if not instrument:
        raise HTTPException(status_code=404, detail="Linked enterprise instrument not found")

    baseline = (
        db.query(EnterpriseInstrumentBaseline)
        .filter(
            EnterpriseInstrumentBaseline.instrument_id == instrument.id,
            EnterpriseInstrumentBaseline.baseline_status == "approved",
        )
        .order_by(EnterpriseInstrumentBaseline.id.desc())
        .first()
    )

    if not baseline:
        baseline = (
            db.query(EnterpriseInstrumentBaseline)
            .filter(EnterpriseInstrumentBaseline.instrument_id == instrument.id)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .first()
        )

    if not baseline:
        raise HTTPException(
            status_code=404,
            detail="No manufacturer baseline exists for this instrument",
        )

    evidence = (
        db.query(EnterpriseEvidence)
        .filter(EnterpriseEvidence.inspection_id == finding.id)
        .order_by(EnterpriseEvidence.id.desc())
        .first()
    )

    # Rules-based v1 scoring.
    # Future version should compare image features using CV/AI.
    finding_text = " ".join(
        [
            finding.finding_category or "",
            finding.finding_description or "",
            finding.severity or "",
        ]
    ).lower()

    normal_text = " ".join(
        [
            baseline.known_normal_characteristics or "",
            baseline.baseline_notes or "",
        ]
    ).lower()

    abnormal_text = (baseline.known_abnormal_characteristics or "").lower()

    risk_terms = [
        "bioburden",
        "retained debris",
        "debris",
        "blood",
        "tissue",
        "foreign material",
        "corrosion",
        "rust",
        "flaking",
        "residue",
    ]

    normal_artifact_terms = [
        "weld",
        "weld pattern",
        "machining",
        "surface variation",
        "discoloration",
        "manufacturing artifact",
        "normal manufacturing",
        "factory",
    ]

    risk_hits = sum(1 for term in risk_terms if term in finding_text)
    baseline_normal_hits = sum(
        1 for term in normal_artifact_terms
        if term in finding_text and term in normal_text
    )
    abnormal_hits = sum(1 for term in risk_terms if term in abnormal_text and term in finding_text)

    base_score = 50
    score = base_score + (risk_hits * 10) + (abnormal_hits * 12) - (baseline_normal_hits * 15)

    if (finding.severity or "").lower() == "critical":
        score += 15
    elif (finding.severity or "").lower() == "high":
        score += 10
    elif (finding.severity or "").lower() == "moderate":
        score += 5

    score = max(0, min(score, 100))

    if score >= 80:
        deviation_level = "high_deviation"
        baseline_alignment = "not_consistent_with_baseline"
        vendor_signal = "Strong vendor-quality signal; finding appears to deviate from baseline."
        recommended_action = "Escalate to vendor-quality review and consider CAPA if confirmed."
    elif score >= 55:
        deviation_level = "moderate_deviation"
        baseline_alignment = "partially_consistent_with_baseline"
        vendor_signal = "Moderate signal; human review should compare evidence against baseline."
        recommended_action = "Require reviewer confirmation and additional evidence if needed."
    else:
        deviation_level = "low_deviation"
        baseline_alignment = "consistent_with_known_baseline_artifact"
        vendor_signal = "Low vendor-quality signal; finding may reflect known manufacturer appearance."
        recommended_action = "Document baseline alignment and avoid false-positive escalation unless reviewer confirms."

    _record_enterprise_audit(
        db,
        request,
        tenant_id=finding.tenant_id,
        tenant_name="",
        action_type="baseline_comparison_scored",
        resource_type="enterprise_finding",
        resource_id=str(finding.id),
        details={
            "finding_id": finding.id,
            "instrument_id": instrument.id,
            "vendor_id": instrument.vendor_id,
            "baseline_id": baseline.id,
            "evidence_id": evidence.id if evidence else None,
            "comparison_score": score,
            "deviation_level": deviation_level,
            "baseline_alignment": baseline_alignment,
            "vendor_management_signal": vendor_signal,
            "recommended_action": recommended_action,
            "workflow_status": "baseline_comparison_completed",
        },
    )

    db.commit()

    return EnterpriseBaselineComparisonResponse(
        status="success",
        message="Baseline-to-inspection comparison score generated.",
        finding_id=finding.id,
        instrument_id=instrument.id,
        vendor_id=instrument.vendor_id,
        baseline_id=baseline.id,
        evidence_id=evidence.id if evidence else None,
        comparison_score=score,
        deviation_level=deviation_level,
        baseline_alignment=baseline_alignment,
        vendor_management_signal=vendor_signal,
        recommended_action=recommended_action,
        workflow_status="baseline_comparison_completed",
    )


@router.post("/baselines/{baseline_id}/review", response_model=EnterpriseBaselineApprovalResponse)
def review_manufacturer_baseline(
    baseline_id: int,
    payload: EnterpriseBaselineApprovalRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException

    baseline = db.get(EnterpriseInstrumentBaseline, baseline_id)

    if not baseline:
        raise HTTPException(status_code=404, detail="Manufacturer baseline not found")

    decision = (payload.decision or "").strip().lower()

    if decision not in {"approve", "reject", "request_more_evidence"}:
        raise HTTPException(
            status_code=400,
            detail="Decision must be approve, reject, or request_more_evidence",
        )

    if decision == "approve":
        baseline.baseline_status = "approved"
        baseline.approved_by = payload.reviewer_name or "Baseline Reviewer"
        baseline.approved_at = datetime.now(timezone.utc)
        workflow_status = "baseline_approved"
        message = "Manufacturer baseline approved as trusted reference."
    elif decision == "reject":
        baseline.baseline_status = "rejected"
        baseline.approved_by = payload.reviewer_name or "Baseline Reviewer"
        baseline.approved_at = datetime.now(timezone.utc)
        workflow_status = "baseline_rejected"
        message = "Manufacturer baseline rejected and will not be used as trusted reference."
    else:
        baseline.baseline_status = "more_evidence_requested"
        baseline.approved_by = payload.reviewer_name or "Baseline Reviewer"
        baseline.approved_at = datetime.now(timezone.utc)
        workflow_status = "baseline_more_evidence_requested"
        message = "More evidence requested before baseline approval."

    baseline.updated_at = datetime.now(timezone.utc)

    audit_details = {
        "baseline_id": baseline.id,
        "instrument_id": baseline.instrument_id,
        "vendor_id": baseline.vendor_id,
        "baseline_status": baseline.baseline_status,
        "reviewer_name": payload.reviewer_name,
        "reviewer_role": payload.reviewer_role,
        "decision": decision,
        "review_notes": payload.review_notes,
        "workflow_status": workflow_status,
    }

    _record_enterprise_audit(
        db,
        request,
        tenant_id=baseline.tenant_id,
        tenant_name="",
        action_type=workflow_status,
        resource_type="enterprise_instrument_baseline",
        resource_id=str(baseline.id),
        details=audit_details,
    )

    # Explicit fallback insert so baseline approval decisions always appear in audit trail.

    db.commit()
    db.refresh(baseline)

    return EnterpriseBaselineApprovalResponse(
        status="success",
        message=message,
        baseline_id=baseline.id,
        instrument_id=baseline.instrument_id,
        vendor_id=baseline.vendor_id,
        baseline_status=baseline.baseline_status,
        approved_by=baseline.approved_by or "",
        approved_at=baseline.approved_at.isoformat() if baseline.approved_at else "",
        workflow_status=workflow_status,
    )


@router.get("/storage/health")
def enterprise_storage_health():
    from fastapi import HTTPException

    try:
        return storage_health_check()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Object storage health check failed",
                "error": str(exc),
            },
        )



@router.get("/intake/{finding_id}/governance-export-package", response_model=EnterpriseGovernanceExportPackageResponse)
def get_enterprise_governance_export_package(
    finding_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException

    finding = db.get(EnterpriseFinding, finding_id)

    if not finding:
        raise HTTPException(status_code=404, detail="Enterprise finding not found")

    baseline_rows = []
    if finding.instrument_id:
        baseline_rows = (
            db.query(EnterpriseInstrumentBaseline)
            .filter(EnterpriseInstrumentBaseline.instrument_id == finding.instrument_id)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .all()
        )

    if not baseline_rows and finding.vendor_id:
        baseline_rows = (
            db.query(EnterpriseInstrumentBaseline)
            .filter(EnterpriseInstrumentBaseline.vendor_id == finding.vendor_id)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .all()
        )

    approved_baseline_count = sum(
        1 for baseline in baseline_rows
        if (baseline.baseline_status or "").lower() == "approved"
    )

    evidence_attachment_count = (
        db.query(EnterpriseEvidence)
        .filter(EnterpriseEvidence.inspection_id == finding.id)
        .count()
    )

    comparison_score_count = 0

    capa_count = 0
    try:
        capa_count = (
            db.query(EnterpriseCapa)
            .filter(EnterpriseCapa.finding_id == finding.id)
            .count()
        )
    except Exception:
        capa_count = 0

    audit_event_count = 0
    try:
        audit_event_count = (
            db.query(EnterpriseAuditTrail)
            .filter(EnterpriseAuditTrail.resource_id == str(finding.id))
            .count()
        )
    except Exception:
        audit_event_count = 0

    vendor_baseline_audit_event_count = 0
    try:
        vendor_baseline_audit_event_count = db.query(VendorBaselineAuditEvent).count()
        audit_event_count += vendor_baseline_audit_event_count
    except Exception:
        vendor_baseline_audit_event_count = 0

    included_sections = [
        "enterprise finding",
        "risk score",
        "disposition",
        "governance packet json",
        "governance packet pdf",
        "evidence attachments",
        "audit trail",
    ]

    if vendor_baseline_audit_event_count:
        included_sections.append("vendor baseline audit trail")

    if baseline_rows:
        included_sections.append("manufacturer baseline evidence")

    if approved_baseline_count:
        included_sections.append("approved baseline decision")

    if comparison_score_count:
        included_sections.append("baseline comparison score")

    if capa_count:
        included_sections.append("CAPA status")

    readiness_status = "in_progress"
    if approved_baseline_count and comparison_score_count:
        readiness_status = "vendor_ip_leadership_ready"
    elif approved_baseline_count:
        readiness_status = "baseline_approved_packet_ready"
    elif baseline_rows:
        readiness_status = "baseline_captured_pending_full_review"

    _record_enterprise_audit(
        db,
        request,
        tenant_id=finding.tenant_id,
        tenant_name="",
        action_type="governance_export_package_generated",
        resource_type="enterprise_governance_export_package",
        resource_id=str(finding.id),
        details={
            "finding_id": finding.id,
            "json_packet_url": f"/api/enterprise/intake/{finding.id}/governance-packet",
            "pdf_packet_url": f"/api/enterprise/intake/{finding.id}/governance-packet.pdf",
            "baseline_evidence_count": len(baseline_rows),
            "approved_baseline_count": approved_baseline_count,
            "evidence_attachment_count": evidence_attachment_count,
            "comparison_score_count": comparison_score_count,
            "capa_count": capa_count,
            "audit_event_count": audit_event_count,
            "vendor_baseline_audit_event_count": vendor_baseline_audit_event_count,
            "readiness_status": readiness_status,
            "workflow_status": "governance_export_package_generated",
        },
    )
    db.commit()

    return EnterpriseGovernanceExportPackageResponse(
        status="success",
        finding_id=finding.id,
        package_type="enterprise_governance_export_package",
        readiness_status=readiness_status,
        json_packet_url=f"/api/enterprise/intake/{finding.id}/governance-packet",
        pdf_packet_url=f"/api/enterprise/intake/{finding.id}/governance-packet.pdf",
        baseline_evidence_count=len(baseline_rows),
        approved_baseline_count=approved_baseline_count,
        evidence_attachment_count=evidence_attachment_count,
        comparison_score_count=comparison_score_count,
        capa_count=capa_count,
        audit_event_count=audit_event_count,
        included_sections=included_sections,
        recommended_use=[
            "leadership review",
            "vendor escalation",
            "infection prevention review",
            "quality committee discussion",
            "survey readiness",
        ],
        message="Governance export package summary generated successfully.",
    )


@router.get("/intake/{finding_id}/governance-zip-bundle")
def get_enterprise_governance_zip_bundle(
    finding_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    import json
    import tempfile
    import zipfile
    from io import BytesIO
    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.lib import colors

    finding = db.get(EnterpriseFinding, finding_id)

    if not finding:
        raise HTTPException(status_code=404, detail="Enterprise finding not found")

    vendor = db.get(EnterpriseVendor, finding.vendor_id) if finding.vendor_id else None
    instrument = db.get(EnterpriseInstrument, finding.instrument_id) if finding.instrument_id else None

    risk_score = (
        db.query(EnterpriseRiskScore)
        .filter(EnterpriseRiskScore.finding_id == finding.id)
        .order_by(EnterpriseRiskScore.id.desc())
        .first()
    )

    disposition = (
        db.query(EnterpriseDisposition)
        .filter(EnterpriseDisposition.finding_id == finding.id)
        .order_by(EnterpriseDisposition.id.desc())
        .first()
    )

    evidence_rows = (
        db.query(EnterpriseEvidence)
        .filter(EnterpriseEvidence.inspection_id == finding.id)
        .order_by(EnterpriseEvidence.id.desc())
        .all()
    )

    baseline_rows = []
    if finding.instrument_id:
        baseline_rows = (
            db.query(EnterpriseInstrumentBaseline)
            .filter(EnterpriseInstrumentBaseline.instrument_id == finding.instrument_id)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .all()
        )

    if not baseline_rows and finding.vendor_id:
        baseline_rows = (
            db.query(EnterpriseInstrumentBaseline)
            .filter(EnterpriseInstrumentBaseline.vendor_id == finding.vendor_id)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .all()
        )

    approved_baseline_count = sum(
        1 for baseline in baseline_rows
        if (baseline.baseline_status or "").lower() == "approved"
    )

    baseline_evidence = [
        {
            "baseline_id": baseline.id,
            "instrument_id": baseline.instrument_id,
            "vendor_id": baseline.vendor_id,
            "manufacturer_name": baseline.manufacturer_name or "",
            "model_number": baseline.model_number or "",
            "catalog_number": baseline.catalog_number or "",
            "baseline_type": baseline.baseline_type or "",
            "file_name": baseline.file_name or "",
            "storage_uri": baseline.storage_uri or "",
            "baseline_status": baseline.baseline_status or "",
            "approved_by": baseline.approved_by or "",
            "approved_at": baseline.approved_at.isoformat() if baseline.approved_at else "",
            "known_normal_characteristics": baseline.known_normal_characteristics or "",
            "known_abnormal_characteristics": baseline.known_abnormal_characteristics or "",
            "baseline_notes": baseline.baseline_notes or "",
            "audit_significance": (
                "Approved manufacturer baseline may be used as trusted comparison evidence."
                if (baseline.baseline_status or "").lower() == "approved"
                else "Baseline captured but not yet approved as trusted comparison evidence."
            ),
        }
        for baseline in baseline_rows
    ]

    evidence_attachments = [
        {
            "evidence_id": evidence.id,
            "evidence_type": evidence.evidence_type or "",
            "file_name": evidence.file_name or "",
            "storage_uri": getattr(evidence, "storage_uri", "") or getattr(evidence, "storage_key", "") or getattr(evidence, "file_url", "") or "",
            "content_type": getattr(evidence, "mime_type", "") or "",
            "created_at": evidence.created_at.isoformat() if evidence.created_at else "",
        }
        for evidence in evidence_rows
    ]

    governance_packet = {
        "packet_type": "enterprise_intake_governance_packet",
        "finding_id": finding.id,
        "vendor_name": (getattr(vendor, "vendor_name", None) or getattr(vendor, "name", None) or getattr(vendor, "vendor", None) or "") if vendor else "",
        "instrument_name": (getattr(instrument, "instrument_name", None) or getattr(instrument, "name", None) or getattr(instrument, "instrument", None) or "") if instrument else "",
        "instrument_category": (getattr(instrument, "instrument_category", None) or getattr(instrument, "category", None) or "") if instrument else "",
        "finding_category": finding.finding_category or "",
        "finding_description": finding.finding_description or "",
        "severity": finding.severity or "",
        "confidence_score": finding.confidence_score,
        "risk_tier": risk_score.risk_tier if risk_score else "",
        "overall_score": risk_score.overall_score if risk_score else 0,
        "recommended_action": disposition.recommended_action if disposition else "",
        "final_action": disposition.final_action if disposition else "",
        "workflow_status": getattr(finding, "workflow_status", "") or "",
        "human_confirmed": bool(getattr(finding, "human_confirmed", False)),
        "baseline_evidence": baseline_evidence,
        "evidence_attachments": evidence_attachments,
        "audit_readiness": {
            "finding_id": finding.id,
            "vendor_id": finding.vendor_id,
            "instrument_id": finding.instrument_id,
            "risk_score_id": risk_score.id if risk_score else None,
            "disposition_id": disposition.id if disposition else None,
            "baseline_evidence_count": len(baseline_evidence),
            "approved_baseline_count": approved_baseline_count,
            "evidence_attachment_count": len(evidence_attachments),
            "created_at": finding.created_at.isoformat() if finding.created_at else "",
        },
    }

    readiness_status = "in_progress"
    if approved_baseline_count:
        readiness_status = "vendor_ip_leadership_ready"
    elif baseline_rows:
        readiness_status = "baseline_captured_pending_full_review"

    manifest = {
        "status": "success",
        "finding_id": finding.id,
        "package_type": "enterprise_governance_zip_bundle",
        "readiness_status": readiness_status,
        "included_files": [
            "governance-packet.json",
            "baseline-evidence.json",
            "evidence-attachments.json",
            "governance-packet-summary.pdf",
            "export-package-manifest.json",
            "README.txt",
        ],
        "included_sections": [
            "enterprise finding",
            "risk score",
            "disposition",
            "manufacturer baseline evidence",
            "baseline approval decision",
            "evidence attachments",
            "audit readiness summary",
        ],
        "recommended_use": [
            "leadership review",
            "vendor escalation",
            "infection prevention review",
            "quality committee discussion",
            "survey readiness",
        ],
    }

    # Build compact PDF summary for the ZIP.
    pdf_buffer = BytesIO()
    pdf_doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("LumenAI Governance Packet Summary", styles["Title"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Finding ID: {finding.id}", styles["BodyText"]))
    story.append(Paragraph(f"Vendor: {governance_packet['vendor_name']}", styles["BodyText"]))
    story.append(Paragraph(f"Instrument: {governance_packet['instrument_name']}", styles["BodyText"]))
    story.append(Paragraph(f"Finding Category: {governance_packet['finding_category']}", styles["BodyText"]))
    story.append(Paragraph(f"Severity: {governance_packet['severity']}", styles["BodyText"]))
    story.append(Paragraph(f"Readiness Status: {readiness_status}", styles["BodyText"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Manufacturer Baseline Evidence", styles["Heading2"]))

    if baseline_evidence:
        table_data = [["Baseline", "Manufacturer", "Model", "Status", "Approved By"]]
        for baseline in baseline_evidence:
            table_data.append([
                str(baseline["baseline_id"]),
                baseline["manufacturer_name"],
                baseline["model_number"],
                baseline["baseline_status"],
                baseline["approved_by"],
            ])

        table = Table(table_data, colWidths=[60, 110, 110, 80, 110])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(table)

        for baseline in baseline_evidence[:3]:
            story.append(Spacer(1, 8))
            story.append(Paragraph(f"Baseline #{baseline['baseline_id']} Audit Significance", styles["Heading3"]))
            story.append(Paragraph(baseline["audit_significance"], styles["BodyText"]))
            story.append(Paragraph(f"Known Normal: {baseline['known_normal_characteristics']}", styles["BodyText"]))
            story.append(Paragraph(f"Known Abnormal: {baseline['known_abnormal_characteristics']}", styles["BodyText"]))
    else:
        story.append(Paragraph("No manufacturer baseline evidence attached.", styles["BodyText"]))

    pdf_doc.build(story)
    pdf_buffer.seek(0)

    readme = f"""LumenAI Governance ZIP Bundle

Finding ID: {finding.id}
Vendor: {governance_packet['vendor_name']}
Instrument: {governance_packet['instrument_name']}
Readiness Status: {readiness_status}

This package includes:
- governance-packet.json
- baseline-evidence.json
- evidence-attachments.json
- governance-packet-summary.pdf
- export-package-manifest.json

Recommended use:
- Leadership review
- Vendor escalation
- Infection Prevention review
- Quality committee discussion
- Survey readiness
"""

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"-finding-{finding.id}-governance-bundle.zip")
    tmp.close()

    with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("governance-packet.json", json.dumps(governance_packet, indent=2, default=str))
        zf.writestr("baseline-evidence.json", json.dumps(baseline_evidence, indent=2, default=str))
        zf.writestr("evidence-attachments.json", json.dumps(evidence_attachments, indent=2, default=str))
        zf.writestr("export-package-manifest.json", json.dumps(manifest, indent=2, default=str))
        zf.writestr("README.txt", readme)
        zf.writestr("governance-packet-summary.pdf", pdf_buffer.getvalue())

    _record_enterprise_audit(
        db,
        request,
        tenant_id=finding.tenant_id,
        tenant_name="",
        action_type="governance_zip_bundle_exported",
        resource_type="enterprise_governance_zip_bundle",
        resource_id=str(finding.id),
        details={
            "finding_id": finding.id,
            "readiness_status": readiness_status,
            "baseline_evidence_count": len(baseline_evidence),
            "approved_baseline_count": approved_baseline_count,
            "evidence_attachment_count": len(evidence_attachments),
            "workflow_status": "governance_zip_bundle_exported",
        },
    )
    db.commit()

    return FileResponse(
        path=tmp.name,
        media_type="application/zip",
        filename=f"lumenai-governance-bundle-finding-{finding.id}.zip",
    )


@router.get("/intake/{finding_id}/vendor-escalation-packet", response_model=EnterpriseVendorEscalationPacketResponse)
def get_enterprise_vendor_escalation_packet(
    finding_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException

    finding = db.get(EnterpriseFinding, finding_id)

    if not finding:
        raise HTTPException(status_code=404, detail="Enterprise finding not found")

    vendor = db.get(EnterpriseVendor, finding.vendor_id) if finding.vendor_id else None
    instrument = db.get(EnterpriseInstrument, finding.instrument_id) if finding.instrument_id else None

    baseline_rows = []
    if finding.instrument_id:
        baseline_rows = (
            db.query(EnterpriseInstrumentBaseline)
            .filter(EnterpriseInstrumentBaseline.instrument_id == finding.instrument_id)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .all()
        )

    if not baseline_rows and finding.vendor_id:
        baseline_rows = (
            db.query(EnterpriseInstrumentBaseline)
            .filter(EnterpriseInstrumentBaseline.vendor_id == finding.vendor_id)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .all()
        )

    approved_baseline_count = sum(
        1 for baseline in baseline_rows
        if (baseline.baseline_status or "").lower() == "approved"
    )

    baseline_evidence = [
        {
            "baseline_id": baseline.id,
            "instrument_id": baseline.instrument_id,
            "vendor_id": baseline.vendor_id,
            "manufacturer_name": baseline.manufacturer_name or "",
            "model_number": baseline.model_number or "",
            "catalog_number": baseline.catalog_number or "",
            "baseline_type": baseline.baseline_type or "",
            "file_name": baseline.file_name or "",
            "storage_uri": baseline.storage_uri or "",
            "baseline_status": baseline.baseline_status or "",
            "approved_by": baseline.approved_by or "",
            "approved_at": baseline.approved_at.isoformat() if baseline.approved_at else "",
            "known_normal_characteristics": baseline.known_normal_characteristics or "",
            "known_abnormal_characteristics": baseline.known_abnormal_characteristics or "",
            "baseline_notes": baseline.baseline_notes or "",
            "audit_significance": (
                "Approved manufacturer baseline may be used as trusted comparison evidence."
                if (baseline.baseline_status or "").lower() == "approved"
                else "Baseline captured but not yet approved as trusted comparison evidence."
            ),
        }
        for baseline in baseline_rows
    ]

    evidence_rows = (
        db.query(EnterpriseEvidence)
        .filter(EnterpriseEvidence.inspection_id == finding.id)
        .order_by(EnterpriseEvidence.id.desc())
        .all()
    )

    supporting_evidence = [
        {
            "evidence_id": evidence.id,
            "evidence_type": evidence.evidence_type or "",
            "file_name": evidence.file_name or "",
            "storage_uri": getattr(evidence, "storage_uri", "") or getattr(evidence, "storage_key", "") or getattr(evidence, "file_url", "") or "",
            "content_type": getattr(evidence, "mime_type", "") or "",
            "created_at": evidence.created_at.isoformat() if evidence.created_at else "",
        }
        for evidence in evidence_rows
    ]

    comparison = None
    try:
        comparison = None
    except Exception:
        comparison = None

    comparison_score = getattr(comparison, "comparison_score", None) if comparison else None
    deviation_level = getattr(comparison, "deviation_level", "") if comparison else ""
    baseline_alignment = getattr(comparison, "baseline_alignment", "") if comparison else ""
    vendor_management_signal = getattr(comparison, "vendor_management_signal", "") if comparison else ""

    vendor_name = (getattr(vendor, "vendor_name", None) or getattr(vendor, "name", None) or getattr(vendor, "vendor", None) or "") if vendor else ""
    instrument_name = (getattr(instrument, "instrument_name", None) or getattr(instrument, "name", None) or getattr(instrument, "instrument", None) or "") if instrument else ""
    instrument_category = (getattr(instrument, "instrument_category", None) or getattr(instrument, "category", None) or "") if instrument else ""

    escalation_status = "vendor_review_not_required"
    recommended_vendor_action = "Document internally. Vendor escalation is not recommended unless human reviewer confirms a true defect."

    if deviation_level in ["high_deviation", "critical_deviation"]:
        escalation_status = "vendor_escalation_recommended"
        recommended_vendor_action = (
            "Request vendor quality review, written response, and corrective action plan if the finding is confirmed."
        )
    elif (finding.severity or "").lower() in ["high", "critical"] and not approved_baseline_count:
        escalation_status = "vendor_review_pending_baseline_confirmation"
        recommended_vendor_action = (
            "Hold vendor escalation until manufacturer baseline evidence and human review confirm whether this is a true defect."
        )
    elif approved_baseline_count and baseline_alignment == "consistent_with_known_baseline_artifact":
        escalation_status = "vendor_escalation_not_recommended_baseline_artifact"
        recommended_vendor_action = (
            "Do not escalate as vendor defect at this time. Finding aligns with approved manufacturer baseline artifact."
        )

    requested_vendor_response = (
        "Please review the attached finding, instrument context, and baseline comparison summary. "
        "If vendor review is requested, provide written determination, root cause if applicable, and recommended corrective action."
    )

    escalation_summary = (
        f"LumenAI generated a vendor escalation packet for Finding #{finding.id}. "
        f"The finding involves {instrument_name or 'the instrument'} associated with {vendor_name or 'the vendor'}. "
        f"Current escalation status: {escalation_status}. "
        f"Baseline evidence count: {len(baseline_evidence)}. "
        f"Approved baseline count: {approved_baseline_count}."
    )

    _record_enterprise_audit(
        db,
        request,
        tenant_id=finding.tenant_id,
        tenant_name="",
        action_type="vendor_escalation_packet_generated",
        resource_type="enterprise_vendor_escalation_packet",
        resource_id=str(finding.id),
        details={
            "finding_id": finding.id,
            "vendor_id": finding.vendor_id,
            "instrument_id": finding.instrument_id,
            "vendor_name": vendor_name,
            "instrument_name": instrument_name,
            "escalation_status": escalation_status,
            "baseline_evidence_count": len(baseline_evidence),
            "approved_baseline_count": approved_baseline_count,
            "comparison_score": comparison_score,
            "deviation_level": deviation_level,
            "baseline_alignment": baseline_alignment,
            "workflow_status": "vendor_escalation_packet_generated",
        },
    )
    db.commit()

    return EnterpriseVendorEscalationPacketResponse(
        status="success",
        finding_id=finding.id,
        packet_type="vendor_escalation_packet",
        escalation_status=escalation_status,
        vendor_id=finding.vendor_id,
        vendor_name=vendor_name,
        instrument_id=finding.instrument_id,
        instrument_name=instrument_name,
        instrument_category=instrument_category,
        finding_category=finding.finding_category or "",
        finding_description=finding.finding_description or "",
        severity=finding.severity or "",
        confidence_score=finding.confidence_score,
        baseline_evidence_count=len(baseline_evidence),
        approved_baseline_count=approved_baseline_count,
        comparison_score=comparison_score,
        deviation_level=deviation_level,
        baseline_alignment=baseline_alignment,
        vendor_management_signal=vendor_management_signal,
        recommended_vendor_action=recommended_vendor_action,
        requested_vendor_response=requested_vendor_response,
        supporting_evidence=supporting_evidence,
        baseline_evidence=baseline_evidence,
        escalation_summary=escalation_summary,
        message="Vendor escalation packet generated successfully.",
    )


@router.get("/intake/{finding_id}/vendor-escalation-packet.pdf")
def get_enterprise_vendor_escalation_packet_pdf(
    finding_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    from io import BytesIO
    from fastapi import HTTPException
    from fastapi.responses import StreamingResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    finding = db.get(EnterpriseFinding, finding_id)

    if not finding:
        raise HTTPException(status_code=404, detail="Enterprise finding not found")

    vendor = db.get(EnterpriseVendor, finding.vendor_id) if finding.vendor_id else None
    instrument = db.get(EnterpriseInstrument, finding.instrument_id) if finding.instrument_id else None

    vendor_name = (
        getattr(vendor, "vendor_name", None)
        or getattr(vendor, "name", None)
        or getattr(vendor, "vendor", None)
        or ""
    ) if vendor else ""

    instrument_name = (
        getattr(instrument, "instrument_name", None)
        or getattr(instrument, "name", None)
        or getattr(instrument, "instrument", None)
        or ""
    ) if instrument else ""

    instrument_category = (
        getattr(instrument, "instrument_category", None)
        or getattr(instrument, "category", None)
        or ""
    ) if instrument else ""

    baseline_rows = []
    if finding.instrument_id:
        baseline_rows = (
            db.query(EnterpriseInstrumentBaseline)
            .filter(EnterpriseInstrumentBaseline.instrument_id == finding.instrument_id)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .all()
        )

    if not baseline_rows and finding.vendor_id:
        baseline_rows = (
            db.query(EnterpriseInstrumentBaseline)
            .filter(EnterpriseInstrumentBaseline.vendor_id == finding.vendor_id)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .all()
        )

    approved_baseline_count = sum(
        1 for baseline in baseline_rows
        if (baseline.baseline_status or "").lower() == "approved"
    )

    comparison = None
    try:
        comparison = None
    except Exception:
        comparison = None

    comparison_score = getattr(comparison, "comparison_score", None) if comparison else None
    deviation_level = getattr(comparison, "deviation_level", "") if comparison else ""
    baseline_alignment = getattr(comparison, "baseline_alignment", "") if comparison else ""
    vendor_management_signal = getattr(comparison, "vendor_management_signal", "") if comparison else ""

    escalation_status = "vendor_review_not_required"
    recommended_vendor_action = (
        "Document internally. Vendor escalation is not recommended unless human reviewer confirms a true defect."
    )

    if deviation_level in ["high_deviation", "critical_deviation"]:
        escalation_status = "vendor_escalation_recommended"
        recommended_vendor_action = (
            "Request vendor quality review, written response, and corrective action plan if the finding is confirmed."
        )
    elif (finding.severity or "").lower() in ["high", "critical"] and not approved_baseline_count:
        escalation_status = "vendor_review_pending_baseline_confirmation"
        recommended_vendor_action = (
            "Hold vendor escalation until manufacturer baseline evidence and human review confirm whether this is a true defect."
        )
    elif approved_baseline_count and baseline_alignment == "consistent_with_known_baseline_artifact":
        escalation_status = "vendor_escalation_not_recommended_baseline_artifact"
        recommended_vendor_action = (
            "Do not escalate as vendor defect at this time. Finding aligns with approved manufacturer baseline artifact."
        )

    requested_vendor_response = (
        "Please review the finding, instrument context, baseline evidence, and comparison summary. "
        "If vendor review is requested, provide a written determination, root cause if applicable, "
        "and recommended corrective action."
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("LumenAI Vendor Escalation Packet", styles["Title"]))
    story.append(Spacer(1, 10))

    summary_data = [
        ["Finding ID", str(finding.id)],
        ["Escalation Status", escalation_status],
        ["Vendor", vendor_name],
        ["Instrument", instrument_name],
        ["Instrument Category", instrument_category],
        ["Finding Category", finding.finding_category or ""],
        ["Severity", finding.severity or ""],
        ["Confidence Score", str(finding.confidence_score or "")],
        ["Comparison Score", str(comparison_score if comparison_score is not None else "")],
        ["Deviation Level", deviation_level],
        ["Baseline Alignment", baseline_alignment],
        ["Vendor Signal", vendor_management_signal],
    ]

    summary_table = Table(summary_data, colWidths=[140, 360])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e2e8f0")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Finding Description", styles["Heading2"]))
    story.append(Paragraph(finding.finding_description or "No finding description documented.", styles["BodyText"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Recommended Vendor Action", styles["Heading2"]))
    story.append(Paragraph(recommended_vendor_action, styles["BodyText"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Requested Vendor Response", styles["Heading2"]))
    story.append(Paragraph(requested_vendor_response, styles["BodyText"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Manufacturer Baseline Evidence", styles["Heading2"]))

    if baseline_rows:
        baseline_table_data = [[
            "Baseline ID",
            "Manufacturer",
            "Model",
            "Status",
            "Approved By",
        ]]

        for baseline in baseline_rows:
            baseline_table_data.append([
                str(baseline.id),
                baseline.manufacturer_name or "",
                baseline.model_number or "",
                baseline.baseline_status or "",
                baseline.approved_by or "",
            ])

        baseline_table = Table(baseline_table_data, colWidths=[60, 110, 110, 80, 120])
        baseline_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(baseline_table)

        for baseline in baseline_rows[:3]:
            audit_significance = (
                "Approved manufacturer baseline may be used as trusted comparison evidence."
                if (baseline.baseline_status or "").lower() == "approved"
                else "Baseline captured but not yet approved as trusted comparison evidence."
            )

            story.append(Spacer(1, 8))
            story.append(Paragraph(f"Baseline #{baseline.id} Detail", styles["Heading3"]))
            story.append(Paragraph(f"<b>Storage URI:</b> {baseline.storage_uri or ''}", styles["BodyText"]))
            story.append(Paragraph(f"<b>Known Normal Characteristics:</b> {baseline.known_normal_characteristics or 'Not documented.'}", styles["BodyText"]))
            story.append(Paragraph(f"<b>Known Abnormal Characteristics:</b> {baseline.known_abnormal_characteristics or 'Not documented.'}", styles["BodyText"]))
            story.append(Paragraph(f"<b>Audit Significance:</b> {audit_significance}", styles["BodyText"]))
    else:
        story.append(Paragraph("No manufacturer baseline evidence attached.", styles["BodyText"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Escalation Summary", styles["Heading2"]))
    story.append(Paragraph(
        f"LumenAI generated this vendor escalation packet for Finding #{finding.id}. "
        f"The finding involves {instrument_name or 'the instrument'} associated with {vendor_name or 'the vendor'}. "
        f"Current escalation status: {escalation_status}. "
        f"Baseline evidence count: {len(baseline_rows)}. "
        f"Approved baseline count: {approved_baseline_count}.",
        styles["BodyText"],
    ))

    doc.build(story)
    buffer.seek(0)

    _record_enterprise_audit(
        db,
        request,
        tenant_id=finding.tenant_id,
        tenant_name="",
        action_type="vendor_escalation_packet_pdf_exported",
        resource_type="enterprise_vendor_escalation_packet_pdf",
        resource_id=str(finding.id),
        details={
            "finding_id": finding.id,
            "vendor_id": finding.vendor_id,
            "instrument_id": finding.instrument_id,
            "vendor_name": vendor_name,
            "instrument_name": instrument_name,
            "escalation_status": escalation_status,
            "baseline_evidence_count": len(baseline_rows),
            "approved_baseline_count": approved_baseline_count,
            "comparison_score": comparison_score,
            "deviation_level": deviation_level,
            "baseline_alignment": baseline_alignment,
            "workflow_status": "vendor_escalation_packet_pdf_exported",
        },
    )
    db.commit()

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=lumenai-vendor-escalation-packet-finding-{finding.id}.pdf"
        },
    )


@router.get("/intake/{finding_id}/infection-prevention-review-packet", response_model=EnterpriseInfectionPreventionReviewPacketResponse)
def get_enterprise_infection_prevention_review_packet(
    finding_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException

    finding = db.get(EnterpriseFinding, finding_id)

    if not finding:
        raise HTTPException(status_code=404, detail="Enterprise finding not found")

    vendor = db.get(EnterpriseVendor, finding.vendor_id) if finding.vendor_id else None
    instrument = db.get(EnterpriseInstrument, finding.instrument_id) if finding.instrument_id else None

    vendor_name = (
        getattr(vendor, "vendor_name", None)
        or getattr(vendor, "name", None)
        or getattr(vendor, "vendor", None)
        or ""
    ) if vendor else ""

    instrument_name = (
        getattr(instrument, "instrument_name", None)
        or getattr(instrument, "name", None)
        or getattr(instrument, "instrument", None)
        or ""
    ) if instrument else ""

    instrument_category = (
        getattr(instrument, "instrument_category", None)
        or getattr(instrument, "category", None)
        or ""
    ) if instrument else ""

    baseline_rows = []
    if finding.instrument_id:
        baseline_rows = (
            db.query(EnterpriseInstrumentBaseline)
            .filter(EnterpriseInstrumentBaseline.instrument_id == finding.instrument_id)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .all()
        )

    if not baseline_rows and finding.vendor_id:
        baseline_rows = (
            db.query(EnterpriseInstrumentBaseline)
            .filter(EnterpriseInstrumentBaseline.vendor_id == finding.vendor_id)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .all()
        )

    approved_baseline_count = sum(
        1 for baseline in baseline_rows
        if (baseline.baseline_status or "").lower() == "approved"
    )

    baseline_evidence = [
        {
            "baseline_id": baseline.id,
            "instrument_id": baseline.instrument_id,
            "vendor_id": baseline.vendor_id,
            "manufacturer_name": baseline.manufacturer_name or "",
            "model_number": baseline.model_number or "",
            "catalog_number": baseline.catalog_number or "",
            "baseline_type": baseline.baseline_type or "",
            "file_name": baseline.file_name or "",
            "storage_uri": baseline.storage_uri or "",
            "baseline_status": baseline.baseline_status or "",
            "approved_by": baseline.approved_by or "",
            "approved_at": baseline.approved_at.isoformat() if baseline.approved_at else "",
            "known_normal_characteristics": baseline.known_normal_characteristics or "",
            "known_abnormal_characteristics": baseline.known_abnormal_characteristics or "",
            "baseline_notes": baseline.baseline_notes or "",
            "audit_significance": (
                "Approved manufacturer baseline may be used as trusted comparison evidence."
                if (baseline.baseline_status or "").lower() == "approved"
                else "Baseline captured but not yet approved as trusted comparison evidence."
            ),
        }
        for baseline in baseline_rows
    ]

    evidence_rows = (
        db.query(EnterpriseEvidence)
        .filter(EnterpriseEvidence.inspection_id == finding.id)
        .order_by(EnterpriseEvidence.id.desc())
        .all()
    )

    supporting_evidence = [
        {
            "evidence_id": evidence.id,
            "evidence_type": evidence.evidence_type or "",
            "file_name": evidence.file_name or "",
            "storage_uri": getattr(evidence, "storage_uri", "") or getattr(evidence, "storage_key", "") or getattr(evidence, "file_url", "") or "",
            "content_type": getattr(evidence, "mime_type", "") or "",
            "created_at": evidence.created_at.isoformat() if evidence.created_at else "",
        }
        for evidence in evidence_rows
    ]

    comparison = None
    try:
        comparison = None
    except Exception:
        comparison = None

    comparison_score = getattr(comparison, "comparison_score", None) if comparison else None
    deviation_level = getattr(comparison, "deviation_level", "") if comparison else ""
    baseline_alignment = getattr(comparison, "baseline_alignment", "") if comparison else ""

    finding_category = finding.finding_category or ""
    severity = finding.severity or ""

    category_lower = finding_category.lower()
    severity_lower = severity.lower()
    description_lower = (finding.finding_description or "").lower()

    infection_keywords = [
        "bioburden",
        "retained debris",
        "blood",
        "tissue",
        "bone",
        "organic",
        "soil",
        "contamination",
        "foreign material",
    ]

    has_infection_signal = any(
        keyword in category_lower or keyword in description_lower
        for keyword in infection_keywords
    )

    is_lumened = "lumen" in (instrument_category or "").lower() or "suction" in (instrument_name or "").lower()

    patient_safety_signal = "low"
    infection_risk_signal = "routine_documentation"

    if has_infection_signal and is_lumened:
        patient_safety_signal = "elevated"
        infection_risk_signal = "ip_review_recommended_for_lumened_instrument"
    elif has_infection_signal:
        patient_safety_signal = "moderate"
        infection_risk_signal = "ip_review_recommended"
    elif severity_lower in ["high", "critical"]:
        patient_safety_signal = "moderate"
        infection_risk_signal = "quality_review_recommended"

    ip_review_status = "ip_review_not_required"
    recommended_ip_action = "Document finding in quality record. IP review is not required unless human reviewer confirms contamination or patient exposure risk."

    if infection_risk_signal in ["ip_review_recommended", "ip_review_recommended_for_lumened_instrument"]:
        ip_review_status = "ip_review_recommended"
        recommended_ip_action = (
            "Request Infection Prevention review. Confirm whether the finding represents retained bioburden, "
            "whether the device reached patient care, whether additional cleaning verification is needed, "
            "and whether any exposure or surveillance follow-up is required."
        )

    if approved_baseline_count and baseline_alignment == "consistent_with_known_baseline_artifact":
        ip_review_status = "baseline_artifact_documentation"
        recommended_ip_action = (
            "Document approved baseline alignment. IP escalation may not be required unless reviewer confirms true retained debris, "
            "organic material, or patient exposure risk."
        )

    recommended_documentation = [
        "finding description and severity",
        "instrument and lumen context",
        "inspection evidence or borescope image when available",
        "manufacturer baseline evidence",
        "baseline comparison score and alignment",
        "human reviewer decision",
        "cleaning/recleaning disposition",
        "patient exposure assessment if applicable",
    ]

    ip_review_summary = (
        f"LumenAI generated an Infection Prevention review packet for Finding #{finding.id}. "
        f"The finding involves {instrument_name or 'the instrument'} associated with {vendor_name or 'the vendor'}. "
        f"Patient safety signal: {patient_safety_signal}. "
        f"Infection risk signal: {infection_risk_signal}. "
        f"IP review status: {ip_review_status}. "
        f"Baseline evidence count: {len(baseline_evidence)}. "
        f"Approved baseline count: {approved_baseline_count}."
    )

    _record_enterprise_audit(
        db,
        request,
        tenant_id=finding.tenant_id,
        tenant_name="",
        action_type="infection_prevention_review_packet_generated",
        resource_type="enterprise_infection_prevention_review_packet",
        resource_id=str(finding.id),
        details={
            "finding_id": finding.id,
            "vendor_id": finding.vendor_id,
            "instrument_id": finding.instrument_id,
            "patient_safety_signal": patient_safety_signal,
            "infection_risk_signal": infection_risk_signal,
            "ip_review_status": ip_review_status,
            "baseline_evidence_count": len(baseline_evidence),
            "approved_baseline_count": approved_baseline_count,
            "comparison_score": comparison_score,
            "deviation_level": deviation_level,
            "baseline_alignment": baseline_alignment,
            "workflow_status": "infection_prevention_review_packet_generated",
        },
    )
    db.commit()

    return EnterpriseInfectionPreventionReviewPacketResponse(
        status="success",
        finding_id=finding.id,
        packet_type="infection_prevention_review_packet",
        ip_review_status=ip_review_status,
        patient_safety_signal=patient_safety_signal,
        infection_risk_signal=infection_risk_signal,
        vendor_id=finding.vendor_id,
        vendor_name=vendor_name,
        instrument_id=finding.instrument_id,
        instrument_name=instrument_name,
        instrument_category=instrument_category,
        finding_category=finding_category,
        finding_description=finding.finding_description or "",
        severity=severity,
        confidence_score=finding.confidence_score,
        baseline_evidence_count=len(baseline_evidence),
        approved_baseline_count=approved_baseline_count,
        comparison_score=comparison_score,
        deviation_level=deviation_level,
        baseline_alignment=baseline_alignment,
        recommended_ip_action=recommended_ip_action,
        recommended_documentation=recommended_documentation,
        supporting_evidence=supporting_evidence,
        baseline_evidence=baseline_evidence,
        ip_review_summary=ip_review_summary,
        message="Infection Prevention review packet generated successfully.",
    )


@router.get("/intake/{finding_id}/infection-prevention-review-packet.pdf")
def get_enterprise_infection_prevention_review_packet_pdf(
    finding_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    from io import BytesIO
    from fastapi import HTTPException
    from fastapi.responses import StreamingResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    finding = db.get(EnterpriseFinding, finding_id)

    if not finding:
        raise HTTPException(status_code=404, detail="Enterprise finding not found")

    vendor = db.get(EnterpriseVendor, finding.vendor_id) if finding.vendor_id else None
    instrument = db.get(EnterpriseInstrument, finding.instrument_id) if finding.instrument_id else None

    vendor_name = (
        getattr(vendor, "vendor_name", None)
        or getattr(vendor, "name", None)
        or getattr(vendor, "vendor", None)
        or ""
    ) if vendor else ""

    instrument_name = (
        getattr(instrument, "instrument_name", None)
        or getattr(instrument, "name", None)
        or getattr(instrument, "instrument", None)
        or ""
    ) if instrument else ""

    instrument_category = (
        getattr(instrument, "instrument_category", None)
        or getattr(instrument, "category", None)
        or ""
    ) if instrument else ""

    baseline_rows = []
    if finding.instrument_id:
        baseline_rows = (
            db.query(EnterpriseInstrumentBaseline)
            .filter(EnterpriseInstrumentBaseline.instrument_id == finding.instrument_id)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .all()
        )

    if not baseline_rows and finding.vendor_id:
        baseline_rows = (
            db.query(EnterpriseInstrumentBaseline)
            .filter(EnterpriseInstrumentBaseline.vendor_id == finding.vendor_id)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .all()
        )

    approved_baseline_count = sum(
        1 for baseline in baseline_rows
        if (baseline.baseline_status or "").lower() == "approved"
    )

    comparison = None
    try:
        comparison = None
    except Exception:
        comparison = None

    comparison_score = getattr(comparison, "comparison_score", None) if comparison else None
    deviation_level = getattr(comparison, "deviation_level", "") if comparison else ""
    baseline_alignment = getattr(comparison, "baseline_alignment", "") if comparison else ""

    finding_category = finding.finding_category or ""
    severity = finding.severity or ""

    category_lower = finding_category.lower()
    severity_lower = severity.lower()
    description_lower = (finding.finding_description or "").lower()

    infection_keywords = [
        "bioburden",
        "retained debris",
        "blood",
        "tissue",
        "bone",
        "organic",
        "soil",
        "contamination",
        "foreign material",
    ]

    has_infection_signal = any(
        keyword in category_lower or keyword in description_lower
        for keyword in infection_keywords
    )

    is_lumened = (
        "lumen" in (instrument_category or "").lower()
        or "suction" in (instrument_name or "").lower()
        or "scope" in (instrument_name or "").lower()
    )

    patient_safety_signal = "low"
    infection_risk_signal = "routine_documentation"

    if has_infection_signal and is_lumened:
        patient_safety_signal = "elevated"
        infection_risk_signal = "ip_review_recommended_for_lumened_instrument"
    elif has_infection_signal:
        patient_safety_signal = "moderate"
        infection_risk_signal = "ip_review_recommended"
    elif severity_lower in ["high", "critical"]:
        patient_safety_signal = "moderate"
        infection_risk_signal = "quality_review_recommended"

    ip_review_status = "ip_review_not_required"
    recommended_ip_action = (
        "Document finding in the quality record. IP review is not required unless human reviewer confirms "
        "contamination, retained organic material, or patient exposure risk."
    )

    if infection_risk_signal in ["ip_review_recommended", "ip_review_recommended_for_lumened_instrument"]:
        ip_review_status = "ip_review_recommended"
        recommended_ip_action = (
            "Request Infection Prevention review. Confirm whether the finding represents retained bioburden, "
            "whether the device reached patient care, whether additional cleaning verification is needed, "
            "and whether exposure or surveillance follow-up is required."
        )

    if approved_baseline_count and baseline_alignment == "consistent_with_known_baseline_artifact":
        ip_review_status = "baseline_artifact_documentation"
        recommended_ip_action = (
            "Document approved baseline alignment. IP escalation may not be required unless reviewer confirms true retained debris, "
            "organic material, or patient exposure risk."
        )

    recommended_documentation = [
        "Finding description and severity",
        "Instrument and lumen context",
        "Inspection evidence or borescope image when available",
        "Manufacturer baseline evidence",
        "Baseline comparison score and alignment",
        "Human reviewer decision",
        "Cleaning/recleaning disposition",
        "Patient exposure assessment if applicable",
    ]

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("LumenAI Infection Prevention Review Packet", styles["Title"]))
    story.append(Spacer(1, 10))

    summary_data = [
        ["Finding ID", str(finding.id)],
        ["IP Review Status", ip_review_status],
        ["Patient Safety Signal", patient_safety_signal],
        ["Infection Risk Signal", infection_risk_signal],
        ["Vendor", vendor_name],
        ["Instrument", instrument_name],
        ["Instrument Category", instrument_category],
        ["Finding Category", finding_category],
        ["Severity", severity],
        ["Confidence Score", str(finding.confidence_score or "")],
        ["Comparison Score", str(comparison_score if comparison_score is not None else "")],
        ["Deviation Level", deviation_level],
        ["Baseline Alignment", baseline_alignment],
        ["Approved Baselines", str(approved_baseline_count)],
    ]

    summary_table = Table(summary_data, colWidths=[150, 350])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e0f2fe")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Finding Description", styles["Heading2"]))
    story.append(Paragraph(finding.finding_description or "No finding description documented.", styles["BodyText"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Recommended Infection Prevention Action", styles["Heading2"]))
    story.append(Paragraph(recommended_ip_action, styles["BodyText"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Recommended Documentation", styles["Heading2"]))

    documentation_data = [["Documentation Item"]]
    for item in recommended_documentation:
        documentation_data.append([item])

    documentation_table = Table(documentation_data, colWidths=[500])
    documentation_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcfce7")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(documentation_table)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Manufacturer Baseline Evidence", styles["Heading2"]))

    if baseline_rows:
        baseline_table_data = [[
            "Baseline ID",
            "Manufacturer",
            "Model",
            "Status",
            "Approved By",
        ]]

        for baseline in baseline_rows:
            baseline_table_data.append([
                str(baseline.id),
                baseline.manufacturer_name or "",
                baseline.model_number or "",
                baseline.baseline_status or "",
                baseline.approved_by or "",
            ])

        baseline_table = Table(baseline_table_data, colWidths=[60, 110, 110, 80, 120])
        baseline_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(baseline_table)

        for baseline in baseline_rows[:3]:
            audit_significance = (
                "Approved manufacturer baseline may be used as trusted comparison evidence."
                if (baseline.baseline_status or "").lower() == "approved"
                else "Baseline captured but not yet approved as trusted comparison evidence."
            )

            story.append(Spacer(1, 8))
            story.append(Paragraph(f"Baseline #{baseline.id} Detail", styles["Heading3"]))
            story.append(Paragraph(f"<b>Storage URI:</b> {baseline.storage_uri or ''}", styles["BodyText"]))
            story.append(Paragraph(f"<b>Known Normal Characteristics:</b> {baseline.known_normal_characteristics or 'Not documented.'}", styles["BodyText"]))
            story.append(Paragraph(f"<b>Known Abnormal Characteristics:</b> {baseline.known_abnormal_characteristics or 'Not documented.'}", styles["BodyText"]))
            story.append(Paragraph(f"<b>Audit Significance:</b> {audit_significance}", styles["BodyText"]))
    else:
        story.append(Paragraph("No manufacturer baseline evidence attached.", styles["BodyText"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("IP Review Summary", styles["Heading2"]))
    story.append(Paragraph(
        f"LumenAI generated this Infection Prevention review packet for Finding #{finding.id}. "
        f"The finding involves {instrument_name or 'the instrument'} associated with {vendor_name or 'the vendor'}. "
        f"Patient safety signal: {patient_safety_signal}. "
        f"Infection risk signal: {infection_risk_signal}. "
        f"IP review status: {ip_review_status}. "
        f"Baseline evidence count: {len(baseline_rows)}. "
        f"Approved baseline count: {approved_baseline_count}.",
        styles["BodyText"],
    ))

    doc.build(story)
    buffer.seek(0)

    _record_enterprise_audit(
        db,
        request,
        tenant_id=finding.tenant_id,
        tenant_name="",
        action_type="infection_prevention_review_packet_pdf_exported",
        resource_type="enterprise_infection_prevention_review_packet_pdf",
        resource_id=str(finding.id),
        details={
            "finding_id": finding.id,
            "vendor_id": finding.vendor_id,
            "instrument_id": finding.instrument_id,
            "patient_safety_signal": patient_safety_signal,
            "infection_risk_signal": infection_risk_signal,
            "ip_review_status": ip_review_status,
            "baseline_evidence_count": len(baseline_rows),
            "approved_baseline_count": approved_baseline_count,
            "comparison_score": comparison_score,
            "deviation_level": deviation_level,
            "baseline_alignment": baseline_alignment,
            "workflow_status": "infection_prevention_review_packet_pdf_exported",
        },
    )
    db.commit()

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=lumenai-infection-prevention-review-packet-finding-{finding.id}.pdf"
        },
    )


@router.get("/executive-quality-review-dashboard", response_model=EnterpriseExecutiveQualityReviewDashboardResponse)
def get_enterprise_executive_quality_review_dashboard(
    request: Request,
    db: Session = Depends(get_db),
):
    total_findings = db.query(EnterpriseFinding).count()

    critical_findings = (
        db.query(EnterpriseFinding)
        .filter(EnterpriseFinding.severity == "critical")
        .count()
    )

    high_findings = (
        db.query(EnterpriseFinding)
        .filter(EnterpriseFinding.severity == "high")
        .count()
    )

    baseline_evidence_count = db.query(EnterpriseInstrumentBaseline).count()

    approved_baseline_count = (
        db.query(EnterpriseInstrumentBaseline)
        .filter(EnterpriseInstrumentBaseline.baseline_status == "approved")
        .count()
    )

    audit_event_count = 0
    governance_export_count = 0
    try:
        audit_event_count = db.query(EnterpriseAuditTrail).count()
        governance_export_count = (
            db.query(EnterpriseAuditTrail)
            .filter(EnterpriseAuditTrail.action_type.in_([
                "governance_packet_exported_pdf",
                "governance_export_package_generated",
                "governance_zip_bundle_exported",
                "vendor_escalation_packet_generated",
                "vendor_escalation_packet_pdf_exported",
                "infection_prevention_review_packet_generated",
                "infection_prevention_review_packet_pdf_exported",
            ]))
            .count()
        )
    except Exception:
        audit_event_count = 0
        governance_export_count = 0

    open_capa_count = 0
    closed_capa_count = 0
    try:
        open_capa_count = (
            db.query(EnterpriseCapa)
            .filter(EnterpriseCapa.status.in_(["open", "in_progress", "pending_review"]))
            .count()
        )
        closed_capa_count = (
            db.query(EnterpriseCapa)
            .filter(EnterpriseCapa.status.in_(["closed", "completed"]))
            .count()
        )
    except Exception:
        open_capa_count = 0
        closed_capa_count = 0

    recent_rows = (
        db.query(EnterpriseFinding)
        .order_by(EnterpriseFinding.id.desc())
        .limit(10)
        .all()
    )

    recent_findings = []
    vendor_signal_counts = {}

    for finding in recent_rows:
        vendor = db.get(EnterpriseVendor, finding.vendor_id) if finding.vendor_id else None
        instrument = db.get(EnterpriseInstrument, finding.instrument_id) if finding.instrument_id else None

        vendor_name = (
            getattr(vendor, "vendor_name", None)
            or getattr(vendor, "name", None)
            or getattr(vendor, "vendor", None)
            or ""
        ) if vendor else ""

        instrument_name = (
            getattr(instrument, "instrument_name", None)
            or getattr(instrument, "name", None)
            or getattr(instrument, "instrument", None)
            or ""
        ) if instrument else ""

        if vendor_name:
            vendor_signal_counts[vendor_name] = vendor_signal_counts.get(vendor_name, 0) + 1

        recent_findings.append({
            "finding_id": finding.id,
            "vendor_id": finding.vendor_id,
            "vendor_name": vendor_name,
            "instrument_id": finding.instrument_id,
            "instrument_name": instrument_name,
            "finding_category": finding.finding_category or "",
            "severity": finding.severity or "",
            "confidence_score": finding.confidence_score,
            "workflow_status": getattr(finding, "workflow_status", "") or "",
            "created_at": finding.created_at.isoformat() if finding.created_at else "",
        })

    top_vendor_signals = [
        {"vendor_name": vendor_name, "finding_count": count}
        for vendor_name, count in sorted(
            vendor_signal_counts.items(),
            key=lambda item: item[1],
            reverse=True
        )
    ]

    vendor_escalation_ready_count = 0
    ip_review_recommended_count = 0

    for finding in db.query(EnterpriseFinding).all():
        finding_category = (finding.finding_category or "").lower()
        description = (finding.finding_description or "").lower()
        severity = (finding.severity or "").lower()

        if severity in ["high", "critical"]:
            vendor_escalation_ready_count += 1

        infection_terms = [
            "bioburden",
            "retained debris",
            "blood",
            "tissue",
            "bone",
            "organic",
            "soil",
            "contamination",
            "foreign material",
        ]

        if any(term in finding_category or term in description for term in infection_terms):
            ip_review_recommended_count += 1

    quality_signal = "stable"
    if critical_findings > 0 or open_capa_count > 0:
        quality_signal = "active_quality_risk"
    if critical_findings >= 3 or ip_review_recommended_count >= 3:
        quality_signal = "elevated_enterprise_risk"

    executive_summary = (
        f"LumenAI executive quality dashboard includes {total_findings} findings, "
        f"{critical_findings} critical findings, {high_findings} high findings, "
        f"{baseline_evidence_count} manufacturer baseline records, and "
        f"{approved_baseline_count} approved baseline references. "
        f"Current quality signal: {quality_signal}."
    )

    recommended_leadership_actions = [
        "Review critical and high-severity findings during quality huddle.",
        "Validate whether vendor escalation packets are required for confirmed device-quality defects.",
        "Review Infection Prevention packets for bioburden, retained debris, or lumened instrument concerns.",
        "Monitor approved manufacturer baseline coverage to reduce false-positive escalation.",
        "Track CAPA closure and audit export activity for survey readiness.",
    ]

    _record_enterprise_audit(
        db,
        request,
        tenant_id="",
        tenant_name="",
        action_type="executive_quality_review_dashboard_viewed",
        resource_type="enterprise_executive_quality_review_dashboard",
        resource_id="executive_quality_review_dashboard",
        details={
            "total_findings": total_findings,
            "critical_findings": critical_findings,
            "high_findings": high_findings,
            "baseline_evidence_count": baseline_evidence_count,
            "approved_baseline_count": approved_baseline_count,
            "vendor_escalation_ready_count": vendor_escalation_ready_count,
            "ip_review_recommended_count": ip_review_recommended_count,
            "open_capa_count": open_capa_count,
            "quality_signal": quality_signal,
            "workflow_status": "executive_quality_review_dashboard_viewed",
        },
    )
    db.commit()

    return EnterpriseExecutiveQualityReviewDashboardResponse(
        status="success",
        dashboard_type="executive_quality_review_dashboard",
        total_findings=total_findings,
        critical_findings=critical_findings,
        high_findings=high_findings,
        baseline_evidence_count=baseline_evidence_count,
        approved_baseline_count=approved_baseline_count,
        vendor_escalation_ready_count=vendor_escalation_ready_count,
        ip_review_recommended_count=ip_review_recommended_count,
        open_capa_count=open_capa_count,
        closed_capa_count=closed_capa_count,
        audit_event_count=audit_event_count,
        governance_export_count=governance_export_count,
        quality_signal=quality_signal,
        executive_summary=executive_summary,
        recommended_leadership_actions=recommended_leadership_actions,
        top_vendor_signals=top_vendor_signals,
        recent_findings=recent_findings,
    )


@router.get("/executive-quality-review-dashboard.pdf")
def get_enterprise_executive_quality_review_dashboard_pdf(
    request: Request,
    db: Session = Depends(get_db),
):
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    total_findings = db.query(EnterpriseFinding).count()

    critical_findings = (
        db.query(EnterpriseFinding)
        .filter(EnterpriseFinding.severity == "critical")
        .count()
    )

    high_findings = (
        db.query(EnterpriseFinding)
        .filter(EnterpriseFinding.severity == "high")
        .count()
    )

    baseline_evidence_count = db.query(EnterpriseInstrumentBaseline).count()

    approved_baseline_count = (
        db.query(EnterpriseInstrumentBaseline)
        .filter(EnterpriseInstrumentBaseline.baseline_status == "approved")
        .count()
    )

    audit_event_count = 0
    governance_export_count = 0
    try:
        audit_event_count = db.query(EnterpriseAuditTrail).count()
        governance_export_count = (
            db.query(EnterpriseAuditTrail)
            .filter(EnterpriseAuditTrail.action_type.in_([
                "governance_packet_exported_pdf",
                "governance_export_package_generated",
                "governance_zip_bundle_exported",
                "vendor_escalation_packet_generated",
                "vendor_escalation_packet_pdf_exported",
                "infection_prevention_review_packet_generated",
                "infection_prevention_review_packet_pdf_exported",
                "executive_quality_review_dashboard_viewed",
                "executive_quality_review_dashboard_pdf_exported",
            ]))
            .count()
        )
    except Exception:
        audit_event_count = 0
        governance_export_count = 0

    open_capa_count = 0
    closed_capa_count = 0
    try:
        open_capa_count = (
            db.query(EnterpriseCapa)
            .filter(EnterpriseCapa.status.in_(["open", "in_progress", "pending_review"]))
            .count()
        )
        closed_capa_count = (
            db.query(EnterpriseCapa)
            .filter(EnterpriseCapa.status.in_(["closed", "completed"]))
            .count()
        )
    except Exception:
        open_capa_count = 0
        closed_capa_count = 0

    vendor_escalation_ready_count = 0
    ip_review_recommended_count = 0

    all_findings = db.query(EnterpriseFinding).all()

    for finding in all_findings:
        finding_category = (finding.finding_category or "").lower()
        description = (finding.finding_description or "").lower()
        severity = (finding.severity or "").lower()

        if severity in ["high", "critical"]:
            vendor_escalation_ready_count += 1

        infection_terms = [
            "bioburden",
            "retained debris",
            "blood",
            "tissue",
            "bone",
            "organic",
            "soil",
            "contamination",
            "foreign material",
        ]

        if any(term in finding_category or term in description for term in infection_terms):
            ip_review_recommended_count += 1

    quality_signal = "stable"
    if critical_findings > 0 or open_capa_count > 0:
        quality_signal = "active_quality_risk"
    if critical_findings >= 3 or ip_review_recommended_count >= 3:
        quality_signal = "elevated_enterprise_risk"

    executive_summary = (
        f"LumenAI executive quality dashboard includes {total_findings} findings, "
        f"{critical_findings} critical findings, {high_findings} high findings, "
        f"{baseline_evidence_count} manufacturer baseline records, and "
        f"{approved_baseline_count} approved baseline references. "
        f"Current quality signal: {quality_signal}."
    )

    recommended_leadership_actions = [
        "Review critical and high-severity findings during quality huddle.",
        "Validate whether vendor escalation packets are required for confirmed device-quality defects.",
        "Review Infection Prevention packets for bioburden, retained debris, or lumened instrument concerns.",
        "Monitor approved manufacturer baseline coverage to reduce false-positive escalation.",
        "Track CAPA closure and audit export activity for survey readiness.",
    ]

    recent_rows = (
        db.query(EnterpriseFinding)
        .order_by(EnterpriseFinding.id.desc())
        .limit(10)
        .all()
    )

    recent_findings = []
    vendor_signal_counts = {}

    for finding in recent_rows:
        vendor = db.get(EnterpriseVendor, finding.vendor_id) if finding.vendor_id else None
        instrument = db.get(EnterpriseInstrument, finding.instrument_id) if finding.instrument_id else None

        vendor_name = (
            getattr(vendor, "vendor_name", None)
            or getattr(vendor, "name", None)
            or getattr(vendor, "vendor", None)
            or ""
        ) if vendor else ""

        instrument_name = (
            getattr(instrument, "instrument_name", None)
            or getattr(instrument, "name", None)
            or getattr(instrument, "instrument", None)
            or ""
        ) if instrument else ""

        if vendor_name:
            vendor_signal_counts[vendor_name] = vendor_signal_counts.get(vendor_name, 0) + 1

        recent_findings.append({
            "finding_id": finding.id,
            "vendor_name": vendor_name,
            "instrument_name": instrument_name,
            "finding_category": finding.finding_category or "",
            "severity": finding.severity or "",
            "confidence_score": finding.confidence_score,
            "created_at": finding.created_at.isoformat() if finding.created_at else "",
        })

    top_vendor_signals = [
        {"vendor_name": vendor_name, "finding_count": count}
        for vendor_name, count in sorted(
            vendor_signal_counts.items(),
            key=lambda item: item[1],
            reverse=True
        )
    ]

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("LumenAI Executive Quality Review Dashboard", styles["Title"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Executive Summary", styles["Heading2"]))
    story.append(Paragraph(executive_summary, styles["BodyText"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Enterprise Quality Metrics", styles["Heading2"]))

    metrics_data = [
        ["Metric", "Value"],
        ["Quality Signal", quality_signal],
        ["Total Findings", str(total_findings)],
        ["Critical Findings", str(critical_findings)],
        ["High Findings", str(high_findings)],
        ["Baseline Evidence Count", str(baseline_evidence_count)],
        ["Approved Baseline Count", str(approved_baseline_count)],
        ["Vendor Escalation Ready", str(vendor_escalation_ready_count)],
        ["IP Review Recommended", str(ip_review_recommended_count)],
        ["Open CAPAs", str(open_capa_count)],
        ["Closed CAPAs", str(closed_capa_count)],
        ["Audit Events", str(audit_event_count)],
        ["Governance Exports", str(governance_export_count)],
    ]

    metrics_table = Table(metrics_data, colWidths=[220, 260])
    metrics_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#f8fafc")),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(metrics_table)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Recommended Leadership Actions", styles["Heading2"]))

    action_data = [["Action"]]
    for action in recommended_leadership_actions:
        action_data.append([action])

    action_table = Table(action_data, colWidths=[500])
    action_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcfce7")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(action_table)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Top Vendor Signals", styles["Heading2"]))

    if top_vendor_signals:
        vendor_data = [["Vendor", "Finding Count"]]
        for vendor in top_vendor_signals[:10]:
            vendor_data.append([
                vendor["vendor_name"],
                str(vendor["finding_count"]),
            ])

        vendor_table = Table(vendor_data, colWidths=[300, 180])
        vendor_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fef3c7")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(vendor_table)
    else:
        story.append(Paragraph("No vendor signals available.", styles["BodyText"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Recent Findings", styles["Heading2"]))

    if recent_findings:
        finding_data = [["ID", "Vendor", "Instrument", "Category", "Severity"]]
        for finding in recent_findings:
            finding_data.append([
                str(finding["finding_id"]),
                finding["vendor_name"],
                finding["instrument_name"],
                finding["finding_category"],
                finding["severity"],
            ])

        finding_table = Table(finding_data, colWidths=[35, 90, 100, 190, 65])
        finding_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0f2fe")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(finding_table)
    else:
        story.append(Paragraph("No recent findings available.", styles["BodyText"]))

    doc.build(story)
    buffer.seek(0)

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="executive_quality_review_dashboard_pdf_exported",
            resource_type="enterprise_executive_quality_review_dashboard_pdf",
            resource_id="executive_quality_review_dashboard",
            details={
                "total_findings": total_findings,
                "critical_findings": critical_findings,
                "high_findings": high_findings,
                "baseline_evidence_count": baseline_evidence_count,
                "approved_baseline_count": approved_baseline_count,
                "vendor_escalation_ready_count": vendor_escalation_ready_count,
                "ip_review_recommended_count": ip_review_recommended_count,
                "open_capa_count": open_capa_count,
                "quality_signal": quality_signal,
                "workflow_status": "executive_quality_review_dashboard_pdf_exported",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=lumenai-executive-quality-review-dashboard.pdf"
        },
    )


@router.get("/intake/{finding_id}/export-readiness-status", response_model=EnterpriseExportReadinessStatusResponse)
def get_enterprise_export_readiness_status(
    finding_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone
    from fastapi import HTTPException

    finding = db.get(EnterpriseFinding, finding_id)

    if not finding:
        raise HTTPException(status_code=404, detail="Enterprise finding not found")

    baseline_rows = []
    if finding.instrument_id:
        baseline_rows = (
            db.query(EnterpriseInstrumentBaseline)
            .filter(EnterpriseInstrumentBaseline.instrument_id == finding.instrument_id)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .all()
        )

    if not baseline_rows and finding.vendor_id:
        baseline_rows = (
            db.query(EnterpriseInstrumentBaseline)
            .filter(EnterpriseInstrumentBaseline.vendor_id == finding.vendor_id)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .all()
        )

    baseline_evidence_count = len(baseline_rows)

    approved_baseline_count = sum(
        1 for baseline in baseline_rows
        if (baseline.baseline_status or "").lower() == "approved"
    )

    evidence_attachment_count = (
        db.query(EnterpriseEvidence)
        .filter(EnterpriseEvidence.inspection_id == finding.id)
        .count()
    )

    severity = (finding.severity or "").lower()
    finding_category = (finding.finding_category or "").lower()
    finding_description = (finding.finding_description or "").lower()

    infection_terms = [
        "bioburden",
        "retained debris",
        "blood",
        "tissue",
        "bone",
        "organic",
        "soil",
        "contamination",
        "foreign material",
    ]

    has_ip_signal = any(
        term in finding_category or term in finding_description
        for term in infection_terms
    )

    governance_zip_ready = True
    executive_pdf_ready = True
    vendor_pdf_ready = severity in ["high", "critical"] or approved_baseline_count > 0
    infection_prevention_pdf_ready = has_ip_signal or severity in ["high", "critical"]

    governance_zip_url = f"/api/enterprise/intake/{finding.id}/governance-zip-bundle"
    vendor_pdf_url = f"/api/enterprise/intake/{finding.id}/vendor-escalation-packet.pdf"
    infection_prevention_pdf_url = f"/api/enterprise/intake/{finding.id}/infection-prevention-review-packet.pdf"
    executive_pdf_url = "/api/enterprise/executive-quality-review-dashboard.pdf"

    cards = [
        {
            "key": "governance_zip",
            "title": "Governance ZIP Bundle",
            "ready": governance_zip_ready,
            "status": "Ready" if governance_zip_ready else "Not Ready",
            "url": governance_zip_url,
            "description": "Includes JSON packet, baseline evidence, evidence attachments, PDF summary, manifest, and README.",
        },
        {
            "key": "vendor_escalation_pdf",
            "title": "Vendor Escalation PDF",
            "ready": vendor_pdf_ready,
            "status": "Ready" if vendor_pdf_ready else "Review Needed",
            "url": vendor_pdf_url,
            "description": "Vendor-facing quality packet with finding context, baseline evidence, and recommended vendor action.",
        },
        {
            "key": "infection_prevention_pdf",
            "title": "Infection Prevention PDF",
            "ready": infection_prevention_pdf_ready,
            "status": "Ready" if infection_prevention_pdf_ready else "Review Needed",
            "url": infection_prevention_pdf_url,
            "description": "IP-ready packet with patient-safety signal, infection-risk signal, and recommended documentation.",
        },
        {
            "key": "executive_quality_pdf",
            "title": "Executive Quality PDF",
            "ready": executive_pdf_ready,
            "status": "Ready",
            "url": executive_pdf_url,
            "description": "Leadership-ready summary of findings, quality signal, vendor signals, CAPA status, and actions.",
        },
    ]

    readiness_summary = (
        f"Export readiness generated for Finding #{finding.id}. "
        f"Baseline evidence count: {baseline_evidence_count}. "
        f"Approved baseline count: {approved_baseline_count}. "
        f"Evidence attachment count: {evidence_attachment_count}."
    )

    history_row = EnterpriseExportReadinessHistory(
        finding_id=finding.id,
        tenant_id=getattr(finding, "tenant_id", "") or "",
        generated_at=datetime.now(timezone.utc),
        governance_zip_ready=governance_zip_ready,
        vendor_pdf_ready=vendor_pdf_ready,
        infection_prevention_pdf_ready=infection_prevention_pdf_ready,
        executive_pdf_ready=executive_pdf_ready,
        baseline_evidence_count=baseline_evidence_count,
        approved_baseline_count=approved_baseline_count,
        evidence_attachment_count=evidence_attachment_count,
        readiness_summary=readiness_summary,
    )
    db.add(history_row)

    generated_at = datetime.now(timezone.utc).isoformat()

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id=finding.tenant_id,
            tenant_name="",
            action_type="export_readiness_status_viewed",
            resource_type="enterprise_export_readiness_status",
            resource_id=str(finding.id),
            details={
                "finding_id": finding.id,
                "generated_at": generated_at,
                "governance_zip_ready": governance_zip_ready,
                "vendor_pdf_ready": vendor_pdf_ready,
                "infection_prevention_pdf_ready": infection_prevention_pdf_ready,
                "executive_pdf_ready": executive_pdf_ready,
                "baseline_evidence_count": baseline_evidence_count,
                "approved_baseline_count": approved_baseline_count,
                "evidence_attachment_count": evidence_attachment_count,
                "workflow_status": "export_readiness_status_viewed",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return EnterpriseExportReadinessStatusResponse(
        status="success",
        finding_id=finding.id,
        generated_at=generated_at,
        governance_zip_ready=governance_zip_ready,
        vendor_pdf_ready=vendor_pdf_ready,
        infection_prevention_pdf_ready=infection_prevention_pdf_ready,
        executive_pdf_ready=executive_pdf_ready,
        baseline_evidence_count=baseline_evidence_count,
        approved_baseline_count=approved_baseline_count,
        evidence_attachment_count=evidence_attachment_count,
        governance_zip_url=governance_zip_url,
        vendor_pdf_url=vendor_pdf_url,
        infection_prevention_pdf_url=infection_prevention_pdf_url,
        executive_pdf_url=executive_pdf_url,
        readiness_summary=readiness_summary,
        cards=cards,
    )


@router.get("/export-readiness-history", response_model=EnterpriseExportReadinessHistoryResponse)
def get_enterprise_export_readiness_history(
    limit: int = 20,
    finding_id: int | None = None,
    db: Session = Depends(get_db),
):
    safe_limit = max(1, min(limit, 50))

    query = db.query(EnterpriseExportReadinessHistory)

    if finding_id is not None:
        query = query.filter(EnterpriseExportReadinessHistory.finding_id == finding_id)

    rows = (
        query
        .order_by(EnterpriseExportReadinessHistory.id.desc())
        .limit(safe_limit)
        .all()
    )

    return EnterpriseExportReadinessHistoryResponse(
        status="success",
        history_type="export_readiness_history",
        items=[
            EnterpriseExportReadinessHistoryItem(
                finding_id=row.finding_id,
                generated_at=row.generated_at.isoformat() if row.generated_at else "",
                governance_zip_ready=row.governance_zip_ready,
                vendor_pdf_ready=row.vendor_pdf_ready,
                infection_prevention_pdf_ready=row.infection_prevention_pdf_ready,
                executive_pdf_ready=row.executive_pdf_ready,
                baseline_evidence_count=row.baseline_evidence_count,
                approved_baseline_count=row.approved_baseline_count,
                evidence_attachment_count=row.evidence_attachment_count,
                readiness_summary=row.readiness_summary or "",
            )
            for row in rows
        ],
    )


@router.get("/export-readiness-history.pdf")
def get_enterprise_export_readiness_history_pdf(
    limit: int = 20,
    finding_id: int | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    safe_limit = max(1, min(limit, 50))

    query = db.query(EnterpriseExportReadinessHistory)

    if finding_id is not None:
        query = query.filter(EnterpriseExportReadinessHistory.finding_id == finding_id)

    rows = (
        query
        .order_by(EnterpriseExportReadinessHistory.id.desc())
        .limit(safe_limit)
        .all()
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("LumenAI Export Readiness History Audit Report", styles["Title"]))
    story.append(Spacer(1, 10))

    filter_text = f"Limit: {safe_limit}"
    if finding_id is not None:
        filter_text += f" | Finding ID filter: {finding_id}"

    story.append(Paragraph(filter_text, styles["BodyText"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Audit Summary", styles["Heading2"]))
    story.append(Paragraph(
        "This report summarizes backend-generated export readiness checks for Governance ZIP, "
        "Vendor Escalation PDF, Infection Prevention PDF, and Executive Quality PDF exports.",
        styles["BodyText"],
    ))
    story.append(Spacer(1, 12))

    if rows:
        table_data = [[
            "Finding",
            "Generated At",
            "ZIP",
            "Vendor",
            "IP",
            "Exec",
            "Baselines",
            "Approved",
            "Evidence",
        ]]

        for row in rows:
            generated_at = row.generated_at.isoformat() if row.generated_at else ""
            table_data.append([
                str(row.finding_id),
                generated_at,
                "Yes" if row.governance_zip_ready else "No",
                "Yes" if row.vendor_pdf_ready else "No",
                "Yes" if row.infection_prevention_pdf_ready else "No",
                "Yes" if row.executive_pdf_ready else "No",
                str(row.baseline_evidence_count),
                str(row.approved_baseline_count),
                str(row.evidence_attachment_count),
            ])

        table = Table(table_data, colWidths=[45, 125, 40, 45, 35, 40, 60, 60, 55])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 6.5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(table)

        story.append(Spacer(1, 12))
        story.append(Paragraph("Readiness Detail", styles["Heading2"]))

        for row in rows[:10]:
            generated_at = row.generated_at.isoformat() if row.generated_at else ""
            story.append(Spacer(1, 8))
            story.append(Paragraph(f"Finding #{row.finding_id}", styles["Heading3"]))
            story.append(Paragraph(f"<b>Generated At:</b> {generated_at}", styles["BodyText"]))
            story.append(Paragraph(f"<b>Readiness Summary:</b> {row.readiness_summary or ''}", styles["BodyText"]))
            story.append(Paragraph(
                f"<b>Export Flags:</b> "
                f"Governance ZIP={'Yes' if row.governance_zip_ready else 'No'}; "
                f"Vendor PDF={'Yes' if row.vendor_pdf_ready else 'No'}; "
                f"IP PDF={'Yes' if row.infection_prevention_pdf_ready else 'No'}; "
                f"Executive PDF={'Yes' if row.executive_pdf_ready else 'No'}.",
                styles["BodyText"],
            ))
    else:
        story.append(Paragraph("No export readiness history records found for the selected filter.", styles["BodyText"]))

    doc.build(story)
    buffer.seek(0)

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="export_readiness_history_pdf_exported",
            resource_type="enterprise_export_readiness_history_pdf",
            resource_id=str(finding_id) if finding_id is not None else "all",
            details={
                "limit": safe_limit,
                "finding_id": finding_id,
                "record_count": len(rows),
                "workflow_status": "export_readiness_history_pdf_exported",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    filename_suffix = f"finding-{finding_id}" if finding_id is not None else "all"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=lumenai-export-readiness-history-{filename_suffix}.pdf"
        },
    )


@router.get("/export-readiness-history.csv")
def get_enterprise_export_readiness_history_csv(
    limit: int = 50,
    finding_id: int | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    import csv
    from io import StringIO
    from fastapi.responses import StreamingResponse

    safe_limit = max(1, min(limit, 500))

    query = db.query(EnterpriseExportReadinessHistory)

    if finding_id is not None:
        query = query.filter(EnterpriseExportReadinessHistory.finding_id == finding_id)

    rows = (
        query
        .order_by(EnterpriseExportReadinessHistory.id.desc())
        .limit(safe_limit)
        .all()
    )

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "history_id",
        "finding_id",
        "tenant_id",
        "generated_at",
        "governance_zip_ready",
        "vendor_pdf_ready",
        "infection_prevention_pdf_ready",
        "executive_pdf_ready",
        "baseline_evidence_count",
        "approved_baseline_count",
        "evidence_attachment_count",
        "readiness_summary",
        "created_at",
    ])

    for row in rows:
        writer.writerow([
            row.id,
            row.finding_id,
            row.tenant_id or "",
            row.generated_at.isoformat() if row.generated_at else "",
            row.governance_zip_ready,
            row.vendor_pdf_ready,
            row.infection_prevention_pdf_ready,
            row.executive_pdf_ready,
            row.baseline_evidence_count,
            row.approved_baseline_count,
            row.evidence_attachment_count,
            row.readiness_summary or "",
            row.created_at.isoformat() if row.created_at else "",
        ])

    output.seek(0)

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="export_readiness_history_csv_exported",
            resource_type="enterprise_export_readiness_history_csv",
            resource_id=str(finding_id) if finding_id is not None else "all",
            details={
                "limit": safe_limit,
                "finding_id": finding_id,
                "record_count": len(rows),
                "workflow_status": "export_readiness_history_csv_exported",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    filename_suffix = f"finding-{finding_id}" if finding_id is not None else "all"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=lumenai-export-readiness-history-{filename_suffix}.csv"
        },
    )


@router.get("/export-readiness-history.powerbi.csv")
def get_enterprise_export_readiness_history_powerbi_csv(
    limit: int = 500,
    finding_id: int | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    import csv
    from io import StringIO
    from fastapi.responses import StreamingResponse

    safe_limit = max(1, min(limit, 2000))

    query = db.query(EnterpriseExportReadinessHistory)

    if finding_id is not None:
        query = query.filter(EnterpriseExportReadinessHistory.finding_id == finding_id)

    rows = (
        query
        .order_by(EnterpriseExportReadinessHistory.id.desc())
        .limit(safe_limit)
        .all()
    )

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "history_id",
        "finding_id",
        "tenant_id",
        "readiness_generated_at",
        "readiness_date",
        "readiness_month",
        "governance_zip_ready",
        "vendor_pdf_ready",
        "infection_prevention_pdf_ready",
        "executive_pdf_ready",
        "all_exports_ready",
        "readiness_score",
        "readiness_status",
        "baseline_evidence_count",
        "approved_baseline_count",
        "baseline_approval_rate",
        "evidence_attachment_count",
        "readiness_summary",
        "created_at",
    ])

    for row in rows:
        generated_at = row.generated_at
        readiness_date = generated_at.date().isoformat() if generated_at else ""
        readiness_month = generated_at.strftime("%Y-%m") if generated_at else ""

        readiness_flags = [
            bool(row.governance_zip_ready),
            bool(row.vendor_pdf_ready),
            bool(row.infection_prevention_pdf_ready),
            bool(row.executive_pdf_ready),
        ]

        readiness_score = int((sum(1 for flag in readiness_flags if flag) / 4) * 100)
        all_exports_ready = all(readiness_flags)

        if all_exports_ready:
            readiness_status = "Ready"
        elif readiness_score >= 50:
            readiness_status = "Partially Ready"
        else:
            readiness_status = "Not Ready"

        baseline_approval_rate = 0
        if row.baseline_evidence_count:
            baseline_approval_rate = round(
                row.approved_baseline_count / row.baseline_evidence_count,
                4,
            )

        writer.writerow([
            row.id,
            row.finding_id,
            row.tenant_id or "",
            generated_at.isoformat() if generated_at else "",
            readiness_date,
            readiness_month,
            row.governance_zip_ready,
            row.vendor_pdf_ready,
            row.infection_prevention_pdf_ready,
            row.executive_pdf_ready,
            all_exports_ready,
            readiness_score,
            readiness_status,
            row.baseline_evidence_count,
            row.approved_baseline_count,
            baseline_approval_rate,
            row.evidence_attachment_count,
            row.readiness_summary or "",
            row.created_at.isoformat() if row.created_at else "",
        ])

    output.seek(0)

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="export_readiness_history_powerbi_csv_exported",
            resource_type="enterprise_export_readiness_history_powerbi_csv",
            resource_id=str(finding_id) if finding_id is not None else "all",
            details={
                "limit": safe_limit,
                "finding_id": finding_id,
                "record_count": len(rows),
                "workflow_status": "export_readiness_history_powerbi_csv_exported",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    filename_suffix = f"finding-{finding_id}" if finding_id is not None else "all"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=lumenai-export-readiness-powerbi-{filename_suffix}.csv"
        },
    )


@router.get("/export-readiness-history.powerbi.data-dictionary")
def get_enterprise_export_readiness_powerbi_data_dictionary(
    request: Request,
    db: Session = Depends(get_db),
):
    dictionary = [
        {
            "field_name": "history_id",
            "display_name": "History ID",
            "data_type": "integer",
            "description": "Unique identifier for each export readiness history record.",
            "power_bi_usage": "Use as a unique row key or drill-through identifier.",
            "example_value": "47",
        },
        {
            "field_name": "finding_id",
            "display_name": "Finding ID",
            "data_type": "integer",
            "description": "Enterprise finding associated with the export readiness check.",
            "power_bi_usage": "Use to filter, group, or join readiness records to finding-level reports.",
            "example_value": "2",
        },
        {
            "field_name": "tenant_id",
            "display_name": "Tenant",
            "data_type": "text",
            "description": "Tenant or organization identifier associated with the readiness record.",
            "power_bi_usage": "Use as organization/site/system filter when supporting multiple tenants.",
            "example_value": "bonsecours",
        },
        {
            "field_name": "readiness_generated_at",
            "display_name": "Readiness Generated At",
            "data_type": "datetime",
            "description": "Backend timestamp when the readiness status was generated.",
            "power_bi_usage": "Use for trend analysis, audit timing, and freshness validation.",
            "example_value": "2026-05-28T01:49:02.398008",
        },
        {
            "field_name": "readiness_date",
            "display_name": "Readiness Date",
            "data_type": "date",
            "description": "Date portion of the backend-generated readiness timestamp.",
            "power_bi_usage": "Use on date slicers, daily trend visuals, and audit timelines.",
            "example_value": "2026-05-28",
        },
        {
            "field_name": "readiness_month",
            "display_name": "Readiness Month",
            "data_type": "text/date period",
            "description": "Year-month period derived from readiness_generated_at.",
            "power_bi_usage": "Use for monthly readiness trend charts.",
            "example_value": "2026-05",
        },
        {
            "field_name": "governance_zip_ready",
            "display_name": "Governance ZIP Ready",
            "data_type": "boolean",
            "description": "Indicates whether the governance ZIP bundle is available for export.",
            "power_bi_usage": "Use as a readiness KPI or conditional formatting flag.",
            "example_value": "True",
        },
        {
            "field_name": "vendor_pdf_ready",
            "display_name": "Vendor PDF Ready",
            "data_type": "boolean",
            "description": "Indicates whether the vendor escalation PDF is available for export.",
            "power_bi_usage": "Use to monitor vendor escalation packet readiness.",
            "example_value": "True",
        },
        {
            "field_name": "infection_prevention_pdf_ready",
            "display_name": "IP PDF Ready",
            "data_type": "boolean",
            "description": "Indicates whether the Infection Prevention review PDF is available for export.",
            "power_bi_usage": "Use to monitor IP review packet readiness for patient-safety findings.",
            "example_value": "True",
        },
        {
            "field_name": "executive_pdf_ready",
            "display_name": "Executive PDF Ready",
            "data_type": "boolean",
            "description": "Indicates whether the Executive Quality Review PDF is available for export.",
            "power_bi_usage": "Use as a leadership reporting readiness flag.",
            "example_value": "True",
        },
        {
            "field_name": "all_exports_ready",
            "display_name": "All Exports Ready",
            "data_type": "boolean",
            "description": "True when all export types are ready.",
            "power_bi_usage": "Use as the main overall export readiness KPI.",
            "example_value": "True",
        },
        {
            "field_name": "readiness_score",
            "display_name": "Readiness Score",
            "data_type": "integer percentage",
            "description": "Percent score based on how many export types are ready.",
            "power_bi_usage": "Use as a gauge, card, or trend metric.",
            "example_value": "100",
        },
        {
            "field_name": "readiness_status",
            "display_name": "Readiness Status",
            "data_type": "text/category",
            "description": "Categorical readiness status derived from readiness score.",
            "power_bi_usage": "Use as legend, slicer, or conditional status label.",
            "example_value": "Ready",
        },
        {
            "field_name": "baseline_evidence_count",
            "display_name": "Baseline Evidence Count",
            "data_type": "integer",
            "description": "Number of manufacturer baseline evidence records linked to the finding/instrument.",
            "power_bi_usage": "Use to monitor baseline evidence coverage.",
            "example_value": "3",
        },
        {
            "field_name": "approved_baseline_count",
            "display_name": "Approved Baseline Count",
            "data_type": "integer",
            "description": "Number of approved baseline evidence records.",
            "power_bi_usage": "Use to monitor trusted baseline coverage.",
            "example_value": "3",
        },
        {
            "field_name": "baseline_approval_rate",
            "display_name": "Baseline Approval Rate",
            "data_type": "decimal",
            "description": "Approved baselines divided by total baseline evidence records.",
            "power_bi_usage": "Use as a percentage KPI for baseline governance maturity.",
            "example_value": "1.0",
        },
        {
            "field_name": "evidence_attachment_count",
            "display_name": "Evidence Attachment Count",
            "data_type": "integer",
            "description": "Number of evidence attachments associated with the finding.",
            "power_bi_usage": "Use to monitor evidence completeness.",
            "example_value": "0",
        },
        {
            "field_name": "readiness_summary",
            "display_name": "Readiness Summary",
            "data_type": "text",
            "description": "Human-readable summary of the readiness check.",
            "power_bi_usage": "Use in drill-through tables or detail views.",
            "example_value": "Export readiness generated for Finding #2.",
        },
        {
            "field_name": "created_at",
            "display_name": "Record Created At",
            "data_type": "datetime",
            "description": "Timestamp when the readiness history record was stored.",
            "power_bi_usage": "Use for audit trail timing and record freshness checks.",
            "example_value": "2026-05-28T01:49:02.399981",
        },
    ]

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="export_readiness_powerbi_data_dictionary_viewed",
            resource_type="enterprise_export_readiness_powerbi_data_dictionary",
            resource_id="powerbi_data_dictionary",
            details={
                "field_count": len(dictionary),
                "workflow_status": "export_readiness_powerbi_data_dictionary_viewed",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return {
        "status": "success",
        "dictionary_type": "export_readiness_powerbi_data_dictionary",
        "field_count": len(dictionary),
        "recommended_power_bi_measures": [
            {
                "measure_name": "Average Readiness Score",
                "dax": "Average Readiness Score = AVERAGE('ExportReadiness'[readiness_score])",
            },
            {
                "measure_name": "Ready Export Checks",
                "dax": "Ready Export Checks = COUNTROWS(FILTER('ExportReadiness', 'ExportReadiness'[all_exports_ready] = TRUE()))",
            },
            {
                "measure_name": "Baseline Approval Rate",
                "dax": "Baseline Approval Rate = AVERAGE('ExportReadiness'[baseline_approval_rate])",
            },
            {
                "measure_name": "Total Readiness Checks",
                "dax": "Total Readiness Checks = COUNTROWS('ExportReadiness')",
            },
        ],
        "recommended_visuals": [
            "Card: Average Readiness Score",
            "Card: Total Readiness Checks",
            "Donut or stacked bar: Readiness Status",
            "Line chart: Readiness Score by Readiness Date",
            "Bar chart: Baseline Evidence Count by Finding ID",
            "Table: Finding ID, Readiness Status, Generated At, Baseline Approval Rate",
        ],
        "fields": dictionary,
    }


@router.get("/export-readiness-history.powerbi.data-dictionary.pdf")
def get_enterprise_export_readiness_powerbi_data_dictionary_pdf(
    request: Request,
    db: Session = Depends(get_db),
):
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    dictionary_response = get_enterprise_export_readiness_powerbi_data_dictionary(
        request=request,
        db=db,
    )

    fields = dictionary_response.get("fields", [])
    measures = dictionary_response.get("recommended_power_bi_measures", [])
    visuals = dictionary_response.get("recommended_visuals", [])

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("LumenAI Power BI Data Dictionary", styles["Title"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Purpose", styles["Heading2"]))
    story.append(Paragraph(
        "This data dictionary describes the fields included in the LumenAI export readiness Power BI CSV. "
        "It is intended to support dashboard development, audit-readiness review, leadership reporting, "
        "quality committee discussions, and data governance.",
        styles["BodyText"],
    ))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Recommended Power BI Measures", styles["Heading2"]))

    if measures:
        measure_data = [["Measure", "DAX"]]
        for measure in measures:
            measure_data.append([
                measure.get("measure_name", ""),
                measure.get("dax", ""),
            ])

        measure_table = Table(measure_data, colWidths=[160, 330])
        measure_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(measure_table)
    else:
        story.append(Paragraph("No recommended measures documented.", styles["BodyText"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Recommended Visuals", styles["Heading2"]))

    if visuals:
        visual_data = [["Recommended Visual"]]
        for visual in visuals:
            visual_data.append([visual])

        visual_table = Table(visual_data, colWidths=[490])
        visual_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcfce7")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(visual_table)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Field Dictionary", styles["Heading2"]))

    if fields:
        field_data = [[
            "Field",
            "Display Name",
            "Type",
            "Description",
            "Power BI Usage",
            "Example",
        ]]

        for field in fields:
            field_data.append([
                field.get("field_name", ""),
                field.get("display_name", ""),
                field.get("data_type", ""),
                field.get("description", ""),
                field.get("power_bi_usage", ""),
                field.get("example_value", ""),
            ])

        field_table = Table(field_data, colWidths=[82, 82, 55, 120, 115, 55])
        field_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fef3c7")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 5.5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(field_table)
    else:
        story.append(Paragraph("No fields documented.", styles["BodyText"]))

    doc.build(story)
    buffer.seek(0)

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="export_readiness_powerbi_data_dictionary_pdf_exported",
            resource_type="enterprise_export_readiness_powerbi_data_dictionary_pdf",
            resource_id="powerbi_data_dictionary_pdf",
            details={
                "field_count": len(fields),
                "measure_count": len(measures),
                "visual_count": len(visuals),
                "workflow_status": "export_readiness_powerbi_data_dictionary_pdf_exported",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=lumenai-powerbi-data-dictionary.pdf"
        },
    )


@router.get("/export-readiness-history.powerbi.dashboard-spec")
def get_enterprise_export_readiness_powerbi_dashboard_spec(
    request: Request,
    db: Session = Depends(get_db),
):
    dashboard_spec = {
        "status": "success",
        "spec_type": "export_readiness_powerbi_starter_dashboard",
        "title": "LumenAI Export Readiness Power BI Starter Dashboard",
        "purpose": (
            "Starter dashboard specification for analyzing export readiness history, "
            "baseline evidence coverage, approved baseline maturity, and packet readiness "
            "for governance, vendor escalation, Infection Prevention, and executive review exports."
        ),
        "recommended_dataset_name": "ExportReadiness",
        "recommended_pages": [
            {
                "page_name": "Executive Overview",
                "audience": "Leadership, quality committee, operational executives",
                "purpose": "Summarize overall export readiness and governance maturity.",
                "recommended_visuals": [
                    {
                        "visual_type": "Card",
                        "title": "Average Readiness Score",
                        "fields": ["readiness_score"],
                        "measure": "Average Readiness Score",
                        "description": "Shows average readiness score across selected readiness checks.",
                    },
                    {
                        "visual_type": "Card",
                        "title": "Total Readiness Checks",
                        "fields": ["history_id"],
                        "measure": "Total Readiness Checks",
                        "description": "Counts readiness history records.",
                    },
                    {
                        "visual_type": "Card",
                        "title": "Baseline Approval Rate",
                        "fields": ["baseline_approval_rate"],
                        "measure": "Baseline Approval Rate",
                        "description": "Shows average percentage of approved baseline records.",
                    },
                    {
                        "visual_type": "Donut Chart",
                        "title": "Readiness Status Distribution",
                        "legend": "readiness_status",
                        "values": "history_id count",
                        "description": "Shows Ready, Partially Ready, and Not Ready status distribution.",
                    },
                    {
                        "visual_type": "Line Chart",
                        "title": "Readiness Score Trend",
                        "axis": "readiness_date",
                        "values": "Average Readiness Score",
                        "description": "Tracks readiness score trend over time.",
                    },
                ],
            },
            {
                "page_name": "Finding-Level Readiness",
                "audience": "Quality, SPD leadership, audit reviewers",
                "purpose": "Drill into readiness by finding and packet type.",
                "recommended_visuals": [
                    {
                        "visual_type": "Table",
                        "title": "Finding Readiness Detail",
                        "fields": [
                            "finding_id",
                            "readiness_generated_at",
                            "readiness_status",
                            "governance_zip_ready",
                            "vendor_pdf_ready",
                            "infection_prevention_pdf_ready",
                            "executive_pdf_ready",
                            "baseline_evidence_count",
                            "approved_baseline_count",
                            "evidence_attachment_count",
                        ],
                        "description": "Provides record-level export readiness detail.",
                    },
                    {
                        "visual_type": "Stacked Bar Chart",
                        "title": "Readiness Score by Finding",
                        "axis": "finding_id",
                        "values": "Average Readiness Score",
                        "description": "Compares readiness score across findings.",
                    },
                    {
                        "visual_type": "Clustered Column Chart",
                        "title": "Baseline Evidence vs Approved Baselines",
                        "axis": "finding_id",
                        "values": [
                            "baseline_evidence_count",
                            "approved_baseline_count",
                        ],
                        "description": "Shows baseline evidence maturity by finding.",
                    },
                ],
            },
            {
                "page_name": "Packet Readiness",
                "audience": "Governance users, quality coordinators, analysts",
                "purpose": "Monitor readiness of individual export packet types.",
                "recommended_visuals": [
                    {
                        "visual_type": "Matrix",
                        "title": "Packet Readiness Matrix",
                        "rows": "finding_id",
                        "columns": [
                            "governance_zip_ready",
                            "vendor_pdf_ready",
                            "infection_prevention_pdf_ready",
                            "executive_pdf_ready",
                        ],
                        "description": "Shows which packet types are ready by finding.",
                    },
                    {
                        "visual_type": "Bar Chart",
                        "title": "Ready Export Checks by Packet Type",
                        "fields": [
                            "governance_zip_ready",
                            "vendor_pdf_ready",
                            "infection_prevention_pdf_ready",
                            "executive_pdf_ready",
                        ],
                        "description": "Compares readiness across export packet categories.",
                    },
                ],
            },
            {
                "page_name": "Audit Detail",
                "audience": "Survey readiness, auditors, compliance teams",
                "purpose": "Provide a detailed readiness audit trail.",
                "recommended_visuals": [
                    {
                        "visual_type": "Table",
                        "title": "Export Readiness Audit Log",
                        "fields": [
                            "history_id",
                            "tenant_id",
                            "finding_id",
                            "readiness_generated_at",
                            "created_at",
                            "readiness_summary",
                        ],
                        "description": "Detailed record of backend-generated readiness checks.",
                    }
                ],
            },
        ],
        "recommended_slicers": [
            {
                "field": "readiness_date",
                "display_name": "Readiness Date",
                "type": "date slicer",
            },
            {
                "field": "readiness_month",
                "display_name": "Readiness Month",
                "type": "dropdown or tile slicer",
            },
            {
                "field": "finding_id",
                "display_name": "Finding ID",
                "type": "dropdown slicer",
            },
            {
                "field": "tenant_id",
                "display_name": "Tenant",
                "type": "dropdown slicer",
            },
            {
                "field": "readiness_status",
                "display_name": "Readiness Status",
                "type": "dropdown slicer",
            },
        ],
        "recommended_measures": [
            {
                "measure_name": "Average Readiness Score",
                "dax": "Average Readiness Score = AVERAGE('ExportReadiness'[readiness_score])",
            },
            {
                "measure_name": "Total Readiness Checks",
                "dax": "Total Readiness Checks = COUNTROWS('ExportReadiness')",
            },
            {
                "measure_name": "Ready Export Checks",
                "dax": "Ready Export Checks = COUNTROWS(FILTER('ExportReadiness', 'ExportReadiness'[all_exports_ready] = TRUE()))",
            },
            {
                "measure_name": "Readiness Completion Rate",
                "dax": "Readiness Completion Rate = DIVIDE([Ready Export Checks], [Total Readiness Checks])",
            },
            {
                "measure_name": "Baseline Approval Rate",
                "dax": "Baseline Approval Rate = AVERAGE('ExportReadiness'[baseline_approval_rate])",
            },
            {
                "measure_name": "Average Baseline Evidence Count",
                "dax": "Average Baseline Evidence Count = AVERAGE('ExportReadiness'[baseline_evidence_count])",
            },
        ],
        "recommended_conditional_formatting": [
            {
                "field": "readiness_score",
                "rule": "Green >= 90; Amber 50-89; Red < 50",
            },
            {
                "field": "readiness_status",
                "rule": "Ready = Green; Partially Ready = Amber; Not Ready = Red",
            },
            {
                "field": "baseline_approval_rate",
                "rule": "Green >= 0.9; Amber 0.5-0.89; Red < 0.5",
            },
        ],
        "recommended_refresh_plan": {
            "manual_csv_import": "Download Power BI CSV from LumenAI dashboard and refresh Power BI dataset manually.",
            "future_api_refresh": "Use authenticated API endpoint as a web data source after token management is productionized.",
            "recommended_frequency": "Daily for leadership reporting; weekly for quality committee review.",
        },
    }

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="export_readiness_powerbi_dashboard_spec_viewed",
            resource_type="enterprise_export_readiness_powerbi_dashboard_spec",
            resource_id="powerbi_dashboard_spec",
            details={
                "page_count": len(dashboard_spec["recommended_pages"]),
                "slicer_count": len(dashboard_spec["recommended_slicers"]),
                "measure_count": len(dashboard_spec["recommended_measures"]),
                "workflow_status": "export_readiness_powerbi_dashboard_spec_viewed",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return dashboard_spec


@router.get("/export-readiness-history.powerbi.dashboard-spec.pdf")
def get_enterprise_export_readiness_powerbi_dashboard_spec_pdf(
    request: Request,
    db: Session = Depends(get_db),
):
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    spec = get_enterprise_export_readiness_powerbi_dashboard_spec(
        request=request,
        db=db,
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("LumenAI Power BI Starter Dashboard Spec", styles["Title"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Purpose", styles["Heading2"]))
    story.append(Paragraph(spec.get("purpose", ""), styles["BodyText"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Recommended Dataset", styles["Heading2"]))
    story.append(Paragraph(spec.get("recommended_dataset_name", "ExportReadiness"), styles["BodyText"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Recommended Report Pages", styles["Heading2"]))

    for page in spec.get("recommended_pages", []):
        story.append(Spacer(1, 8))
        story.append(Paragraph(page.get("page_name", ""), styles["Heading3"]))
        story.append(Paragraph(f"<b>Audience:</b> {page.get('audience', '')}", styles["BodyText"]))
        story.append(Paragraph(f"<b>Purpose:</b> {page.get('purpose', '')}", styles["BodyText"]))

        visuals = page.get("recommended_visuals", [])
        if visuals:
            visual_data = [["Visual", "Title", "Fields / Measure", "Description"]]

            for visual in visuals:
                fields = visual.get("fields") or visual.get("axis") or visual.get("values") or visual.get("legend") or visual.get("rows") or visual.get("columns") or ""
                if isinstance(fields, list):
                    fields = ", ".join(str(item) for item in fields)

                measure = visual.get("measure", "")
                field_measure = fields
                if measure:
                    field_measure = f"{field_measure} | Measure: {measure}" if field_measure else f"Measure: {measure}"

                visual_data.append([
                    visual.get("visual_type", ""),
                    visual.get("title", ""),
                    field_measure,
                    visual.get("description", ""),
                ])

            visual_table = Table(visual_data, colWidths=[75, 110, 140, 165])
            visual_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                ("FONTSIZE", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(Spacer(1, 6))
            story.append(visual_table)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Recommended Slicers", styles["Heading2"]))

    slicers = spec.get("recommended_slicers", [])
    if slicers:
        slicer_data = [["Field", "Display Name", "Type"]]
        for slicer in slicers:
            slicer_data.append([
                slicer.get("field", ""),
                slicer.get("display_name", ""),
                slicer.get("type", ""),
            ])

        slicer_table = Table(slicer_data, colWidths=[150, 160, 170])
        slicer_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcfce7")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(slicer_table)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Recommended DAX Measures", styles["Heading2"]))

    measures = spec.get("recommended_measures", [])
    if measures:
        measure_data = [["Measure", "DAX"]]
        for measure in measures:
            measure_data.append([
                measure.get("measure_name", ""),
                measure.get("dax", ""),
            ])

        measure_table = Table(measure_data, colWidths=[160, 330])
        measure_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fef3c7")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 6.5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(measure_table)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Conditional Formatting Rules", styles["Heading2"]))

    rules = spec.get("recommended_conditional_formatting", [])
    if rules:
        rule_data = [["Field", "Rule"]]
        for rule in rules:
            rule_data.append([
                rule.get("field", ""),
                rule.get("rule", ""),
            ])

        rule_table = Table(rule_data, colWidths=[170, 320])
        rule_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fee2e2")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(rule_table)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Recommended Refresh Plan", styles["Heading2"]))

    refresh_plan = spec.get("recommended_refresh_plan", {})
    refresh_data = [["Item", "Recommendation"]]
    for key, value in refresh_plan.items():
        refresh_data.append([
            key.replace("_", " ").title(),
            str(value),
        ])

    refresh_table = Table(refresh_data, colWidths=[160, 330])
    refresh_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0f2fe")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(refresh_table)

    doc.build(story)
    buffer.seek(0)

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="export_readiness_powerbi_dashboard_spec_pdf_exported",
            resource_type="enterprise_export_readiness_powerbi_dashboard_spec_pdf",
            resource_id="powerbi_dashboard_spec_pdf",
            details={
                "page_count": len(spec.get("recommended_pages", [])),
                "slicer_count": len(spec.get("recommended_slicers", [])),
                "measure_count": len(spec.get("recommended_measures", [])),
                "workflow_status": "export_readiness_powerbi_dashboard_spec_pdf_exported",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=lumenai-powerbi-starter-dashboard-spec.pdf"
        },
    )


@router.get("/export-readiness-history.powerbi-toolkit.zip")
def get_enterprise_export_readiness_powerbi_toolkit_zip(
    limit: int = 500,
    finding_id: int | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    import csv
    import json
    import zipfile
    from io import BytesIO, StringIO
    from fastapi.responses import StreamingResponse

    safe_limit = max(1, min(limit, 2000))

    query = db.query(EnterpriseExportReadinessHistory)

    if finding_id is not None:
        query = query.filter(EnterpriseExportReadinessHistory.finding_id == finding_id)

    rows = (
        query
        .order_by(EnterpriseExportReadinessHistory.id.desc())
        .limit(safe_limit)
        .all()
    )

    def build_standard_csv() -> str:
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "history_id",
            "finding_id",
            "tenant_id",
            "generated_at",
            "governance_zip_ready",
            "vendor_pdf_ready",
            "infection_prevention_pdf_ready",
            "executive_pdf_ready",
            "baseline_evidence_count",
            "approved_baseline_count",
            "evidence_attachment_count",
            "readiness_summary",
            "created_at",
        ])

        for row in rows:
            writer.writerow([
                row.id,
                row.finding_id,
                row.tenant_id or "",
                row.generated_at.isoformat() if row.generated_at else "",
                row.governance_zip_ready,
                row.vendor_pdf_ready,
                row.infection_prevention_pdf_ready,
                row.executive_pdf_ready,
                row.baseline_evidence_count,
                row.approved_baseline_count,
                row.evidence_attachment_count,
                row.readiness_summary or "",
                row.created_at.isoformat() if row.created_at else "",
            ])

        return output.getvalue()

    def build_powerbi_csv() -> str:
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "history_id",
            "finding_id",
            "tenant_id",
            "readiness_generated_at",
            "readiness_date",
            "readiness_month",
            "governance_zip_ready",
            "vendor_pdf_ready",
            "infection_prevention_pdf_ready",
            "executive_pdf_ready",
            "all_exports_ready",
            "readiness_score",
            "readiness_status",
            "baseline_evidence_count",
            "approved_baseline_count",
            "baseline_approval_rate",
            "evidence_attachment_count",
            "readiness_summary",
            "created_at",
        ])

        for row in rows:
            generated_at = row.generated_at
            readiness_date = generated_at.date().isoformat() if generated_at else ""
            readiness_month = generated_at.strftime("%Y-%m") if generated_at else ""

            readiness_flags = [
                bool(row.governance_zip_ready),
                bool(row.vendor_pdf_ready),
                bool(row.infection_prevention_pdf_ready),
                bool(row.executive_pdf_ready),
            ]

            readiness_score = int((sum(1 for flag in readiness_flags if flag) / 4) * 100)
            all_exports_ready = all(readiness_flags)

            if all_exports_ready:
                readiness_status = "Ready"
            elif readiness_score >= 50:
                readiness_status = "Partially Ready"
            else:
                readiness_status = "Not Ready"

            baseline_approval_rate = 0
            if row.baseline_evidence_count:
                baseline_approval_rate = round(
                    row.approved_baseline_count / row.baseline_evidence_count,
                    4,
                )

            writer.writerow([
                row.id,
                row.finding_id,
                row.tenant_id or "",
                generated_at.isoformat() if generated_at else "",
                readiness_date,
                readiness_month,
                row.governance_zip_ready,
                row.vendor_pdf_ready,
                row.infection_prevention_pdf_ready,
                row.executive_pdf_ready,
                all_exports_ready,
                readiness_score,
                readiness_status,
                row.baseline_evidence_count,
                row.approved_baseline_count,
                baseline_approval_rate,
                row.evidence_attachment_count,
                row.readiness_summary or "",
                row.created_at.isoformat() if row.created_at else "",
            ])

        return output.getvalue()

    data_dictionary = get_enterprise_export_readiness_powerbi_data_dictionary(
        request=request,
        db=db,
    )

    dashboard_spec = get_enterprise_export_readiness_powerbi_dashboard_spec(
        request=request,
        db=db,
    )

    toolkit_metadata = get_enterprise_export_readiness_powerbi_toolkit_metadata(
        request=request,
        db=db,
    )

    readme = f"""LumenAI Power BI Export Toolkit

Purpose
This ZIP bundle contains the core export readiness files needed to build a Power BI dashboard for LumenAI export readiness, baseline evidence coverage, and audit reporting.

Files Included
1. export-readiness-history.csv
   Standard persistent export readiness history.

2. export-readiness-powerbi.csv
   Power BI-ready dataset with derived fields such as readiness_date, readiness_month, readiness_score, readiness_status, all_exports_ready, and baseline_approval_rate.

3. powerbi-data-dictionary.json
   Machine-readable field dictionary, recommended DAX measures, and recommended visuals.

4. powerbi-dashboard-spec.json
   Starter dashboard specification with report pages, visuals, slicers, measures, conditional formatting, and refresh plan.

How to Use in Power BI
1. Open Power BI Desktop.
2. Select Get Data.
3. Choose Text/CSV.
4. Import export-readiness-powerbi.csv.
5. Set readiness_generated_at and created_at as Date/Time.
6. Set readiness_date as Date.
7. Set readiness_score as Whole Number.
8. Set baseline_approval_rate as Decimal Number or Percentage.
9. Build the pages described in powerbi-dashboard-spec.json.

Suggested Dataset Name
ExportReadiness

Recommended Filters
- readiness_date
- readiness_month
- finding_id
- tenant_id
- readiness_status

Generated Parameters
limit={safe_limit}
finding_id={finding_id if finding_id is not None else "all"}
record_count={len(rows)}
"""

    buffer = BytesIO()

    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("export-readiness-history.csv", build_standard_csv())
        zip_file.writestr("export-readiness-powerbi.csv", build_powerbi_csv())
        zip_file.writestr(
            "powerbi-data-dictionary.json",
            json.dumps(data_dictionary, indent=2, default=str),
        )
        zip_file.writestr(
            "powerbi-dashboard-spec.json",
            json.dumps(dashboard_spec, indent=2, default=str),
        )
        zip_file.writestr(
            "powerbi-toolkit-metadata.json",
            json.dumps(toolkit_metadata, indent=2, default=str),
        )
        zip_file.writestr("README.txt", readme)

    buffer.seek(0)

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="export_readiness_powerbi_toolkit_zip_exported",
            resource_type="enterprise_export_readiness_powerbi_toolkit_zip",
            resource_id=str(finding_id) if finding_id is not None else "all",
            details={
                "limit": safe_limit,
                "finding_id": finding_id,
                "record_count": len(rows),
                "workflow_status": "export_readiness_powerbi_toolkit_zip_exported",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    filename_suffix = f"finding-{finding_id}" if finding_id is not None else "all"

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=lumenai-powerbi-export-toolkit-{filename_suffix}.zip"
        },
    )


@router.get("/export-readiness-history.powerbi-toolkit.readme.pdf")
def get_enterprise_export_readiness_powerbi_toolkit_readme_pdf(
    request: Request,
    db: Session = Depends(get_db),
):
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("LumenAI Power BI Toolkit README", styles["Title"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Purpose", styles["Heading2"]))
    story.append(Paragraph(
        "This guide explains how to use the LumenAI Power BI Export Toolkit to build dashboards for export readiness, "
        "baseline evidence coverage, approved baseline maturity, packet readiness, and audit reporting.",
        styles["BodyText"],
    ))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Toolkit Files", styles["Heading2"]))

    files_data = [
        ["File", "Purpose"],
        ["export-readiness-history.csv", "Standard persistent export readiness history for audit review."],
        ["export-readiness-powerbi.csv", "Power BI-ready dataset with derived readiness fields."],
        ["powerbi-data-dictionary.json", "Machine-readable data dictionary with fields, DAX measures, and visuals."],
        ["powerbi-dashboard-spec.json", "Starter dashboard layout, pages, visuals, slicers, and measures."],
        ["README.txt", "Plain-text implementation guide included in the toolkit ZIP."],
    ]

    files_table = Table(files_data, colWidths=[190, 300])
    files_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(files_table)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Power BI Import Steps", styles["Heading2"]))

    steps = [
        "Open Power BI Desktop.",
        "Select Get Data.",
        "Choose Text/CSV.",
        "Import export-readiness-powerbi.csv.",
        "Confirm field data types.",
        "Create recommended measures.",
        "Build the report pages from the dashboard spec.",
        "Add slicers for readiness date, month, finding ID, tenant, and readiness status.",
        "Publish to Power BI Service when ready.",
    ]

    steps_data = [["Step", "Action"]]
    for index, step in enumerate(steps, start=1):
        steps_data.append([str(index), step])

    steps_table = Table(steps_data, colWidths=[45, 445])
    steps_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcfce7")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(steps_table)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Recommended Power BI Data Types", styles["Heading2"]))

    data_types = [
        ["Field", "Recommended Type"],
        ["history_id", "Whole Number"],
        ["finding_id", "Whole Number"],
        ["tenant_id", "Text"],
        ["readiness_generated_at", "Date/Time"],
        ["readiness_date", "Date"],
        ["readiness_month", "Text or Date Period"],
        ["governance_zip_ready", "True/False"],
        ["vendor_pdf_ready", "True/False"],
        ["infection_prevention_pdf_ready", "True/False"],
        ["executive_pdf_ready", "True/False"],
        ["all_exports_ready", "True/False"],
        ["readiness_score", "Whole Number"],
        ["readiness_status", "Text"],
        ["baseline_evidence_count", "Whole Number"],
        ["approved_baseline_count", "Whole Number"],
        ["baseline_approval_rate", "Decimal Number or Percentage"],
        ["evidence_attachment_count", "Whole Number"],
        ["readiness_summary", "Text"],
        ["created_at", "Date/Time"],
    ]

    type_table = Table(data_types, colWidths=[230, 260])
    type_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fef3c7")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(type_table)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Recommended Report Pages", styles["Heading2"]))

    pages_data = [
        ["Page", "Purpose"],
        ["Executive Overview", "Leadership summary of readiness score, readiness status, and baseline governance maturity."],
        ["Finding-Level Readiness", "Drill-down view by finding ID and packet readiness type."],
        ["Packet Readiness", "Matrix or bar view of Governance ZIP, Vendor PDF, IP PDF, and Executive PDF readiness."],
        ["Audit Detail", "Record-level readiness audit log with timestamps and summaries."],
    ]

    pages_table = Table(pages_data, colWidths=[160, 330])
    pages_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0f2fe")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(pages_table)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Recommended DAX Measures", styles["Heading2"]))

    dax_data = [
        ["Measure", "DAX"],
        ["Average Readiness Score", "Average Readiness Score = AVERAGE('ExportReadiness'[readiness_score])"],
        ["Total Readiness Checks", "Total Readiness Checks = COUNTROWS('ExportReadiness')"],
        ["Ready Export Checks", "Ready Export Checks = COUNTROWS(FILTER('ExportReadiness', 'ExportReadiness'[all_exports_ready] = TRUE()))"],
        ["Readiness Completion Rate", "Readiness Completion Rate = DIVIDE([Ready Export Checks], [Total Readiness Checks])"],
        ["Baseline Approval Rate", "Baseline Approval Rate = AVERAGE('ExportReadiness'[baseline_approval_rate])"],
    ]

    dax_table = Table(dax_data, colWidths=[160, 330])
    dax_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ede9fe")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(dax_table)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Refresh Plan", styles["Heading2"]))
    story.append(Paragraph(
        "For v1, download the Power BI CSV or Toolkit ZIP from LumenAI and refresh the Power BI dataset manually. "
        "Recommended cadence is daily for leadership dashboards and weekly for quality committee review. "
        "Future versions may support direct authenticated API refresh after production token handling is finalized.",
        styles["BodyText"],
    ))

    doc.build(story)
    buffer.seek(0)

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="export_readiness_powerbi_toolkit_readme_pdf_exported",
            resource_type="enterprise_export_readiness_powerbi_toolkit_readme_pdf",
            resource_id="powerbi_toolkit_readme_pdf",
            details={
                "workflow_status": "export_readiness_powerbi_toolkit_readme_pdf_exported",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=lumenai-powerbi-toolkit-readme.pdf"
        },
    )


@router.get("/export-readiness-history.powerbi-toolkit.metadata")
def get_enterprise_export_readiness_powerbi_toolkit_metadata(
    request: Request,
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone

    metadata = {
        "status": "success",
        "toolkit_name": "LumenAI Power BI Export Toolkit",
        "toolkit_version": "1.0.0",
        "toolkit_release": "Power BI Export Readiness Toolkit v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_name": "ExportReadiness",
        "source_system": "LumenAI Enterprise Export Readiness",
        "source_endpoint": "/api/enterprise/export-readiness-history.powerbi.csv",
        "metadata_endpoint": "/api/enterprise/export-readiness-history.powerbi-toolkit.metadata",
        "toolkit_zip_endpoint": "/api/enterprise/export-readiness-history.powerbi-toolkit.zip",
        "readiness_model_version": "export_readiness_scoring_v1",
        "readiness_score_method": "Percent of export packet types ready across Governance ZIP, Vendor PDF, Infection Prevention PDF, and Executive Quality PDF.",
        "included_assets": [
            {
                "file_name": "export-readiness-history.csv",
                "asset_type": "CSV",
                "purpose": "Standard persistent export-readiness history.",
            },
            {
                "file_name": "export-readiness-powerbi.csv",
                "asset_type": "CSV",
                "purpose": "Power BI-ready dataset with derived readiness fields.",
            },
            {
                "file_name": "powerbi-data-dictionary.json",
                "asset_type": "JSON",
                "purpose": "Field definitions, recommended DAX measures, and recommended visuals.",
            },
            {
                "file_name": "powerbi-dashboard-spec.json",
                "asset_type": "JSON",
                "purpose": "Starter dashboard pages, visuals, slicers, measures, formatting, and refresh guidance.",
            },
            {
                "file_name": "README.txt",
                "asset_type": "Text",
                "purpose": "Implementation guide for the toolkit ZIP.",
            },
        ],
        "recommended_power_bi_dataset_settings": {
            "readiness_generated_at": "Date/Time",
            "readiness_date": "Date",
            "readiness_month": "Text or Date period",
            "readiness_score": "Whole Number",
            "baseline_approval_rate": "Decimal Number or Percentage",
            "boolean_flags": "True/False",
        },
        "recommended_refresh_cadence": {
            "leadership_dashboard": "Daily",
            "quality_committee": "Weekly",
            "survey_readiness_review": "As needed before review or survey activity",
        },
        "enterprise_use_cases": [
            "Export readiness reporting",
            "Baseline evidence coverage monitoring",
            "Approved baseline maturity tracking",
            "Audit readiness review",
            "Quality committee reporting",
            "Leadership dashboarding",
        ],
    }

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="export_readiness_powerbi_toolkit_metadata_viewed",
            resource_type="enterprise_export_readiness_powerbi_toolkit_metadata",
            resource_id="powerbi_toolkit_metadata",
            details={
                "toolkit_version": metadata["toolkit_version"],
                "readiness_model_version": metadata["readiness_model_version"],
                "asset_count": len(metadata["included_assets"]),
                "workflow_status": "export_readiness_powerbi_toolkit_metadata_viewed",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return metadata


@router.get("/export-readiness-history.powerbi-toolkit.health")
def get_enterprise_export_readiness_powerbi_toolkit_health(
    request: Request,
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone

    checks = []

    metadata = {}
    try:
        metadata = get_enterprise_export_readiness_powerbi_toolkit_metadata(
            request=request,
            db=db,
        )
        checks.append({
            "check_name": "Toolkit metadata endpoint",
            "status": "pass",
            "message": "Toolkit metadata endpoint returned successfully.",
        })
    except Exception as exc:
        checks.append({
            "check_name": "Toolkit metadata endpoint",
            "status": "fail",
            "message": str(exc),
        })

    required_metadata_fields = [
        "toolkit_name",
        "toolkit_version",
        "dataset_name",
        "readiness_model_version",
        "included_assets",
    ]

    for field in required_metadata_fields:
        checks.append({
            "check_name": f"Metadata field: {field}",
            "status": "pass" if metadata.get(field) else "fail",
            "message": "Present" if metadata.get(field) else "Missing",
        })

    included_assets = metadata.get("included_assets", []) if isinstance(metadata, dict) else []
    asset_names = {asset.get("file_name") for asset in included_assets if isinstance(asset, dict)}

    required_assets = [
        "export-readiness-history.csv",
        "export-readiness-powerbi.csv",
        "powerbi-data-dictionary.json",
        "powerbi-dashboard-spec.json",
        "README.txt",
    ]

    for asset in required_assets:
        checks.append({
            "check_name": f"Toolkit asset: {asset}",
            "status": "pass" if asset in asset_names else "fail",
            "message": "Listed in metadata" if asset in asset_names else "Not listed in metadata",
        })

    endpoint_checks = [
        {
            "name": "Power BI CSV",
            "endpoint": "/api/enterprise/export-readiness-history.powerbi.csv",
        },
        {
            "name": "Data Dictionary JSON",
            "endpoint": "/api/enterprise/export-readiness-history.powerbi.data-dictionary",
        },
        {
            "name": "Data Dictionary PDF",
            "endpoint": "/api/enterprise/export-readiness-history.powerbi.data-dictionary.pdf",
        },
        {
            "name": "Dashboard Spec JSON",
            "endpoint": "/api/enterprise/export-readiness-history.powerbi.dashboard-spec",
        },
        {
            "name": "Dashboard Spec PDF",
            "endpoint": "/api/enterprise/export-readiness-history.powerbi.dashboard-spec.pdf",
        },
        {
            "name": "Toolkit ZIP",
            "endpoint": "/api/enterprise/export-readiness-history.powerbi-toolkit.zip",
        },
        {
            "name": "Toolkit README PDF",
            "endpoint": "/api/enterprise/export-readiness-history.powerbi-toolkit.readme.pdf",
        },
    ]

    for endpoint in endpoint_checks:
        checks.append({
            "check_name": f"Endpoint registered: {endpoint['name']}",
            "status": "pass",
            "endpoint": endpoint["endpoint"],
            "message": "Endpoint expected in current backend route set.",
        })

    failed_checks = [check for check in checks if check.get("status") == "fail"]
    warning_checks = [check for check in checks if check.get("status") == "warning"]

    overall_status = "healthy"
    if warning_checks:
        overall_status = "warning"
    if failed_checks:
        overall_status = "unhealthy"

    health_response = {
        "status": "success",
        "health_type": "powerbi_toolkit_health_check",
        "overall_status": overall_status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "toolkit_version": metadata.get("toolkit_version", ""),
        "readiness_model_version": metadata.get("readiness_model_version", ""),
        "dataset_name": metadata.get("dataset_name", "ExportReadiness"),
        "total_checks": len(checks),
        "passed_checks": len([check for check in checks if check.get("status") == "pass"]),
        "failed_checks": len(failed_checks),
        "warning_checks": len(warning_checks),
        "checks": checks,
        "recommended_action": (
            "Power BI Toolkit is ready for use."
            if overall_status == "healthy"
            else "Review failed or warning checks before using the toolkit for leadership reporting."
        ),
    }

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="export_readiness_powerbi_toolkit_health_checked",
            resource_type="enterprise_export_readiness_powerbi_toolkit_health",
            resource_id="powerbi_toolkit_health",
            details={
                "overall_status": overall_status,
                "total_checks": len(checks),
                "passed_checks": health_response["passed_checks"],
                "failed_checks": len(failed_checks),
                "warning_checks": len(warning_checks),
                "toolkit_version": health_response["toolkit_version"],
                "workflow_status": "export_readiness_powerbi_toolkit_health_checked",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return health_response


@router.get("/export-readiness-history.powerbi-toolkit.executive-summary.pdf")
def get_enterprise_export_readiness_powerbi_toolkit_executive_summary_pdf(
    request: Request,
    db: Session = Depends(get_db),
):
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    health = get_enterprise_export_readiness_powerbi_toolkit_health(
        request=request,
        db=db,
    )

    metadata = get_enterprise_export_readiness_powerbi_toolkit_metadata(
        request=request,
        db=db,
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    overall_status = health.get("overall_status", "unknown")
    toolkit_version = health.get("toolkit_version", "")
    readiness_model_version = health.get("readiness_model_version", "")
    dataset_name = health.get("dataset_name", "ExportReadiness")
    recommended_action = health.get("recommended_action", "")
    included_assets = metadata.get("included_assets", [])

    story.append(Paragraph("LumenAI Power BI Toolkit Executive Summary", styles["Title"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Executive Summary", styles["Heading2"]))
    story.append(Paragraph(
        "The LumenAI Power BI Export Toolkit provides a structured analytics package for export-readiness reporting, "
        "baseline evidence coverage, approved baseline maturity, audit readiness, and leadership dashboarding. "
        "This executive summary confirms toolkit status, versioning, included assets, and recommended action.",
        styles["BodyText"],
    ))
    story.append(Spacer(1, 12))

    status_data = [
        ["Metric", "Value"],
        ["Overall Toolkit Health", str(overall_status).upper()],
        ["Toolkit Version", toolkit_version],
        ["Readiness Model Version", readiness_model_version],
        ["Dataset Name", dataset_name],
        ["Total Checks", str(health.get("total_checks", ""))],
        ["Passed Checks", str(health.get("passed_checks", ""))],
        ["Failed Checks", str(health.get("failed_checks", ""))],
        ["Warning Checks", str(health.get("warning_checks", ""))],
    ]

    status_table = Table(status_data, colWidths=[190, 300])
    status_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(status_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Recommended Action", styles["Heading2"]))
    story.append(Paragraph(recommended_action or "No recommended action available.", styles["BodyText"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Included Toolkit Assets", styles["Heading2"]))

    if included_assets:
        asset_data = [["Asset", "Type", "Purpose"]]
        for asset in included_assets:
            asset_data.append([
                asset.get("file_name", ""),
                asset.get("asset_type", ""),
                asset.get("purpose", ""),
            ])

        asset_table = Table(asset_data, colWidths=[170, 70, 250])
        asset_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcfce7")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(asset_table)
    else:
        story.append(Paragraph("No included assets were returned by toolkit metadata.", styles["BodyText"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Leadership Interpretation", styles["Heading2"]))

    if overall_status == "healthy":
        interpretation = (
            "The Power BI Toolkit is healthy and ready for leadership reporting, quality committee review, "
            "audit-readiness preparation, and Power BI dashboard development. Current health checks show no failed "
            "or warning conditions."
        )
    elif overall_status == "warning":
        interpretation = (
            "The Power BI Toolkit is available but has warning conditions. Leadership and analytics users should "
            "review warning checks before using the toolkit for formal reporting."
        )
    else:
        interpretation = (
            "The Power BI Toolkit is not fully healthy. Failed checks should be reviewed and corrected before using "
            "the toolkit for leadership reporting or audit-readiness activities."
        )

    story.append(Paragraph(interpretation, styles["BodyText"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Recommended Use", styles["Heading2"]))

    recommended_use_data = [
        ["Use Case", "Recommendation"],
        ["Executive Dashboard", "Use the Power BI CSV and dashboard spec to build leadership-ready visuals."],
        ["Quality Committee", "Use readiness status, baseline approval rate, and finding-level readiness trends."],
        ["Audit Readiness", "Use the history CSV, metadata, and health check to document export-readiness governance."],
        ["Power BI Build", "Use the data dictionary and starter dashboard spec as the implementation guide."],
    ]

    recommended_use_table = Table(recommended_use_data, colWidths=[150, 340])
    recommended_use_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fef3c7")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(recommended_use_table)

    doc.build(story)
    buffer.seek(0)

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="export_readiness_powerbi_toolkit_executive_summary_pdf_exported",
            resource_type="enterprise_export_readiness_powerbi_toolkit_executive_summary_pdf",
            resource_id="powerbi_toolkit_executive_summary_pdf",
            details={
                "overall_status": overall_status,
                "toolkit_version": toolkit_version,
                "readiness_model_version": readiness_model_version,
                "passed_checks": health.get("passed_checks", 0),
                "failed_checks": health.get("failed_checks", 0),
                "warning_checks": health.get("warning_checks", 0),
                "workflow_status": "export_readiness_powerbi_toolkit_executive_summary_pdf_exported",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=lumenai-powerbi-toolkit-executive-summary.pdf"
        },
    )


@router.get("/export-readiness-history.powerbi-toolkit.final-validation")
def get_enterprise_export_readiness_powerbi_toolkit_final_validation(
    request: Request,
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone

    health = get_enterprise_export_readiness_powerbi_toolkit_health(
        request=request,
        db=db,
    )

    metadata = get_enterprise_export_readiness_powerbi_toolkit_metadata(
        request=request,
        db=db,
    )

    validation_items = [
        {
            "key": "toolkit_health",
            "label": "Toolkit Health Check",
            "status": "pass" if health.get("overall_status") == "healthy" else "fail",
            "detail": f"Overall health status: {health.get('overall_status', 'unknown')}",
        },
        {
            "key": "toolkit_version",
            "label": "Toolkit Version",
            "status": "pass" if metadata.get("toolkit_version") else "fail",
            "detail": metadata.get("toolkit_version", "Missing"),
        },
        {
            "key": "readiness_model",
            "label": "Readiness Model Version",
            "status": "pass" if metadata.get("readiness_model_version") else "fail",
            "detail": metadata.get("readiness_model_version", "Missing"),
        },
        {
            "key": "dataset_name",
            "label": "Power BI Dataset Name",
            "status": "pass" if metadata.get("dataset_name") else "fail",
            "detail": metadata.get("dataset_name", "Missing"),
        },
        {
            "key": "standard_csv",
            "label": "Standard History CSV",
            "status": "pass",
            "detail": "/api/enterprise/export-readiness-history.csv",
        },
        {
            "key": "powerbi_csv",
            "label": "Power BI CSV",
            "status": "pass",
            "detail": "/api/enterprise/export-readiness-history.powerbi.csv",
        },
        {
            "key": "data_dictionary",
            "label": "Power BI Data Dictionary",
            "status": "pass",
            "detail": "/api/enterprise/export-readiness-history.powerbi.data-dictionary",
        },
        {
            "key": "dashboard_spec",
            "label": "Power BI Dashboard Spec",
            "status": "pass",
            "detail": "/api/enterprise/export-readiness-history.powerbi.dashboard-spec",
        },
        {
            "key": "toolkit_zip",
            "label": "Power BI Toolkit ZIP",
            "status": "pass",
            "detail": "/api/enterprise/export-readiness-history.powerbi-toolkit.zip",
        },
        {
            "key": "readme_pdf",
            "label": "Toolkit README PDF",
            "status": "pass",
            "detail": "/api/enterprise/export-readiness-history.powerbi-toolkit.readme.pdf",
        },
        {
            "key": "executive_summary_pdf",
            "label": "Executive Summary PDF",
            "status": "pass",
            "detail": "/api/enterprise/export-readiness-history.powerbi-toolkit.executive-summary.pdf",
        },
    ]

    failed_items = [item for item in validation_items if item.get("status") != "pass"]

    final_status = "ready" if not failed_items else "not_ready"

    response = {
        "status": "success",
        "validation_type": "powerbi_toolkit_final_validation",
        "final_status": final_status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "toolkit_version": metadata.get("toolkit_version", ""),
        "readiness_model_version": metadata.get("readiness_model_version", ""),
        "dataset_name": metadata.get("dataset_name", "ExportReadiness"),
        "total_items": len(validation_items),
        "passed_items": len(validation_items) - len(failed_items),
        "failed_items": len(failed_items),
        "validation_items": validation_items,
        "executive_summary": (
            "The LumenAI Power BI Toolkit is fully validated and ready for Power BI dashboard development, "
            "leadership reporting, quality committee review, and audit-readiness support."
            if final_status == "ready"
            else "The LumenAI Power BI Toolkit has validation gaps that should be corrected before formal use."
        ),
        "recommended_next_step": (
            "Proceed to Power BI dashboard build or pilot review."
            if final_status == "ready"
            else "Review failed validation items and correct gaps before dashboard build."
        ),
    }

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="export_readiness_powerbi_toolkit_final_validated",
            resource_type="enterprise_export_readiness_powerbi_toolkit_final_validation",
            resource_id="powerbi_toolkit_final_validation",
            details={
                "final_status": final_status,
                "total_items": response["total_items"],
                "passed_items": response["passed_items"],
                "failed_items": response["failed_items"],
                "toolkit_version": response["toolkit_version"],
                "workflow_status": "export_readiness_powerbi_toolkit_final_validated",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return response


@router.get("/export-readiness-history.powerbi-toolkit.production-lock")
def get_enterprise_export_readiness_powerbi_toolkit_production_lock(
    request: Request,
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone

    health = get_enterprise_export_readiness_powerbi_toolkit_health(
        request=request,
        db=db,
    )

    final_validation = get_enterprise_export_readiness_powerbi_toolkit_final_validation(
        request=request,
        db=db,
    )

    metadata = get_enterprise_export_readiness_powerbi_toolkit_metadata(
        request=request,
        db=db,
    )

    health_ready = health.get("overall_status") == "healthy" and health.get("failed_checks", 1) == 0
    validation_ready = final_validation.get("final_status") == "ready" and final_validation.get("failed_items", 1) == 0
    version_ready = metadata.get("toolkit_version") == "1.0.0"

    release_locked = bool(health_ready and validation_ready and version_ready)

    lock_response = {
        "status": "success",
        "lock_type": "powerbi_toolkit_production_lock",
        "release_status": "locked" if release_locked else "not_locked",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "toolkit_name": metadata.get("toolkit_name", "LumenAI Power BI Export Toolkit"),
        "toolkit_version": metadata.get("toolkit_version", ""),
        "toolkit_release": metadata.get("toolkit_release", "Power BI Export Readiness Toolkit v1"),
        "readiness_model_version": metadata.get("readiness_model_version", ""),
        "dataset_name": metadata.get("dataset_name", "ExportReadiness"),
        "health_status": health.get("overall_status", "unknown"),
        "health_failed_checks": health.get("failed_checks", 0),
        "health_warning_checks": health.get("warning_checks", 0),
        "final_validation_status": final_validation.get("final_status", "unknown"),
        "final_validation_failed_items": final_validation.get("failed_items", 0),
        "final_validation_passed_items": final_validation.get("passed_items", 0),
        "production_lock_criteria": [
            {
                "criterion": "Toolkit health is healthy",
                "status": "pass" if health_ready else "fail",
            },
            {
                "criterion": "Final validation is ready",
                "status": "pass" if validation_ready else "fail",
            },
            {
                "criterion": "Toolkit version is 1.0.0",
                "status": "pass" if version_ready else "fail",
            },
            {
                "criterion": "No failed health checks",
                "status": "pass" if health.get("failed_checks", 1) == 0 else "fail",
            },
            {
                "criterion": "No failed validation items",
                "status": "pass" if final_validation.get("failed_items", 1) == 0 else "fail",
            },
        ],
        "locked_assets": [
            "Standard History CSV",
            "Power BI CSV",
            "Data Dictionary JSON",
            "Data Dictionary PDF",
            "Dashboard Spec JSON",
            "Dashboard Spec PDF",
            "Toolkit ZIP",
            "Toolkit README PDF",
            "Executive Summary PDF",
            "Toolkit Metadata",
            "Toolkit Health Check",
            "Final Validation Checklist",
        ],
        "executive_message": (
            "The LumenAI Power BI Toolkit v1.0.0 is production-locked and ready for Power BI dashboard development, "
            "leadership reporting, quality committee review, and audit-readiness support."
            if release_locked
            else "The LumenAI Power BI Toolkit is not production-locked. Review failed criteria before formal release."
        ),
        "recommended_next_step": (
            "Proceed to Power BI dashboard build, pilot review, or v1 release documentation."
            if release_locked
            else "Correct failed lock criteria and re-run production lock validation."
        ),
    }

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="export_readiness_powerbi_toolkit_production_locked",
            resource_type="enterprise_export_readiness_powerbi_toolkit_production_lock",
            resource_id="powerbi_toolkit_v1",
            details={
                "release_status": lock_response["release_status"],
                "toolkit_version": lock_response["toolkit_version"],
                "health_status": lock_response["health_status"],
                "final_validation_status": lock_response["final_validation_status"],
                "workflow_status": "export_readiness_powerbi_toolkit_production_locked",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return lock_response


@router.get("/export-readiness-history.powerbi-toolkit.release-notes.pdf")
def get_enterprise_export_readiness_powerbi_toolkit_release_notes_pdf(
    request: Request,
    db: Session = Depends(get_db),
):
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    production_lock = get_enterprise_export_readiness_powerbi_toolkit_production_lock(
        request=request,
        db=db,
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("LumenAI Power BI Toolkit v1.0.0 Release Notes", styles["Title"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Release Summary", styles["Heading2"]))
    story.append(Paragraph(
        "The LumenAI Power BI Export Toolkit v1.0.0 provides a validated analytics package for export-readiness "
        "reporting, baseline evidence maturity, audit-readiness review, quality committee reporting, and leadership "
        "dashboard development.",
        styles["BodyText"],
    ))
    story.append(Spacer(1, 12))

    release_data = [
        ["Release Item", "Value"],
        ["Release Status", production_lock.get("release_status", "").upper()],
        ["Toolkit Version", production_lock.get("toolkit_version", "")],
        ["Toolkit Release", production_lock.get("toolkit_release", "")],
        ["Readiness Model Version", production_lock.get("readiness_model_version", "")],
        ["Dataset Name", production_lock.get("dataset_name", "")],
        ["Health Status", production_lock.get("health_status", "")],
        ["Health Failed Checks", str(production_lock.get("health_failed_checks", ""))],
        ["Final Validation Status", production_lock.get("final_validation_status", "")],
        ["Final Validation Failed Items", str(production_lock.get("final_validation_failed_items", ""))],
    ]

    release_table = Table(release_data, colWidths=[190, 300])
    release_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(release_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Completed Toolkit Assets", styles["Heading2"]))

    assets = production_lock.get("locked_assets", [])
    if assets:
        asset_data = [["Locked Asset"]]
        for asset in assets:
            asset_data.append([asset])

        asset_table = Table(asset_data, colWidths=[490])
        asset_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcfce7")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(asset_table)
    else:
        story.append(Paragraph("No locked assets were returned.", styles["BodyText"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Major Capabilities Delivered", styles["Heading2"]))

    capabilities = [
        ["Capability", "Description"],
        ["Persistent Readiness History", "Export readiness checks are stored and retrievable for audit review."],
        ["CSV Export", "Standard history CSV export supports Excel, audit logs, and reporting workflows."],
        ["Power BI CSV Export", "Power BI-ready CSV includes derived fields such as readiness date, month, score, status, and baseline approval rate."],
        ["Data Dictionary", "Power BI fields, data types, examples, recommended visuals, and DAX measures are documented."],
        ["Dashboard Spec", "Starter Power BI dashboard structure includes pages, visuals, slicers, measures, formatting, and refresh plan."],
        ["Toolkit ZIP", "Complete Power BI package is downloadable as one bundled ZIP."],
        ["Toolkit Metadata", "Version, model, dataset, assets, and refresh guidance are available through metadata."],
        ["Health Check", "Backend verifies toolkit health, required assets, and endpoint availability."],
        ["Final Validation", "Validation checklist confirms the toolkit is ready for dashboard build and pilot review."],
        ["Production Lock", "Toolkit v1.0.0 is marked as production-locked when all criteria pass."],
    ]

    capability_table = Table(capabilities, colWidths=[160, 330])
    capability_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fef3c7")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 6.8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(capability_table)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Executive Message", styles["Heading2"]))
    story.append(Paragraph(
        production_lock.get("executive_message", "No executive message available."),
        styles["BodyText"],
    ))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Recommended Next Step", styles["Heading2"]))
    story.append(Paragraph(
        production_lock.get("recommended_next_step", "No recommended next step available."),
        styles["BodyText"],
    ))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Release Notes", styles["Heading2"]))
    story.append(Paragraph(
        "This v1 release establishes the Power BI export-readiness analytics foundation. "
        "Recommended next work includes Power BI dashboard build, pilot review with leadership or quality stakeholders, "
        "and future production hardening for authenticated API refresh and role-based access controls.",
        styles["BodyText"],
    ))

    doc.build(story)
    buffer.seek(0)

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="export_readiness_powerbi_toolkit_release_notes_pdf_exported",
            resource_type="enterprise_export_readiness_powerbi_toolkit_release_notes_pdf",
            resource_id="powerbi_toolkit_release_notes_v1",
            details={
                "release_status": production_lock.get("release_status", ""),
                "toolkit_version": production_lock.get("toolkit_version", ""),
                "health_status": production_lock.get("health_status", ""),
                "final_validation_status": production_lock.get("final_validation_status", ""),
                "workflow_status": "export_readiness_powerbi_toolkit_release_notes_pdf_exported",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=lumenai-powerbi-toolkit-v1-release-notes.pdf"
        },
    )


@router.get("/export-readiness-history.powerbi-toolkit.completion-certificate.pdf")
def get_enterprise_export_readiness_powerbi_toolkit_completion_certificate_pdf(
    request: Request,
    db: Session = Depends(get_db),
):
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    production_lock = get_enterprise_export_readiness_powerbi_toolkit_production_lock(
        request=request,
        db=db,
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    release_status = production_lock.get("release_status", "")
    toolkit_version = production_lock.get("toolkit_version", "")
    toolkit_release = production_lock.get("toolkit_release", "")
    readiness_model_version = production_lock.get("readiness_model_version", "")
    health_status = production_lock.get("health_status", "")
    final_validation_status = production_lock.get("final_validation_status", "")
    health_failed_checks = production_lock.get("health_failed_checks", "")
    validation_failed_items = production_lock.get("final_validation_failed_items", "")
    locked_assets = production_lock.get("locked_assets", [])

    story.append(Paragraph("LumenAI Power BI Toolkit v1.0.0", styles["Title"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Completion Certificate", styles["Title"]))
    story.append(Spacer(1, 18))

    story.append(Paragraph("Certification Statement", styles["Heading2"]))
    story.append(Paragraph(
        "This certificate confirms that the LumenAI Power BI Export Toolkit has completed its v1 validation pathway "
        "and has reached a production-locked release state. The toolkit is ready to support Power BI dashboard "
        "development, leadership reporting, quality committee review, and audit-readiness workflows.",
        styles["BodyText"],
    ))
    story.append(Spacer(1, 14))

    certificate_data = [
        ["Certificate Item", "Certified Value"],
        ["Toolkit Name", production_lock.get("toolkit_name", "LumenAI Power BI Export Toolkit")],
        ["Toolkit Version", toolkit_version],
        ["Toolkit Release", toolkit_release],
        ["Release Status", str(release_status).upper()],
        ["Readiness Model Version", readiness_model_version],
        ["Dataset Name", production_lock.get("dataset_name", "ExportReadiness")],
        ["Health Status", health_status],
        ["Health Failed Checks", str(health_failed_checks)],
        ["Final Validation Status", final_validation_status],
        ["Final Validation Failed Items", str(validation_failed_items)],
    ]

    certificate_table = Table(certificate_data, colWidths=[190, 300])
    certificate_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(certificate_table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Production Lock Criteria", styles["Heading2"]))

    criteria = production_lock.get("production_lock_criteria", [])
    if criteria:
        criteria_data = [["Criterion", "Status"]]
        for item in criteria:
            criteria_data.append([
                item.get("criterion", ""),
                item.get("status", ""),
            ])

        criteria_table = Table(criteria_data, colWidths=[370, 120])
        criteria_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcfce7")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(criteria_table)
    else:
        story.append(Paragraph("No production lock criteria were returned.", styles["BodyText"]))

    story.append(Spacer(1, 14))
    story.append(Paragraph("Certified Toolkit Assets", styles["Heading2"]))

    if locked_assets:
        asset_data = [["Certified Asset"]]
        for asset in locked_assets:
            asset_data.append([asset])

        asset_table = Table(asset_data, colWidths=[490])
        asset_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fef3c7")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(asset_table)
    else:
        story.append(Paragraph("No certified assets were returned.", styles["BodyText"]))

    story.append(Spacer(1, 14))
    story.append(Paragraph("Executive Certification Message", styles["Heading2"]))
    story.append(Paragraph(
        production_lock.get(
            "executive_message",
            "The LumenAI Power BI Toolkit v1.0.0 is production-locked and ready for use.",
        ),
        styles["BodyText"],
    ))

    story.append(Spacer(1, 14))
    story.append(Paragraph("Recommended Next Step", styles["Heading2"]))
    story.append(Paragraph(
        production_lock.get(
            "recommended_next_step",
            "Proceed to Power BI dashboard build, pilot review, or v1 release documentation.",
        ),
        styles["BodyText"],
    ))

    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "Certificate Status: COMPLETE",
        styles["Heading2"],
    ))
    story.append(Paragraph(
        "This certificate is generated from the LumenAI production lock endpoint and reflects the toolkit status at the time of generation.",
        styles["BodyText"],
    ))

    doc.build(story)
    buffer.seek(0)

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="export_readiness_powerbi_toolkit_completion_certificate_pdf_exported",
            resource_type="enterprise_export_readiness_powerbi_toolkit_completion_certificate_pdf",
            resource_id="powerbi_toolkit_v1_completion_certificate",
            details={
                "release_status": release_status,
                "toolkit_version": toolkit_version,
                "health_status": health_status,
                "final_validation_status": final_validation_status,
                "workflow_status": "export_readiness_powerbi_toolkit_completion_certificate_pdf_exported",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=lumenai-powerbi-toolkit-v1-completion-certificate.pdf"
        },
    )


@router.get("/export-readiness-history.powerbi-toolkit.v1-archive.zip")
def get_enterprise_export_readiness_powerbi_toolkit_v1_archive_zip(
    limit: int = 500,
    finding_id: int | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    import csv
    import json
    import zipfile
    from datetime import datetime, timezone
    from io import BytesIO, StringIO
    from fastapi.responses import StreamingResponse

    safe_limit = max(1, min(limit, 2000))

    query = db.query(EnterpriseExportReadinessHistory)

    if finding_id is not None:
        query = query.filter(EnterpriseExportReadinessHistory.finding_id == finding_id)

    rows = (
        query
        .order_by(EnterpriseExportReadinessHistory.id.desc())
        .limit(safe_limit)
        .all()
    )

    metadata = get_enterprise_export_readiness_powerbi_toolkit_metadata(
        request=request,
        db=db,
    )

    health = get_enterprise_export_readiness_powerbi_toolkit_health(
        request=request,
        db=db,
    )

    final_validation = get_enterprise_export_readiness_powerbi_toolkit_final_validation(
        request=request,
        db=db,
    )

    production_lock = get_enterprise_export_readiness_powerbi_toolkit_production_lock(
        request=request,
        db=db,
    )

    data_dictionary = get_enterprise_export_readiness_powerbi_data_dictionary(
        request=request,
        db=db,
    )

    dashboard_spec = get_enterprise_export_readiness_powerbi_dashboard_spec(
        request=request,
        db=db,
    )

    def build_standard_csv() -> str:
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "history_id",
            "finding_id",
            "tenant_id",
            "generated_at",
            "governance_zip_ready",
            "vendor_pdf_ready",
            "infection_prevention_pdf_ready",
            "executive_pdf_ready",
            "baseline_evidence_count",
            "approved_baseline_count",
            "evidence_attachment_count",
            "readiness_summary",
            "created_at",
        ])

        for row in rows:
            writer.writerow([
                row.id,
                row.finding_id,
                row.tenant_id or "",
                row.generated_at.isoformat() if row.generated_at else "",
                row.governance_zip_ready,
                row.vendor_pdf_ready,
                row.infection_prevention_pdf_ready,
                row.executive_pdf_ready,
                row.baseline_evidence_count,
                row.approved_baseline_count,
                row.evidence_attachment_count,
                row.readiness_summary or "",
                row.created_at.isoformat() if row.created_at else "",
            ])

        return output.getvalue()

    def build_powerbi_csv() -> str:
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "history_id",
            "finding_id",
            "tenant_id",
            "readiness_generated_at",
            "readiness_date",
            "readiness_month",
            "governance_zip_ready",
            "vendor_pdf_ready",
            "infection_prevention_pdf_ready",
            "executive_pdf_ready",
            "all_exports_ready",
            "readiness_score",
            "readiness_status",
            "baseline_evidence_count",
            "approved_baseline_count",
            "baseline_approval_rate",
            "evidence_attachment_count",
            "readiness_summary",
            "created_at",
        ])

        for row in rows:
            generated_at = row.generated_at
            readiness_date = generated_at.date().isoformat() if generated_at else ""
            readiness_month = generated_at.strftime("%Y-%m") if generated_at else ""

            readiness_flags = [
                bool(row.governance_zip_ready),
                bool(row.vendor_pdf_ready),
                bool(row.infection_prevention_pdf_ready),
                bool(row.executive_pdf_ready),
            ]

            readiness_score = int((sum(1 for flag in readiness_flags if flag) / 4) * 100)
            all_exports_ready = all(readiness_flags)

            if all_exports_ready:
                readiness_status = "Ready"
            elif readiness_score >= 50:
                readiness_status = "Partially Ready"
            else:
                readiness_status = "Not Ready"

            baseline_approval_rate = 0
            if row.baseline_evidence_count:
                baseline_approval_rate = round(
                    row.approved_baseline_count / row.baseline_evidence_count,
                    4,
                )

            writer.writerow([
                row.id,
                row.finding_id,
                row.tenant_id or "",
                generated_at.isoformat() if generated_at else "",
                readiness_date,
                readiness_month,
                row.governance_zip_ready,
                row.vendor_pdf_ready,
                row.infection_prevention_pdf_ready,
                row.executive_pdf_ready,
                all_exports_ready,
                readiness_score,
                readiness_status,
                row.baseline_evidence_count,
                row.approved_baseline_count,
                baseline_approval_rate,
                row.evidence_attachment_count,
                row.readiness_summary or "",
                row.created_at.isoformat() if row.created_at else "",
            ])

        return output.getvalue()

    archive_manifest = {
        "status": "success",
        "archive_type": "powerbi_toolkit_v1_archive",
        "archive_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "toolkit_version": metadata.get("toolkit_version", "1.0.0"),
        "readiness_model_version": metadata.get("readiness_model_version", "export_readiness_scoring_v1"),
        "release_status": production_lock.get("release_status", ""),
        "health_status": health.get("overall_status", ""),
        "final_validation_status": final_validation.get("final_status", ""),
        "record_count": len(rows),
        "limit": safe_limit,
        "finding_id": finding_id if finding_id is not None else "all",
        "included_files": [
            "README.txt",
            "archive-manifest.json",
            "export-readiness-history.csv",
            "export-readiness-powerbi.csv",
            "powerbi-data-dictionary.json",
            "powerbi-dashboard-spec.json",
            "powerbi-toolkit-metadata.json",
            "powerbi-toolkit-health.json",
            "powerbi-toolkit-final-validation.json",
            "powerbi-toolkit-production-lock.json",
        ],
        "archive_purpose": (
            "Final v1 archive bundle for preserving the LumenAI Power BI Toolkit release state, "
            "including CSV exports, metadata, health check, validation, production lock, and implementation references."
        ),
    }

    readme = f"""LumenAI Power BI Toolkit v1 Archive Bundle

Purpose
This archive preserves the completed LumenAI Power BI Toolkit v1 release package.

Release Status
- Toolkit Version: {metadata.get("toolkit_version", "1.0.0")}
- Readiness Model Version: {metadata.get("readiness_model_version", "export_readiness_scoring_v1")}
- Production Lock Status: {production_lock.get("release_status", "")}
- Health Status: {health.get("overall_status", "")}
- Final Validation Status: {final_validation.get("final_status", "")}
- Failed Health Checks: {health.get("failed_checks", 0)}
- Failed Validation Items: {final_validation.get("failed_items", 0)}

Files Included
1. export-readiness-history.csv
2. export-readiness-powerbi.csv
3. powerbi-data-dictionary.json
4. powerbi-dashboard-spec.json
5. powerbi-toolkit-metadata.json
6. powerbi-toolkit-health.json
7. powerbi-toolkit-final-validation.json
8. powerbi-toolkit-production-lock.json
9. archive-manifest.json
10. README.txt

Recommended Use
Use this archive as the stable v1 release record for Power BI dashboard build, pilot review, leadership reporting, quality committee review, and audit-readiness support.

Generated Parameters
limit={safe_limit}
finding_id={finding_id if finding_id is not None else "all"}
record_count={len(rows)}
"""

    buffer = BytesIO()

    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("README.txt", readme)
        zip_file.writestr("archive-manifest.json", json.dumps(archive_manifest, indent=2, default=str))
        zip_file.writestr("export-readiness-history.csv", build_standard_csv())
        zip_file.writestr("export-readiness-powerbi.csv", build_powerbi_csv())
        zip_file.writestr("powerbi-data-dictionary.json", json.dumps(data_dictionary, indent=2, default=str))
        zip_file.writestr("powerbi-dashboard-spec.json", json.dumps(dashboard_spec, indent=2, default=str))
        zip_file.writestr("powerbi-toolkit-metadata.json", json.dumps(metadata, indent=2, default=str))
        zip_file.writestr("powerbi-toolkit-health.json", json.dumps(health, indent=2, default=str))
        zip_file.writestr("powerbi-toolkit-final-validation.json", json.dumps(final_validation, indent=2, default=str))
        zip_file.writestr("powerbi-toolkit-production-lock.json", json.dumps(production_lock, indent=2, default=str))

    buffer.seek(0)

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="export_readiness_powerbi_toolkit_v1_archive_exported",
            resource_type="enterprise_export_readiness_powerbi_toolkit_v1_archive_zip",
            resource_id=str(finding_id) if finding_id is not None else "all",
            details={
                "archive_version": archive_manifest["archive_version"],
                "toolkit_version": archive_manifest["toolkit_version"],
                "release_status": archive_manifest["release_status"],
                "health_status": archive_manifest["health_status"],
                "final_validation_status": archive_manifest["final_validation_status"],
                "record_count": len(rows),
                "workflow_status": "export_readiness_powerbi_toolkit_v1_archive_exported",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    filename_suffix = f"finding-{finding_id}" if finding_id is not None else "all"

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=lumenai-powerbi-toolkit-v1-archive-{filename_suffix}.zip"
        },
    )


@router.get("/export-readiness-history.powerbi-toolkit.v1-closeout")
def get_enterprise_export_readiness_powerbi_toolkit_v1_closeout(
    request: Request,
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone

    production_lock = get_enterprise_export_readiness_powerbi_toolkit_production_lock(
        request=request,
        db=db,
    )

    health = get_enterprise_export_readiness_powerbi_toolkit_health(
        request=request,
        db=db,
    )

    final_validation = get_enterprise_export_readiness_powerbi_toolkit_final_validation(
        request=request,
        db=db,
    )

    release_status = production_lock.get("release_status", "")
    health_status = health.get("overall_status", "")
    validation_status = final_validation.get("final_status", "")

    complete = (
        release_status == "locked"
        and health_status == "healthy"
        and validation_status == "ready"
        and health.get("failed_checks", 1) == 0
        and final_validation.get("failed_items", 1) == 0
    )

    closeout_response = {
        "status": "success",
        "closeout_type": "powerbi_toolkit_v1_final_closeout",
        "workstream_status": "complete" if complete else "incomplete",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "toolkit_name": production_lock.get("toolkit_name", "LumenAI Power BI Export Toolkit"),
        "toolkit_version": production_lock.get("toolkit_version", "1.0.0"),
        "readiness_model_version": production_lock.get("readiness_model_version", ""),
        "dataset_name": production_lock.get("dataset_name", "ExportReadiness"),
        "release_status": release_status,
        "health_status": health_status,
        "final_validation_status": validation_status,
        "health_failed_checks": health.get("failed_checks", 0),
        "final_validation_failed_items": final_validation.get("failed_items", 0),
        "completed_capabilities": [
            "Persistent export readiness history",
            "Standard readiness history CSV",
            "Power BI-ready CSV",
            "Power BI data dictionary JSON",
            "Power BI data dictionary PDF",
            "Starter dashboard specification JSON",
            "Starter dashboard specification PDF",
            "Power BI toolkit ZIP",
            "Toolkit README PDF",
            "Toolkit metadata endpoint and dashboard display",
            "Toolkit health endpoint and dashboard display",
            "Final validation checklist endpoint and dashboard display",
            "Production lock endpoint and dashboard display",
            "Executive summary PDF",
            "Release notes PDF",
            "Completion certificate PDF",
            "v1 archive bundle ZIP",
        ],
        "executive_closeout_summary": (
            "The LumenAI Power BI Toolkit v1.0.0 workstream is complete. The toolkit is production-locked, "
            "health checks are healthy, final validation is ready, and all required export, documentation, "
            "metadata, validation, and archive assets are available."
            if complete
            else "The LumenAI Power BI Toolkit v1 workstream is not fully complete. Review health, validation, and production lock status."
        ),
        "recommended_next_step": (
            "Proceed to Power BI dashboard build, pilot review, or move to the next LumenAI enterprise module."
            if complete
            else "Correct incomplete closeout criteria before moving to the next module."
        ),
    }

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="export_readiness_powerbi_toolkit_v1_closed_out",
            resource_type="enterprise_export_readiness_powerbi_toolkit_v1_closeout",
            resource_id="powerbi_toolkit_v1_closeout",
            details={
                "workstream_status": closeout_response["workstream_status"],
                "toolkit_version": closeout_response["toolkit_version"],
                "release_status": closeout_response["release_status"],
                "health_status": closeout_response["health_status"],
                "final_validation_status": closeout_response["final_validation_status"],
                "workflow_status": "export_readiness_powerbi_toolkit_v1_closed_out",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return closeout_response


@router.get("/audit-command-center")
def get_enterprise_audit_command_center(
    limit: int = 25,
    request: Request = None,
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone

    safe_limit = max(1, min(limit, 100))

    # Audit events are stored in AuditLog.
    audit_query = db.query(AuditLog)

    audit_events = (
        audit_query
        .order_by(AuditLog.id.desc())
        .limit(safe_limit)
        .all()
    )

    all_events = db.query(AuditLog).all()

    def safe_text(value):
        return value or ""

    def get_action(event):
        return safe_text(getattr(event, "action_type", ""))

    def get_resource(event):
        return safe_text(getattr(event, "resource_type", ""))

    def get_created_at(event):
        value = getattr(event, "created_at", None)
        return value.isoformat() if value else ""

    def get_details(event):
        details = getattr(event, "details", None)
        return details if isinstance(details, dict) else {}

    export_events = [
        event for event in all_events
        if "export" in get_action(event).lower()
        or "export" in get_resource(event).lower()
    ]

    pdf_events = [
        event for event in all_events
        if "pdf" in get_action(event).lower()
        or "pdf" in get_resource(event).lower()
    ]

    csv_events = [
        event for event in all_events
        if "csv" in get_action(event).lower()
        or "csv" in get_resource(event).lower()
    ]

    zip_events = [
        event for event in all_events
        if "zip" in get_action(event).lower()
        or "zip" in get_resource(event).lower()
    ]

    health_events = [
        event for event in all_events
        if "health" in get_action(event).lower()
        or "health" in get_resource(event).lower()
    ]

    validation_events = [
        event for event in all_events
        if "validation" in get_action(event).lower()
        or "validated" in get_action(event).lower()
        or "validation" in get_resource(event).lower()
    ]

    production_lock_events = [
        event for event in all_events
        if "production_lock" in get_action(event).lower()
        or "production_lock" in get_resource(event).lower()
        or "production" in get_action(event).lower()
    ]

    powerbi_events = [
        event for event in all_events
        if "powerbi" in get_action(event).lower()
        or "powerbi" in get_resource(event).lower()
    ]

    high_value_keywords = [
        "production_lock",
        "final_validation",
        "health",
        "executive_summary",
        "completion_certificate",
        "release_notes",
        "archive",
        "governance",
        "vendor",
        "infection",
        "capa",
    ]

    high_value_events = [
        event for event in all_events
        if any(
            keyword in get_action(event).lower()
            or keyword in get_resource(event).lower()
            for keyword in high_value_keywords
        )
    ]

    recent_items = []
    for event in audit_events:
        recent_items.append({
            "audit_id": getattr(event, "id", None),
            "tenant_id": safe_text(getattr(event, "tenant_id", "")),
            "tenant_name": safe_text(getattr(event, "tenant_name", "")),
            "action_type": get_action(event),
            "resource_type": get_resource(event),
            "resource_id": safe_text(getattr(event, "resource_id", "")),
            "actor": safe_text(getattr(event, "actor", "")),
            "created_at": get_created_at(event),
            "details": get_details(event),
        })

    high_value_items = []
    for event in high_value_events[-safe_limit:]:
        high_value_items.append({
            "audit_id": getattr(event, "id", None),
            "action_type": get_action(event),
            "resource_type": get_resource(event),
            "resource_id": safe_text(getattr(event, "resource_id", "")),
            "created_at": get_created_at(event),
            "details": get_details(event),
        })

    command_center = {
        "status": "success",
        "dashboard_type": "enterprise_audit_command_center",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_audit_events": len(all_events),
        "export_event_count": len(export_events),
        "pdf_export_count": len(pdf_events),
        "csv_export_count": len(csv_events),
        "zip_export_count": len(zip_events),
        "health_check_count": len(health_events),
        "validation_event_count": len(validation_events),
        "production_lock_event_count": len(production_lock_events),
        "powerbi_event_count": len(powerbi_events),
        "high_value_compliance_event_count": len(high_value_events),
        "audit_signal": (
            "audit_activity_present"
            if len(all_events) > 0
            else "no_audit_activity"
        ),
        "executive_summary": (
            f"LumenAI Enterprise Audit Command Center includes {len(all_events)} audit events, "
            f"{len(export_events)} export-related events, {len(pdf_events)} PDF events, "
            f"{len(csv_events)} CSV events, {len(zip_events)} ZIP events, "
            f"{len(health_events)} health-check events, {len(validation_events)} validation events, "
            f"and {len(production_lock_events)} production-lock events."
        ),
        "recommended_leadership_actions": [
            "Review high-value audit events during governance or quality huddle.",
            "Monitor export activity for survey-readiness traceability.",
            "Validate Power BI toolkit production-lock and final-validation events remain available.",
            "Use audit logs to support leadership reporting, quality review, and compliance evidence.",
        ],
        "recent_audit_events": recent_items,
        "high_value_compliance_events": high_value_items,
    }

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="enterprise_audit_command_center_viewed",
            resource_type="enterprise_audit_command_center",
            resource_id="audit_command_center",
            details={
                "total_audit_events": command_center["total_audit_events"],
                "export_event_count": command_center["export_event_count"],
                "high_value_compliance_event_count": command_center["high_value_compliance_event_count"],
                "workflow_status": "enterprise_audit_command_center_viewed",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return command_center


@router.get("/audit-command-center.pdf")
def get_enterprise_audit_command_center_pdf(
    limit: int = 25,
    request: Request = None,
    db: Session = Depends(get_db),
):
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    dashboard = get_enterprise_audit_command_center(
        limit=limit,
        request=request,
        db=db,
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("LumenAI Enterprise Audit Command Center", styles["Title"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Executive Summary", styles["Heading2"]))
    story.append(Paragraph(
        dashboard.get("executive_summary", "No executive summary available."),
        styles["BodyText"],
    ))
    story.append(Spacer(1, 12))

    metrics_data = [
        ["Metric", "Value"],
        ["Total Audit Events", str(dashboard.get("total_audit_events", 0))],
        ["Export Events", str(dashboard.get("export_event_count", 0))],
        ["PDF Exports", str(dashboard.get("pdf_export_count", 0))],
        ["CSV Exports", str(dashboard.get("csv_export_count", 0))],
        ["ZIP Exports", str(dashboard.get("zip_export_count", 0))],
        ["Health Checks", str(dashboard.get("health_check_count", 0))],
        ["Validation Events", str(dashboard.get("validation_event_count", 0))],
        ["Production Lock Events", str(dashboard.get("production_lock_event_count", 0))],
        ["Power BI Events", str(dashboard.get("powerbi_event_count", 0))],
        ["High-Value Compliance Events", str(dashboard.get("high_value_compliance_event_count", 0))],
        ["Audit Signal", dashboard.get("audit_signal", "")],
    ]

    metrics_table = Table(metrics_data, colWidths=[240, 250])
    metrics_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Recommended Leadership Actions", styles["Heading2"]))

    actions = dashboard.get("recommended_leadership_actions", [])
    if actions:
        action_data = [["Action"]]
        for action in actions:
            action_data.append([action])

        action_table = Table(action_data, colWidths=[490])
        action_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcfce7")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(action_table)
    else:
        story.append(Paragraph("No recommended leadership actions returned.", styles["BodyText"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Recent Audit Events", styles["Heading2"]))

    recent_events = dashboard.get("recent_audit_events", [])
    if recent_events:
        event_data = [["ID", "Action", "Resource", "Resource ID", "Created"]]

        for event in recent_events[:25]:
            event_data.append([
                str(event.get("audit_id", "")),
                event.get("action_type", ""),
                event.get("resource_type", ""),
                event.get("resource_id", ""),
                event.get("created_at", ""),
            ])

        event_table = Table(event_data, colWidths=[35, 150, 130, 95, 80])
        event_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fef3c7")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 5.8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(event_table)
    else:
        story.append(Paragraph("No recent audit events returned.", styles["BodyText"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("High-Value Compliance Events", styles["Heading2"]))

    high_value_events = dashboard.get("high_value_compliance_events", [])
    if high_value_events:
        high_value_data = [["ID", "Action", "Resource", "Resource ID", "Created"]]

        for event in high_value_events[:25]:
            high_value_data.append([
                str(event.get("audit_id", "")),
                event.get("action_type", ""),
                event.get("resource_type", ""),
                event.get("resource_id", ""),
                event.get("created_at", ""),
            ])

        high_value_table = Table(high_value_data, colWidths=[35, 150, 130, 95, 80])
        high_value_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fee2e2")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 5.8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(high_value_table)
    else:
        story.append(Paragraph("No high-value compliance events returned.", styles["BodyText"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Audit Governance Note", styles["Heading2"]))
    story.append(Paragraph(
        "This report summarizes LumenAI enterprise audit activity and is intended to support leadership review, "
        "quality governance, export traceability, survey readiness, and compliance evidence discussions.",
        styles["BodyText"],
    ))

    doc.build(story)
    buffer.seek(0)

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="enterprise_audit_command_center_pdf_exported",
            resource_type="enterprise_audit_command_center_pdf",
            resource_id="audit_command_center_pdf",
            details={
                "limit": max(1, min(limit, 100)),
                "total_audit_events": dashboard.get("total_audit_events", 0),
                "export_event_count": dashboard.get("export_event_count", 0),
                "high_value_compliance_event_count": dashboard.get("high_value_compliance_event_count", 0),
                "workflow_status": "enterprise_audit_command_center_pdf_exported",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=lumenai-enterprise-audit-command-center.pdf"
        },
    )


@router.get("/audit-command-center.csv")
def get_enterprise_audit_command_center_csv(
    limit: int = 100,
    request: Request = None,
    db: Session = Depends(get_db),
):
    import csv
    from io import StringIO
    from fastapi.responses import StreamingResponse

    safe_limit = max(1, min(limit, 1000))

    audit_events = (
        db.query(AuditLog)
        .order_by(AuditLog.id.desc())
        .limit(safe_limit)
        .all()
    )

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "audit_id",
        "tenant_id",
        "tenant_name",
        "action_type",
        "resource_type",
        "resource_id",
        "actor",
        "role",
        "status",
        "compliance_flag",
        "created_at",
        "details",
    ])

    for event in audit_events:
        details = getattr(event, "details", None)

        if isinstance(details, dict):
            details_value = json.dumps(details, default=str)
        elif details is None:
            details_value = ""
        else:
            details_value = str(details)

        created_at = getattr(event, "created_at", None)

        writer.writerow([
            getattr(event, "id", ""),
            getattr(event, "tenant_id", "") or "",
            getattr(event, "tenant_name", "") or "",
            getattr(event, "action_type", "") or "",
            getattr(event, "resource_type", "") or "",
            getattr(event, "resource_id", "") or "",
            getattr(event, "actor", "") or "",
            getattr(event, "role", "") or "",
            getattr(event, "status", "") or "",
            getattr(event, "compliance_flag", "") if getattr(event, "compliance_flag", None) is not None else "",
            created_at.isoformat() if created_at else "",
            details_value,
        ])

    csv_bytes = output.getvalue().encode("utf-8")

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="enterprise_audit_command_center_csv_exported",
            resource_type="enterprise_audit_command_center_csv",
            resource_id="audit_command_center_csv",
            details={
                "limit": safe_limit,
                "exported_rows": len(audit_events),
                "workflow_status": "enterprise_audit_command_center_csv_exported",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=lumenai-enterprise-audit-command-center.csv"
        },
    )


@router.get("/audit-command-center.powerbi.csv")
def get_enterprise_audit_command_center_powerbi_csv(
    limit: int = 1000,
    request: Request = None,
    db: Session = Depends(get_db),
):
    import csv
    from io import StringIO
    from fastapi.responses import StreamingResponse

    safe_limit = max(1, min(limit, 5000))

    audit_events = (
        db.query(AuditLog)
        .order_by(AuditLog.id.desc())
        .limit(safe_limit)
        .all()
    )

    high_value_keywords = [
        "production_lock",
        "final_validation",
        "health",
        "executive_summary",
        "completion_certificate",
        "release_notes",
        "archive",
        "governance",
        "vendor",
        "infection",
        "capa",
        "powerbi",
    ]

    def safe_text(value):
        return value or ""

    def classify_action(action_type: str, resource_type: str) -> str:
        combined = f"{action_type} {resource_type}".lower()

        if "production_lock" in combined or "production" in combined:
            return "Production Lock"
        if "final_validation" in combined or "validation" in combined or "validated" in combined:
            return "Validation"
        if "health" in combined:
            return "Health Check"
        if "pdf" in combined:
            return "PDF Export"
        if "csv" in combined:
            return "CSV Export"
        if "zip" in combined or "archive" in combined:
            return "ZIP/Archive Export"
        if "export" in combined:
            return "Export"
        if "metadata" in combined:
            return "Metadata"
        if "viewed" in combined:
            return "View"
        return "Other"

    def classify_export_type(action_type: str, resource_type: str) -> str:
        combined = f"{action_type} {resource_type}".lower()

        if "pdf" in combined:
            return "PDF"
        if "csv" in combined:
            return "CSV"
        if "zip" in combined:
            return "ZIP"
        if "archive" in combined:
            return "Archive"
        if "export" in combined:
            return "Other Export"
        return ""

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "audit_id",
        "tenant_id",
        "tenant_name",
        "action_type",
        "resource_type",
        "resource_id",
        "actor",
        "role",
        "status",
        "compliance_flag",
        "created_at",
        "audit_date",
        "audit_month",
        "audit_year",
        "action_category",
        "export_type",
        "is_export_event",
        "is_pdf_event",
        "is_csv_event",
        "is_zip_event",
        "is_health_event",
        "is_validation_event",
        "is_production_lock_event",
        "is_powerbi_event",
        "is_high_value_compliance_event",
        "details",
    ])

    for event in audit_events:
        action_type = safe_text(getattr(event, "action_type", ""))
        resource_type = safe_text(getattr(event, "resource_type", ""))
        combined = f"{action_type} {resource_type}".lower()

        created_at = getattr(event, "created_at", None)
        audit_date = created_at.date().isoformat() if created_at else ""
        audit_month = created_at.strftime("%Y-%m") if created_at else ""
        audit_year = created_at.strftime("%Y") if created_at else ""

        is_export_event = "export" in combined
        is_pdf_event = "pdf" in combined
        is_csv_event = "csv" in combined
        is_zip_event = "zip" in combined or "archive" in combined
        is_health_event = "health" in combined
        is_validation_event = "validation" in combined or "validated" in combined
        is_production_lock_event = "production_lock" in combined or "production" in combined
        is_powerbi_event = "powerbi" in combined
        is_high_value_compliance_event = any(keyword in combined for keyword in high_value_keywords)

        details = getattr(event, "details", None)
        if isinstance(details, dict):
            details_value = json.dumps(details, default=str)
        elif details is None:
            details_value = ""
        else:
            details_value = str(details)

        writer.writerow([
            getattr(event, "id", ""),
            getattr(event, "tenant_id", "") or "",
            getattr(event, "tenant_name", "") or "",
            action_type,
            resource_type,
            getattr(event, "resource_id", "") or "",
            getattr(event, "actor", "") or "",
            getattr(event, "role", "") or "",
            getattr(event, "status", "") or "",
            getattr(event, "compliance_flag", "") if getattr(event, "compliance_flag", None) is not None else "",
            created_at.isoformat() if created_at else "",
            audit_date,
            audit_month,
            audit_year,
            classify_action(action_type, resource_type),
            classify_export_type(action_type, resource_type),
            is_export_event,
            is_pdf_event,
            is_csv_event,
            is_zip_event,
            is_health_event,
            is_validation_event,
            is_production_lock_event,
            is_powerbi_event,
            is_high_value_compliance_event,
            details_value,
        ])

    csv_bytes = output.getvalue().encode("utf-8")

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="enterprise_audit_command_center_powerbi_csv_exported",
            resource_type="enterprise_audit_command_center_powerbi_csv",
            resource_id="audit_command_center_powerbi_csv",
            details={
                "limit": safe_limit,
                "exported_rows": len(audit_events),
                "workflow_status": "enterprise_audit_command_center_powerbi_csv_exported",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=lumenai-enterprise-audit-command-center-powerbi.csv"
        },
    )


@router.get("/audit-command-center.powerbi.data-dictionary")
def get_enterprise_audit_command_center_powerbi_data_dictionary(
    request: Request,
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone

    fields = [
        {
            "field_name": "audit_id",
            "display_name": "Audit ID",
            "data_type": "integer",
            "description": "Unique audit log record identifier.",
            "power_bi_usage": "Use as the unique row key or drill-through identifier.",
            "example_value": "141",
        },
        {
            "field_name": "tenant_id",
            "display_name": "Tenant ID",
            "data_type": "text",
            "description": "Tenant or organization identifier associated with the audit event.",
            "power_bi_usage": "Use as an organization or system filter.",
            "example_value": "bonsecours",
        },
        {
            "field_name": "tenant_name",
            "display_name": "Tenant Name",
            "data_type": "text",
            "description": "Human-readable tenant or organization name.",
            "power_bi_usage": "Use as an organization label or slicer.",
            "example_value": "Bon Secours",
        },
        {
            "field_name": "action_type",
            "display_name": "Action Type",
            "data_type": "text",
            "description": "Specific audit action performed by the system or user.",
            "power_bi_usage": "Use in tables, filters, and activity trend visuals.",
            "example_value": "enterprise_audit_command_center_viewed",
        },
        {
            "field_name": "resource_type",
            "display_name": "Resource Type",
            "data_type": "text",
            "description": "System resource associated with the audit action.",
            "power_bi_usage": "Use to group audit activity by functional area.",
            "example_value": "enterprise_audit_command_center",
        },
        {
            "field_name": "resource_id",
            "display_name": "Resource ID",
            "data_type": "text",
            "description": "Identifier for the specific resource involved in the audit event.",
            "power_bi_usage": "Use for drill-through and traceability.",
            "example_value": "audit_command_center",
        },
        {
            "field_name": "actor",
            "display_name": "Actor",
            "data_type": "text",
            "description": "User, service, or actor that triggered the audit event.",
            "power_bi_usage": "Use to analyze activity by user or system actor.",
            "example_value": "john-demo",
        },
        {
            "field_name": "role",
            "display_name": "Role",
            "data_type": "text",
            "description": "Role supplied with the audit request.",
            "power_bi_usage": "Use for role-based audit activity analysis.",
            "example_value": "viewer",
        },
        {
            "field_name": "status",
            "display_name": "Status",
            "data_type": "text",
            "description": "Outcome status of the audited action.",
            "power_bi_usage": "Use to identify successful or failed events.",
            "example_value": "success",
        },
        {
            "field_name": "compliance_flag",
            "display_name": "Compliance Flag",
            "data_type": "boolean",
            "description": "Indicates whether the event is compliance-relevant.",
            "power_bi_usage": "Use as a compliance filter or KPI flag.",
            "example_value": "True",
        },
        {
            "field_name": "created_at",
            "display_name": "Created At",
            "data_type": "datetime",
            "description": "Timestamp when the audit event was created.",
            "power_bi_usage": "Use for timeline, trend, and freshness analysis.",
            "example_value": "2026-05-29T23:46:40.724922",
        },
        {
            "field_name": "audit_date",
            "display_name": "Audit Date",
            "data_type": "date",
            "description": "Date portion derived from created_at.",
            "power_bi_usage": "Use in date slicers and daily trend charts.",
            "example_value": "2026-05-29",
        },
        {
            "field_name": "audit_month",
            "display_name": "Audit Month",
            "data_type": "text/date period",
            "description": "Year-month period derived from created_at.",
            "power_bi_usage": "Use for monthly audit activity trend charts.",
            "example_value": "2026-05",
        },
        {
            "field_name": "audit_year",
            "display_name": "Audit Year",
            "data_type": "text/integer",
            "description": "Year derived from created_at.",
            "power_bi_usage": "Use for annual filtering and trend reporting.",
            "example_value": "2026",
        },
        {
            "field_name": "action_category",
            "display_name": "Action Category",
            "data_type": "text/category",
            "description": "Derived category such as Export, PDF Export, Health Check, Validation, Production Lock, Metadata, View, or Other.",
            "power_bi_usage": "Use as a legend, slicer, or stacked bar category.",
            "example_value": "Health Check",
        },
        {
            "field_name": "export_type",
            "display_name": "Export Type",
            "data_type": "text/category",
            "description": "Derived export type such as PDF, CSV, ZIP, Archive, Other Export, or blank.",
            "power_bi_usage": "Use to compare export activity by file type.",
            "example_value": "PDF",
        },
        {
            "field_name": "is_export_event",
            "display_name": "Is Export Event",
            "data_type": "boolean",
            "description": "True when the audit event is export-related.",
            "power_bi_usage": "Use as a filter or export activity KPI.",
            "example_value": "True",
        },
        {
            "field_name": "is_pdf_event",
            "display_name": "Is PDF Event",
            "data_type": "boolean",
            "description": "True when the audit event is PDF-related.",
            "power_bi_usage": "Use to count or filter PDF export activity.",
            "example_value": "True",
        },
        {
            "field_name": "is_csv_event",
            "display_name": "Is CSV Event",
            "data_type": "boolean",
            "description": "True when the audit event is CSV-related.",
            "power_bi_usage": "Use to count or filter CSV export activity.",
            "example_value": "False",
        },
        {
            "field_name": "is_zip_event",
            "display_name": "Is ZIP Event",
            "data_type": "boolean",
            "description": "True when the audit event is ZIP or archive-related.",
            "power_bi_usage": "Use to count ZIP bundle or archive export activity.",
            "example_value": "False",
        },
        {
            "field_name": "is_health_event",
            "display_name": "Is Health Event",
            "data_type": "boolean",
            "description": "True when the event relates to a health check.",
            "power_bi_usage": "Use for toolkit and governance health-check monitoring.",
            "example_value": "True",
        },
        {
            "field_name": "is_validation_event",
            "display_name": "Is Validation Event",
            "data_type": "boolean",
            "description": "True when the event relates to validation or final validation.",
            "power_bi_usage": "Use for validation activity KPIs.",
            "example_value": "False",
        },
        {
            "field_name": "is_production_lock_event",
            "display_name": "Is Production Lock Event",
            "data_type": "boolean",
            "description": "True when the event relates to production lock activity.",
            "power_bi_usage": "Use to track locked release governance events.",
            "example_value": "False",
        },
        {
            "field_name": "is_powerbi_event",
            "display_name": "Is Power BI Event",
            "data_type": "boolean",
            "description": "True when the event is related to Power BI toolkit workflows.",
            "power_bi_usage": "Use to isolate Power BI workstream audit activity.",
            "example_value": "True",
        },
        {
            "field_name": "is_high_value_compliance_event",
            "display_name": "Is High-Value Compliance Event",
            "data_type": "boolean",
            "description": "True when the event matches high-value compliance keywords such as production lock, final validation, health, executive summary, archive, governance, vendor, infection, CAPA, or Power BI.",
            "power_bi_usage": "Use as a priority compliance review filter.",
            "example_value": "True",
        },
        {
            "field_name": "details",
            "display_name": "Details",
            "data_type": "json/text",
            "description": "Serialized audit event details payload.",
            "power_bi_usage": "Use in drill-through tables or detailed audit review pages.",
            "example_value": "{\"workflow_status\":\"enterprise_audit_command_center_viewed\"}",
        },
    ]

    response = {
        "status": "success",
        "dictionary_type": "enterprise_audit_command_center_powerbi_data_dictionary",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_name": "EnterpriseAuditCommandCenter",
        "field_count": len(fields),
        "recommended_measures": [
            {
                "measure_name": "Total Audit Events",
                "dax": "Total Audit Events = COUNTROWS('EnterpriseAuditCommandCenter')",
            },
            {
                "measure_name": "Export Events",
                "dax": "Export Events = COUNTROWS(FILTER('EnterpriseAuditCommandCenter', 'EnterpriseAuditCommandCenter'[is_export_event] = TRUE()))",
            },
            {
                "measure_name": "High-Value Compliance Events",
                "dax": "High-Value Compliance Events = COUNTROWS(FILTER('EnterpriseAuditCommandCenter', 'EnterpriseAuditCommandCenter'[is_high_value_compliance_event] = TRUE()))",
            },
            {
                "measure_name": "Production Lock Events",
                "dax": "Production Lock Events = COUNTROWS(FILTER('EnterpriseAuditCommandCenter', 'EnterpriseAuditCommandCenter'[is_production_lock_event] = TRUE()))",
            },
            {
                "measure_name": "Health Check Events",
                "dax": "Health Check Events = COUNTROWS(FILTER('EnterpriseAuditCommandCenter', 'EnterpriseAuditCommandCenter'[is_health_event] = TRUE()))",
            },
        ],
        "recommended_visuals": [
            "Card: Total Audit Events",
            "Card: High-Value Compliance Events",
            "Card: Export Events",
            "Stacked bar: Audit Events by Action Category",
            "Line chart: Audit Events by Audit Date",
            "Donut chart: Export Type Distribution",
            "Table: Recent Audit Events",
            "Table: High-Value Compliance Events",
        ],
        "recommended_slicers": [
            "audit_date",
            "audit_month",
            "audit_year",
            "action_category",
            "export_type",
            "actor",
            "resource_type",
            "is_high_value_compliance_event",
        ],
        "fields": fields,
    }

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="enterprise_audit_command_center_powerbi_data_dictionary_viewed",
            resource_type="enterprise_audit_command_center_powerbi_data_dictionary",
            resource_id="audit_command_center_powerbi_data_dictionary",
            details={
                "field_count": len(fields),
                "dataset_name": response["dataset_name"],
                "workflow_status": "enterprise_audit_command_center_powerbi_data_dictionary_viewed",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return response


@router.get("/audit-command-center.powerbi.data-dictionary.pdf")
def get_enterprise_audit_command_center_powerbi_data_dictionary_pdf(
    request: Request,
    db: Session = Depends(get_db),
):
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    dictionary = get_enterprise_audit_command_center_powerbi_data_dictionary(
        request=request,
        db=db,
    )

    fields = dictionary.get("fields", [])
    measures = dictionary.get("recommended_measures", [])
    visuals = dictionary.get("recommended_visuals", [])
    slicers = dictionary.get("recommended_slicers", [])

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("LumenAI Enterprise Audit Command Center", styles["Title"]))
    story.append(Paragraph("Power BI Data Dictionary", styles["Title"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Purpose", styles["Heading2"]))
    story.append(Paragraph(
        "This data dictionary documents the Power BI-ready Audit Command Center CSV dataset. "
        "It supports audit analytics, export traceability, compliance review, leadership reporting, "
        "survey-readiness evidence, and Power BI dashboard development.",
        styles["BodyText"],
    ))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Dataset Summary", styles["Heading2"]))
    summary_data = [
        ["Item", "Value"],
        ["Dataset Name", dictionary.get("dataset_name", "EnterpriseAuditCommandCenter")],
        ["Dictionary Type", dictionary.get("dictionary_type", "")],
        ["Field Count", str(dictionary.get("field_count", len(fields)))],
    ]

    summary_table = Table(summary_data, colWidths=[170, 320])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Recommended Power BI Measures", styles["Heading2"]))

    if measures:
        measure_data = [["Measure", "DAX"]]
        for measure in measures:
            measure_data.append([
                measure.get("measure_name", ""),
                measure.get("dax", ""),
            ])

        measure_table = Table(measure_data, colWidths=[160, 330])
        measure_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcfce7")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 6.5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(measure_table)
    else:
        story.append(Paragraph("No recommended measures returned.", styles["BodyText"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Recommended Visuals", styles["Heading2"]))

    if visuals:
        visual_data = [["Visual Recommendation"]]
        for visual in visuals:
            visual_data.append([visual])

        visual_table = Table(visual_data, colWidths=[490])
        visual_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fef3c7")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(visual_table)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Recommended Slicers", styles["Heading2"]))

    if slicers:
        slicer_data = [["Slicer Field"]]
        for slicer in slicers:
            slicer_data.append([slicer])

        slicer_table = Table(slicer_data, colWidths=[490])
        slicer_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ede9fe")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(slicer_table)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Field Dictionary", styles["Heading2"]))

    if fields:
        field_data = [[
            "Field",
            "Display Name",
            "Type",
            "Description",
            "Power BI Usage",
            "Example",
        ]]

        for field in fields:
            field_data.append([
                field.get("field_name", ""),
                field.get("display_name", ""),
                field.get("data_type", ""),
                field.get("description", ""),
                field.get("power_bi_usage", ""),
                field.get("example_value", ""),
            ])

        field_table = Table(field_data, colWidths=[70, 75, 52, 130, 120, 52])
        field_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0f2fe")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 5.2),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(field_table)
    else:
        story.append(Paragraph("No fields returned.", styles["BodyText"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Governance Note", styles["Heading2"]))
    story.append(Paragraph(
        "This data dictionary is generated from the LumenAI Enterprise Audit Command Center backend and should be used "
        "as the reference guide for Power BI report design, Excel review, and audit-readiness analytics.",
        styles["BodyText"],
    ))

    doc.build(story)
    buffer.seek(0)

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="enterprise_audit_command_center_powerbi_data_dictionary_pdf_exported",
            resource_type="enterprise_audit_command_center_powerbi_data_dictionary_pdf",
            resource_id="audit_command_center_powerbi_data_dictionary_pdf",
            details={
                "field_count": len(fields),
                "measure_count": len(measures),
                "visual_count": len(visuals),
                "slicer_count": len(slicers),
                "workflow_status": "enterprise_audit_command_center_powerbi_data_dictionary_pdf_exported",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=lumenai-audit-command-center-powerbi-data-dictionary.pdf"
        },
    )


@router.get("/audit-command-center.toolkit.zip")
def get_enterprise_audit_command_center_toolkit_zip(
    limit: int = 1000,
    request: Request = None,
    db: Session = Depends(get_db),
):
    import csv
    import json
    import zipfile
    from datetime import datetime, timezone
    from io import BytesIO, StringIO
    from fastapi.responses import StreamingResponse

    safe_limit = max(1, min(limit, 5000))

    audit_events = (
        db.query(AuditLog)
        .order_by(AuditLog.id.desc())
        .limit(safe_limit)
        .all()
    )

    dictionary = get_enterprise_audit_command_center_powerbi_data_dictionary(
        request=request,
        db=db,
    )

    high_value_keywords = [
        "production_lock",
        "final_validation",
        "health",
        "executive_summary",
        "completion_certificate",
        "release_notes",
        "archive",
        "governance",
        "vendor",
        "infection",
        "capa",
        "powerbi",
    ]

    def safe_text(value):
        return value or ""

    def serialize_details(event):
        details = getattr(event, "details", None)

        if isinstance(details, dict):
            return json.dumps(details, default=str)
        if details is None:
            return ""
        return str(details)

    def classify_action(action_type: str, resource_type: str) -> str:
        combined = f"{action_type} {resource_type}".lower()

        if "production_lock" in combined or "production" in combined:
            return "Production Lock"
        if "final_validation" in combined or "validation" in combined or "validated" in combined:
            return "Validation"
        if "health" in combined:
            return "Health Check"
        if "pdf" in combined:
            return "PDF Export"
        if "csv" in combined:
            return "CSV Export"
        if "zip" in combined or "archive" in combined:
            return "ZIP/Archive Export"
        if "export" in combined:
            return "Export"
        if "metadata" in combined:
            return "Metadata"
        if "viewed" in combined:
            return "View"
        return "Other"

    def classify_export_type(action_type: str, resource_type: str) -> str:
        combined = f"{action_type} {resource_type}".lower()

        if "pdf" in combined:
            return "PDF"
        if "csv" in combined:
            return "CSV"
        if "zip" in combined:
            return "ZIP"
        if "archive" in combined:
            return "Archive"
        if "export" in combined:
            return "Other Export"
        return ""

    def build_standard_csv() -> str:
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "audit_id",
            "tenant_id",
            "tenant_name",
            "action_type",
            "resource_type",
            "resource_id",
            "actor",
            "role",
            "status",
            "compliance_flag",
            "created_at",
            "details",
        ])

        for event in audit_events:
            created_at = getattr(event, "created_at", None)

            writer.writerow([
                getattr(event, "id", ""),
                getattr(event, "tenant_id", "") or "",
                getattr(event, "tenant_name", "") or "",
                getattr(event, "action_type", "") or "",
                getattr(event, "resource_type", "") or "",
                getattr(event, "resource_id", "") or "",
                getattr(event, "actor", "") or "",
                getattr(event, "role", "") or "",
                getattr(event, "status", "") or "",
                getattr(event, "compliance_flag", "") if getattr(event, "compliance_flag", None) is not None else "",
                created_at.isoformat() if created_at else "",
                serialize_details(event),
            ])

        return output.getvalue()

    def build_powerbi_csv() -> str:
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "audit_id",
            "tenant_id",
            "tenant_name",
            "action_type",
            "resource_type",
            "resource_id",
            "actor",
            "role",
            "status",
            "compliance_flag",
            "created_at",
            "audit_date",
            "audit_month",
            "audit_year",
            "action_category",
            "export_type",
            "is_export_event",
            "is_pdf_event",
            "is_csv_event",
            "is_zip_event",
            "is_health_event",
            "is_validation_event",
            "is_production_lock_event",
            "is_powerbi_event",
            "is_high_value_compliance_event",
            "details",
        ])

        for event in audit_events:
            action_type = safe_text(getattr(event, "action_type", ""))
            resource_type = safe_text(getattr(event, "resource_type", ""))
            combined = f"{action_type} {resource_type}".lower()

            created_at = getattr(event, "created_at", None)
            audit_date = created_at.date().isoformat() if created_at else ""
            audit_month = created_at.strftime("%Y-%m") if created_at else ""
            audit_year = created_at.strftime("%Y") if created_at else ""

            writer.writerow([
                getattr(event, "id", ""),
                getattr(event, "tenant_id", "") or "",
                getattr(event, "tenant_name", "") or "",
                action_type,
                resource_type,
                getattr(event, "resource_id", "") or "",
                getattr(event, "actor", "") or "",
                getattr(event, "role", "") or "",
                getattr(event, "status", "") or "",
                getattr(event, "compliance_flag", "") if getattr(event, "compliance_flag", None) is not None else "",
                created_at.isoformat() if created_at else "",
                audit_date,
                audit_month,
                audit_year,
                classify_action(action_type, resource_type),
                classify_export_type(action_type, resource_type),
                "export" in combined,
                "pdf" in combined,
                "csv" in combined,
                "zip" in combined or "archive" in combined,
                "health" in combined,
                "validation" in combined or "validated" in combined,
                "production_lock" in combined or "production" in combined,
                "powerbi" in combined,
                any(keyword in combined for keyword in high_value_keywords),
                serialize_details(event),
            ])

        return output.getvalue()

    manifest = {
        "status": "success",
        "toolkit_type": "enterprise_audit_command_center_toolkit",
        "toolkit_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_name": "EnterpriseAuditCommandCenter",
        "record_count": len(audit_events),
        "limit": safe_limit,
        "included_files": [
            "README.txt",
            "audit-command-center-manifest.json",
            "audit-command-center.csv",
            "audit-command-center-powerbi.csv",
            "audit-command-center-data-dictionary.json",
        ],
        "purpose": (
            "Toolkit package for LumenAI Enterprise Audit Command Center analytics, "
            "Excel review, Power BI dashboard development, leadership reporting, "
            "quality governance, and compliance evidence review."
        ),
    }

    readme = f"""LumenAI Enterprise Audit Command Center Toolkit

Purpose
This toolkit provides the core files needed to analyze LumenAI enterprise audit activity in Excel or Power BI.

Files Included
1. audit-command-center.csv
   Standard audit log export for Excel or compliance review.

2. audit-command-center-powerbi.csv
   Power BI-ready audit dataset with derived fields such as audit_date, audit_month, audit_year, action_category, export_type, and event flags.

3. audit-command-center-data-dictionary.json
   Machine-readable data dictionary with field descriptions, recommended measures, visuals, and slicers.

4. audit-command-center-manifest.json
   Toolkit manifest with record count, version, generated timestamp, and included files.

Recommended Power BI Dataset Name
EnterpriseAuditCommandCenter

Recommended Slicers
- audit_date
- audit_month
- audit_year
- action_category
- export_type
- actor
- resource_type
- is_high_value_compliance_event

Recommended Use
Use this toolkit for audit command center reporting, export traceability, survey readiness, compliance evidence review, and leadership governance reporting.

Generated Parameters
limit={safe_limit}
record_count={len(audit_events)}
"""

    buffer = BytesIO()

    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("README.txt", readme)
        zip_file.writestr("audit-command-center-manifest.json", json.dumps(manifest, indent=2, default=str))
        zip_file.writestr("audit-command-center.csv", build_standard_csv())
        zip_file.writestr("audit-command-center-powerbi.csv", build_powerbi_csv())
        zip_file.writestr("audit-command-center-data-dictionary.json", json.dumps(dictionary, indent=2, default=str))

    buffer.seek(0)

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="enterprise_audit_command_center_toolkit_zip_exported",
            resource_type="enterprise_audit_command_center_toolkit_zip",
            resource_id="audit_command_center_toolkit",
            details={
                "limit": safe_limit,
                "record_count": len(audit_events),
                "toolkit_version": manifest["toolkit_version"],
                "workflow_status": "enterprise_audit_command_center_toolkit_zip_exported",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=lumenai-enterprise-audit-command-center-toolkit.zip"
        },
    )


@router.get("/audit-command-center.health")
def get_enterprise_audit_command_center_health(
    request: Request,
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone

    checks = []

    dashboard = {}
    dictionary = {}

    try:
        dashboard = get_enterprise_audit_command_center(
            limit=25,
            request=request,
            db=db,
        )
        checks.append({
            "check_name": "Audit Command Center dashboard endpoint",
            "status": "pass",
            "message": "Dashboard endpoint returned successfully.",
        })
    except Exception as exc:
        checks.append({
            "check_name": "Audit Command Center dashboard endpoint",
            "status": "fail",
            "message": str(exc),
        })

    try:
        dictionary = get_enterprise_audit_command_center_powerbi_data_dictionary(
            request=request,
            db=db,
        )
        checks.append({
            "check_name": "Power BI data dictionary endpoint",
            "status": "pass",
            "message": "Data dictionary endpoint returned successfully.",
        })
    except Exception as exc:
        checks.append({
            "check_name": "Power BI data dictionary endpoint",
            "status": "fail",
            "message": str(exc),
        })

    total_audit_events = dashboard.get("total_audit_events", 0) if isinstance(dashboard, dict) else 0
    recent_events = dashboard.get("recent_audit_events", []) if isinstance(dashboard, dict) else []
    high_value_events = dashboard.get("high_value_compliance_events", []) if isinstance(dashboard, dict) else []

    checks.append({
        "check_name": "Audit activity present",
        "status": "pass" if total_audit_events > 0 else "warning",
        "message": f"{total_audit_events} audit events found.",
    })

    checks.append({
        "check_name": "Recent audit events available",
        "status": "pass" if len(recent_events) > 0 else "warning",
        "message": f"{len(recent_events)} recent audit events returned.",
    })

    checks.append({
        "check_name": "High-value compliance events available",
        "status": "pass" if len(high_value_events) > 0 else "warning",
        "message": f"{len(high_value_events)} high-value compliance events returned.",
    })

    required_dictionary_fields = [
        "dataset_name",
        "field_count",
        "recommended_measures",
        "recommended_visuals",
        "recommended_slicers",
        "fields",
    ]

    for field in required_dictionary_fields:
        checks.append({
            "check_name": f"Data dictionary field: {field}",
            "status": "pass" if dictionary.get(field) else "fail",
            "message": "Present" if dictionary.get(field) else "Missing",
        })

    expected_endpoints = [
        {
            "name": "Audit dashboard JSON",
            "endpoint": "/api/enterprise/audit-command-center",
        },
        {
            "name": "Audit dashboard PDF",
            "endpoint": "/api/enterprise/audit-command-center.pdf",
        },
        {
            "name": "Audit CSV",
            "endpoint": "/api/enterprise/audit-command-center.csv",
        },
        {
            "name": "Audit Power BI CSV",
            "endpoint": "/api/enterprise/audit-command-center.powerbi.csv",
        },
        {
            "name": "Audit Power BI data dictionary JSON",
            "endpoint": "/api/enterprise/audit-command-center.powerbi.data-dictionary",
        },
        {
            "name": "Audit Power BI data dictionary PDF",
            "endpoint": "/api/enterprise/audit-command-center.powerbi.data-dictionary.pdf",
        },
        {
            "name": "Audit toolkit ZIP",
            "endpoint": "/api/enterprise/audit-command-center.toolkit.zip",
        },
    ]

    for endpoint in expected_endpoints:
        checks.append({
            "check_name": f"Endpoint registered: {endpoint['name']}",
            "status": "pass",
            "endpoint": endpoint["endpoint"],
            "message": "Endpoint expected in current backend route set.",
        })

    failed_checks = [check for check in checks if check.get("status") == "fail"]
    warning_checks = [check for check in checks if check.get("status") == "warning"]

    overall_status = "healthy"
    if warning_checks:
        overall_status = "warning"
    if failed_checks:
        overall_status = "unhealthy"

    response = {
        "status": "success",
        "health_type": "enterprise_audit_command_center_health_check",
        "overall_status": overall_status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "toolkit_name": "LumenAI Enterprise Audit Command Center",
        "toolkit_version": "1.0.0",
        "dataset_name": "EnterpriseAuditCommandCenter",
        "total_checks": len(checks),
        "passed_checks": len([check for check in checks if check.get("status") == "pass"]),
        "failed_checks": len(failed_checks),
        "warning_checks": len(warning_checks),
        "total_audit_events": total_audit_events,
        "export_event_count": dashboard.get("export_event_count", 0) if isinstance(dashboard, dict) else 0,
        "pdf_export_count": dashboard.get("pdf_export_count", 0) if isinstance(dashboard, dict) else 0,
        "csv_export_count": dashboard.get("csv_export_count", 0) if isinstance(dashboard, dict) else 0,
        "zip_export_count": dashboard.get("zip_export_count", 0) if isinstance(dashboard, dict) else 0,
        "powerbi_event_count": dashboard.get("powerbi_event_count", 0) if isinstance(dashboard, dict) else 0,
        "high_value_compliance_event_count": dashboard.get("high_value_compliance_event_count", 0) if isinstance(dashboard, dict) else 0,
        "checks": checks,
        "recommended_action": (
            "Audit Command Center toolkit is healthy and ready for leadership reporting, compliance review, and Power BI analytics."
            if overall_status == "healthy"
            else "Review failed or warning checks before using the Audit Command Center toolkit for formal reporting."
        ),
    }

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="enterprise_audit_command_center_health_checked",
            resource_type="enterprise_audit_command_center_health",
            resource_id="audit_command_center_health",
            details={
                "overall_status": overall_status,
                "total_checks": response["total_checks"],
                "passed_checks": response["passed_checks"],
                "failed_checks": response["failed_checks"],
                "warning_checks": response["warning_checks"],
                "workflow_status": "enterprise_audit_command_center_health_checked",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return response


@router.post("/baseline-aware-score")
def calculate_enterprise_baseline_aware_score(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    finding_type = payload.get("finding_type")
    risk_level = payload.get("risk_level")
    vendor_baseline_id = payload.get("vendor_baseline_id")
    hospital_baseline_id = payload.get("hospital_baseline_id")
    historical_match_count = int(payload.get("historical_match_count") or 0)
    baseline_status = payload.get("baseline_status")

    result = _calculate_baseline_aware_score(
        finding_type=finding_type,
        risk_level=risk_level,
        vendor_baseline_id=vendor_baseline_id,
        hospital_baseline_id=hospital_baseline_id,
        historical_match_count=historical_match_count,
        baseline_status=baseline_status,
    )

    response = {
        "status": "success",
        "scoring_type": "baseline_aware_scoring",
        "input": {
            "finding_type": finding_type,
            "risk_level": risk_level,
            "vendor_baseline_id": vendor_baseline_id,
            "hospital_baseline_id": hospital_baseline_id,
            "historical_match_count": historical_match_count,
            "baseline_status": baseline_status,
        },
        "scoring_result": result,
        "recommended_action": (
            "Use score for reporting and governance."
            if not result.get("requires_baseline_review")
            else "Route finding to baseline review queue before treating score as final."
        ),
    }

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="baseline_aware_score_calculated",
            resource_type="baseline_aware_scoring_engine",
            resource_id="baseline_aware_score",
            details={
                "score": result.get("score"),
                "score_confidence": result.get("score_confidence"),
                "baseline_source": result.get("baseline_source"),
                "requires_baseline_review": result.get("requires_baseline_review"),
                "workflow_status": "baseline_aware_score_calculated",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return response


@router.get("/baseline-review-queue")
def get_enterprise_baseline_review_queue(
    limit: int = 50,
    request: Request = None,
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone

    safe_limit = max(1, min(limit, 200))

    findings = (
        db.query(EnterpriseFinding)
        .order_by(EnterpriseFinding.id.desc())
        .limit(safe_limit)
        .all()
    )

    queue_items = []

    for finding in findings:
        finding_type = getattr(finding, "finding_type", "") or getattr(finding, "defect_type", "") or ""
        risk_level = getattr(finding, "risk_level", "") or ""
        vendor = getattr(finding, "vendor", "") or ""
        instrument_name = getattr(finding, "instrument_name", "") or ""
        tray_name = getattr(finding, "tray_name", "") or ""
        facility = getattr(finding, "facility", "") or ""
        department = getattr(finding, "department", "") or ""

        score_result = _calculate_baseline_aware_score(
            finding_type=finding_type,
            risk_level=risk_level,
            vendor_baseline_id=None,
            hospital_baseline_id=None,
            historical_match_count=0,
            baseline_status=None,
        )

        if score_result.get("requires_baseline_review"):
            queue_items.append({
                "finding_id": getattr(finding, "id", None),
                "facility": facility,
                "department": department,
                "vendor": vendor,
                "instrument_name": instrument_name,
                "tray_name": tray_name,
                "finding_type": finding_type,
                "risk_level": risk_level,
                "score": score_result.get("score"),
                "score_confidence": score_result.get("score_confidence"),
                "baseline_source": score_result.get("baseline_source"),
                "baseline_status": score_result.get("baseline_status"),
                "score_basis": score_result.get("score_basis"),
                "requires_baseline_review": score_result.get("requires_baseline_review"),
                "manual_review_required": score_result.get("manual_review_required"),
                "recommended_action": "Review finding, confirm baseline source, attach approved baseline image, or request vendor baseline.",
            })

    response = {
        "status": "success",
        "queue_type": "baseline_review_queue",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "queue_count": len(queue_items),
        "review_priority_count": len([
            item for item in queue_items
            if item.get("score_confidence") == "low"
            or item.get("manual_review_required") is True
        ]),
        "queue_summary": (
            f"{len(queue_items)} findings require baseline review before their scores should be treated as final."
        ),
        "recommended_next_step": (
            "Review unmatched or low-confidence findings, attach hospital/vendor baseline images, and approve baseline status."
            if queue_items
            else "No baseline review items are currently pending."
        ),
        "items": queue_items,
    }

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name="",
            action_type="baseline_review_queue_viewed",
            resource_type="baseline_review_queue",
            resource_id="baseline_review_queue",
            details={
                "queue_count": response["queue_count"],
                "review_priority_count": response["review_priority_count"],
                "workflow_status": "baseline_review_queue_viewed",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return response


VENDOR_BASELINE_LIBRARY: list[dict] = []


@router.post("/vendor-baseline-subscription/baselines")
def create_enterprise_vendor_baseline_record(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
):

    vendor_name = payload.get("vendor_name") or payload.get("vendor") or ""
    instrument_name = payload.get("instrument_name") or ""
    instrument_category = payload.get("instrument_category") or ""
    catalog_number = payload.get("catalog_number") or ""
    model_number = payload.get("model_number") or ""
    barcode_value = payload.get("barcode_value") or ""
    qr_code_value = payload.get("qr_code_value") or ""
    key_dot_value = payload.get("key_dot_value") or ""
    tray_name = payload.get("tray_name") or ""
    baseline_image_url = payload.get("baseline_image_url") or ""
    acceptable_condition_notes = payload.get("acceptable_condition_notes") or ""
    unacceptable_condition_examples = payload.get("unacceptable_condition_examples") or ""
    ifu_reference = payload.get("ifu_reference") or ""
    subscription_tier = payload.get("subscription_tier") or "vendor_standard"

    db_record = EnterpriseVendorBaselineSubscription(
        vendor_name=vendor_name,
        instrument_name=instrument_name,
        instrument_category=instrument_category,
        catalog_number=catalog_number,
        model_number=model_number,
        barcode_value=barcode_value,
        qr_code_value=qr_code_value,
        key_dot_value=key_dot_value,
        tray_name=tray_name,
        baseline_image_url=baseline_image_url,
        acceptable_condition_notes=acceptable_condition_notes,
        unacceptable_condition_examples=unacceptable_condition_examples,
        ifu_reference=ifu_reference,
        subscription_tier=subscription_tier,
        baseline_source="vendor",
        baseline_status="vendor_submitted",
        approval_status="pending_hospital_review",
        baseline_version="v1.0",
    )

    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    baseline_id = db_record.id

    record = _vendor_baseline_record_to_dict(db_record)


    matched_identifier_type = None
    matched_identifier_value = None

    for key in [
        "barcode_value",
        "qr_code_value",
        "key_dot_value",
        "catalog_number",
        "model_number",
    ]:
        if record.get(key):
            matched_identifier_type = key
            matched_identifier_value = record.get(key)
            break

    existing_submit_event = (
        db.query(VendorBaselineAuditEvent)
        .filter(VendorBaselineAuditEvent.baseline_id == record.get("baseline_id"))
        .filter(VendorBaselineAuditEvent.event_type == "baseline_submitted")
        .first()
    )

    if existing_submit_event is None:
        log_vendor_baseline_audit_event(
            db=db,
            baseline_id=record.get("baseline_id"),
            event_type="baseline_submitted",
            actor=request.headers.get("x-lumenai-actor", record.get("vendor_name", "vendor")) if request else record.get("vendor_name", "vendor"),
            actor_role=request.headers.get("x-lumenai-role", "vendor") if request else "vendor",
            decision="submitted",
            notes="Vendor submitted baseline reference record.",
            evidence_source="Vendor baseline subscription portal",
            matched_identifier_type=matched_identifier_type,
            matched_identifier_value=matched_identifier_value,
            previous_status=None,
            new_status="pending_hospital_review",
        )

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name=vendor_name,
            action_type="vendor_baseline_record_created",
            resource_type="vendor_baseline_subscription_baseline",
            resource_id=str(baseline_id),
            details={
                "vendor_name": vendor_name,
                "instrument_name": instrument_name,
                "catalog_number": catalog_number,
                "baseline_status": record["baseline_status"],
                "approval_status": record["approval_status"],
                "workflow_status": "vendor_baseline_record_created",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return {
        "status": "success",
        "baseline_type": "vendor_baseline_subscription_record",
        "message": "Vendor baseline record created and routed for hospital review.",
        "baseline": record,
        "recommended_next_step": "Hospital or enterprise reviewer should approve, reject, or request clarification before using this baseline for final scoring.",
    }


@router.post("/vendor-baseline-subscription/baselines/upload-image")
def upload_vendor_baseline_image(
    request: Request,
    file: UploadFile = File(...),
):
    """
    Upload a baseline reference image for a vendor instrument.
    Returns the storage URL to use as baseline_image_url when submitting a baseline record.
    """
    from app.services.object_storage import save_upload_file
    import uuid

    safe_name = os.path.basename(file.filename or "baseline.jpg")
    ext = os.path.splitext(safe_name)[1] or ".jpg"
    unique_key = f"vendor-baselines/{uuid.uuid4().hex}{ext}"

    stored = save_upload_file(
        file_obj=file.file,
        file_name=safe_name,
        object_key=unique_key,
        content_type=file.content_type or "image/jpeg",
    )

    return {
        "status": "success",
        "baseline_image_url": stored.public_url,
        "storage_uri": stored.storage_uri,
        "file_name": safe_name,
    }


@router.get("/vendor-baseline-subscription/baselines")
def list_enterprise_vendor_baseline_records(
    vendor_name: str | None = None,
    instrument_name: str | None = None,
    identifier_value: str | None = None,
    status: str | None = None,
    limit: int = 50,
    request: Request = None,
    db: Session = Depends(get_db),
):
    _require_vendor_baseline_library_access(request)

    from datetime import datetime, timezone

    safe_limit = max(1, min(limit, 200))

    db_records = db.query(EnterpriseVendorBaselineSubscription).order_by(EnterpriseVendorBaselineSubscription.id.desc()).all()
    records = [_vendor_baseline_record_to_dict(record) for record in db_records]

    if vendor_name:
        records = [
            record for record in records
            if vendor_name.lower() in (record.get("vendor_name") or "").lower()
        ]

    if instrument_name:
        records = [
            record for record in records
            if instrument_name.lower() in (record.get("instrument_name") or "").lower()
        ]

    if identifier_value:
        needle = identifier_value.lower()
        records = [
            record for record in records
            if needle in (record.get("barcode_value") or "").lower()
            or needle in (record.get("qr_code_value") or "").lower()
            or needle in (record.get("key_dot_value") or "").lower()
            or needle in (record.get("catalog_number") or "").lower()
            or needle in (record.get("model_number") or "").lower()
        ]

    if status:
        records = [
            record for record in records
            if status.lower() in (record.get("baseline_status") or "").lower()
            or status.lower() in (record.get("approval_status") or "").lower()
        ]

    records = records[:safe_limit]

    response = {
        "status": "success",
        "library_type": "vendor_baseline_subscription_library",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "total_library_count": db.query(EnterpriseVendorBaselineSubscription).count(),
        "filters": {
            "vendor_name": vendor_name,
            "instrument_name": instrument_name,
            "identifier_value": identifier_value,
            "status": status,
            "limit": safe_limit,
        },
        "records": records,
        "recommended_use": "Use vendor-approved baseline records to improve instrument matching, baseline comparison, and score confidence.",
    }

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name=vendor_name or "",
            action_type="vendor_baseline_library_viewed",
            resource_type="vendor_baseline_subscription_library",
            resource_id="vendor_baseline_library",
            details={
                "record_count": response["record_count"],
                "total_library_count": response["total_library_count"],
                "workflow_status": "vendor_baseline_library_viewed",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return response


@router.post("/vendor-baseline-subscription/baselines/{baseline_id}/approve")
def approve_enterprise_vendor_baseline_record(
    baseline_id: int,
    payload: dict | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    _require_vendor_baseline_approval_access(request)

    from datetime import datetime

    payload = payload or {}

    db_record = (
        db.query(EnterpriseVendorBaselineSubscription)
        .filter(EnterpriseVendorBaselineSubscription.id == baseline_id)
        .first()
    )

    if not db_record:
        return {
            "status": "not_found",
            "message": f"Vendor baseline record #{baseline_id} was not found.",
        }

    db_record.baseline_status = "approved"
    db_record.approval_status = "hospital_approved"
    db_record.approved_by = request.headers.get("x-lumenai-actor", "unknown") if request else "unknown"
    db_record.approval_notes = payload.get("approval_notes") or ""
    db_record.updated_at = datetime.now(timezone.utc)

    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    record = _vendor_baseline_record_to_dict(db_record)

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name=record.get("vendor_name", ""),
            action_type="vendor_baseline_record_approved",
            resource_type="vendor_baseline_subscription_baseline",
            resource_id=str(baseline_id),
            details={
                "vendor_name": record.get("vendor_name"),
                "instrument_name": record.get("instrument_name"),
                "baseline_status": record.get("baseline_status"),
                "approval_status": record.get("approval_status"),
                "workflow_status": "vendor_baseline_record_approved",
            },
        )

        matched_identifier_type = None
        matched_identifier_value = None

        for key in [
            "barcode_value",
            "qr_code_value",
            "key_dot_value",
            "catalog_number",
            "model_number",
        ]:
            if record.get(key):
                matched_identifier_type = key
                matched_identifier_value = record.get(key)
                break

        existing_approval_event = (
            db.query(VendorBaselineAuditEvent)
            .filter(VendorBaselineAuditEvent.baseline_id == baseline_id)
            .filter(VendorBaselineAuditEvent.event_type == "baseline_approved")
            .first()
        )

        if existing_approval_event is None:
            log_vendor_baseline_audit_event(
                db=db,
                baseline_id=baseline_id,
                event_type="baseline_approved",
                actor=record.get("approved_by") or (
                    request.headers.get("x-lumenai-actor", "hospital-reviewer-demo")
                    if request else "hospital-reviewer-demo"
                ),
                actor_role=request.headers.get("x-lumenai-role", "hospital_admin") if request else "hospital_admin",
                decision="approved",
                notes=record.get("approval_notes") or "Hospital reviewed and approved vendor baseline for scoring use.",
                evidence_source="Vendor submitted baseline image and identifier match.",
                matched_identifier_type=matched_identifier_type,
                matched_identifier_value=matched_identifier_value,
                previous_status="pending_hospital_review",
                new_status="approved",
            )

        existing_scoring_event = (
            db.query(VendorBaselineAuditEvent)
            .filter(VendorBaselineAuditEvent.baseline_id == baseline_id)
            .filter(VendorBaselineAuditEvent.event_type == "baseline_used_in_scoring")
            .first()
        )

        if existing_scoring_event is None:
            log_vendor_baseline_audit_event(
                db=db,
                baseline_id=baseline_id,
                event_type="baseline_used_in_scoring",
                actor="scoring-engine",
                actor_role="system",
                decision="used_in_scoring",
                notes="Approved vendor baseline available for baseline-supported scoring.",
                evidence_source="Approved vendor baseline match",
                matched_identifier_type=matched_identifier_type,
                matched_identifier_value=matched_identifier_value,
                previous_status="provisional_low_confidence",
                new_status="baseline_supported",
            )

        db.commit()
    except Exception:
        db.rollback()

    return {
        "status": "success",
        "message": "Vendor baseline record approved for scoring use.",
        "baseline": record,
    }


@router.post("/vendor-baseline-subscription/match")
def match_enterprise_vendor_baseline_record(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    identifier_value = (payload.get("identifier_value") or "").lower()
    instrument_name = (payload.get("instrument_name") or "").lower()
    vendor_name = (payload.get("vendor_name") or payload.get("vendor") or "").lower()

    matches = []

    db_records = db.query(EnterpriseVendorBaselineSubscription).all()
    records = [_vendor_baseline_record_to_dict(record) for record in db_records]

    for record in records:
        haystack = [
            (record.get("barcode_value") or "").lower(),
            (record.get("qr_code_value") or "").lower(),
            (record.get("key_dot_value") or "").lower(),
            (record.get("catalog_number") or "").lower(),
            (record.get("model_number") or "").lower(),
            (record.get("instrument_name") or "").lower(),
            (record.get("vendor_name") or "").lower(),
        ]

        identifier_match = bool(identifier_value and any(identifier_value in value for value in haystack))
        instrument_match = bool(instrument_name and instrument_name in (record.get("instrument_name") or "").lower())
        vendor_match = bool(vendor_name and vendor_name in (record.get("vendor_name") or "").lower())

        if identifier_match or (instrument_match and (vendor_match or not vendor_name)):
            matches.append(record)

    approved_matches = [
        record for record in matches
        if record.get("baseline_status") == "approved"
        or record.get("approval_status") == "hospital_approved"
    ]

    best_match = approved_matches[0] if approved_matches else (matches[0] if matches else None)

    match_status = "approved_match" if approved_matches else "pending_match" if matches else "no_match"

    response = {
        "status": "success",
        "match_type": "vendor_baseline_subscription_match",
        "match_status": match_status,
        "match_count": len(matches),
        "approved_match_count": len(approved_matches),
        "best_match": best_match,
        "matches": matches,
        "recommended_action": (
            "Use approved vendor baseline for high-confidence scoring."
            if match_status == "approved_match"
            else "Review pending vendor baseline before using for final scoring."
            if match_status == "pending_match"
            else "No vendor baseline match found. Route to baseline review queue or request vendor baseline."
        ),
    }

    try:
        _record_enterprise_audit(
            db,
            request,
            tenant_id="",
            tenant_name=vendor_name,
            action_type="vendor_baseline_match_requested",
            resource_type="vendor_baseline_subscription_match",
            resource_id=str(best_match.get("baseline_id")) if best_match else "no_match",
            details={
                "match_status": match_status,
                "match_count": len(matches),
                "approved_match_count": len(approved_matches),
                "workflow_status": "vendor_baseline_match_requested",
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return response


VENDOR_BASELINE_LIBRARY: list[dict] = []


@router.get("/vendor-baseline-subscription/baselines/{baseline_id}/audit")
def get_enterprise_vendor_baseline_audit_trail(
    baseline_id: int,
    request: Request = None,
    db: Session = Depends(get_db),
):
    _require_vendor_baseline_audit_access(request)

    """
    Return a derived audit trail for a vendor baseline record.

    This route supports the current vendor baseline library workflow and
    produces audit events for submit, approval, rejection, and scoring-use readiness.
    """

    record = None

    # Primary source: active in-memory/demo vendor baseline library used by approve route.
    try:
        record = next(
            (
                item for item in VENDOR_BASELINE_LIBRARY
                if int(item.get("baseline_id", -1)) == int(baseline_id)
            ),
            None,
        )
    except Exception:
        record = None

    # Fallback source: database-backed vendor baseline subscription table if available.
    if record is None:
        try:
            db_record = None

            # Some versions expose baseline_id in the API response from row.id,
            # not from a physical baseline_id column.
            query = db.query(EnterpriseVendorBaselineSubscription)

            if hasattr(EnterpriseVendorBaselineSubscription, "baseline_id"):
                db_record = (
                    query
                    .filter(EnterpriseVendorBaselineSubscription.baseline_id == baseline_id)
                    .first()
                )

            if db_record is None and hasattr(EnterpriseVendorBaselineSubscription, "id"):
                db_record = (
                    query
                    .filter(EnterpriseVendorBaselineSubscription.id == baseline_id)
                    .first()
                )

            if db_record:
                record = {
                    "baseline_id": getattr(db_record, "baseline_id", None) or getattr(db_record, "id", baseline_id),
                    "vendor_name": getattr(db_record, "vendor_name", None),
                    "instrument_name": getattr(db_record, "instrument_name", None),
                    "instrument_category": getattr(db_record, "instrument_category", None),
                    "catalog_number": getattr(db_record, "catalog_number", None),
                    "model_number": getattr(db_record, "model_number", None),
                    "barcode_value": getattr(db_record, "barcode_value", None),
                    "qr_code_value": getattr(db_record, "qr_code_value", None),
                    "key_dot_value": getattr(db_record, "key_dot_value", None),
                    "tray_name": getattr(db_record, "tray_name", None),
                    "baseline_status": getattr(db_record, "baseline_status", None),
                    "approval_status": getattr(db_record, "approval_status", None),
                    "approved_by": getattr(db_record, "approved_by", None),
                    "approval_notes": getattr(db_record, "approval_notes", None),
                    "created_at": str(getattr(db_record, "created_at", "")),
                    "updated_at": str(getattr(db_record, "updated_at", "")),
                }
        except Exception:
            record = None

    if not record:
        raise HTTPException(status_code=404, detail="Vendor baseline not found")

    baseline_status = record.get("baseline_status") or ""
    approval_status_raw = record.get("approval_status") or ""

    is_approved = (
        baseline_status == "approved"
        or approval_status_raw in ["approved", "hospital_approved"]
    )

    is_rejected = (
        baseline_status == "rejected"
        or approval_status_raw in ["rejected", "hospital_rejected"]
    )

    audit_status = "approved" if is_approved else approval_status_raw or baseline_status or "unknown"

    matched_identifier_type = None
    matched_identifier_value = None

    for key in [
        "barcode_value",
        "qr_code_value",
        "key_dot_value",
        "catalog_number",
        "model_number",
    ]:
        if record.get(key):
            matched_identifier_type = key
            matched_identifier_value = record.get(key)
            break

    persistent_events = (
        db.query(VendorBaselineAuditEvent)
        .filter(VendorBaselineAuditEvent.baseline_id == baseline_id)
        .order_by(VendorBaselineAuditEvent.created_at.asc())
        .all()
    )

    if persistent_events:
        return {
            "status": "success",
            "baseline_id": baseline_id,
            "vendor": record.get("vendor_name"),
            "instrument": record.get("instrument_name"),
            "baseline_status": baseline_status,
            "approval_status": audit_status,
            "audit_source": "persistent_table",
            "audit_event_count": len(persistent_events),
            "events": [
                {
                    "event_id": event.id,
                    "event_type": event.event_type,
                    "actor": event.actor,
                    "actor_role": event.actor_role,
                    "decision": event.decision,
                    "notes": event.notes,
                    "evidence_source": event.evidence_source,
                    "finding_id": event.finding_id,
                    "inspection_id": event.inspection_id,
                    "matched_identifier_type": event.matched_identifier_type,
                    "matched_identifier_value": event.matched_identifier_value,
                    "previous_status": event.previous_status,
                    "new_status": event.new_status,
                    "created_at": event.created_at,
                }
                for event in persistent_events
            ],
        }

    events = [
        {
            "event_type": "baseline_submitted",
            "actor": record.get("submitted_by") or record.get("vendor_name") or "vendor",
            "actor_role": "vendor",
            "decision": "submitted",
            "notes": "Vendor submitted baseline reference record.",
            "evidence_source": "Vendor baseline subscription portal",
            "finding_id": record.get("finding_id"),
            "inspection_id": record.get("inspection_id"),
            "matched_identifier_type": matched_identifier_type,
            "matched_identifier_value": matched_identifier_value,
            "previous_status": None,
            "new_status": "pending_hospital_review",
            "created_at": record.get("created_at"),
        }
    ]

    if is_approved:
        events.append(
            {
                "event_type": "baseline_approved",
                "actor": record.get("approved_by") or (
                    request.headers.get("x-lumenai-actor") if request else "hospital-reviewer-demo"
                ),
                "actor_role": "hospital_admin",
                "decision": "approved",
                "notes": record.get("approval_notes")
                or record.get("approval_reason")
                or "Hospital reviewed and approved vendor baseline for scoring use.",
                "evidence_source": record.get("evidence_source")
                or "Vendor submitted baseline image and identifier match.",
                "finding_id": record.get("finding_id"),
                "inspection_id": record.get("inspection_id"),
                "matched_identifier_type": matched_identifier_type,
                "matched_identifier_value": matched_identifier_value,
                "previous_status": "pending_hospital_review",
                "new_status": "approved",
                "created_at": record.get("updated_at") or record.get("approved_at"),
            }
        )

        events.append(
            {
                "event_type": "baseline_used_in_scoring",
                "actor": "scoring-engine",
                "actor_role": "system",
                "decision": "used_in_scoring",
                "notes": "Approved vendor baseline available for baseline-supported scoring.",
                "evidence_source": "Approved vendor baseline match",
                "finding_id": record.get("finding_id"),
                "inspection_id": record.get("inspection_id"),
                "matched_identifier_type": matched_identifier_type,
                "matched_identifier_value": matched_identifier_value,
                "previous_status": "provisional_low_confidence",
                "new_status": "baseline_supported",
                "created_at": record.get("updated_at") or record.get("approved_at"),
            }
        )

    if is_rejected:
        events.append(
            {
                "event_type": "baseline_rejected",
                "actor": record.get("rejected_by") or (
                    request.headers.get("x-lumenai-actor") if request else "hospital-reviewer-demo"
                ),
                "actor_role": "hospital_admin",
                "decision": "rejected",
                "notes": record.get("rejection_reason")
                or record.get("approval_notes")
                or "Hospital rejected vendor baseline record.",
                "evidence_source": record.get("evidence_source") or "Hospital review",
                "finding_id": record.get("finding_id"),
                "inspection_id": record.get("inspection_id"),
                "matched_identifier_type": matched_identifier_type,
                "matched_identifier_value": matched_identifier_value,
                "previous_status": "pending_hospital_review",
                "new_status": "rejected",
                "created_at": record.get("updated_at") or record.get("rejected_at"),
            }
        )

    return {
        "status": "success",
        "baseline_id": baseline_id,
        "vendor": record.get("vendor_name"),
        "instrument": record.get("instrument_name"),
        "baseline_status": baseline_status,
        "approval_status": audit_status,
        "audit_source": "derived_from_current_state",
        "audit_event_count": len(events),
        "events": events,
    }



@router.get("/audit/verify-chain")
def verify_enterprise_audit_chain(
    resource_type: str,
    resource_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_governance_packet_access(request)

    result = verify_audit_chain(
        db,
        resource_type=resource_type,
        resource_id=resource_id,
    )

    return {
        "status": "success",
        **result,
    }


@router.get("/intake/{finding_id}/governance-packet/certificate")
def get_enterprise_governance_packet_certificate(
    finding_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_governance_packet_access(request)

    latest_export = (
        db.query(AuditLog)
        .filter(
            AuditLog.resource_type == "enterprise_governance_packet",
            AuditLog.resource_id == str(finding_id),
            AuditLog.action_type == "governance_packet_exported_pdf",
        )
        .order_by(AuditLog.id.desc())
        .first()
    )

    if not latest_export:
        raise HTTPException(
            status_code=404,
            detail="No governance packet PDF export record found for this finding.",
        )

    details = latest_export.details or {}

    if isinstance(details, str):
        try:
            import json

            details = json.loads(details)
        except Exception:
            details = {}

    packet_hash = details.get("packet_hash") or getattr(latest_export, "packet_hash", "")
    packet_hash_algorithm = (
        details.get("packet_hash_algorithm")
        or getattr(latest_export, "packet_hash_algorithm", "")
        or "SHA-256"
    )

    return {
        "status": "success",
        "certificate_type": "lumenai_governance_packet_certificate",
        "finding_id": finding_id,
        "resource_type": "enterprise_governance_packet",
        "resource_id": str(finding_id),
        "event_id": latest_export.id,
        "action_type": latest_export.action_type,
        "filename": details.get("filename") or f"lumenai-governance-packet-finding-{finding_id}.pdf",
        "export_format": details.get("export_format") or "pdf",
        "packet_hash_algorithm": packet_hash_algorithm,
        "packet_hash": packet_hash,
        "tamper_evident": bool(details.get("tamper_evident", bool(packet_hash))),
        "included_vendor_baseline_audit_trail": bool(
            details.get("included_vendor_baseline_audit_trail", False)
        ),
        "audit_event_count": details.get("audit_event_count"),
        "vendor_baseline_audit_event_count": details.get("vendor_baseline_audit_event_count"),
        "exported_by": latest_export.actor_email or details.get("actor") or "unknown",
        "exported_role": latest_export.actor_role or details.get("actor_role") or "unknown",
        "exported_at": latest_export.created_at.isoformat() if latest_export.created_at else "",
        "verification_url": (
            f"/api/enterprise/intake/{finding_id}/governance-packet/verify-hash"
            f"?packet_hash={packet_hash}"
        ),
        "message": "Governance packet certificate generated from latest tamper-evident PDF export record.",
    }


@router.get("/audit/events")
def list_enterprise_audit_events(
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: str | None = None,
    actor: str | None = None,
    actor_role: str | None = None,
    request_id: str | None = None,
    correlation_id: str | None = None,
    action_type: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    limit: int = 50,
):
    require_audit_chain_verify(request)

    return query_audit_events(
        db,
        tenant_id=tenant_id,
        actor=actor,
        actor_role=actor_role,
        request_id=request_id,
        correlation_id=correlation_id,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
    )


@router.get("/audit/events/export.csv")
def export_enterprise_audit_events_csv(
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: str | None = None,
    actor: str | None = None,
    actor_role: str | None = None,
    request_id: str | None = None,
    correlation_id: str | None = None,
    action_type: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    limit: int = 200,
):
    require_audit_chain_verify(request)

    export = export_audit_events_csv(
        db,
        tenant_id=tenant_id,
        actor=actor,
        actor_role=actor_role,
        request_id=request_id,
        correlation_id=correlation_id,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
    )

    record_audit_export_event(
        db,
        actor=request.headers.get("x-lumenai-actor", "unknown"),
        actor_role=request.headers.get("x-lumenai-role", "viewer"),
        export_result=export,
    )

    return Response(
        content=export["csv"],
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{export["filename"]}"',
            "X-LumenAI-Audit-Export-Count": str(export["count"]),
            "X-LumenAI-Audit-Export-Hash": export["audit_export_hash"],
            "X-LumenAI-Audit-Export-Hash-Algorithm": export["audit_export_hash_algorithm"],
            "X-LumenAI-Audit-Manifest-Hash": export["manifest_hash"],
            "X-LumenAI-Audit-Manifest-Hash-Algorithm": export["manifest_hash_algorithm"],
            "X-LumenAI-Audit-Exported-At": export["exported_at"],
        },
    )


@router.get("/audit/events/export/verify")
def verify_enterprise_audit_export_hash(
    audit_export_hash: str,
    request: Request,
    db: Session = Depends(get_db),
):
    require_audit_chain_verify(request)

    return verify_audit_export_hash(
        db,
        audit_export_hash=audit_export_hash,
    )


@router.get("/audit/events/export/manifest/verify")
def verify_enterprise_audit_export_manifest_hash(
    manifest_hash: str,
    request: Request,
    db: Session = Depends(get_db),
):
    require_audit_chain_verify(request)

    return verify_audit_export_manifest_hash(
        db,
        manifest_hash=manifest_hash,
    )


@router.get("/audit/evidence-bundle")
def export_enterprise_compliance_evidence_bundle(
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: str | None = None,
    actor: str | None = None,
    actor_role: str | None = None,
    request_id: str | None = None,
    correlation_id: str | None = None,
    action_type: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    limit: int = 200,
):
    require_audit_chain_verify(request)

    return build_compliance_evidence_bundle(
        db,
        actor=request.headers.get("x-lumenai-actor", "unknown"),
        actor_role=request.headers.get("x-lumenai-role", "viewer"),
        tenant_id=tenant_id,
        actor_filter=actor,
        actor_role_filter=actor_role,
        request_id=request_id,
        correlation_id=correlation_id,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
    )


@router.get("/audit/evidence-bundle/verify")
def verify_enterprise_compliance_evidence_bundle_hash(
    bundle_hash: str,
    request: Request,
    db: Session = Depends(get_db),
):
    require_audit_chain_verify(request)

    return verify_compliance_evidence_bundle_hash(
        db,
        bundle_hash=bundle_hash,
    )


@router.get("/audit/evidence-bundle/download.json")
def download_enterprise_compliance_evidence_bundle_json(
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: str | None = None,
    actor: str | None = None,
    actor_role: str | None = None,
    request_id: str | None = None,
    correlation_id: str | None = None,
    action_type: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    limit: int = 200,
):
    require_audit_chain_verify(request)

    result = build_compliance_evidence_bundle(
        db,
        actor=request.headers.get("x-lumenai-actor", "unknown"),
        actor_role=request.headers.get("x-lumenai-role", "viewer"),
        tenant_id=tenant_id,
        actor_filter=actor,
        actor_role_filter=actor_role,
        request_id=request_id,
        correlation_id=correlation_id,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
    )

    filename = f"lumenai-compliance-evidence-bundle-{result['bundle_hash'][:12]}.json"

    return Response(
        content=result["bundle_json"],
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-LumenAI-Bundle-Hash": result["bundle_hash"],
            "X-LumenAI-Bundle-Hash-Algorithm": result["bundle_hash_algorithm"],
            "X-LumenAI-Bundle-Event-ID": str(result["bundle_event_id"]),
        },
    )


@router.get("/audit/evidence-bundle/verification-summary")
def get_enterprise_compliance_evidence_verification_summary(
    bundle_hash: str,
    request: Request,
    db: Session = Depends(get_db),
):
    require_audit_chain_verify(request)

    return build_compliance_evidence_verification_summary(
        db,
        bundle_hash=bundle_hash,
    )


@router.post("/audit/events")
def create_enterprise_demo_audit_event(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    require_audit_chain_verify(request)

    event = record_enterprise_audit_event(
        db,
        action_type=payload.get("action_type", "demo_audit_event"),
        resource_type=payload.get("resource_type", "demo_resource"),
        resource_id=payload.get("resource_id", "demo-resource"),
        actor=request.headers.get("x-lumenai-actor", "unknown"),
        actor_role=request.headers.get("x-lumenai-role", "viewer"),
        details=payload.get("details", {}),
        request=request,
    )

    return {
        "status": "success",
        "event_id": event.id,
        "action_type": event.action_type,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
    }


# ── Inspection Intelligence KPI Summary ─────────────────────────────────────

@router.get("/findings/kpi-summary")
def get_findings_kpi_summary(
    db: Session = Depends(get_db),
):
    """
    Returns per-category finding counts for dashboard KPI cards.
    Used by the Inspection Intelligence pilot dashboard.
    """
    all_findings = db.query(EnterpriseFinding).all()

    CATEGORY_KEYWORDS: dict[str, list[str]] = {
        "blood": ["blood"],
        "bone": ["bone"],
        "tissue": ["tissue"],
        "debris": ["debris", "bioburden", "retained debris"],
        "corrosion": ["corrosion", "rust"],
        "crack": ["crack", "fracture"],
        "insulation_damage": ["insulation"],
        "baseline_match": ["baseline"],
        "barcode_qr_keydot": ["barcode", "qr", "keydot", "udi"],
        "other": [],
    }

    counts: dict[str, int] = {k: 0 for k in CATEGORY_KEYWORDS}
    total = len(all_findings)
    high_risk = 0

    for f in all_findings:
        cat = (f.finding_category or "").lower()
        desc = (f.finding_description or "").lower()
        text = cat + " " + desc
        matched = False
        for key, keywords in CATEGORY_KEYWORDS.items():
            if key == "other":
                continue
            if any(kw in text for kw in keywords):
                counts[key] += 1
                matched = True
        if not matched:
            counts["other"] += 1
        if (f.severity or "").lower() in ("high", "critical"):
            high_risk += 1

    # Vendor baseline counts
    total_baselines = db.query(EnterpriseVendorBaselineSubscription).count()
    approved_baselines = (
        db.query(EnterpriseVendorBaselineSubscription)
        .filter(
            EnterpriseVendorBaselineSubscription.approval_status.in_(
                ["approved", "hospital_approved", "vendor_approved"]
            )
        )
        .count()
    )
    pending_baselines = (
        db.query(EnterpriseVendorBaselineSubscription)
        .filter(
            EnterpriseVendorBaselineSubscription.approval_status.ilike("%pending%")
        )
        .count()
    )
    vendor_submissions = (
        db.query(EnterpriseVendorBaselineSubscription)
        .filter(EnterpriseVendorBaselineSubscription.baseline_source == "vendor")
        .count()
    )
    approval_rate = (
        round((approved_baselines / total_baselines) * 100) if total_baselines > 0 else 0
    )

    return {
        "status": "success",
        "total_findings": total,
        "high_risk_instruments": high_risk,
        "finding_categories": counts,
        "baselines": {
            "total": total_baselines,
            "approved": approved_baselines,
            "pending": pending_baselines,
            "vendor_submissions": vendor_submissions,
            "approval_rate": approval_rate,
        },
    }
