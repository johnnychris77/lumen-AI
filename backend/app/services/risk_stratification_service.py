"""v1.6 — Instrument Risk Stratification (Deliverable 8).

Classifies an inspection's instrument into Low / Moderate / High / Critical
risk, using anatomy (high-retention zone involvement), findings severity,
damage presence, coverage completeness, and baseline confidence — a
point-based rubric over already-computed signals, not a new model.
"""
from __future__ import annotations

LOW = "Low Risk"
MODERATE = "Moderate Risk"
HIGH = "High Risk"
CRITICAL = "Critical"

RISK_TIERS = [LOW, MODERATE, HIGH, CRITICAL]

_STRUCTURAL_FINDINGS = {"crack", "missing_component", "insulation_damage"}


def stratify_risk(insp, *, high_risk_zone_finding: bool = False, primary_finding_type: str | None = None) -> dict:
    """Point-based risk stratification. Each contributing signal is returned
    alongside the tier so the classification is auditable, not a black box.

    `primary_finding_type` should be the real detected finding (see
    `readiness_engine.get_primary_finding_type`) — `insp.detected_issue` is
    only used as a fallback for the no-image manual-entry path."""
    points = 0
    reasons: list[str] = []

    detected_issue = (
        primary_finding_type if primary_finding_type is not None
        else (insp.detected_issue or "").strip().lower()
    )

    if detected_issue in _STRUCTURAL_FINDINGS:
        points += 3
        reasons.append(f"Structural finding ({detected_issue}).")
    elif detected_issue not in ("", "none", "unknown"):
        points += 1
        reasons.append(f"Contamination/condition finding ({detected_issue}).")

    if insp.disposition == "REMOVE FROM SERVICE":
        points += 3
        reasons.append("Escalated to remove-from-service.")

    if high_risk_zone_finding:
        points += 2
        reasons.append("Finding located in a high-retention anatomy zone.")

    if insp.coverage_pct is not None and insp.coverage_pct < 75:
        points += 1
        reasons.append(f"Inspection coverage below 75% ({insp.coverage_pct}%).")
    elif insp.coverage_pct is None:
        points += 1
        reasons.append("Inspection coverage not assessed.")

    if insp.baseline_status != "approved_baseline_found":
        points += 1
        reasons.append("No approved baseline confidence available.")

    if points >= 7:
        tier = CRITICAL
    elif points >= 5:
        tier = HIGH
    elif points >= 2:
        tier = MODERATE
    else:
        tier = LOW

    return {"risk_tier": tier, "points": points, "reasons": reasons}
