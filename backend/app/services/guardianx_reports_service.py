"""v5.2 — Project GuardianX, Section 10: AI Assurance Reports.

Five named reports, each a read-only composition over the services this
sprint (and Olympus/Phoenix before it) already built -- no new table,
no fabricated PDF pipeline. Report contents are exactly the same
governed, evidence-based, human-review-required data every other
GuardianX endpoint already returns.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.guardianx_assurance import GOVERNANCE_GATES
from app.models.olympus_network import AIModelRegistryEntry
from app.services import (
    guardianx_audit_replay_service,
    guardianx_compliance_mapping_service,
    guardianx_model_governance_service,
    guardianx_risk_registry_service,
    guardianx_trust_score_service,
)


def executive_ai_assurance_report(db: Session, tenant_id: str) -> dict:
    models = db.query(AIModelRegistryEntry).all()
    return {
        "report_type": "executive_ai_assurance_report",
        "total_models": len(models),
        "models_governance_approved": sum(1 for m in models if m.governance_status == "approved"),
        "models_certified": sum(1 for m in models if m.certification_status == "certified"),
        "risk_registry": guardianx_risk_registry_service.risk_registry_summary(db),
        "platform_trust_score": guardianx_trust_score_service.compute_platform_trust_score(db, tenant_id),
        "human_review_required": True,
    }


def model_validation_report(db: Session, model_id: int) -> dict:
    governance = guardianx_model_governance_service.get_governance_record(db, model_id)
    return {
        "report_type": "model_validation_report",
        "model": governance,
        "risks": guardianx_risk_registry_service.list_risks_for_model(db, model_id),
        "trust_score": guardianx_trust_score_service.compute_model_trust_score(db, model_id),
        "human_review_required": True,
    }


def governance_report(db: Session) -> dict:
    models = db.query(AIModelRegistryEntry).all()
    statuses: dict[str, int] = {}
    for m in models:
        statuses[m.governance_status] = statuses.get(m.governance_status, 0) + 1
    return {
        "report_type": "governance_report",
        "gates": GOVERNANCE_GATES,
        "by_governance_status": statuses,
        "total_models": len(models),
        "human_review_required": True,
    }


def audit_evidence_package(db: Session, source_type: str, source_id: str) -> dict:
    return {
        "report_type": "audit_evidence_package",
        "replay": guardianx_audit_replay_service.replay_recommendation(db, source_type, source_id),
        "human_review_required": True,
    }


def knowledge_provenance_report(db: Session, tenant_id: str) -> dict:
    return {
        "report_type": "knowledge_provenance_report",
        "knowledge_trust_score": guardianx_trust_score_service.compute_knowledge_trust_score(db, tenant_id),
        "compliance_traceability": guardianx_compliance_mapping_service.traceability_matrix(db),
        "human_review_required": True,
    }
