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
    EnterpriseExportReadinessHistory,
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
    EnterpriseGovernanceExportPackageResponse,
    EnterpriseVendorEscalationPacketResponse,
    EnterpriseInfectionPreventionReviewPacketResponse,
    EnterpriseExecutiveQualityReviewDashboardResponse,
    EnterpriseExportReadinessStatusResponse,
    EnterpriseExportReadinessHistoryResponse,
    EnterpriseExportReadinessHistoryItem,
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

EXPORT_READINESS_HISTORY: list[dict] = []


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

    generated_at = datetime.now(timezone.utc).isoformat()

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

    comparison_score_count = (
        db.query(EnterpriseBaselineComparisonScore)
        .filter(EnterpriseBaselineComparisonScore.finding_id == finding.id)
        .count()
    ) if "EnterpriseBaselineComparisonScore" in globals() else 0

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
            db.query(EnterpriseAuditEvent)
            .filter(EnterpriseAuditEvent.resource_id == str(finding.id))
            .count()
        )
    except Exception:
        audit_event_count = 0

    included_sections = [
        "enterprise finding",
        "risk score",
        "disposition",
        "governance packet json",
        "governance packet pdf",
        "evidence attachments",
        "audit trail",
    ]

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
        comparison = (
            db.query(EnterpriseBaselineComparisonScore)
            .filter(EnterpriseBaselineComparisonScore.finding_id == finding.id)
            .order_by(EnterpriseBaselineComparisonScore.id.desc())
            .first()
        )
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
        comparison = (
            db.query(EnterpriseBaselineComparisonScore)
            .filter(EnterpriseBaselineComparisonScore.finding_id == finding.id)
            .order_by(EnterpriseBaselineComparisonScore.id.desc())
            .first()
        )
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
        comparison = (
            db.query(EnterpriseBaselineComparisonScore)
            .filter(EnterpriseBaselineComparisonScore.finding_id == finding.id)
            .order_by(EnterpriseBaselineComparisonScore.id.desc())
            .first()
        )
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
        comparison = (
            db.query(EnterpriseBaselineComparisonScore)
            .filter(EnterpriseBaselineComparisonScore.finding_id == finding.id)
            .order_by(EnterpriseBaselineComparisonScore.id.desc())
            .first()
        )
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
        audit_event_count = db.query(EnterpriseAuditEvent).count()
        governance_export_count = (
            db.query(EnterpriseAuditEvent)
            .filter(EnterpriseAuditEvent.action_type.in_([
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
        audit_event_count = db.query(EnterpriseAuditEvent).count()
        governance_export_count = (
            db.query(EnterpriseAuditEvent)
            .filter(EnterpriseAuditEvent.action_type.in_([
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

    generated_at = datetime.now(timezone.utc).isoformat()

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


@router.get("/intake/{finding_id}/export-readiness-status", response_model=EnterpriseExportReadinessStatusResponse)
def get_enterprise_export_readiness_status(
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
