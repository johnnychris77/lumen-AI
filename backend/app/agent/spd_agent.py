from __future__ import annotations

from typing import Dict, Any


def build_agent_assessment(inspection) -> Dict[str, Any]:
    issue = (inspection.detected_issue or "unknown").lower()
    instrument = inspection.instrument_type or "unknown"
    confidence = float(inspection.confidence or 0.0)
    risk_score = int(getattr(inspection, "risk_score", 0) or 0)

    priority = "low"
    if risk_score >= 80:
        priority = "critical"
    elif risk_score >= 60:
        priority = "high"
    elif risk_score >= 30:
        priority = "medium"

    escalation_needed = priority in {"high", "critical"} or issue in {
        "debris",
        "stain",
        "corrosion",
    }

    recommended_actions = []

    if issue in {"debris", "stain"}:
        recommended_actions.append("Hold instrument for manual SPD QA review")
        recommended_actions.append("Repeat cleaning and borescope inspection before release")

    if issue == "corrosion":
        recommended_actions.append("Quarantine instrument from clinical use")
        recommended_actions.append("Escalate to vendor/manufacturer quality review")

    if instrument in {"orthopedic_drill", "arthroscopy_shaver"}:
        recommended_actions.append("Confirm lumen/cannulation pathway is visually clear")

    if confidence >= 0.85:
        recommended_actions.append("Prioritize immediate leadership review due to high-confidence finding")

    if not recommended_actions:
        recommended_actions.append("No critical issue flagged; continue standard QA workflow")

    summary = (
        f"LumenAI SPD Agent reviewed inspection {inspection.id} for "
        f"{instrument}. Detected issue: {issue}. "
        f"Priority: {priority}. Risk score: {risk_score}."
    )

    return {
        "inspection_id": inspection.id,
        "priority": priority,
        "risk_score": risk_score,
        "escalation_needed": escalation_needed,
        "recommended_actions": recommended_actions,
        "summary": summary,
    }
