"""v4.6 — Project Vanguard, Section 9: Governance Dashboard.

At least five pre-existing governance-adjacent surfaces were checked
before writing this file: Horizon's `/api/horizon/governance/*` and
Beacon's `/api/beacon/governance/*` (both scoped narrowly to their own
sprint's knowledge-sharing participation, not general org governance),
`governance_console.py` (retention-policy compliance), `governance_
command_center.py` (SLA + packet-release work items — real, composed
here for "workflow compliance"), `accreditation_engine.py` (real
audit-readiness scoring — composed here), and
`/api/enterprise/governance-intelligence` — whose `/summary` route
returns **literal hard-coded integers** (92, 88, 86, 90) for every
signal, not a real computation. That last one is a genuinely fabricated
pre-existing surface; this module does not read from or extend it.

  * Policy compliance — real count of enabled `RetentionPolicy` rows
    (the same table `governance_console.py`'s summary already reads).
  * Knowledge adoption — `knowledge_graph_service.learning_confidence`.
  * Workflow compliance — `governance_command_center.command_center_
    summary` (SLA events + packet-release exceptions).
  * Audit readiness — `accreditation_engine.compute_regulatory_dashboard`.
  * Training completion — a genuinely new, small org-wide rollup:
    averages `competency_service.technician_quality_dashboard`'s
    real per-technician `training_progress_pct` across the org (no
    existing "% required training completed" aggregation existed
    anywhere before this).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.governance_command_center import command_center_summary
from app.services import accreditation_engine, competency_service, knowledge_graph_service


def _policy_compliance(db: Session, tenant_id: str) -> dict:
    enabled = (
        db.query(models.RetentionPolicy)
        .filter(models.RetentionPolicy.tenant_id == tenant_id, models.RetentionPolicy.is_enabled)
        .count()
    )
    total = db.query(models.RetentionPolicy).filter(models.RetentionPolicy.tenant_id == tenant_id).count()
    return {"enabled_policy_count": enabled, "total_policy_count": total}


def _training_completion(db: Session, tenant_id: str) -> dict:
    dashboard = competency_service.technician_quality_dashboard(db, tenant_id)
    values = [t["training_progress_pct"] for t in dashboard["technicians"] if t.get("training_progress_pct") is not None]
    return {
        "org_avg_training_progress_pct": round(sum(values) / len(values), 1) if values else None,
        "technician_count": len(dashboard["technicians"]),
    }


def governance_dashboard(db: Session, tenant_id: str, *, tenant_name: str = "") -> dict:
    tenant_name = tenant_name or tenant_id
    regulatory = accreditation_engine.compute_regulatory_dashboard(tenant_id, "", db)
    workflow = command_center_summary(db, tenant_id, tenant_name)
    knowledge = knowledge_graph_service.learning_confidence(db, tenant_id)

    return {
        "policy_compliance": _policy_compliance(db, tenant_id),
        "knowledge_adoption": knowledge,
        "workflow_compliance": {
            "sla_open_count": workflow["sla"]["open_count"],
            "release_exception_count": workflow["release_governance"]["exception_count"],
            "work_item_count": workflow["work_items"]["count"],
            "critical_work_items": workflow["work_items"]["critical_count"],
        },
        "audit_readiness": {
            "overall_readiness_score": regulatory.overall_readiness_score,
            "readiness_tier": regulatory.readiness_tier,
            "total_deficiencies": regulatory.total_deficiencies,
            "critical_deficiencies": regulatory.critical_deficiencies,
            "data_source": regulatory.data_source,
        },
        "training_completion": _training_completion(db, tenant_id),
        "human_review_required": True,
    }
