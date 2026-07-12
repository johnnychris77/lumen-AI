"""Project Sentinel-X, Section 8: Predictive Risk.

Deterministic trend extrapolation over real, already-computed signal --
never a trained forecasting model. Every forecast states its confidence
and the assumptions behind it explicitly, so it is never mistaken for a
statistically validated prediction.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.models.sentinelx_risk import RISK_LEVEL_CRITICAL, RISK_LEVEL_HIGH, SentinelXRiskAssessment
from app.services.vulcan_anatomy_zone_service import zone_reliability_analysis
from app.services.vulcan_progression_service import compute_progression, findings_timeline


def forecast_escalating_corrosion(db: Session, tenant_id: str, instrument_identity: str) -> dict:
    progression = compute_progression(db, tenant_id, instrument_identity)
    timeline = findings_timeline(db, tenant_id, instrument_identity)
    corrosion_events = [e for e in timeline if e["finding_type"] in ("corrosion", "rust", "pitting")]
    escalating = progression["progression"] in ("rapidly_worsening", "slowly_worsening") and len(corrosion_events) >= 2
    return {
        "forecast": "escalating_corrosion_likely" if escalating else "no_clear_escalation_pattern",
        "confidence": progression["confidence"] if corrosion_events else "low",
        "assumptions": "Based on the real severity trend across prior corrosion/rust/pitting findings; does not account for any future intervention.",
        "supporting_evidence": {"progression": progression["progression"], "corrosion_event_count": len(corrosion_events)},
    }


def forecast_repeat_blood_findings(db: Session, tenant_id: str, instrument_identity: str) -> dict:
    timeline = findings_timeline(db, tenant_id, instrument_identity)
    blood_events = [e for e in timeline if e["finding_type"] == "blood"]
    likely = len(blood_events) >= 2
    return {
        "forecast": "repeat_blood_finding_risk_elevated" if likely else "no_repeat_pattern_established",
        "confidence": "moderate" if len(blood_events) >= 3 else "low",
        "assumptions": "Based on the count of real prior blood findings for this instrument; cleaning process itself is not directly observed.",
        "supporting_evidence": {"blood_event_count": len(blood_events)},
    }


def forecast_inspection_backlog_risk(db: Session, tenant_id: str) -> dict:
    queued = db.query(models.Inspection).filter(models.Inspection.tenant_id == tenant_id, models.Inspection.status == "queued").count()
    total = db.query(models.Inspection).filter(models.Inspection.tenant_id == tenant_id).count()
    backlog_pct = round(100 * queued / total, 1) if total else 0.0
    return {
        "forecast": "elevated_backlog_risk" if backlog_pct >= 20 else "backlog_within_normal_range",
        "confidence": "moderate" if total >= 10 else "low",
        "assumptions": "Based on the real proportion of inspections still queued; does not model future inspection throughput.",
        "supporting_evidence": {"queued_count": queued, "total_inspections": total, "backlog_pct": backlog_pct},
    }


def forecast_high_risk_workflows(db: Session, tenant_id: str) -> dict:
    assessments = db.query(SentinelXRiskAssessment).filter(SentinelXRiskAssessment.tenant_id == tenant_id).order_by(SentinelXRiskAssessment.created_at.desc()).limit(50).all()
    high_risk = sum(1 for a in assessments if a.risk_level in (RISK_LEVEL_HIGH, RISK_LEVEL_CRITICAL))
    pct = round(100 * high_risk / len(assessments), 1) if assessments else 0.0
    return {
        "forecast": "elevated_high_risk_workflow_share" if pct >= 25 else "high_risk_share_within_normal_range",
        "confidence": "moderate" if len(assessments) >= 10 else "low",
        "assumptions": "Based on the most recent 50 real risk assessments; not a prediction of any specific future inspection.",
        "supporting_evidence": {"high_or_critical_count": high_risk, "sample_size": len(assessments), "pct": pct},
    }


def forecast_recurring_anatomy_failures(db: Session, tenant_id: str, instrument_identity: str, instrument_type: str) -> dict:
    analysis = zone_reliability_analysis(db, tenant_id, instrument_identity, instrument_type)
    recurring_zones = [z for z in analysis["zones"] if z["recurrence_count"] >= 2]
    return {
        "forecast": "recurring_anatomy_failure_pattern" if recurring_zones else "no_recurring_zone_pattern",
        "confidence": "moderate" if recurring_zones else "low",
        "assumptions": "Based on real per-zone finding recurrence counts for this instrument.",
        "supporting_evidence": {"recurring_zones": [z["anatomy_zone"] for z in recurring_zones]},
    }


def predictive_risk_summary(db: Session, tenant_id: str, instrument_identity: str, instrument_type: str = "") -> dict:
    return {
        "escalating_corrosion": forecast_escalating_corrosion(db, tenant_id, instrument_identity),
        "repeat_blood_findings": forecast_repeat_blood_findings(db, tenant_id, instrument_identity),
        "inspection_backlog_risk": forecast_inspection_backlog_risk(db, tenant_id),
        "high_risk_workflows": forecast_high_risk_workflows(db, tenant_id),
        "recurring_anatomy_failures": forecast_recurring_anatomy_failures(db, tenant_id, instrument_identity, instrument_type),
        "human_review_required": True,
    }
