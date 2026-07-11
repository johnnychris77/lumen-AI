"""v4.9 — Project Phoenix, Section 7: Platform Health Dashboard.

Composes seven named health areas from real, already-computed signals
across prior sprints — no re-derivation. Where no clean existing signal
exists (Security, Integration), Phoenix computes a real ratio from
existing tables (`TenantMembership`, `TenantSubscriptionP14`,
`ExternalSystemConnector`) rather than fabricating a score, and reports
"insufficient data" when a tenant has no rows in the relevant table yet.
Digital Twin Health reads the *instrument-flow* twin (`digital_twin_
engine.py`) — a different twin from Apollo's Quality Digital Twin, which
is instead this dashboard's real input for "Quality Health".
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.models.phoenix_intelligence import DISCLAIMER
from app.services import phoenix_ai_observatory_service, phoenix_knowledge_evolution_service, phoenix_workflow_optimization_service
from app.services.apollo_quality_twin_service import twin_history
from app.services.knowledge_governance_service import governance_summary


def compute_ai_health_score(db: Session, tenant_id: str) -> dict:
    obs = phoenix_ai_observatory_service.observatory_summary(db, tenant_id)
    if not obs["sample_size"]:
        return {"score": None, "note": "insufficient data — no supervisor reviews recorded yet"}
    agreement = obs["human_agreement_rate"] or 0.0
    score = round(100 * agreement * (0.7 if obs["model_drift_detected"] else 1.0), 1)
    return {"score": score, "sample_size": obs["sample_size"], "drift_detected": obs["model_drift_detected"]}


def compute_knowledge_health_score(db: Session, tenant_id: str) -> dict:
    gov = governance_summary(db, tenant_id)
    if not gov["total_articles"]:
        return {"score": None, "note": "insufficient data — no knowledge articles recorded yet"}
    evolution = phoenix_knowledge_evolution_service.knowledge_evolution_summary(db, tenant_id)
    penalty = min(50.0, 5.0 * (len(evolution["duplicate_candidates"]) + len(evolution["contradictory_guidance"]) + len(evolution["outdated_guidance"])))
    approved_ratio = gov["by_approval_status"].get("approved", 0) / gov["total_articles"]
    score = round(max(0.0, 100 * approved_ratio - penalty), 1)
    return {"score": score, "total_articles": gov["total_articles"]}


def compute_workflow_health_score(db: Session, tenant_id: str) -> dict:
    opt = phoenix_workflow_optimization_service.workflow_optimization_summary(db, tenant_id)
    duration = opt["duration_analysis"]
    if not duration.get("sample_size"):
        return {"score": None, "note": "insufficient data — no workflow executions recorded yet"}
    failed = duration["by_status"].get("failed", 0)
    penalty = min(60.0, 10.0 * failed + 5.0 * len(opt["approval_bottlenecks"]))
    return {"score": round(max(0.0, 100 - penalty), 1), "sample_size": duration["sample_size"]}


def compute_digital_twin_health_score(db: Session, tenant_id: str) -> dict:
    try:
        from app.services.digital_twin_engine import compute_twin_dashboard

        dashboard = compute_twin_dashboard(tenant_id, "", db)
    except Exception:
        return {"score": None, "note": "insufficient data — digital twin unavailable for this tenant"}
    if dashboard.data_source != "real":
        # digital_twin_engine falls back to seeded-random mock data when no
        # real flow/station rows exist for this tenant — that's a
        # legitimate demo fallback for the twin's own dashboard, but never a
        # real health signal, so Phoenix reports it as no data rather than
        # scoring a fabricated number.
        return {"score": None, "note": "insufficient data — no real digital twin data recorded for this tenant yet"}
    utilization = dashboard.twin_state.utilization_pct
    open_alerts = len(dashboard.open_alerts)
    # A healthy utilization band is 40-85%; too low (idle) or too high
    # (overloaded) both reduce the score, same as too many open alerts.
    band_penalty = 0.0 if 40 <= utilization <= 85 else min(40.0, abs(utilization - 62.5))
    alert_penalty = min(40.0, 10.0 * open_alerts)
    score = round(max(0.0, 100 - band_penalty - alert_penalty), 1)
    return {"score": score, "utilization_pct": utilization, "open_alerts": open_alerts, "data_source": dashboard.data_source}


def compute_security_health_score(db: Session, tenant_id: str) -> dict:
    total = db.query(models.TenantMembership).filter(models.TenantMembership.tenant_id == tenant_id).count()
    if not total:
        return {"score": None, "note": "insufficient data — no tenant memberships recorded yet"}
    enabled = db.query(models.TenantMembership).filter(
        models.TenantMembership.tenant_id == tenant_id, models.TenantMembership.is_enabled,
    ).count()
    from app.models.tenant_subscription_p14 import TenantSubscriptionP14

    baa_signed = False
    sub = db.query(TenantSubscriptionP14).filter_by(tenant_id=tenant_id).first()
    if sub is not None:
        baa_signed = sub.hipaa_baa_signed_at is not None
    score = round(80 * (enabled / total) + (20 if baa_signed else 0), 1)
    return {"score": score, "enabled_membership_ratio": round(enabled / total, 2), "hipaa_baa_signed": baa_signed}


def compute_integration_health_score(db: Session, tenant_id: str) -> dict:
    rows = db.query(models.ExternalSystemConnector).filter(models.ExternalSystemConnector.tenant_id == tenant_id).all()
    if not rows:
        return {"score": None, "note": "insufficient data — no external connectors configured yet"}
    active = sum(1 for r in rows if r.connection_status == "active")
    errored = sum(1 for r in rows if r.connection_status == "error")
    score = round(max(0.0, 100 * (active / len(rows)) - 20 * errored), 1)
    return {"score": score, "connector_count": len(rows), "active_count": active, "error_count": errored}


def compute_quality_health_score(db: Session, tenant_id: str) -> dict:
    """Reads the most recent Quality Digital Twin snapshot (Apollo,
    v4.7) — never recomputes one here, since that would add a write
    side-effect to a read-only health dashboard."""
    history = twin_history(db, tenant_id, "unspecified", limit=1)
    if not history:
        return {"score": None, "note": "insufficient data — no Quality Digital Twin snapshot recorded yet"}
    latest = history[0]
    return {"score": latest["overall_score"], "snapshot_at": latest["created_at"]}


def platform_health_dashboard(db: Session, tenant_id: str) -> dict:
    areas = {
        "ai_health": compute_ai_health_score(db, tenant_id),
        "knowledge_health": compute_knowledge_health_score(db, tenant_id),
        "workflow_health": compute_workflow_health_score(db, tenant_id),
        "digital_twin_health": compute_digital_twin_health_score(db, tenant_id),
        "security_health": compute_security_health_score(db, tenant_id),
        "integration_health": compute_integration_health_score(db, tenant_id),
        "quality_health": compute_quality_health_score(db, tenant_id),
    }
    scored = [a["score"] for a in areas.values() if a["score"] is not None]
    overall = round(sum(scored) / len(scored), 1) if scored else None
    return {
        **areas, "overall_platform_maturity": overall,
        "human_review_required": True, "disclaimer": DISCLAIMER,
    }
