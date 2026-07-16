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
from app.models.inspection import Inspection
from app.models.model_registry import ModelRegistryEntry
from app.models.shadow_prediction import ShadowPrediction
from app.services.ml import candidate_promotion, model_promotion, shadow_mode
from app.services.ml.deployment_gates import (
    APPROVAL_STAGES, GATE_CAPABILITIES, capabilities, evaluate_promotion,
)
from app.services.ml.model_card import generate_model_card
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
        "dataset_version_id": row.dataset_version_id,
        "training_status": row.training_status,
        "evaluation_metrics": json.loads(row.evaluation_metrics or "{}"),
        "known_limitations": row.known_limitations,
        "approval_status": row.approval_status,
        "approved_by": row.approved_by,
        "release_notes": row.release_notes,
        "architecture": row.architecture,
        "framework": row.framework,
        "hyperparameters": json.loads(row.hyperparameters or "{}"),
        "git_commit": row.git_commit,
        "training_metrics": json.loads(row.training_metrics or "{}"),
        "documentation_complete": row.documentation_complete,
        "clinical_review_complete": row.clinical_review_complete,
        "metrics_approved": row.metrics_approved,
        "model_card_generated": bool(row.model_card_markdown),
        "capabilities": caps,
        "human_review_required": True,
    }


class RecordTrainingResultIn(BaseModel):
    architecture: str = Field("", max_length=100)
    framework: str = Field("", max_length=60)
    hyperparameters: dict = Field(default_factory=dict)
    git_commit: str = Field("", max_length=64)
    dataset_version_id: int | None = None
    training_status: str = Field("trained", description="trained | failed | insufficient_data")
    training_metrics: dict = Field(default_factory=dict)
    evaluation_metrics: dict = Field(default_factory=dict)


