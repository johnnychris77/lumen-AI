"""v5.2 — Project GuardianX, Section 9: Trust Score.

Knowledge/Workflow/Digital Twin Trust Score reuse Phoenix's
`compute_knowledge_health_score`/`compute_workflow_health_score`/
`compute_digital_twin_health_score` (`phoenix_platform_health_service.py`,
v4.9) directly -- never a third scoring engine for the same signal.
Model Trust Score is genuinely new (nothing scores an individual AI
model's trustworthiness). Platform Trust Score is a new,
assurance-specific composite -- distinct from Phoenix's Platform
Maturity Index (platform *improvement*) and Phoenix's own Platform
Health (operational health): this one specifically weighs governance/
certification/risk posture across every registered AI model.

Every computation is persisted as an `AIAssuranceTrustSnapshot` --
"Display why each score was calculated" means the `components`
breakdown is always stored alongside the overall number, the same
snapshot discipline established by `NetworkTrustSnapshot` (Olympus).
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.guardianx_assurance import (
    TRUST_SCOPE_DIGITAL_TWIN,
    TRUST_SCOPE_KNOWLEDGE,
    TRUST_SCOPE_MODEL,
    TRUST_SCOPE_PLATFORM,
    TRUST_SCOPE_WORKFLOW,
    AIAssuranceTrustSnapshot,
    AIModelRiskEntry,
)
from app.models.olympus_network import MODEL_CERT_CERTIFIED, AIModelRegistryEntry
from app.services import phoenix_platform_health_service
from app.services.olympus_model_registry_service import get_model_or_404


def _persist(db: Session, *, scope: str, scope_ref_id: str, components: dict, overall_score: float | None) -> dict:
    row = AIAssuranceTrustSnapshot(
        scope=scope, scope_ref_id=scope_ref_id, components_json=json.dumps(components), overall_score=overall_score,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id, "scope": row.scope, "scope_ref_id": row.scope_ref_id, "components": components,
        "overall_score": row.overall_score, "computed_at": row.computed_at.isoformat(),
        "human_review_required": row.human_review_required,
    }


def compute_model_trust_score(db: Session, model_id: int) -> dict:
    model = get_model_or_404(db, model_id)
    model_risks = db.query(AIModelRiskEntry).filter(AIModelRiskEntry.model_id == model_id).all()
    open_high_risk = sum(1 for r in model_risks if r.status == "open" and r.severity in ("critical", "high"))

    components = {
        "validated": 100.0 if model.validation_status == "validated" else 0.0,
        "certified": 100.0 if model.certification_status == MODEL_CERT_CERTIFIED else 0.0,
        "governance_approved": 100.0 if model.governance_status == "approved" else 0.0,
        "risk_posture": max(0.0, 100.0 - 25.0 * open_high_risk),
    }
    overall = round(sum(components.values()) / len(components), 1)
    return _persist(db, scope=TRUST_SCOPE_MODEL, scope_ref_id=str(model_id), components=components, overall_score=overall)


def compute_knowledge_trust_score(db: Session, tenant_id: str) -> dict:
    result = phoenix_platform_health_service.compute_knowledge_health_score(db, tenant_id)
    return _persist(db, scope=TRUST_SCOPE_KNOWLEDGE, scope_ref_id=tenant_id, components=result, overall_score=result.get("score"))


def compute_workflow_trust_score(db: Session, tenant_id: str) -> dict:
    result = phoenix_platform_health_service.compute_workflow_health_score(db, tenant_id)
    return _persist(db, scope=TRUST_SCOPE_WORKFLOW, scope_ref_id=tenant_id, components=result, overall_score=result.get("score"))


def compute_digital_twin_trust_score(db: Session, tenant_id: str) -> dict:
    result = phoenix_platform_health_service.compute_digital_twin_health_score(db, tenant_id)
    return _persist(db, scope=TRUST_SCOPE_DIGITAL_TWIN, scope_ref_id=tenant_id, components=result, overall_score=result.get("score"))


def compute_platform_trust_score(db: Session, tenant_id: str) -> dict:
    models = db.query(AIModelRegistryEntry).all()
    governed = sum(1 for m in models if m.governance_status == "approved")
    governance_ratio = round(100.0 * governed / len(models), 1) if models else None

    knowledge = phoenix_platform_health_service.compute_knowledge_health_score(db, tenant_id)
    workflow = phoenix_platform_health_service.compute_workflow_health_score(db, tenant_id)
    digital_twin = phoenix_platform_health_service.compute_digital_twin_health_score(db, tenant_id)

    scored_components = {
        "governance_ratio": governance_ratio,
        "knowledge": knowledge.get("score"),
        "workflow": workflow.get("score"),
        "digital_twin": digital_twin.get("score"),
    }
    available = [v for v in scored_components.values() if v is not None]
    overall = round(sum(available) / len(available), 1) if available else None

    return _persist(
        db, scope=TRUST_SCOPE_PLATFORM, scope_ref_id=tenant_id, components=scored_components, overall_score=overall,
    )


def trust_score_history(db: Session, *, scope: str, scope_ref_id: str = "", limit: int = 20) -> list[dict]:
    query = db.query(AIAssuranceTrustSnapshot).filter(AIAssuranceTrustSnapshot.scope == scope)
    if scope_ref_id:
        query = query.filter(AIAssuranceTrustSnapshot.scope_ref_id == scope_ref_id)
    rows = query.order_by(AIAssuranceTrustSnapshot.computed_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id, "scope": r.scope, "scope_ref_id": r.scope_ref_id, "overall_score": r.overall_score,
            "components": json.loads(r.components_json), "computed_at": r.computed_at.isoformat(),
        }
        for r in rows
    ]
