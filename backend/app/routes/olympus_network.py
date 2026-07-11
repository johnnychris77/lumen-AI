"""v5.1 — LumenAI Network: Project Olympus — Autonomous Healthcare
Intelligence Network routes.

Frontend route: /network. API prefix: /api/olympus.

Uses `tenant_authz.require_tenant_roles` (real `TenantMembership`
verification), consistent with Athena (v4.8), Phoenix (v4.9), and
Infinity (v5.0) -- Olympus is a new module and does not carry forward the
older, unverified `_tenant()` header-trust pattern.

  * GET  /participants, GET /participants/{tenant_id},
    GET  /directory-summary                                       — Section 1
  * POST /trust/{tenant_id}/compute, GET /trust/{tenant_id}/history,
    GET  /trust/leaderboard                                        — Section 2
  * POST /exchange/packages, POST /exchange/packages/{id}/governance-review,
    POST /exchange/packages/{id}/publish, GET /exchange/packages/{id},
    GET  /exchange/packages, GET /exchange/packages/mine            — Sections 3, 4
  * GET  /observatory/contamination-trends, /instrument-trends,
    /quality-initiatives, /research, /summary                      — Section 5
  * POST /models, GET /models, GET /models/{id},
    PATCH /models/{id}/validation-status, GET /models/{id}/version-chain — Section 6
  * POST /models/{id}/certification/start, /advance,
    GET  /models/{id}/certification, GET /certification-registry    — Section 7
  * GET  /marketplace/summary                                       — Section 8
  * POST /governance/cases, POST /governance/cases/{id}/decide,
    GET  /governance/cases/{id}, GET /governance/cases,
    GET  /governance/summary                                        — Section 9
  * GET  /summary                                                    — umbrella
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.services import (
    olympus_certification_registry_service,
    olympus_exchange_service,
    olympus_governance_council_service,
    olympus_marketplace_service,
    olympus_model_registry_service,
    olympus_network_identity_service,
    olympus_network_summary_service,
    olympus_observatory_service,
    olympus_trust_service,
)
from app.tenant_authz import require_tenant_roles

router = APIRouter(prefix="/api/olympus", tags=["olympus"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user: dict) -> str:
    return current_user["tenant_id"]


def _actor(current_user: dict) -> str:
    return current_user["user_email"]


# ---------------------------------------------------------------------------
# Section 1 — Network Identity
# ---------------------------------------------------------------------------


@router.get("/participants")
def get_participants(
    organization_type: str = Query(""), active_only: bool = Query(True),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    try:
        return {"participants": olympus_network_identity_service.list_participants(
            db, organization_type=organization_type, active_only=active_only,
        )}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/participants/{tenant_id}")
def get_participant(tenant_id: str, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    result = olympus_network_identity_service.get_participant(db, tenant_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Network participant '{tenant_id}' not found.")
    return result


@router.get("/directory-summary")
def get_directory_summary(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return olympus_network_identity_service.network_directory_summary(db)


# ---------------------------------------------------------------------------
# Section 2 — Trust Network
# ---------------------------------------------------------------------------


@router.post("/trust/{tenant_id}/compute")
def post_compute_trust(tenant_id: str, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return olympus_trust_service.compute_and_record_trust_snapshot(db, tenant_id)


@router.get("/trust/{tenant_id}/history")
def get_trust_history(
    tenant_id: str, limit: int = Query(20, le=100),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {"history": olympus_trust_service.trust_history(db, tenant_id, limit=limit)}


@router.get("/trust/leaderboard")
def get_trust_leaderboard(
    top_n: int = Query(10, le=50), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {"leaderboard": olympus_trust_service.network_trust_leaderboard(db, top_n=top_n)}


# ---------------------------------------------------------------------------
# Sections 3, 4 — Global Intelligence Exchange & Healthcare Intelligence Exchange
# ---------------------------------------------------------------------------


@router.post("/exchange/packages", status_code=201)
def post_exchange_package(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        return olympus_exchange_service.submit_package(
            db, tenant_id, package_type=payload.get("package_type", ""), title=payload.get("title", ""),
            description=payload.get("description", ""), content_ref_type=payload.get("content_ref_type", ""),
            content_ref_id=payload.get("content_ref_id"),
            no_phi_confirmed=bool(payload.get("no_phi_confirmed", False)),
            no_identifiable_customer_data_confirmed=bool(payload.get("no_identifiable_customer_data_confirmed", False)),
            submitted_by=actor,
        )
    except (ValueError, olympus_exchange_service.InvalidPackageStateError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/exchange/packages/{package_id}/governance-review")
def post_exchange_governance_review(
    package_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    actor = _actor(current_user)
    try:
        return olympus_exchange_service.governance_review_package(
            db, package_id, decision=payload.get("decision", ""), reviewed_by=actor,
            governance_case_id=payload.get("governance_case_id"),
        )
    except olympus_exchange_service.UnknownExchangePackageError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, olympus_exchange_service.InvalidPackageStateError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/exchange/packages/{package_id}/publish")
def post_exchange_publish(package_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    actor = _actor(current_user)
    try:
        return olympus_exchange_service.publish_package(db, package_id, published_by=actor)
    except olympus_exchange_service.UnknownExchangePackageError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except olympus_exchange_service.InvalidPackageStateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/exchange/packages/mine")
def get_my_exchange_packages(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"packages": olympus_exchange_service.list_organization_packages(db, _tenant(current_user))}


@router.get("/exchange/packages/{package_id}")
def get_exchange_package(package_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return olympus_exchange_service.get_package(db, package_id, requesting_tenant_id=_tenant(current_user))
    except olympus_exchange_service.UnknownExchangePackageError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/exchange/packages")
def get_exchange_packages(
    package_type: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    try:
        return {"packages": olympus_exchange_service.list_published_packages(
            db, package_type=package_type, requesting_tenant_id=_tenant(current_user),
        )}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 5 — Global Research Observatory
# ---------------------------------------------------------------------------


@router.get("/observatory/contamination-trends")
def get_observatory_contamination_trends(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"trends": olympus_observatory_service.emerging_contamination_trends(db)}


@router.get("/observatory/instrument-trends")
def get_observatory_instrument_trends(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"trends": olympus_observatory_service.instrument_performance_trends(db)}


@router.get("/observatory/quality-initiatives")
def get_observatory_quality_initiatives(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"initiatives": olympus_observatory_service.quality_improvement_initiatives(db)}


@router.get("/observatory/research")
def get_observatory_research(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"research": olympus_observatory_service.published_research(db)}


@router.get("/observatory/summary")
def get_observatory_summary(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return olympus_observatory_service.observatory_summary(db)


# ---------------------------------------------------------------------------
# Section 6 — AI Model Registry
# ---------------------------------------------------------------------------


@router.post("/models", status_code=201)
def post_model(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    actor = _actor(current_user)
    try:
        return olympus_model_registry_service.register_model(
            db, model_type=payload.get("model_type", ""), name=payload.get("name", ""),
            version=payload.get("version", "0.1.0"), clinical_scope=payload.get("clinical_scope", ""),
            evidence=payload.get("evidence"), performance_metrics=payload.get("performance_metrics"),
            registered_by=actor, supersedes_id=payload.get("supersedes_id"),
        )
    except (ValueError, olympus_model_registry_service.UnknownModelRegistryEntryError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/models")
def get_models(
    model_type: str = Query(""), validation_status: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    try:
        return {"models": olympus_model_registry_service.list_models(
            db, model_type=model_type, validation_status=validation_status,
        )}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/models/{model_id}")
def get_model(model_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return olympus_model_registry_service.get_model(db, model_id)
    except olympus_model_registry_service.UnknownModelRegistryEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/models/{model_id}/validation-status")
def patch_model_validation_status(
    model_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    try:
        return olympus_model_registry_service.set_validation_status(db, model_id, validation_status=payload.get("validation_status", ""))
    except olympus_model_registry_service.UnknownModelRegistryEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/models/{model_id}/version-chain")
def get_model_version_chain(model_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return {"chain": olympus_model_registry_service.version_chain(db, model_id)}
    except olympus_model_registry_service.UnknownModelRegistryEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 7 — Certification Registry
# ---------------------------------------------------------------------------


@router.post("/models/{model_id}/certification/start")
def post_model_certification_start(model_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return olympus_certification_registry_service.start_model_certification(db, model_id)
    except olympus_model_registry_service.UnknownModelRegistryEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/models/{model_id}/certification/advance")
def post_model_certification_advance(
    model_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    actor = _actor(current_user)
    try:
        return olympus_certification_registry_service.advance_model_certification(
            db, model_id, decided_by=actor, decided_role=payload.get("decided_role", ""),
            decision=payload.get("decision", ""), notes=payload.get("notes", ""),
        )
    except olympus_model_registry_service.UnknownModelRegistryEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/models/{model_id}/certification")
def get_model_certification(model_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return olympus_certification_registry_service.get_model_certification_status(db, model_id)
    except olympus_model_registry_service.UnknownModelRegistryEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/certification-registry")
def get_certification_registry(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return olympus_certification_registry_service.certification_registry(db)


# ---------------------------------------------------------------------------
# Section 8 — Innovation Marketplace
# ---------------------------------------------------------------------------


@router.get("/marketplace/summary")
def get_marketplace_summary(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return olympus_marketplace_service.innovation_marketplace_summary(db)


# ---------------------------------------------------------------------------
# Section 9 — Network Governance Council
# ---------------------------------------------------------------------------


@router.post("/governance/cases", status_code=201)
def post_governance_case(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    actor = _actor(current_user)
    try:
        return olympus_governance_council_service.file_case(
            db, case_type=payload.get("case_type", ""), title=payload.get("title", ""),
            description=payload.get("description", ""), filed_by=actor,
            involved_tenant_ids=payload.get("involved_tenant_ids"), meeting_id=payload.get("meeting_id"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/governance/cases/{case_id}/decide")
def post_governance_case_decide(
    case_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    actor = _actor(current_user)
    try:
        return olympus_governance_council_service.decide_case(
            db, case_id, decision=payload.get("decision", ""), resolution=payload.get("resolution", ""), resolved_by=actor,
        )
    except olympus_governance_council_service.UnknownGovernanceCaseError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/governance/cases/{case_id}")
def get_governance_case(case_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return olympus_governance_council_service.get_case(db, case_id)
    except olympus_governance_council_service.UnknownGovernanceCaseError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/governance/cases")
def get_governance_cases(
    case_type: str = Query(""), status: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    try:
        return {"cases": olympus_governance_council_service.list_cases(db, case_type=case_type, status=status)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/governance/summary")
def get_governance_summary(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return olympus_governance_council_service.council_summary(db)


# ---------------------------------------------------------------------------
# Umbrella
# ---------------------------------------------------------------------------


@router.get("/summary")
def get_network_summary(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return olympus_network_summary_service.network_summary(db)