@router.post("/model-pipeline/models/{model_db_id}/record-training-result")
def record_training_result(
    model_db_id: int,
    body: RecordTrainingResultIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Attach the outcome of a real training run (Section 10) to an existing
    registry entry — the reproducible link between ``app.services.ml.
    training_execution.run_training_pipeline`` and this registry row."""
    tenant_id = _tenant(current_user, request)
    row = (
        db.query(ModelRegistryEntry)
        .filter(ModelRegistryEntry.id == model_db_id, ModelRegistryEntry.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Model not found.")

    row.architecture = body.architecture
    row.framework = body.framework
    row.hyperparameters = json.dumps(body.hyperparameters)
    row.git_commit = body.git_commit
    row.dataset_version_id = body.dataset_version_id
    row.training_status = body.training_status
    row.training_metrics = json.dumps(body.training_metrics)
    row.evaluation_metrics = json.dumps(body.evaluation_metrics)
    db.commit()
    db.refresh(row)
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user),
        actor_role=getattr(current_user, "role", ""), action_type="model_training_result_recorded",
        resource_type="model", resource_id=f"{row.model_id}:{row.model_version}",
    )
    return _model_view(row)


@router.post("/model-pipeline/models/{model_db_id}/generate-model-card")
def generate_and_store_model_card(
    model_db_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Generate the Model Card (Section 9) from this entry's own fields and
    persist it — required before ``model_card_generated`` can pass in the
    Section 12 promotion gate."""
    tenant_id = _tenant(current_user, request)
    row = (
        db.query(ModelRegistryEntry)
        .filter(ModelRegistryEntry.id == model_db_id, ModelRegistryEntry.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Model not found.")

    card = generate_model_card(row)
    row.model_card_markdown = card
    db.commit()
    db.refresh(row)
    return {"model_card": card, "model": _model_view(row)}


class GovernanceFlagsIn(BaseModel):
    documentation_complete: bool | None = None
    clinical_review_complete: bool | None = None
    metrics_approved: bool | None = None


@router.patch("/model-pipeline/models/{model_db_id}/governance-flags")
def set_governance_flags(
    model_db_id: int,
    body: GovernanceFlagsIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Human-recorded governance sign-off flags (Section 12) — never
    defaulted true, only ever set explicitly by an authorized reviewer."""
    tenant_id = _tenant(current_user, request)
    row = (
        db.query(ModelRegistryEntry)
        .filter(ModelRegistryEntry.id == model_db_id, ModelRegistryEntry.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Model not found.")

    if body.documentation_complete is not None:
        row.documentation_complete = body.documentation_complete
    if body.clinical_review_complete is not None:
        row.clinical_review_complete = body.clinical_review_complete
    if body.metrics_approved is not None:
        row.metrics_approved = body.metrics_approved
    db.commit()
    db.refresh(row)
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user),
        actor_role=getattr(current_user, "role", ""), action_type="model_governance_flags_updated",
        resource_type="model", resource_id=f"{row.model_id}:{row.model_version}",
    )
    return _model_view(row)


@router.get("/model-pipeline/models/{model_db_id}/promotion-readiness")
def promotion_readiness(
    model_db_id: int,
    target_stage: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Read-only preview of the full Section 12 promotion gate (dataset
    frozen, evaluation complete, metrics approved, clinical review complete,
    documentation complete, model card generated, registry updated) — never
    changes state; call ``/promote`` to actually advance a stage."""
    tenant_id = _tenant(current_user, request)
    row = (
        db.query(ModelRegistryEntry)
        .filter(ModelRegistryEntry.id == model_db_id, ModelRegistryEntry.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Model not found.")
    return model_promotion.evaluate_full_promotion_readiness(db, model=row, target_stage=target_stage)


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


class ShadowRevealIn(BaseModel):
    final_label: str = Field(..., max_length=100)


@router.post("/model-pipeline/shadow-predictions/{shadow_id}/reveal")
def reveal_shadow_prediction(
    shadow_id: int, body: ShadowRevealIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Shadow §1 — attempt to reveal a shadow prediction against the human
    final decision. A no-op (still hidden) unless the prediction's
    inspection has reached a terminal workflow state (Completed/Cancelled)
    — the technician's finding and the supervisor's review must already be
    locked. See app.services.ml.shadow_mode.reveal_if_finalized."""
    tenant_id = _tenant(current_user, request)
    row = (
        db.query(ShadowPrediction)
        .filter(ShadowPrediction.id == shadow_id, ShadowPrediction.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Shadow prediction not found.")

    insp = None
    if row.inspection_id is not None:
        insp = (
            db.query(Inspection)
            .filter(Inspection.id == row.inspection_id, Inspection.tenant_id == tenant_id)
            .first()
        )
    row = shadow_mode.reveal_if_finalized(db, row, insp=insp, final_label=body.final_label)
    return shadow_mode.public_view(row)


# ── Genesis: Candidate promotion ladder (Section 11) ────────────────────────

def _get_model_or_404(db: Session, tenant_id: str, model_db_id: int) -> ModelRegistryEntry:
    row = (
        db.query(ModelRegistryEntry)
        .filter(ModelRegistryEntry.id == model_db_id, ModelRegistryEntry.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Model not found.")
    return row


@router.get("/model-pipeline/models/{model_db_id}/candidate-checklist")
def candidate_checklist(
    model_db_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    """Read-only view of the 8-item Section 11 checklist against this
    model's current state — never changes anything."""
    tenant_id = _tenant(current_user, request)
    row = _get_model_or_404(db, tenant_id, model_db_id)
    return {
        "candidate_stage": row.candidate_stage,
        "checklist": candidate_promotion.evaluate_candidate_checklist(db, row),
    }


@router.get("/model-pipeline/models/{model_db_id}/validated-candidate-checklist")
def validated_candidate_checklist(
    model_db_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    """Shadow §14 — read-only preview of the 4 additional items required
    to advance beyond Candidate (inspection volume, performance targets,
    drift, clinical review board), on top of the base 8-item checklist."""
    tenant_id = _tenant(current_user, request)
    row = _get_model_or_404(db, tenant_id, model_db_id)
    return {
        "candidate_stage": row.candidate_stage,
        "base_checklist": candidate_promotion.evaluate_candidate_checklist(db, row),
        "validated_candidate_checklist": candidate_promotion.evaluate_validated_candidate_checklist(db, row),
    }


class CandidateFlagsIn(BaseModel):
    reviewer: str | None = Field(None, max_length=255)
    clinical_review_status: str | None = Field(None, description="pending | approved | rejected")
    deployment_status: str | None = Field(None, description="not_deployed | shadow | deployed")
    error_analysis_reviewed: bool | None = None
    reproducible_training_confirmed: bool | None = None
    governance_review_completed: bool | None = None


@router.patch("/model-pipeline/models/{model_db_id}/candidate-flags")
def set_candidate_flags(
    model_db_id: int, body: CandidateFlagsIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Human-recorded Section 9/11 fields — reviewer assignment, clinical
    review status, deployment status, and the three boolean gates
    (error analysis reviewed, reproducible training confirmed, governance
    review completed). Never defaulted true."""
    tenant_id = _tenant(current_user, request)
    row = _get_model_or_404(db, tenant_id, model_db_id)

    if body.reviewer is not None:
        row.reviewer = body.reviewer
    if body.clinical_review_status is not None:
        row.clinical_review_status = body.clinical_review_status
    if body.deployment_status is not None:
        row.deployment_status = body.deployment_status
    if body.error_analysis_reviewed is not None:
        row.error_analysis_reviewed = body.error_analysis_reviewed
    if body.reproducible_training_confirmed is not None:
        row.reproducible_training_confirmed = body.reproducible_training_confirmed
    if body.governance_review_completed is not None:
        row.governance_review_completed = body.governance_review_completed
    db.commit()
    db.refresh(row)
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user),
        actor_role=getattr(current_user, "role", ""), action_type="candidate_flags_updated",
        resource_type="model", resource_id=f"{row.model_id}:{row.model_version}",
    )
    return _model_view(row)


class CandidatePromoteIn(BaseModel):
    target_stage: str = Field(..., description=f"One of {candidate_promotion.CANDIDATE_STAGES}")


@router.post("/model-pipeline/models/{model_db_id}/candidate-promotion")
def promote_candidate_model(
    model_db_id: int, body: CandidatePromoteIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Advance a model along the Candidate -> Validated Candidate -> Pilot
    -> Production ladder (Section 11). Never auto-promotes; refuses with
    409 and the unmet checklist until every item is satisfied."""
    tenant_id = _tenant(current_user, request)
    row = _get_model_or_404(db, tenant_id, model_db_id)

    decision = candidate_promotion.promote_candidate(
        db, model=row, target_stage=body.target_stage, approver=_actor(current_user),
    )
    if not decision.get("promoted"):
        raise HTTPException(status_code=409, detail={"message": "Candidate promotion blocked.", **decision})

    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user),
        actor_role=getattr(current_user, "role", ""), action_type="candidate_model_promoted",
        resource_type="model", resource_id=f"{row.model_id}:{row.model_version}->{body.target_stage}",
    )
    return {**decision, "model": _model_view(row)}


@router.get("/model-pipeline/models/{model_db_id}/validation-package")
def validation_package(
    model_db_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    """Section 12 — the full Validation Package assembled from this
    registry entry: Training Report, Evaluation Report, Error Analysis
    Report, Calibration Report, Model Card, and the Approval Checklist.
    Every field is read directly from stored registry data — nothing here
    is recomputed or re-derived at request time."""
    tenant_id = _tenant(current_user, request)
    row = _get_model_or_404(db, tenant_id, model_db_id)
    return {
        "model": _model_view(row),
        "training_report": json.loads(row.training_metrics or "{}"),
        "evaluation_report": json.loads(row.evaluation_metrics or "{}"),
        "error_analysis_report": json.loads(row.error_analysis_report or "{}"),
        "calibration_report": json.loads(row.calibration_report or "{}"),
        "model_card": row.model_card_markdown,
        "approval_checklist": candidate_promotion.evaluate_candidate_checklist(db, row),
        "dataset_summary": {
            "dataset_version_id": row.dataset_version_id,
            "dataset_version": row.dataset_version,
        },
    }
