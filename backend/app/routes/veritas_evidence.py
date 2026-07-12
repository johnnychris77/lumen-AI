"""LumenAI AI Specialist — Project Veritas: Baseline Governance, Evidence
Integrity & Clinical Data Quality routes.

Frontend route: /veritas. API prefix: /api/veritas.

Uses `tenant_authz.require_tenant_roles`, consistent with every sprint since
Athena (v4.8). Per Section 20: viewers may not approve baselines or
override evidence gates; technicians (`operator` role) may not alter
baseline governance status. Both are enforced at the route layer via
`_LEADERSHIP_ROLES` for governance/override endpoints, with an additional
in-handler check on the shared `/feedback` endpoint since only one of its
several actions (`override_evidence_gate`) requires leadership.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.veritas_evidence import FEEDBACK_ACTION_OVERRIDE_EVIDENCE_GATE, VeritasEvidenceReadinessAssessment
from app.services import (
    veritas_baseline_governance_service,
    veritas_data_quality_service,
    veritas_evidence_agent_service,
    veritas_feedback_service,
    veritas_provenance_service,
    veritas_reports_service,
    veritas_specialist_collaboration_service,
    veritas_training_dataset_service,
    veritas_watchlist_service,
    veritas_workspace_service,
)
from app.tenant_authz import require_tenant_roles

router = APIRouter(prefix="/api/veritas", tags=["veritas"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user: dict) -> str:
    return current_user["tenant_id"]


def _actor(current_user: dict) -> str:
    return current_user["user_email"]


# ---------------------------------------------------------------------------
# Sections 1, 10, 12 — Evidence Assurance Agent + Evidence Gate + Panel data
# ---------------------------------------------------------------------------


@router.post("/assess/{inspection_id}", status_code=201)
def post_assess(inspection_id: int, payload: dict | None = None, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    payload = payload or {}
    try:
        row = veritas_evidence_agent_service.run_evidence_assessment(
            db, _tenant(current_user), inspection_id,
            model_version=payload.get("model_version", ""), dataset_version=payload.get("dataset_version", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return veritas_evidence_agent_service.to_dict(row)


@router.get("/assessments/{assessment_id}")
def get_assessment(assessment_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    row = (
        db.query(VeritasEvidenceReadinessAssessment)
        .filter(VeritasEvidenceReadinessAssessment.id == assessment_id, VeritasEvidenceReadinessAssessment.tenant_id == _tenant(current_user))
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Veritas assessment not found")
    return veritas_evidence_agent_service.to_dict(row)


@router.get("/assessments")
def get_assessments(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    rows = (
        db.query(VeritasEvidenceReadinessAssessment)
        .filter(VeritasEvidenceReadinessAssessment.tenant_id == _tenant(current_user))
        .order_by(VeritasEvidenceReadinessAssessment.created_at.desc())
        .all()
    )
    return {"assessments": [veritas_evidence_agent_service.to_dict(r) for r in rows]}


# ---------------------------------------------------------------------------
# Sections 3, 13 — Baseline Governance + Review Workspace
# ---------------------------------------------------------------------------


@router.post("/baselines/{source_type}/{source_id}/governance-action", status_code=201)
def post_governance_action(
    source_type: str, source_id: int, payload: dict,
    current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    try:
        row = veritas_baseline_governance_service.record_governance_action(
            db, _tenant(current_user), baseline_source_type=source_type, baseline_source_id=source_id,
            action=payload.get("action", ""), performed_by=_actor(current_user), performed_role=current_user.get("role", ""),
            owner=payload.get("owner", ""), review_date=payload.get("review_date"),
            known_limitations=payload.get("known_limitations", ""), usage_rights=payload.get("usage_rights", ""),
            rationale=payload.get("rationale", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return veritas_baseline_governance_service._to_dict(row)


@router.get("/baselines/{source_type}/{source_id}/governance-history")
def get_governance_history(source_type: str, source_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {
        "history": veritas_baseline_governance_service.governance_history(db, _tenant(current_user), source_type, source_id),
        "effective_status": veritas_baseline_governance_service.effective_status(db, _tenant(current_user), source_type, source_id),
    }


@router.post("/baselines/compare")
def post_compare_baselines(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    candidates = [(c["source_type"], c["source_id"]) for c in payload.get("candidates", [])]
    return {"comparison": veritas_baseline_governance_service.compare_candidates(db, _tenant(current_user), candidates)}


# ---------------------------------------------------------------------------
# Section 7 — Evidence Provenance Ledger
# ---------------------------------------------------------------------------


@router.post("/provenance", status_code=201)
def post_provenance(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        row = veritas_provenance_service.record_provenance(db, _tenant(current_user), **payload)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return veritas_provenance_service.to_dict(row)


@router.get("/provenance")
def get_provenance(inspection_id: int = Query(None), evidence_type: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"records": veritas_provenance_service.list_provenance(db, _tenant(current_user), inspection_id=inspection_id, evidence_type=evidence_type)}


# ---------------------------------------------------------------------------
# Section 15 — Training Dataset Assurance
# ---------------------------------------------------------------------------


@router.post("/training-dataset/{retained_image_id}/evaluate", status_code=201)
def post_evaluate_training(retained_image_id: int, payload: dict | None = None, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    payload = payload or {}
    try:
        row = veritas_training_dataset_service.evaluate_for_training(
            db, _tenant(current_user), retained_image_id,
            instrument_family=payload.get("instrument_family", ""), anatomy_zone=payload.get("anatomy_zone", ""),
            usage_rights=payload.get("usage_rights", ""), image_quality_threshold_met=bool(payload.get("image_quality_threshold_met", False)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return veritas_training_dataset_service.to_dict(row)


@router.get("/training-dataset")
def get_training_dataset(dataset_status: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return {"entries": veritas_training_dataset_service.list_dataset_entries(db, _tenant(current_user), dataset_status=dataset_status)}


# ---------------------------------------------------------------------------
# Section 17 — Supervisor Feedback (+ Section 10 gate override)
# ---------------------------------------------------------------------------


@router.post("/feedback", status_code=201)
def post_feedback(payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    action = payload.get("action", "")
    if action == FEEDBACK_ACTION_OVERRIDE_EVIDENCE_GATE and current_user.get("role") not in _LEADERSHIP_ROLES:
        raise HTTPException(status_code=403, detail="Only an authorized supervisor/manager may override an evidence gate")
    try:
        row = veritas_feedback_service.submit_feedback(
            db, _tenant(current_user), action=action, submitted_by=_actor(current_user),
            submitted_role=current_user.get("role", ""), assessment_id=payload.get("assessment_id"),
            baseline_match_correct=payload.get("baseline_match_correct"),
            image_quality_assessment_correct=payload.get("image_quality_assessment_correct"),
            anatomy_zone_tag_correct=payload.get("anatomy_zone_tag_correct"),
            coverage_determination_correct=payload.get("coverage_determination_correct"),
            evidence_conflict_valid=payload.get("evidence_conflict_valid"),
            corrected_baseline=payload.get("corrected_baseline", ""), corrected_zone=payload.get("corrected_zone", ""),
            final_evidence_status=payload.get("final_evidence_status", ""), reviewer_rationale=payload.get("reviewer_rationale", ""),
            override_reason=payload.get("override_reason", ""), limitations_acknowledged=payload.get("limitations_acknowledged", ""),
            final_disposition=payload.get("final_disposition", ""),
        )
    except veritas_feedback_service.OverrideReasonRequiredError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return veritas_feedback_service.to_dict(row)


@router.get("/feedback/{assessment_id}")
def get_feedback(assessment_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"feedback": veritas_feedback_service.feedback_for_assessment(db, _tenant(current_user), assessment_id)}


# ---------------------------------------------------------------------------
# Section 11 — Veritas Workspace
# ---------------------------------------------------------------------------


@router.get("/workspace")
def get_workspace(instrument_family: str = Query(""), anatomy_zone: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return veritas_workspace_service.workspace_summary(db, _tenant(current_user), instrument_family=instrument_family, anatomy_zone=anatomy_zone)


# ---------------------------------------------------------------------------
# Section 14 — Data Quality Monitoring
# ---------------------------------------------------------------------------


@router.get("/data-quality")
def get_data_quality(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return veritas_data_quality_service.data_quality_summary(db, _tenant(current_user))


# ---------------------------------------------------------------------------
# Section 18 — Alerts and Watchlists
# ---------------------------------------------------------------------------


@router.get("/watchlists")
def get_watchlists(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return {name: fn(db, tenant_id) for name, fn in veritas_watchlist_service.WATCHLISTS.items()}


@router.get("/watchlists/{name}")
def get_watchlist(name: str, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    result = veritas_watchlist_service.run_watchlist(db, _tenant(current_user), name)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Unknown watchlist '{name}'")
    return {"watchlist": name, "entries": result}


# ---------------------------------------------------------------------------
# Section 19 — Evidence Assurance Reports
# ---------------------------------------------------------------------------


@router.get("/reports/{name}")
def get_report(name: str, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    report = veritas_reports_service.build_named_report(db, _tenant(current_user), name)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Unknown report '{name}'")
    return report


@router.get("/reports/{name}/export")
def get_report_export(name: str, format: str = Query("csv"), current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    report = veritas_reports_service.build_named_report(db, _tenant(current_user), name)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Unknown report '{name}'")
    if format == "pdf":
        data = veritas_reports_service.build_report_pdf_bytes(report["title"], report["content"])
        media_type = "application/pdf"
    elif format == "xlsx":
        data = veritas_reports_service.build_report_xlsx_bytes(report["title"], report["content"])
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        data = veritas_reports_service.build_report_csv_bytes(report["content"])
        media_type = "text/csv"
    return Response(content=data, media_type=media_type)


# ---------------------------------------------------------------------------
# Section 16 — Collaboration With Other Agents
# ---------------------------------------------------------------------------


@router.get("/collaboration/clinical-reasoning/{assessment_id}")
def get_clinical_reasoning_support(assessment_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    row = (
        db.query(VeritasEvidenceReadinessAssessment)
        .filter(VeritasEvidenceReadinessAssessment.id == assessment_id, VeritasEvidenceReadinessAssessment.tenant_id == _tenant(current_user))
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Veritas assessment not found")
    return veritas_specialist_collaboration_service.evidence_support_for_clinical_reasoning(veritas_evidence_agent_service.to_dict(row))
