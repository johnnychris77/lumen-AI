"""v5.2 — LumenAI Network: Project GuardianX — AI Assurance Framework
routes.

Frontend route: /ai-assurance. API prefix: /api/guardianx.

Uses `tenant_authz.require_tenant_roles` (real `TenantMembership`
verification), consistent with Athena/Phoenix/Infinity/Olympus.
`AIModelRegistryEntry` (Olympus, v5.1) is a global registry, not
tenant-scoped, so model-governance/risk/certification/governance-workflow
routes don't take a tenant_id; trust-score and reports routes that
compose Phoenix's per-tenant health scores do.

  * PATCH /models/{id}/ownership, POST /models/{id}/validation-date,
    POST /models/{id}/retire, PATCH /models/{id}/training-dataset-metadata,
    PATCH /models/{id}/known-limitations, PATCH /models/{id}/use-cases,
    GET  /models/{id}/governance, GET /models/governance             — Section 2
  * POST /explainability, GET /explainability/{id},
    POST /explainability/{id}/human-override, GET /explainability      — Section 3
  * GET  /audit-replay/inspections/{id},
    GET  /audit-replay/workflow-executions/{id},
    GET  /audit-replay/rules/{id}, GET /audit-replay/recommendations   — Section 4
  * POST /risks, PATCH /risks/{id}/status, GET /models/{id}/risks,
    GET  /risks/summary                                               — Section 5
  * POST /models/{id}/governance-review/start, /advance,
    GET  /models/{id}/governance-review                                — Section 6
  * POST /compliance-mappings, GET /compliance-mappings/{id},
    GET  /compliance-mappings, GET /compliance-mappings/traceability-matrix — Section 7
  * POST /evidence, GET /evidence/{id}, GET /evidence,
    GET  /evidence/{id}/verify                                         — Section 8
  * POST /trust/models/{id}/compute, /trust/knowledge/compute,
    /trust/workflow/compute, /trust/digital-twin/compute,
    /trust/platform/compute, GET /trust/history                        — Section 9
  * GET  /reports/executive, /reports/model-validation/{id},
    /reports/governance, /reports/audit-evidence-package,
    /reports/knowledge-provenance                                      — Section 10
  * GET  /assurance-center/summary, /assurance-center/models/{id}       — Section 1
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.services import (
    guardianx_assurance_center_service,
    guardianx_audit_replay_service,
    guardianx_compliance_mapping_service,
    guardianx_evidence_ledger_service,
    guardianx_explainability_service,
    guardianx_governance_workflow_service,
    guardianx_model_governance_service,
    guardianx_reports_service,
    guardianx_risk_registry_service,
    guardianx_trust_score_service,
)
from app.services.olympus_model_registry_service import UnknownModelRegistryEntryError
from app.tenant_authz import require_tenant_roles

router = APIRouter(prefix="/api/guardianx", tags=["guardianx"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user: dict) -> str:
    return current_user["tenant_id"]


def _actor(current_user: dict) -> str:
    return current_user["user_email"]


# ---------------------------------------------------------------------------
# Section 2 — Model Governance
# ---------------------------------------------------------------------------


@router.patch("/models/{model_id}/ownership")
def patch_model_ownership(model_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return guardianx_model_governance_service.set_ownership(
            db, model_id, model_owner=payload.get("model_owner", ""), clinical_owner=payload.get("clinical_owner", ""),
            technical_owner=payload.get("technical_owner", ""), approval_committee=payload.get("approval_committee", ""),
        )
    except UnknownModelRegistryEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/models/{model_id}/validation-date")
def post_model_validation_date(model_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return guardianx_model_governance_service.set_validation_date(db, model_id)
    except UnknownModelRegistryEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/models/{model_id}/retire")
def post_model_retire(model_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return guardianx_model_governance_service.retire_model(db, model_id)
    except UnknownModelRegistryEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/models/{model_id}/training-dataset-metadata")
def patch_model_training_dataset_metadata(model_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return guardianx_model_governance_service.set_training_dataset_metadata(db, model_id, payload.get("metadata", {}))
    except UnknownModelRegistryEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/models/{model_id}/known-limitations")
def patch_model_known_limitations(model_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return guardianx_model_governance_service.set_known_limitations(db, model_id, payload.get("known_limitations", ""))
    except UnknownModelRegistryEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/models/{model_id}/use-cases")
def patch_model_use_cases(model_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return guardianx_model_governance_service.set_use_cases(
            db, model_id, approved_use_cases=payload.get("approved_use_cases"), out_of_scope_uses=payload.get("out_of_scope_uses"),
        )
    except UnknownModelRegistryEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/models/{model_id}/governance")
def get_model_governance(model_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return guardianx_model_governance_service.get_governance_record(db, model_id)
    except UnknownModelRegistryEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/models/governance")
def get_all_model_governance(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"models": guardianx_model_governance_service.list_governance_records(db)}


# ---------------------------------------------------------------------------
# Section 3 — Explainability Dashboard
# ---------------------------------------------------------------------------


@router.post("/explainability", status_code=201)
def post_explainability(payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    actor = _actor(current_user)
    return guardianx_explainability_service.create_explanation(
        db, source_type=payload.get("source_type", ""), source_id=payload.get("source_id", ""),
        input_summary=payload.get("input_summary", ""), evidence_used=payload.get("evidence_used"),
        knowledge_sources=payload.get("knowledge_sources"),
        tenant_id_for_digital_twin=payload.get("tenant_id_for_digital_twin", ""),
        clinical_rules_applied=payload.get("clinical_rules_applied"), confidence=payload.get("confidence"),
        alternative_explanations=payload.get("alternative_explanations"),
        human_overrides=payload.get("human_overrides"), created_by=actor,
    )


@router.get("/explainability/{record_id}")
def get_explainability(record_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return guardianx_explainability_service.get_explanation(db, record_id)
    except guardianx_explainability_service.UnknownExplainabilityRecordError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/explainability/{record_id}/human-override")
def post_explainability_human_override(record_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    actor = _actor(current_user)
    try:
        return guardianx_explainability_service.record_human_override(
            db, record_id, override_note=payload.get("override_note", ""), overridden_by=actor,
        )
    except guardianx_explainability_service.UnknownExplainabilityRecordError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/explainability")
def get_explainability_for_source(
    source_type: str = Query(...), source_id: str = Query(...),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {"explanations": guardianx_explainability_service.list_explanations_for_source(db, source_type, source_id)}


# ---------------------------------------------------------------------------
# Section 4 — Audit Replay
# ---------------------------------------------------------------------------


@router.get("/audit-replay/inspections/{inspection_id}")
def get_replay_inspection(inspection_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return guardianx_audit_replay_service.replay_inspection(db, inspection_id)
    except guardianx_audit_replay_service.ReplayNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/audit-replay/workflow-executions/{execution_id}")
def get_replay_workflow_execution(execution_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return guardianx_audit_replay_service.replay_workflow_execution(db, execution_id)
    except guardianx_audit_replay_service.ReplayNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/audit-replay/rules/{rule_id}")
def get_replay_rule(rule_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return guardianx_audit_replay_service.replay_rule(db, rule_id)
    except guardianx_audit_replay_service.ReplayNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/audit-replay/recommendations")
def get_replay_recommendation(
    source_type: str = Query(...), source_id: str = Query(...),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return guardianx_audit_replay_service.replay_recommendation(db, source_type, source_id)


# ---------------------------------------------------------------------------
# Section 5 — AI Risk Registry
# ---------------------------------------------------------------------------


@router.post("/risks", status_code=201)
def post_risk(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    actor = _actor(current_user)
    try:
        return guardianx_risk_registry_service.record_risk(
            db, payload.get("model_id"), risk_type=payload.get("risk_type", ""), description=payload.get("description", ""),
            mitigation=payload.get("mitigation", ""), severity=payload.get("severity", "medium"), identified_by=actor,
        )
    except UnknownModelRegistryEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/risks/{risk_id}/status")
def patch_risk_status(risk_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return guardianx_risk_registry_service.update_risk_status(db, risk_id, status=payload.get("status", ""))
    except guardianx_risk_registry_service.UnknownRiskEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/models/{model_id}/risks")
def get_model_risks(model_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"risks": guardianx_risk_registry_service.list_risks_for_model(db, model_id)}


@router.get("/risks/summary")
def get_risk_summary(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return guardianx_risk_registry_service.risk_registry_summary(db)


# ---------------------------------------------------------------------------
# Section 6 — Governance Workflow
# ---------------------------------------------------------------------------


@router.post("/models/{model_id}/governance-review/start")
def post_governance_review_start(model_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return guardianx_governance_workflow_service.start_governance_review(db, model_id)
    except UnknownModelRegistryEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/models/{model_id}/governance-review/advance")
def post_governance_review_advance(model_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    actor = _actor(current_user)
    try:
        return guardianx_governance_workflow_service.advance_governance_review(
            db, model_id, decided_by=actor, decided_role=payload.get("decided_role", ""),
            decision=payload.get("decision", ""), notes=payload.get("notes", ""),
        )
    except UnknownModelRegistryEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/models/{model_id}/governance-review")
def get_governance_review(model_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return guardianx_governance_workflow_service.get_governance_review_status(db, model_id)
    except UnknownModelRegistryEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 7 — Compliance Mapping
# ---------------------------------------------------------------------------


@router.post("/compliance-mappings", status_code=201)
def post_compliance_mapping(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    actor = _actor(current_user)
    try:
        return guardianx_compliance_mapping_service.create_mapping(
            db, capability_name=payload.get("capability_name", ""), capability_description=payload.get("capability_description", ""),
            requirement_type=payload.get("requirement_type", ""), requirement_reference=payload.get("requirement_reference", ""),
            traceability_notes=payload.get("traceability_notes", ""), mapped_by=actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/compliance-mappings/traceability-matrix")
def get_compliance_traceability_matrix(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return guardianx_compliance_mapping_service.traceability_matrix(db)


@router.get("/compliance-mappings/{mapping_id}")
def get_compliance_mapping(mapping_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return guardianx_compliance_mapping_service.get_mapping(db, mapping_id)
    except guardianx_compliance_mapping_service.UnknownComplianceMappingError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/compliance-mappings")
def get_compliance_mappings(
    capability_name: str = Query(""), requirement_type: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    try:
        return {"mappings": guardianx_compliance_mapping_service.list_mappings(
            db, capability_name=capability_name, requirement_type=requirement_type,
        )}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 8 — Evidence Ledger
# ---------------------------------------------------------------------------


@router.post("/evidence", status_code=201)
def post_evidence(payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    actor = _actor(current_user)
    return guardianx_evidence_ledger_service.record_evidence(
        db, source_type=payload.get("source_type", ""), source_id=payload.get("source_id", ""),
        evidence=payload.get("evidence", []), knowledge_version=payload.get("knowledge_version", ""),
        model_version=payload.get("model_version", ""), workflow_version=payload.get("workflow_version", ""),
        reviewer=actor,
    )


@router.get("/evidence/{entry_id}")
def get_evidence_entry(entry_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return guardianx_evidence_ledger_service.get_entry(db, entry_id)
    except guardianx_evidence_ledger_service.UnknownEvidenceLedgerEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/evidence/{entry_id}/verify")
def get_evidence_verify(entry_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return guardianx_evidence_ledger_service.verify_entry(db, entry_id)
    except guardianx_evidence_ledger_service.UnknownEvidenceLedgerEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/evidence")
def get_evidence_for_source(
    source_type: str = Query(...), source_id: str = Query(...),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {"entries": guardianx_evidence_ledger_service.list_entries_for_source(db, source_type, source_id)}


# ---------------------------------------------------------------------------
# Section 9 — Trust Score
# ---------------------------------------------------------------------------


@router.post("/trust/models/{model_id}/compute")
def post_trust_model_compute(model_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return guardianx_trust_score_service.compute_model_trust_score(db, model_id)
    except UnknownModelRegistryEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/trust/knowledge/compute")
def post_trust_knowledge_compute(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return guardianx_trust_score_service.compute_knowledge_trust_score(db, _tenant(current_user))


@router.post("/trust/workflow/compute")
def post_trust_workflow_compute(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return guardianx_trust_score_service.compute_workflow_trust_score(db, _tenant(current_user))


@router.post("/trust/digital-twin/compute")
def post_trust_digital_twin_compute(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return guardianx_trust_score_service.compute_digital_twin_trust_score(db, _tenant(current_user))


@router.post("/trust/platform/compute")
def post_trust_platform_compute(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return guardianx_trust_score_service.compute_platform_trust_score(db, _tenant(current_user))


@router.get("/trust/history")
def get_trust_history(
    scope: str = Query(...), scope_ref_id: str = Query(""), limit: int = Query(20, le=100),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {"history": guardianx_trust_score_service.trust_score_history(db, scope=scope, scope_ref_id=scope_ref_id, limit=limit)}


# ---------------------------------------------------------------------------
# Section 10 — AI Assurance Reports
# ---------------------------------------------------------------------------


@router.get("/reports/executive")
def get_report_executive(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return guardianx_reports_service.executive_ai_assurance_report(db, _tenant(current_user))


@router.get("/reports/model-validation/{model_id}")
def get_report_model_validation(model_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return guardianx_reports_service.model_validation_report(db, model_id)
    except UnknownModelRegistryEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/reports/governance")
def get_report_governance(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return guardianx_reports_service.governance_report(db)


@router.get("/reports/audit-evidence-package")
def get_report_audit_evidence_package(
    source_type: str = Query(...), source_id: str = Query(...),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return guardianx_reports_service.audit_evidence_package(db, source_type, source_id)


@router.get("/reports/knowledge-provenance")
def get_report_knowledge_provenance(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return guardianx_reports_service.knowledge_provenance_report(db, _tenant(current_user))


# ---------------------------------------------------------------------------
# Section 1 — AI Assurance Center
# ---------------------------------------------------------------------------


@router.get("/assurance-center/summary")
def get_assurance_center_summary(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return guardianx_assurance_center_service.assurance_center_summary(db)


@router.get("/assurance-center/models/{model_id}")
def get_assurance_center_model(model_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return guardianx_assurance_center_service.model_assurance_summary(db, model_id)
    except UnknownModelRegistryEntryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
