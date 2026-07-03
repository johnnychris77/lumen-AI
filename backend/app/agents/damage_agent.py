"""Phase 22 §5 — Damage Detection Agent.

Owns rust, corrosion, crack, pitting, wear, missing component, and
insulation damage. Reads the real inspection's persisted finding — see the
note in contamination_agent.py about the current one-finding-per-row
schema limitation, which applies here too.
"""
from __future__ import annotations

from app.agents.context import DamageContext, DamageFinding
from app.services.pre_sterilization_command_center_service import _REPAIRABLE_ISSUES

DAMAGE_FINDING_TYPES = {"rust", "corrosion", "crack", "pitting", "wear", "missing_component", "insulation_damage"}


class DamageDetectionAgent:
    NAME = "Damage Detection Agent"
    VERSION = "1.0.0"
    CAPABILITIES = ["detect_structural_damage", "recommend_repair_or_removal", "track_damage_trend"]
    DEPENDS_ON = ["InstrumentIntelligenceAgent", "AnatomyIntelligenceAgent"]

    def run(self, detected_issue: str, risk_score: int, prior_risk_score: int | None = None) -> DamageContext:
        issue = (detected_issue or "").strip().lower()
        if issue not in DAMAGE_FINDING_TYPES:
            return DamageContext(findings=[], has_damage=False)

        severity = "critical" if risk_score >= 85 else ("high" if risk_score >= 70 else ("medium" if risk_score >= 40 else "low"))
        repairable = issue in _REPAIRABLE_ISSUES
        repair_recommendation = (
            "Route to repair evaluation." if repairable and severity in ("medium", "high")
            else "Remove from service pending replacement." if not repairable and severity in ("high", "critical")
            else "Monitor and re-inspect at next cycle."
        )

        trend = "stable"
        if prior_risk_score is not None:
            if risk_score > prior_risk_score:
                trend = "worsening"
            elif risk_score < prior_risk_score:
                trend = "improving"

        finding = DamageFinding(
            finding_type=issue,
            severity=severity,
            repair_recommendation=repair_recommendation,
            trend=trend,
        )
        return DamageContext(findings=[finding], has_damage=True)
