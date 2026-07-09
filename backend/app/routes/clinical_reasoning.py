"""v2.5 — Clinical Reasoning & Decision Intelligence API (Project Cortex).

- GET  /api/inspections/{id}/decision          — Sections 2/4/8: the full
  Explainable Decision Tree (evidence, reasoning path, applied rules,
  clinical rationale, final recommendation) + separated confidence.
- GET  /api/inspections/{id}/decision-replay    — Section 9: replay of any
  past inspection's decision, alongside the supervisor's actual outcome.
- GET  /api/decision-rules/library              — Section 5: the built-in
  SPD Rule Library (read-only, code-shipped).
- GET  /api/decision-rules                      — Section 7: supervisor-
  authored rules for this tenant.
- POST /api/decision-rules                      — Section 7: create a
  governed, versioned supervisor rule.
- POST /api/decision-rules/{id}                 — Section 7: governed edit
  (creates a new version rather than mutating in place).
- POST /api/decision-rules/{id}/deactivate      — Section 7: retire a rule.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.db import models
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.clinical_decision_rule import RULE_TYPES
from app.services.decision_reasoning_service import build_explainable_decision, compute_recommendation_confidence
from app.services.decision_replay_service import replay_decision
from app.services.spd_rule_library import list_rules as list_spd_rule_library
from app.services.supervisor_rule_service import (
    create_rule, deactivate_rule, get_rule, list_rules, rule_to_dict, update_rule,
)

router = APIRouter(tags=["clinical-reasoning"])

_READ_ROLES = ("admin", "spd_manager", "supervisor", "operator", "viewer")
_RULE_AUTHOR_ROLES = ("admin", "spd_manager", "supervisor")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


def _actor(current_user) -> str:
    return getattr(current_user, "email", None) or getattr(current_user, "username", "unknown")


def _get_inspection(db: Session, tenant_id: str, inspection_id: int) -> models.Inspection:
    insp = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id, models.Inspection.tenant_id == tenant_id)
        .first()
    )
    if insp is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    return insp


@router.get("/api/inspections/{inspection_id}/decision")
def get_explainable_decision(
    inspection_id: int, request: Request,
    db: Session = Depends(get_db), current_user=Depends(require_roles(*_READ_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    insp = _get_inspection(db, tenant_id, inspection_id)
    decision = build_explainable_decision(db, tenant_id, insp)
    decision["confidence"] = compute_recommendation_confidence(decision["evidence"], decision["applied_rules"])
    return decision


@router.get("/api/inspections/{inspection_id}/decision-replay")
def get_decision_replay(
    inspection_id: int, request: Request,
    db: Session = Depends(get_db), current_user=Depends(require_roles(*_READ_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    replay = replay_decision(db, tenant_id, inspection_id)
    if replay is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    return replay


@router.get("/api/decision-rules/library")
def get_spd_rule_library(current_user=Depends(require_roles(*_READ_ROLES))):
    return {"rules": list_spd_rule_library()}


@router.get("/api/decision-rules")
def get_supervisor_rules(
    request: Request, active_only: bool = True,
    db: Session = Depends(get_db), current_user=Depends(require_roles(*_READ_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"rules": list_rules(db, tenant_id, active_only=active_only)}


class DecisionRuleIn(BaseModel):
    rule_type: str = Field(..., description=f"One of {RULE_TYPES}")
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field("", max_length=4000)
    finding_type: str = Field("", max_length=40)
    zone_keyword: str = Field("", max_length=100)
    requires_high_risk_zone: bool = False
    requires_repeat_finding: bool = False
    min_repeat_occurrences: int = Field(0, ge=0)
    severity: str = Field("Moderate")
    spd_risk: str = Field("Moderate")
    recommendation: list[str] = Field(default_factory=list)


@router.post("/api/decision-rules", status_code=201)
def post_supervisor_rule(
    body: DecisionRuleIn, request: Request,
    db: Session = Depends(get_db), current_user=Depends(require_roles(*_RULE_AUTHOR_ROLES)),
):
    if body.rule_type not in RULE_TYPES:
        raise HTTPException(status_code=422, detail=f"rule_type must be one of {RULE_TYPES}")
    tenant_id = _tenant(current_user, request)
    row = create_rule(db, tenant_id, created_by=_actor(current_user), **body.model_dump())
    return rule_to_dict(row)


@router.post("/api/decision-rules/{rule_id}")
def post_update_supervisor_rule(
    rule_id: int, body: DecisionRuleIn, request: Request,
    db: Session = Depends(get_db), current_user=Depends(require_roles(*_RULE_AUTHOR_ROLES)),
):
    if body.rule_type not in RULE_TYPES:
        raise HTTPException(status_code=422, detail=f"rule_type must be one of {RULE_TYPES}")
    tenant_id = _tenant(current_user, request)
    if get_rule(db, tenant_id, rule_id) is None:
        raise HTTPException(status_code=404, detail="Rule not found.")
    updated = update_rule(db, tenant_id, rule_id, updated_by=_actor(current_user), **body.model_dump())
    return rule_to_dict(updated)


@router.post("/api/decision-rules/{rule_id}/deactivate")
def post_deactivate_supervisor_rule(
    rule_id: int, request: Request,
    db: Session = Depends(get_db), current_user=Depends(require_roles(*_RULE_AUTHOR_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    row = deactivate_rule(db, tenant_id, rule_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Rule not found.")
    return rule_to_dict(row)
