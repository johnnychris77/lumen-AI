"""v5.3 — LumenAI Network: Project Genesis AI — Global Sterile Processing
Intelligence Cloud routes.

**"Project Genesis AI" (this file) is not "Project Genesis" (v4.0,
`platform_core.py`)** — see `app/models/genesis_ai_intelligence_cloud.py`
for the full naming disambiguation.

Frontend route: /intelligence-cloud. API prefix: /api/genesis-ai.

Uses `tenant_authz.require_tenant_roles` (real `TenantMembership`
verification), consistent with Athena/Phoenix/Infinity/Olympus/GuardianX.
Clinical Evidence Cloud CRUD already lives at `/api/horizon/evidence*`
(Horizon, v3.4) — this router only exposes a summary, never a duplicate
CRUD surface. Instrument Intelligence API (Section 7) lives at
`/api/v1/instruments`, `/api/v1/anatomy`, `/api/v1/evidence` (extended
`nexus_api_gateway.py`), not under this prefix.

  * PATCH /instruments/{id}/profile, GET /instruments/{id}/profile,
    GET  /instruments/families/{family}                             — Section 1
  * POST /anatomy-profiles, GET /anatomy-profiles/{id},
    GET  /anatomy-profiles, GET /anatomy-profiles/summary            — Section 2
  * GET  /evidence-cloud/summary                                     — Section 3
  * POST /manufacturer-updates, POST /manufacturer-updates/{id}/review,
    GET  /manufacturer-updates/{id}, GET /manufacturer-updates/{id}/version-chain,
    GET  /manufacturer-updates                                       — Section 4
  * GET  /learning-engine/summary                                    — Section 5
  * GET  /research-hub/summary, PATCH /participants/{tenant_id}/research-opt-in — Section 6
  * POST /intelligence-exchange/research-dataset-packages,
    GET  /intelligence-exchange/summary                              — Section 8
  * GET  /standards-observatory/summary                               — Section 9
  * GET  /summary                                                     — umbrella
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.p24_standards import AdvisoryConsortiumMember
from app.services import (
    genesis_ai_anatomy_registry_service,
    genesis_ai_evidence_cloud_service,
    genesis_ai_instrument_registry_service,
    genesis_ai_intelligence_cloud_summary_service,
    genesis_ai_intelligence_exchange_service,
    genesis_ai_learning_engine_service,
    genesis_ai_manufacturer_portal_service,
    genesis_ai_research_hub_service,
    genesis_ai_standards_observatory_service,
)
from app.services import olympus_exchange_service
from app.tenant_authz import require_tenant_roles

router = APIRouter(prefix="/api/genesis-ai", tags=["genesis-ai"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user: dict) -> str:
    return current_user["tenant_id"]


def _actor(current_user: dict) -> str:
    return current_user["user_email"]


# ---------------------------------------------------------------------------
# Section 1 — Global Instrument Registry
# ---------------------------------------------------------------------------


@router.patch("/instruments/{instrument_id}/profile")
def patch_instrument_profile(
    instrument_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    try:
        return genesis_ai_instrument_registry_service.set_instrument_profile(
            db, instrument_id, instrument_family=payload.get("instrument_family"),
            ifu_versions=payload.get("ifu_versions"), anatomy_profile_id=payload.get("anatomy_profile_id"),
            inspection_zones=payload.get("inspection_zones"), digital_twin_template_ref=payload.get("digital_twin_template_ref"),
            baseline_template_ref=payload.get("baseline_template_ref"), failure_modes=payload.get("failure_modes"),
            repair_guidance=payload.get("repair_guidance"), knowledge_references=payload.get("knowledge_references"),
        )
    except genesis_ai_instrument_registry_service.UnknownRegistryInstrumentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/instruments/{instrument_id}/profile")
def get_instrument_profile(instrument_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return genesis_ai_instrument_registry_service.get_instrument_profile(db, instrument_id)
    except genesis_ai_instrument_registry_service.UnknownRegistryInstrumentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/instruments/families/{instrument_family}")
def get_instruments_by_family(instrument_family: str, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"instruments": genesis_ai_instrument_registry_service.list_instruments_by_family(db, instrument_family)}


# ---------------------------------------------------------------------------
# Section 2 — Global Anatomy Registry
# ---------------------------------------------------------------------------


@router.post("/anatomy-profiles", status_code=201)
def post_anatomy_profile(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return genesis_ai_anatomy_registry_service.create_anatomy_profile(
            db, profile_type=payload.get("profile_type", ""), name=payload.get("name", ""),
            description=payload.get("description", ""), standard_terminology=payload.get("standard_terminology"),
            zones=payload.get("zones"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/anatomy-profiles/summary")
def get_anatomy_profiles_summary(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return genesis_ai_anatomy_registry_service.anatomy_registry_summary(db)


@router.get("/anatomy-profiles/{profile_id}")
def get_anatomy_profile(profile_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return genesis_ai_anatomy_registry_service.get_anatomy_profile(db, profile_id)
    except genesis_ai_anatomy_registry_service.UnknownAnatomyProfileError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/anatomy-profiles")
def get_anatomy_profiles(
    profile_type: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    try:
        return {"profiles": genesis_ai_anatomy_registry_service.list_anatomy_profiles(db, profile_type=profile_type)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 3 — Clinical Evidence Cloud
# ---------------------------------------------------------------------------


@router.get("/evidence-cloud/summary")
def get_evidence_cloud_summary(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return genesis_ai_evidence_cloud_service.evidence_cloud_summary(db)


# ---------------------------------------------------------------------------
# Section 4 — Manufacturer Knowledge Portal
# ---------------------------------------------------------------------------


@router.post("/manufacturer-updates", status_code=201)
def post_manufacturer_update(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        return genesis_ai_manufacturer_portal_service.submit_update(
            db, tenant_id, update_type=payload.get("update_type", ""), title=payload.get("title", ""),
            version=payload.get("version", "1.0"), body=payload.get("body", ""),
            instrument_category=payload.get("instrument_category", ""), submitted_by=actor,
            supersedes_id=payload.get("supersedes_id"),
        )
    except genesis_ai_manufacturer_portal_service.UnknownManufacturerUpdateError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/manufacturer-updates/{update_id}/review")
def post_manufacturer_update_review(
    update_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    actor = _actor(current_user)
    try:
        return genesis_ai_manufacturer_portal_service.review_update(db, update_id, decision=payload.get("decision", ""), reviewed_by=actor)
    except genesis_ai_manufacturer_portal_service.UnknownManufacturerUpdateError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, genesis_ai_manufacturer_portal_service.InvalidManufacturerUpdateStateError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/manufacturer-updates/{update_id}/version-chain")
def get_manufacturer_update_version_chain(update_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return {"chain": genesis_ai_manufacturer_portal_service.version_chain(db, update_id)}
    except genesis_ai_manufacturer_portal_service.UnknownManufacturerUpdateError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/manufacturer-updates/{update_id}")
def get_manufacturer_update(update_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return genesis_ai_manufacturer_portal_service.get_update(db, update_id)
    except genesis_ai_manufacturer_portal_service.UnknownManufacturerUpdateError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/manufacturer-updates")
def get_manufacturer_updates(
    manufacturer_tenant_id: str = Query(""), update_type: str = Query(""), status: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    try:
        return {"updates": genesis_ai_manufacturer_portal_service.list_updates(
            db, manufacturer_tenant_id=manufacturer_tenant_id, update_type=update_type, status=status,
        )}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 5 — Global Learning Engine
# ---------------------------------------------------------------------------


@router.get("/learning-engine/summary")
def get_learning_engine_summary(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return genesis_ai_learning_engine_service.global_learning_summary(db, _tenant(current_user))


# ---------------------------------------------------------------------------
# Section 6 — Research Collaboration Hub
# ---------------------------------------------------------------------------


@router.get("/research-hub/summary")
def get_research_hub_summary(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return genesis_ai_research_hub_service.research_hub_summary(db)


@router.patch("/participants/{tenant_id}/research-opt-in")
def patch_research_opt_in(
    tenant_id: str, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    member = db.query(AdvisoryConsortiumMember).filter(AdvisoryConsortiumMember.tenant_id == tenant_id).first()
    if member is None:
        raise HTTPException(status_code=404, detail=f"Consortium member '{tenant_id}' not found.")
    member.research_opt_in = bool(payload.get("research_opt_in", False))
    db.commit()
    db.refresh(member)
    return {"tenant_id": tenant_id, "research_opt_in": member.research_opt_in}


# ---------------------------------------------------------------------------
# Section 8 — Clinical Intelligence Exchange
# ---------------------------------------------------------------------------


@router.post("/intelligence-exchange/research-dataset-packages", status_code=201)
def post_research_dataset_package(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        return genesis_ai_intelligence_exchange_service.submit_research_dataset_package(
            db, tenant_id, dataset_ref=payload.get("dataset_ref"), title=payload.get("title", ""),
            description=payload.get("description", ""), no_phi_confirmed=bool(payload.get("no_phi_confirmed", False)),
            no_identifiable_customer_data_confirmed=bool(payload.get("no_identifiable_customer_data_confirmed", False)),
            submitted_by=actor,
        )
    except olympus_exchange_service.InvalidPackageStateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/intelligence-exchange/summary")
def get_intelligence_exchange_summary(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return genesis_ai_intelligence_exchange_service.intelligence_exchange_summary(db)


# ---------------------------------------------------------------------------
# Section 9 — Global Standards Observatory
# ---------------------------------------------------------------------------


@router.get("/standards-observatory/summary")
def get_standards_observatory_summary(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return genesis_ai_standards_observatory_service.observatory_summary(db, _tenant(current_user))


# ---------------------------------------------------------------------------
# Umbrella
# ---------------------------------------------------------------------------


@router.get("/summary")
def get_intelligence_cloud_summary(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return genesis_ai_intelligence_cloud_summary_service.intelligence_cloud_summary(db, _tenant(current_user))
