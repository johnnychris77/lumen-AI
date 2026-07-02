"""Phase 17 — Model Training Pipeline & AI Readiness API.

Endpoints for the model lifecycle: task/gate discovery, dataset-split preview,
training-run preparation, model-registry CRUD + human-in-the-loop promotion,
and shadow-mode prediction capture/reconciliation. Nothing here can silently
drive a clinical recommendation — the deployment gate is enforced server-side
and models are never auto-promoted.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.model_registry import ModelRegistryEntry
from app.models.shadow_prediction import ShadowPrediction
from app.services.ml import shadow_mode
from app.services.ml.deployment_gates import (
    APPROVAL_STAGES, GATE_CAPABILITIES, capabilities, evaluate_promotion,
)
from app.services.ml.model_tasks import MODEL_TASKS, SAFETY_CRITICAL_FINDINGS, is_valid_task
from app.services.ml.training_pipeline import prepare_training_run

router = APIRouter(tags=["model-pipeline"])


def _actor(user) -> str:
    return getattr(user, "email", None) or getattr(user, "username", "unknown")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


# ── Discovery ────────────────────────────────────────────────────────────────

@router.get("/model-pipeline/tasks")
def list_tasks(current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer"))):
    """Model task definitions (label spaces) + safety-critical findings."""
    return {
        "tasks": {
            k: {"name": v["name"], "labels": v["labels"], "safety_critical": v["safety_critical"]}
            for k, v in MODEL_TASKS.items()
        },
        "safety_critical_findings": SAFETY_CRITICAL_FINDINGS,
    }


@router.get("/model-pipeline/deployment-gates")
def list_gates(current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer"))):
    """What each approval stage may do (§8)."""
    return {"stages": APPROVAL_STAGES, "capabilities": GATE_CAPABILITIES}


# ── Dataset split preview / training-run preparation ─────────────────────────

class Sample(BaseModel):
    id: str | int
    inspection_id: int | None = None
    instrument_serial: str | None = None
    instrument_family: str | None = None
    anatomy_zone: str | None = None
    finding: str | None = None
    severity: str | None = None
    manufacturer: str | None = None
    image_quality: str | None = None


class PrepareRunIn(BaseModel):
    task: str = Field(..., description="Model task key")
    samples: list[Sample] = Field(default_factory=list)
    seed: str = Field("lumenai-v1", max_length=64)
    group_by_serial: bool = False


@router.post("/model-pipeline/prepare-run")
def prepare_run(
    body: PrepareRunIn,
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Prepare a training run: validate task, split data, check leakage. Does not
    train (no labeled dataset yet) — returns the run manifest honestly."""
    if not is_valid_task(body.task):
        raise HTTPException(status_code=422, detail=f"Unknown task '{body.task}'.")
    samples = [s.model_dump() for s in body.samples]
    run = prepare_training_run(body.task, samples, seed=body.seed, group_by_serial=body.group_by_serial)
    # Drop the bulky raw assignment map from the API response; keep the summary.
    run["split"] = {k: run["split"][k] for k in ("counts", "split_groups", "ratios", "stratified_by")}
    return run


# ── Model registry ───────────────────────────────────────────────────────────

class RegisterModelIn(BaseModel):
    model_id: str = Field(..., min_length=1, max_length=100)
    model_version: str = Field(..., min_length=1, max_length=50)
    model_type: str = Field(..., description="A model task key")
    dataset_version: str = Field("", max_length=100)
    known_limitations: str = Field("", max_length=4000)
    release_notes: str = Field("", max_length=4000)


