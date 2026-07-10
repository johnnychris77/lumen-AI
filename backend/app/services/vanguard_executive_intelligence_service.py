"""v4.6 — Project Vanguard, Section 1: Executive Intelligence Center.

Composes the eight named dimensions from services that already compute
each one for real — this module recomputes none of them:

  * Enterprise Readiness / Enterprise Risk / AI Health / Knowledge Growth
    — `pulse_command_center_service.pulse_command_center`.
  * Surgical Readiness — `orbit_executive_service.executive_surgical_operations`.
  * SPD Quality — `atlas_dashboard_service.enterprise_dashboard` (when the
    tenant has a resolvable enterprise-hierarchy facility; otherwise
    falls back to the live Pulse KPI's inspection-quality signal, never
    a fabricated quality score).
  * Financial Impact — `vanguard_financial_service.financial_intelligence`.
  * Capacity — a genuinely new, small composition: Digital Twin
    utilization plus today's scheduled case volume (`or_connect_service.
    list_cases`). No dedicated "facility capacity" model exists anywhere
    in this codebase; this is the closest real, non-fabricated proxy.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.services import (
    atlas_dashboard_service,
    or_connect_service,
    orbit_executive_service,
    platform_org_service,
    pulse_command_center_service,
    vanguard_financial_service,
)


def _capacity(db: Session, tenant_id: str, *, facility_id: str = "") -> dict:
    from app.services import digital_twin_engine

    twin_dashboard = digital_twin_engine.compute_twin_dashboard(tenant_id, facility_id, db)
    today = datetime.now(timezone.utc).date()
    cases_today = or_connect_service.list_cases(db, tenant_id, target_date=today)
    return {
        "utilization_pct": twin_dashboard.twin_state.utilization_pct,
        "cases_scheduled_today": len(cases_today),
        "bottleneck_station": twin_dashboard.twin_state.bottleneck_station,
    }


def executive_intelligence_center(db: Session, tenant_id: str, *, facility_id: str = "") -> dict:
    command_center = pulse_command_center_service.pulse_command_center(db, tenant_id)
    surgical = orbit_executive_service.executive_surgical_operations(db, tenant_id, facility_id=facility_id)
    financial = vanguard_financial_service.financial_intelligence(db, tenant_id, facility_id=facility_id)
    capacity = _capacity(db, tenant_id, facility_id=facility_id)

    facility = platform_org_service.facility_for_tenant(db, tenant_id)
    if facility is not None:
        enterprise = atlas_dashboard_service.enterprise_dashboard(db, facility["system_id"])
        spd_quality = {"source": "atlas_enterprise_dashboard", "enterprise_quality_score": enterprise["enterprise_quality_score"]}
    else:
        from app.services import pulse_kpi_service

        kpis = pulse_kpi_service.live_kpis(db, tenant_id)
        spd_quality = {
            "source": "pulse_live_kpis", "ai_confidence_avg": kpis["ai_confidence_avg"], "coverage_pct_avg": kpis["coverage_pct_avg"],
            "note": "No enterprise-hierarchy facility on record — falling back to live KPI signal, not a fabricated enterprise quality score.",
        }

    return {
        "enterprise_readiness": {
            "enterprise_risk_score": command_center["enterprise_health"]["enterprise_risk_score"],
            "drift_detected": command_center["enterprise_health"]["drift_detected"],
        },
        "surgical_readiness": {
            "readiness_pct": surgical["readiness_pct"], "delayed_cases": surgical["delayed_cases"],
        },
        "spd_quality": spd_quality,
        "financial_impact": {
            "repair_cost_trend_usd": financial["repair_cost_trend_usd"],
            "avoided_replacement_cost_usd": financial["avoided_replacement_cost_usd"],
            "data_source": financial["data_source"],
        },
        "capacity": capacity,
        "enterprise_risk": {
            "enterprise_alerts": command_center["enterprise_alerts"],
        },
        "ai_health": command_center["ai_model_health"],
        "knowledge_growth": command_center["knowledge_growth"],
        "human_review_required": True,
    }
