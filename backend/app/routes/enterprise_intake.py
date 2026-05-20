from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.enterprise_quality import (
    EnterpriseDepartment,
    EnterpriseDisposition,
    EnterpriseEvidence,
    EnterpriseFacility,
    EnterpriseFinding,
    EnterpriseInstrument,
    EnterpriseRiskScore,
    EnterpriseVendor,
)
from app.schemas.enterprise_intake import (
    EnterpriseInspectionIntakeRequest,
    EnterpriseInspectionIntakeResponse,
    EnterpriseIntakeHistoryItem,
    EnterpriseIntakeHistoryResponse,
    EnterpriseGovernancePacketResponse,
)

router = APIRouter(prefix="/api/enterprise", tags=["Enterprise Intake"])


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
        inspection_id=None,
        finding_id=finding.id,
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
        inspection_id=None,
        finding_id=finding.id,
        recommended_action=payload.recommended_action,
        final_action="Pending human review",
        status="recommended",
    )
    db.add(disposition)

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
                workflow_status="created_pending_human_review",
                created_at=finding.created_at.isoformat() if finding.created_at else "",
            )
        )

    return EnterpriseIntakeHistoryResponse(items=items)


@router.get("/intake/{finding_id}/governance-packet", response_model=EnterpriseGovernancePacketResponse)
def get_enterprise_governance_packet(
    finding_id: int,
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

    vendor_name = vendor.name if vendor else ""
    instrument_name = instrument.name if instrument else ""
    instrument_category = instrument.category if instrument else ""

    severity = finding.severity or "unassigned"
    risk_tier = risk_score.risk_tier if risk_score else "unassigned"
    overall_score = risk_score.overall_score if risk_score else 0
    recommended_action = disposition.recommended_action if disposition else "Pending recommended action"
    final_action = disposition.final_action if disposition else "Pending human review"

    title = f"Governance Packet: Finding #{finding.id} - {instrument_name or 'Instrument Review'}"

    summary = (
        f"LumenAI recorded a {severity} enterprise quality finding for "
        f"{instrument_name or 'an instrument'} associated with "
        f"{vendor_name or 'an identified vendor'}. The finding was classified as "
        f"{finding.finding_category}. The current recommended action is: "
        f"{recommended_action}."
    )

    return EnterpriseGovernancePacketResponse(
        packet_type="enterprise_intake_governance_packet",
        title=title,
        summary=summary,
        finding_id=finding.id,
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
        workflow_status="created_pending_human_review",
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
    )

