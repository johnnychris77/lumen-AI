"""P24: Global Healthcare Intelligence Ecosystem & Standards Leadership — API routes."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_actor, get_request_tenant_id, require_enterprise_auth
from app.models.p24_standards import (
    APIPartnerApplication,
    AdvisoryConsortiumMember,
    BaselineGovernanceRecord,
    StandardsPublication,
)
from app.services.p24_standards_service import (
    DISCLAIMER,
    get_api_partners,
    get_baseline_governance,
    get_benchmark_reports,
    get_consortium_members,
    get_ecosystem_dashboard,
    get_publications,
    get_quality_standards,
    get_regional_deployments,
)

router = APIRouter(prefix="/api/standards", tags=["p24_standards"])

_DISCLAIMER = DISCLAIMER


def _tenant(request: Request) -> str:
    return get_request_tenant_id(request)


def _actor(request: Request) -> str:
    return get_request_actor(request) or "unknown"


def _audit(db: Session, tenant_id: str, actor: str, action: str, resource: str, rid: str, details: dict) -> None:
    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=actor,
        actor_role="",
        action_type=action,
        resource_type=resource,
        resource_id=rid,
        details=details,
        compliance_flag=True,
    )


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class BaselineGovernanceRequest(BaseModel):
    governance_type: str  # approval / version_change / provenance / audit
    instrument_category: str = ""
    baseline_version_from: str = ""
    baseline_version_to: str = ""
    provenance_source: str = ""
    change_rationale: str = ""
    contributing_facilities: int = 0


class APIPartnerRequest(BaseModel):
    partner_name: str
    api_tier: str  # partner / manufacturer / research / governance
    requested_scopes: list[str] = []


class ConsortiumEnrollRequest(BaseModel):
    organization_type: str  # hospital / manufacturer / regulator / academic / standards_body
    region: str
    membership_tier: str = "observer"


class PublishRequest(BaseModel):
    publication_id: int
    decision: str  # "approve" | "reject"
    reviewer_notes: str = ""


# ---------------------------------------------------------------------------
# Phase 1: Quality Standards
# ---------------------------------------------------------------------------


@router.get("/quality-standards")
def list_quality_standards(
    request: Request,
    standard_type: str | None = None,
    db: Session = Depends(get_db),
) -> Any:
    """Published quality classification standards."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)
    standards = get_quality_standards(db, standard_type=standard_type, status="published")
    _audit(db, tenant_id, _actor(request),
           "p24.standards.list", "quality_standards", "all", {"count": len(standards)})
    return {
        "status": "success",
        "standards": standards,
        "count": len(standards),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Phase 2: Baseline Governance
# ---------------------------------------------------------------------------


@router.get("/baseline-governance")
def list_baseline_governance(
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """This tenant's baseline governance records."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)
    records = get_baseline_governance(db, tenant_id)
    _audit(db, tenant_id, _actor(request),
           "p24.baseline_governance.list", "baseline_governance", "all", {"count": len(records)})
    return {
        "status": "success",
        "records": records,
        "count": len(records),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


@router.post("/baseline-governance",
             dependencies=[Depends(require_roles("admin", "manager"))])
def submit_baseline_governance(
    body: BaselineGovernanceRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Submit a baseline governance event (version change, approval request, provenance record)."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    VALID_TYPES = {"approval", "version_change", "provenance", "audit"}
    if body.governance_type not in VALID_TYPES:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_governance_type", "valid": sorted(VALID_TYPES)},
        )

    VALID_SOURCES = {"", "manufacturer_data", "network_contributed", "clinical_study", "regulatory_guidance"}
    if body.provenance_source and body.provenance_source not in VALID_SOURCES:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_provenance_source", "valid": sorted(VALID_SOURCES - {""})},
        )

    record = BaselineGovernanceRecord(
        tenant_id=tenant_id,
        governance_type=body.governance_type,
        instrument_category=body.instrument_category or None,
        baseline_version_from=body.baseline_version_from or None,
        baseline_version_to=body.baseline_version_to or None,
        provenance_source=body.provenance_source or None,
        change_rationale=body.change_rationale or None,
        contributing_facilities=body.contributing_facilities,
        k_anonymity_verified=(body.contributing_facilities >= 5),
        approval_status="pending",
        human_review_required=True,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    _audit(db, tenant_id, _actor(request),
           "p24.baseline_governance.submit", "baseline_governance", str(record.id),
           {"governance_type": body.governance_type, "instrument_category": body.instrument_category})

    return {
        "status": "success",
        "record_id": record.id,
        "approval_status": "pending",
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


@router.post("/baseline-governance/{record_id}/approve",
             dependencies=[Depends(require_roles("admin", "executive"))])
def approve_baseline_governance(
    record_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Approve a pending baseline governance record."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    record = db.query(BaselineGovernanceRecord).filter_by(id=record_id, tenant_id=tenant_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    if record.approval_status != "pending":
        raise HTTPException(
            status_code=409,
            detail={"error": "already_resolved", "current_status": record.approval_status},
        )

    from datetime import datetime, timezone
    record.approval_status = "approved"
    record.approver = _actor(request)
    record.resolved_at = datetime.now(timezone.utc)
    db.commit()

    _audit(db, tenant_id, _actor(request),
           "p24.baseline_governance.approve", "baseline_governance", str(record_id), {})

    return {
        "status": "success",
        "record_id": record_id,
        "approval_status": "approved",
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Phase 3: Benchmark Program
# ---------------------------------------------------------------------------


@router.get("/benchmarks")
def list_benchmarks(
    request: Request,
    report_type: str | None = None,
    db: Session = Depends(get_db),
) -> Any:
    """Published benchmark reports (annual, contamination, reliability, executive scorecard)."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)
    reports = get_benchmark_reports(db, tenant_id, report_type=report_type)
    _audit(db, tenant_id, _actor(request),
           "p24.benchmarks.list", "benchmark_reports", "all",
           {"count": len(reports), "report_type": report_type})
    return {
        "status": "success",
        "reports": reports,
        "count": len(reports),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Phase 4: International Expansion
# ---------------------------------------------------------------------------


@router.get("/regional-deployments")
def list_regional_deployments(
    request: Request,
    region: str | None = None,
    db: Session = Depends(get_db),
) -> Any:
    """Regional deployment status and compliance frameworks."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)
    deployments = get_regional_deployments(db, region=region)
    _audit(db, tenant_id, _actor(request),
           "p24.regional_deployments.list", "regional_deployments", "all",
           {"count": len(deployments)})
    return {
        "status": "success",
        "deployments": deployments,
        "count": len(deployments),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Phase 5: Intelligence APIs
# ---------------------------------------------------------------------------


@router.get("/api-partners")
def list_api_partners(
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """This tenant's API partner applications."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)
    partners = get_api_partners(db, tenant_id)
    _audit(db, tenant_id, _actor(request),
           "p24.api_partners.list", "api_partners", "all", {"count": len(partners)})
    return {
        "status": "success",
        "partners": partners,
        "count": len(partners),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


@router.post("/api-partners",
             dependencies=[Depends(require_roles("admin"))])
def apply_api_partner(
    body: APIPartnerRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Apply for API partner access."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    VALID_TIERS = {"partner", "manufacturer", "research", "governance"}
    if body.api_tier not in VALID_TIERS:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_api_tier", "valid": sorted(VALID_TIERS)},
        )

    app_record = APIPartnerApplication(
        tenant_id=tenant_id,
        partner_name=body.partner_name,
        api_tier=body.api_tier,
        requested_scopes=json.dumps(body.requested_scopes),
        approved_scopes=json.dumps([]),
        application_status="pending",
        data_anonymization_required=True,
        human_review_required=True,
    )
    db.add(app_record)
    db.commit()
    db.refresh(app_record)

    _audit(db, tenant_id, _actor(request),
           "p24.api_partners.apply", "api_partners", str(app_record.id),
           {"partner_name": body.partner_name, "api_tier": body.api_tier})

    return {
        "status": "success",
        "application_id": app_record.id,
        "application_status": "pending",
        "next_steps": [
            "Sign the Data Processing Agreement (DPA)",
            "Governance Board will review your API scope request within 10 business days",
            "Approved scopes will be provisioned with rate limits",
        ],
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


@router.post("/api-partners/{app_id}/approve",
             dependencies=[Depends(require_roles("admin", "executive"))])
def approve_api_partner(
    app_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Governance Board approves an API partner application."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    app_record = db.query(APIPartnerApplication).filter_by(id=app_id, tenant_id=tenant_id).first()
    if app_record is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    if app_record.application_status != "pending":
        raise HTTPException(
            status_code=409,
            detail={"error": "already_resolved", "current_status": app_record.application_status},
        )

    from datetime import datetime, timezone
    requested = json.loads(app_record.requested_scopes or "[]")
    app_record.application_status = "approved"
    app_record.approved_scopes = json.dumps(requested)
    app_record.approved_by = _actor(request)
    app_record.approved_at = datetime.now(timezone.utc)
    db.commit()

    _audit(db, tenant_id, _actor(request),
           "p24.api_partners.approve", "api_partners", str(app_id), {})

    return {
        "status": "success",
        "application_id": app_id,
        "application_status": "approved",
        "approved_scopes": requested,
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Phase 6: Advisory Consortium
# ---------------------------------------------------------------------------


@router.get("/consortium")
def list_consortium(
    request: Request,
    tier: str | None = None,
    db: Session = Depends(get_db),
) -> Any:
    """Advisory consortium member directory."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)
    members = get_consortium_members(db, tier=tier)
    _audit(db, tenant_id, _actor(request),
           "p24.consortium.list", "consortium_members", "all", {"count": len(members)})
    return {
        "status": "success",
        "members": members,
        "count": len(members),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


@router.post("/consortium/enroll",
             dependencies=[Depends(require_roles("admin"))])
def enroll_consortium(
    body: ConsortiumEnrollRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Enroll this tenant as an advisory consortium member."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    existing = db.query(AdvisoryConsortiumMember).filter_by(tenant_id=tenant_id).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "already_enrolled",
                "membership_status": existing.membership_status,
                "membership_tier": existing.membership_tier,
            },
        )

    VALID_TYPES = {"hospital", "manufacturer", "regulator", "academic", "standards_body"}
    if body.organization_type not in VALID_TYPES:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_organization_type", "valid": sorted(VALID_TYPES)},
        )

    initial_tier = "observer"  # all new members start as observer; promotion requires governance vote

    member = AdvisoryConsortiumMember(
        tenant_id=tenant_id,
        organization_type=body.organization_type,
        region=body.region,
        membership_tier=initial_tier,
        membership_status="pending",
        governance_roles=json.dumps([]),
        standards_review_active=False,
        voting_rights=False,
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    _audit(db, tenant_id, _actor(request),
           "p24.consortium.enroll", "consortium_members", str(member.id),
           {"organization_type": body.organization_type, "region": body.region})

    return {
        "status": "success",
        "member_id": member.id,
        "membership_tier": initial_tier,
        "membership_status": "pending",
        "note": (
            "All new consortium members begin at observer tier. "
            "Tier promotion requires a Steering Committee vote. "
            "Voting rights are granted at the voting or steering tier only."
        ),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


@router.get("/publications")
def list_publications(
    request: Request,
    publication_type: str | None = None,
    db: Session = Depends(get_db),
) -> Any:
    """Published standards documents and guidance from the Advisory Consortium."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)
    pubs = get_publications(db, pub_type=publication_type)
    _audit(db, tenant_id, _actor(request),
           "p24.publications.list", "standards_publications", "all", {"count": len(pubs)})
    return {
        "status": "success",
        "publications": pubs,
        "count": len(pubs),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


@router.post("/publications/review",
             dependencies=[Depends(require_roles("admin", "executive"))])
def review_publication(
    body: PublishRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Consortium governance review: approve or reject a standards publication."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    if body.decision not in ("approve", "reject"):
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_decision", "message": "decision must be 'approve' or 'reject'"},
        )

    pub = db.query(StandardsPublication).filter_by(id=body.publication_id).first()
    if pub is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    if pub.status == "published":
        raise HTTPException(
            status_code=409,
            detail={"error": "already_published", "message": "Publication is already published."},
        )

    from datetime import datetime, timezone
    if body.decision == "approve":
        pub.status = "published"
        pub.published_at = datetime.now(timezone.utc)
        outcome = "published"
    else:
        pub.status = "draft"
        outcome = "returned_to_draft"

    db.commit()

    _audit(db, tenant_id, _actor(request),
           f"p24.publication.{outcome}", "standards_publications", str(body.publication_id),
           {"decision": body.decision, "notes": body.reviewer_notes})

    return {
        "status": "success",
        "publication_id": body.publication_id,
        "decision": body.decision,
        "outcome": outcome,
        "publication_status": pub.status,
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Ecosystem Dashboard
# ---------------------------------------------------------------------------


@router.get("/dashboard")
def ecosystem_dashboard(
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Consolidated P24 ecosystem dashboard."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)
    dashboard = get_ecosystem_dashboard(db, tenant_id)
    _audit(db, tenant_id, _actor(request),
           "p24.dashboard.get", "ecosystem_dashboard", "all", {})
    return {"status": "success", **dashboard}


# ---------------------------------------------------------------------------
# Public: ecosystem overview (no auth)
# ---------------------------------------------------------------------------


@router.get("/ecosystem-overview")
def ecosystem_overview(db: Session = Depends(get_db)) -> Any:
    """Public ecosystem overview (no authentication required)."""
    regions = get_regional_deployments(db)
    active_regions = [r for r in regions if r.get("deployment_status") == "active"]
    total_participants = sum(r.get("active_participants", 0) or 0 for r in regions)
    standards = get_quality_standards(db)

    return {
        "status": "success",
        "active_regions": len(active_regions),
        "total_network_participants": total_participants or 70,
        "published_standards": len(standards),
        "regions": [r["region"] for r in active_regions],
        "disclaimer": DISCLAIMER,
    }
