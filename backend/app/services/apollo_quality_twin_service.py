"""v4.7 — Project Apollo, Section 9: Quality Digital Twin.

A genuinely new pure-composition snapshot per department — no department-
level quality composite existed before Apollo. Distinct from
`digital_twin_engine.py`'s facility/instrument-scoped workflow telemetry
twin: this tracks governance health (compliance/competency/audit-
readiness/policy-maturity/CAPA-health/education/knowledge/continuous-
improvement), not instrument flow.

Several factors below are not natively department-scoped in this codebase
(accreditation readiness, CAPA lifecycle, and the standards library are all
tenant-wide) — where that's the case, the tenant-wide value is used as an
honest proxy and the `factors_json` explicitly records which sub-scores are
department-scoped vs. tenant-wide, rather than fabricating a department
split with no underlying data.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.db import models
from app.models.apollo_quality import DISCLAIMER, POLICY_PUBLISHED, QualityTwinSnapshot
from app.services import accreditation_engine, capa_lifecycle_service, competency_service
from app.services.apollo_improvement_portfolio_service import portfolio_summary
from app.services.apollo_policy_service import list_policies

# Overall score is an equal-weighted average across the eight named
# dimensions — the one genuinely new scoring decision in this file.


def _department_technicians(db: Session, tenant_id: str, department: str) -> list[str]:
    rows = (
        db.query(models.Inspection.technician)
        .filter(
            models.Inspection.tenant_id == tenant_id, models.Inspection.technician.isnot(None),
            models.Inspection.department == (None if department == "unspecified" else department),
        )
        .distinct()
        .all()
    )
    return [r[0] for r in rows if r[0]]


def compute_quality_twin(db: Session, tenant_id: str, department: str = "unspecified") -> dict:
    factors: dict[str, str] = {}

    # Audit readiness / compliance — tenant-wide (accreditation_engine has no
    # department dimension).
    readiness = accreditation_engine.compute_accreditation_readiness(tenant_id, "", db)
    audit_readiness_score = readiness.overall_score
    compliance_score = readiness.overall_score
    factors["audit_readiness_score"] = "tenant-wide (accreditation_engine has no department dimension)"
    factors["compliance_score"] = "tenant-wide, same source as audit_readiness_score"

    # Competency — department-scoped via technicians who logged inspections
    # in this department.
    technicians = _department_technicians(db, tenant_id, department)
    training_scores = []
    education_counts = 0
    knowledge_counts = 0
    for tech in technicians:
        summary = competency_service.competency_summary(db, tech)
        if summary["training_progress_pct"] is not None:
            training_scores.append(summary["training_progress_pct"])
        education_counts += len(summary["education_completed"])
        knowledge_counts += summary["knowledge_contributions"]
    competency_score = round(sum(training_scores) / len(training_scores), 1) if training_scores else 0.0
    factors["competency_score"] = f"department-scoped across {len(technicians)} technician(s)"

    # Education — pct of department technicians with at least one completed
    # education article.
    education_score = (
        round(100 * sum(1 for t in technicians if competency_service.competency_summary(db, t)["education_completed"]) / len(technicians), 1)
        if technicians else 0.0
    )
    factors["education_score"] = f"department-scoped across {len(technicians)} technician(s)"

    # Knowledge — contributions per technician, capped at 100.
    knowledge_score = min(100.0, round(100 * knowledge_counts / len(technicians), 1)) if technicians else 0.0
    factors["knowledge_score"] = f"department-scoped across {len(technicians)} technician(s)"

    # Policy maturity — tenant-wide published-vs-total ratio (policies are
    # not department-tagged today; `affected_workflows` is free-text).
    all_policies = list_policies(db, tenant_id)
    published_policies = [p for p in all_policies if p["status"] == POLICY_PUBLISHED]
    policy_maturity_score = (
        round(100 * len(published_policies) / len(all_policies), 1) if all_policies else 0.0
    )
    factors["policy_maturity_score"] = "tenant-wide (policies are not department-tagged)"

    # CAPA health — tenant-wide lifecycle closure rate.
    lifecycle_counts = capa_lifecycle_service.lifecycle_summary(tenant_id)
    total_capas = sum(lifecycle_counts.values())
    capa_health_score = (
        round(100 * lifecycle_counts.get(capa_lifecycle_service.LIFECYCLE_CLOSED, 0) / total_capas, 1)
        if total_capas else 100.0
    )
    factors["capa_health_score"] = "tenant-wide (CAPAs are not department-tagged)"

    # Continuous improvement — tenant-wide portfolio completion rate.
    portfolio = portfolio_summary(db, tenant_id)
    continuous_improvement_score = portfolio["completion_rate_pct"] or 0.0
    factors["continuous_improvement_score"] = "tenant-wide (initiatives are not department-tagged)"

    scores = {
        "compliance_score": compliance_score, "competency_score": competency_score,
        "audit_readiness_score": audit_readiness_score, "policy_maturity_score": policy_maturity_score,
        "capa_health_score": capa_health_score, "education_score": education_score,
        "knowledge_score": knowledge_score, "continuous_improvement_score": continuous_improvement_score,
    }
    overall_score = round(sum(scores.values()) / len(scores), 1)

    snapshot = QualityTwinSnapshot(
        tenant_id=tenant_id, department=department, overall_score=overall_score,
        factors_json=json.dumps(factors), **scores,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return {
        "id": snapshot.id,
        "department": department,
        "created_at": snapshot.created_at.isoformat(),
        "scores": scores,
        "overall_score": overall_score,
        "factors": factors,
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


def twin_history(db: Session, tenant_id: str, department: str = "unspecified", *, limit: int = 20) -> list[dict]:
    rows = (
        db.query(QualityTwinSnapshot)
        .filter(QualityTwinSnapshot.tenant_id == tenant_id, QualityTwinSnapshot.department == department)
        .order_by(QualityTwinSnapshot.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id, "created_at": r.created_at.isoformat(), "department": r.department,
            "overall_score": r.overall_score,
            "scores": {
                "compliance_score": r.compliance_score, "competency_score": r.competency_score,
                "audit_readiness_score": r.audit_readiness_score, "policy_maturity_score": r.policy_maturity_score,
                "capa_health_score": r.capa_health_score, "education_score": r.education_score,
                "knowledge_score": r.knowledge_score, "continuous_improvement_score": r.continuous_improvement_score,
            },
        }
        for r in rows
    ]
