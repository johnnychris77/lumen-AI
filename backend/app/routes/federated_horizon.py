"""v3.4 — Project Horizon: Federated Clinical Intelligence & Global
Learning Network routes.

Routes: /research, /governance (frontend). API prefix: /api/horizon.

  * POST /participation/enroll, GET /participation/status,
    POST /participation/withdraw,
    POST /participation/contribution-categories               — Section 1
  * GET /knowledge-graph/local, GET /knowledge-graph/enterprise,
    POST /knowledge-graph/global/generate, GET /knowledge-graph/global — Section 2
  * POST /contributions, GET /contributions,
    POST /contributions/{id}/approve|reject|revise,
    GET /contributions/{ref}/versions                          — Section 3
  * POST /federated-signals/generate, GET /federated-signals    — Section 4
  * GET /benchmarks, GET /benchmarks/percentile                 — Section 5
  * POST /emerging-trends/detect, GET /emerging-trends,
    POST /emerging-trends/{id}/acknowledge                     — Section 6
  * GET /research/portal                                        — Section 7
  * POST /evidence, GET /evidence, GET /evidence/{id},
    POST /evidence/link, GET /evidence/for/{source_type}/{source_id} — Section 8
  * GET /governance/overview, GET /governance/pending-approvals  — Section 9
  * GET /ai-improvement/suggestions                              — Section 10
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.federated_horizon import BENCHMARK_METRICS
from app.tenant_authz import assert_tenant_membership
from app.services import (
    horizon_ai_improvement_service,
    horizon_benchmark_service,
    horizon_contribution_service,
    horizon_evidence_service,
    horizon_federated_signal_service,
    horizon_governance_service,
    horizon_knowledge_graph_service,
    horizon_participation_service,
    horizon_research_portal_service,
    horizon_trend_detection_service,
)
from app.services.horizon_contribution_service import InvalidContributionStateError, UnknownContributionError

router = APIRouter(prefix="/api/horizon", tags=["horizon"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user, request: Request, db: Session) -> str:
    """Resolve the tenant_id for a Horizon (cross-hospital intelligence) request.

    tenant_id is read from the client-supplied header, but it is never
    trusted on its own -- it must correspond to an enabled TenantMembership
    row for the authenticated user, or the request is rejected with 403.
    Without this check, an authenticated user from one hospital could set
    X-Tenant-Id to a different hospital's tenant id and read (or, worse,
    enroll/withdraw/approve on behalf of) that hospital's cross-hospital
    intelligence data.
    """
    tenant_id = getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)
    assert_tenant_membership(db, tenant_id=tenant_id, user_email=_actor(current_user))
    return tenant_id


def _actor(current_user) -> str:
    return getattr(current_user, "email", None) or getattr(current_user, "username", "unknown")


# ---------------------------------------------------------------------------
# Section 1 — Federated Knowledge Framework: participation
# ---------------------------------------------------------------------------


@router.post("/participation/enroll")
def post_enroll(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request, db)
    result = horizon_participation_service.enroll_organization(
        db, tenant_id, participant_type=payload["participant_type"], region=payload["region"],
        contribution_categories=payload.get("contribution_categories", []), agreed_by=_actor(current_user),
        sharing_scope=payload.get("sharing_scope", "benchmark"),
    )
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user), actor_role="",
        action_type="horizon.participation_enrolled", resource_type="gsin_participants", resource_id=tenant_id,
        details={"participant_type": payload["participant_type"], "region": payload["region"]},
    )
    return result


@router.get("/participation/status")
def get_participation_status(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request, db)
    return horizon_participation_service.get_participation_status(db, tenant_id)


@router.post("/participation/withdraw")
def post_withdraw(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    tenant_id = _tenant(current_user, request, db)
    result = horizon_participation_service.withdraw_organization(db, tenant_id, withdrawn_by=_actor(current_user))
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user), actor_role="",
        action_type="horizon.participation_withdrawn", resource_type="gsin_participants", resource_id=tenant_id, details={},
    )
    return result


@router.post("/participation/contribution-categories")
def post_contribution_categories(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request, db)
    result = horizon_participation_service.update_contribution_categories(db, tenant_id, payload.get("categories", []))
    if result is None:
        raise HTTPException(status_code=404, detail="Organization is not enrolled.")
    return result


# ---------------------------------------------------------------------------
# Section 2 — Global Knowledge Graph
# ---------------------------------------------------------------------------


@router.get("/knowledge-graph/local")
def get_local_graph(
    request: Request, category: str = Query("instrument"), query: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request, db)
    return horizon_knowledge_graph_service.local_graph_summary(db, tenant_id, category=category, query=query)


@router.get("/knowledge-graph/enterprise")
def get_enterprise_graph(current_user=Depends(require_roles(*_ALL_ROLES))):
    return horizon_knowledge_graph_service.enterprise_graph_reference()


@router.post("/knowledge-graph/global/generate")
def post_generate_global_graph(db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    return {"edges": horizon_knowledge_graph_service.compute_global_knowledge_graph(db)}


@router.get("/knowledge-graph/global")
def get_global_graph(source_node_type: str = Query(""), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return {"edges": horizon_knowledge_graph_service.list_global_graph(db, source_node_type=source_node_type)}


# ---------------------------------------------------------------------------
# Section 3 — Knowledge Contribution Workflow
# ---------------------------------------------------------------------------


@router.post("/contributions")
def post_submit_contribution(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request, db)
    try:
        result = horizon_contribution_service.submit_contribution(
            db, tenant_id, contribution_type=payload["contribution_type"], category=payload.get("category", ""),
            title=payload["title"], body=payload["body"], submitted_by=_actor(current_user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user), actor_role="",
        action_type="horizon.contribution_submitted", resource_type="horizon_knowledge_contribution", resource_id=str(result["id"]),
        details={"contribution_type": payload["contribution_type"]},
    )
    return result


@router.get("/contributions")
def get_contributions(
    request: Request, approval_status: str = Query(""), contribution_type: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request, db)
    try:
        return {"contributions": horizon_contribution_service.list_contributions(
            db, approval_status=approval_status, contribution_type=contribution_type, requesting_tenant_id=tenant_id,
        )}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/contributions/{contribution_id}/approve")
def post_approve_contribution(
    contribution_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    try:
        result = horizon_contribution_service.approve_contribution(db, contribution_id, approved_by=_actor(current_user))
    except UnknownContributionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidContributionStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    # Approval is a global leadership action gated by role, not scoped to any
    # one tenant's data (contribution_id is looked up globally above) -- the
    # tenant_id here is only descriptive audit metadata for "which org
    # context this approver represented," so it doesn't need the
    # membership-verified _tenant() used by the tenant-data-scoping routes
    # in this file.
    tenant_id = get_request_tenant_id(request)
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user), actor_role="",
        action_type="horizon.contribution_approved", resource_type="horizon_knowledge_contribution", resource_id=str(contribution_id), details={},
    )
    return result


@router.post("/contributions/{contribution_id}/reject")
def post_reject_contribution(
    contribution_id: int, payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    try:
        result = horizon_contribution_service.reject_contribution(
            db, contribution_id, rejected_by=_actor(current_user), reason=payload.get("reason", ""),
        )
    except UnknownContributionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidContributionStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return result


@router.post("/contributions/{contribution_id}/revise")
def post_revise_contribution(
    contribution_id: int, payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    try:
        return horizon_contribution_service.revise_contribution(
            db, contribution_id, updated_by=_actor(current_user), title=payload.get("title"), body=payload.get("body"),
        )
    except UnknownContributionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidContributionStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/contributions/{contribution_ref}/versions")
def get_contribution_versions(contribution_ref: str, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    try:
        return {"versions": horizon_contribution_service.get_version_history(db, contribution_ref)}
    except UnknownContributionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 4 — Federated Learning Signals
# ---------------------------------------------------------------------------


@router.post("/federated-signals/generate")
def post_generate_federated_signals(db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    return {"signals": horizon_federated_signal_service.generate_all_federated_signals(db)}


@router.get("/federated-signals")
def get_federated_signals(
    signal_category: str = Query(""), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    return {"signals": horizon_federated_signal_service.list_federated_signals(db, signal_category=signal_category)}


# ---------------------------------------------------------------------------
# Section 5 — Global Benchmarking
# ---------------------------------------------------------------------------


@router.get("/benchmarks")
def get_benchmarks(db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return {"benchmarks": horizon_benchmark_service.compute_all_horizon_benchmarks(db)}


@router.get("/benchmarks/percentile")
def get_benchmark_percentile(
    request: Request, metric_name: str = Query(...), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    if metric_name not in BENCHMARK_METRICS:
        raise HTTPException(status_code=422, detail=f"metric_name must be one of {BENCHMARK_METRICS}")
    tenant_id = _tenant(current_user, request, db)
    return horizon_benchmark_service.get_tenant_benchmark_percentile(db, tenant_id, metric_name)


# ---------------------------------------------------------------------------
# Section 6 — Emerging Trend Detection
# ---------------------------------------------------------------------------


@router.post("/emerging-trends/detect")
def post_detect_emerging_trends(db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    return {"trends": horizon_trend_detection_service.detect_emerging_trends(db)}


@router.get("/emerging-trends")
def get_emerging_trends(
    request: Request, mine_only: bool = Query(False), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request, db) if mine_only else ""
    return {"trends": horizon_trend_detection_service.list_emerging_trends(db, tenant_id=tenant_id)}


@router.post("/emerging-trends/{trend_id}/acknowledge")
def post_acknowledge_trend(
    trend_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request, db)
    result = horizon_trend_detection_service.acknowledge_trend(db, tenant_id, trend_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Trend {trend_id} not found.")
    return result


# ---------------------------------------------------------------------------
# Section 7 — Research Portal
# ---------------------------------------------------------------------------


@router.get("/research/portal")
def get_research_portal(db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return horizon_research_portal_service.research_portal_summary(db)


# ---------------------------------------------------------------------------
# Section 8 — Clinical Evidence Repository
# ---------------------------------------------------------------------------


@router.post("/evidence")
def post_add_evidence(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    # Only resolve (and membership-verify) a tenant_id when the evidence is
    # actually going to be scoped as private to that tenant -- shared/public
    # evidence isn't tenant data, so it shouldn't require the submitter to
    # have a matching TenantMembership for whatever X-Tenant-Id they sent.
    is_private = bool(payload.get("private", False))
    tenant_id = _tenant(current_user, request, db) if is_private else ""
    try:
        return horizon_evidence_service.add_evidence(
            db, evidence_type=payload["evidence_type"], title=payload["title"], citation_text=payload["citation_text"],
            source=payload.get("source", ""), url=payload.get("url", ""),
            tenant_id=tenant_id, added_by=_actor(current_user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/evidence")
def get_evidence_list(
    request: Request, evidence_type: str = Query(""), include_private: bool = Query(True), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request, db) if include_private else ""
    return {"evidence": horizon_evidence_service.list_evidence(db, evidence_type=evidence_type, tenant_id=tenant_id)}


@router.get("/evidence/{evidence_id}")
def get_evidence_detail(evidence_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    result = horizon_evidence_service.get_evidence(db, evidence_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found.")
    return result


@router.post("/evidence/link")
def post_link_evidence(
    payload: dict, current_user=Depends(require_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    try:
        return horizon_evidence_service.link_evidence_to_recommendation(
            db, source_type=payload["source_type"], source_id=str(payload["source_id"]), evidence_id=payload["evidence_id"],
            relevance_note=payload.get("relevance_note", ""), linked_by=_actor(current_user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/evidence/for/{source_type}/{source_id}")
def get_evidence_for_recommendation(source_type: str, source_id: str, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return {"evidence": horizon_evidence_service.list_evidence_for_recommendation(db, source_type, source_id)}


# ---------------------------------------------------------------------------
# Section 9 — Governance Center
# ---------------------------------------------------------------------------


@router.get("/governance/overview")
def get_governance_overview(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    tenant_id = _tenant(current_user, request, db)
    return horizon_governance_service.governance_overview(db, tenant_id)


@router.get("/governance/pending-approvals")
def get_pending_approvals(db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    return {"pending": horizon_governance_service.list_all_pending_approvals(db)}


# ---------------------------------------------------------------------------
# Section 10 — Global AI Improvement
# ---------------------------------------------------------------------------


@router.get("/ai-improvement/suggestions")
def get_ai_improvement_suggestions(db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return horizon_ai_improvement_service.improvement_summary(db)