@router.post("/model-pipeline/models", status_code=201)
def register_model(
    body: RegisterModelIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Register a new model version. Always starts as `experimental` — never
    higher. Promotion is a separate, human-gated action."""
    if not is_valid_task(body.model_type):
        raise HTTPException(status_code=422, detail=f"Unknown model_type '{body.model_type}'.")
    tenant_id = _tenant(current_user, request)
    row = ModelRegistryEntry(
        tenant_id=tenant_id,
        model_id=body.model_id,
        model_version=body.model_version,
        model_type=body.model_type,
        dataset_version=body.dataset_version,
        training_status="not_started",
        evaluation_metrics="{}",
        known_limitations=body.known_limitations,
        approval_status="experimental",  # hard default — never trust client
        release_notes=body.release_notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user),
        actor_role=getattr(current_user, "role", ""), action_type="model_registered",
        resource_type="model", resource_id=f"{row.model_id}:{row.model_version}",
    )
    return _model_view(row)


@router.get("/model-pipeline/models")
def list_models(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    tenant_id = _tenant(current_user, request)
    rows = (
        db.query(ModelRegistryEntry)
        .filter(ModelRegistryEntry.tenant_id == tenant_id)
        .order_by(ModelRegistryEntry.id.desc())
        .all()
    )
    return {"count": len(rows), "models": [_model_view(r) for r in rows]}


class PromoteIn(BaseModel):
    target_stage: str = Field(..., description="pilot | validated | deprecated")
    checklist: dict[str, bool] = Field(default_factory=dict)
    sample_size: int = Field(0, ge=0)
    release_notes: str = Field("", max_length=4000)


@router.post("/model-pipeline/models/{model_db_id}/promote")
def promote_model(
    model_db_id: int,
    body: PromoteIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Human-in-the-loop promotion. Refuses to advance until every requirement is
    met; never auto-promotes. The approver is the authenticated user."""
    tenant_id = _tenant(current_user, request)
    row = (
        db.query(ModelRegistryEntry)
        .filter(ModelRegistryEntry.id == model_db_id, ModelRegistryEntry.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Model not found.")

    decision = evaluate_promotion(
        row.approval_status, body.target_stage,
        checklist=body.checklist, sample_size=body.sample_size, approver=_actor(current_user),
    )
    if not decision["allowed"]:
        # 409: the request is well-formed but requirements are unmet.
        raise HTTPException(status_code=409, detail={"message": "Promotion blocked.", **decision})

    row.approval_status = body.target_stage
    row.approved_by = _actor(current_user)
    if body.release_notes:
        row.release_notes = body.release_notes
    db.commit()
    db.refresh(row)
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user),
        actor_role=getattr(current_user, "role", ""), action_type="model_promoted",
        resource_type="model", resource_id=f"{row.model_id}:{row.model_version}->{body.target_stage}",
    )
    return {"promoted": True, "model": _model_view(row), "decision": decision}


def _model_view(row: ModelRegistryEntry) -> dict:
    caps = capabilities(row.approval_status)
    return {
        "id": row.id,
        "model_id": row.model_id,
        "model_version": row.model_version,
        "model_type": row.model_type,
        "dataset_version": row.dataset_version,
        "training_status": row.training_status,
        "evaluation_metrics": json.loads(row.evaluation_metrics or "{}"),
        "known_limitations": row.known_limitations,
        "approval_status": row.approval_status,
        "approved_by": row.approved_by,
        "release_notes": row.release_notes,
        "capabilities": caps,
        "human_review_required": True,
    }


# ── Shadow mode ──────────────────────────────────────────────────────────────

class ShadowIn(BaseModel):
    model_id: str = Field(..., min_length=1, max_length=100)
    model_version: str = Field("", max_length=50)
    model_type: str = Field("", max_length=60)
    predicted_label: str = Field(..., max_length=100)
    predicted_confidence: str = Field("", max_length=20)
    inspection_id: int | None = None
    payload: dict = Field(default_factory=dict)


@router.post("/model-pipeline/shadow-predictions", status_code=201)
def create_shadow_prediction(
    body: ShadowIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Record a silent shadow prediction. The response deliberately does NOT
    surface the predicted label as a clinical recommendation."""
    tenant_id = _tenant(current_user, request)
    # A registered experimental+ model may run shadow; a deprecated one may not.
    reg = (
        db.query(ModelRegistryEntry)
        .filter(ModelRegistryEntry.tenant_id == tenant_id, ModelRegistryEntry.model_id == body.model_id)
        .order_by(ModelRegistryEntry.id.desc())
        .first()
    )
    if reg is not None and not capabilities(reg.approval_status)["can_run_shadow_mode"]:
        raise HTTPException(status_code=409, detail=f"Model stage '{reg.approval_status}' cannot run shadow mode.")

    row = shadow_mode.record_shadow_prediction(
        db, tenant_id=tenant_id, model_id=body.model_id, model_version=body.model_version,
        model_type=body.model_type, predicted_label=body.predicted_label,
        predicted_confidence=body.predicted_confidence, inspection_id=body.inspection_id,
        payload=body.payload,
    )
    return shadow_mode.public_view(row)


@router.get("/model-pipeline/shadow-predictions/performance")
def shadow_perf(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant(current_user, request)
    rows = db.query(ShadowPrediction).filter(ShadowPrediction.tenant_id == tenant_id).all()
    return shadow_mode.shadow_performance(rows)
