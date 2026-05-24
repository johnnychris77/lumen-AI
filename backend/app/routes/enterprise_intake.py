import traceback
import shutil
import os
from datetime import datetime, timezone
import json
from fastapi import APIRouter, Depends, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session

from app.deps import get_db
from app.services.object_storage import save_upload_file, open_stored_object, storage_health_check
from app.models.audit_log import AuditLog
from app.models.enterprise_quality import (
    EnterpriseDepartment,
    EnterpriseDisposition,
    EnterpriseCapa,
    EnterpriseEvidence,
    EnterpriseFacility,
    EnterpriseFinding,
    EnterpriseInstrument,
    EnterpriseInstrumentBaseline,
    EnterpriseRiskScore,
    EnterpriseVendor,
)
from app.schemas.enterprise_intake import (
    EnterpriseInspectionIntakeRequest,
    EnterpriseInspectionIntakeResponse,
    EnterpriseIntakeHistoryItem,
    EnterpriseIntakeHistoryResponse,
    EnterpriseGovernancePacketResponse,
    EnterpriseGovernanceEvidenceItem,
    EnterpriseGovernanceBaselineEvidence,
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


def _audit_actor_from_request(request: Request) -> tuple[str, str]:
    actor = request.headers.get("x-lumenai-actor", "unknown")
    role = request.headers.get("x-lumenai-role", "viewer")
    return actor, role


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


@router.post("/intake", response_model=EnterpriseInspectionIntakeResponse)
def create_enterprise_intake(
    payload: EnterpriseInspectionIntakeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
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

    (
        patient_safety_score,
        regulatory_score,
        operational_score,
        vendor_score,
        overall_score,
        risk_tier,
    ) = _risk_scores_for_severity(payload.severity)

    risk_score = EnterpriseRiskScore(
        tenant_id=payload.tenant_id,
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

    disposition = EnterpriseDisposition(
        tenant_id=payload.tenant_id,
        inspection_id=finding.id,
        recommended_action=payload.recommended_action,
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
    limit: int = 25,
    db: Session = Depends(get_db),
):
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

    baseline_instrument_id = getattr(finding, "instrument_id", None)
    baseline_vendor_id = getattr(finding, "vendor_id", None)

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
    )


@router.get("/intake/{finding_id}/governance-packet.pdf")
def get_enterprise_governance_packet_pdf(
    finding_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    from io import BytesIO

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

    doc.build(story)

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
        },
    )
    db.commit()

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/audit-trail", response_model=EnterpriseAuditTrailResponse)
def list_enterprise_audit_trail(
    limit: int = 50,
    db: Session = Depends(get_db),
):
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
    limit: int = 25,
    db: Session = Depends(get_db),
):
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
    db: Session = Depends(get_db),
):
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

    baseline_trust_status = "approved"

    if not baseline:
        baseline = (
            db.query(EnterpriseInstrumentBaseline)
            .filter(EnterpriseInstrumentBaseline.instrument_id == instrument.id)
            .order_by(EnterpriseInstrumentBaseline.id.desc())
            .first()
        )
        baseline_trust_status = baseline.baseline_status if baseline else "missing"

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
        baseline.approved_at = datetime.utcnow()
        workflow_status = "baseline_approved"
        message = "Manufacturer baseline approved as trusted reference."
    elif decision == "reject":
        baseline.baseline_status = "rejected"
        baseline.approved_by = payload.reviewer_name or "Baseline Reviewer"
        baseline.approved_at = datetime.utcnow()
        workflow_status = "baseline_rejected"
        message = "Manufacturer baseline rejected and will not be used as trusted reference."
    else:
        baseline.baseline_status = "more_evidence_requested"
        baseline.approved_by = payload.reviewer_name or "Baseline Reviewer"
        baseline.approved_at = datetime.utcnow()
        workflow_status = "baseline_more_evidence_requested"
        message = "More evidence requested before baseline approval."

    baseline.updated_at = datetime.utcnow()

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

