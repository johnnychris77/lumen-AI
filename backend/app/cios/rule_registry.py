"""Phase 23 §11 — Clinical Rule Registry.

Every rule here is a real rule already enforced somewhere in the codebase
— this registry documents and versions rules that exist, it does not
invent hypothetical ones. `evidence` points at the function that actually
implements the rule so the registry can never drift from reality.
"""
from __future__ import annotations

CLINICAL_RULE_REGISTRY: list[dict] = [
    {
        "rule_id": "RULE-001",
        "name": "Structural defect escalation",
        "purpose": "Escalate moderate-or-greater crack, missing component, or insulation damage to REMOVE FROM SERVICE.",
        "evidence": "app/services/baseline_comparison_scoring_service.py::recommended_action (structural defects block)",
        "applies_to": ["crack", "missing_component", "insulation_damage"],
        "priority": "critical",
        "version": "1.0",
        "approval_status": "approved",
    },
    {
        "rule_id": "RULE-002",
        "name": "Severe corrosion escalation",
        "purpose": "Escalate severity-3+ corrosion to REMOVE FROM SERVICE.",
        "evidence": "app/services/baseline_comparison_scoring_service.py::recommended_action (corrosion severity_index >= 3)",
        "applies_to": ["corrosion"],
        "priority": "critical",
        "version": "1.0",
        "approval_status": "approved",
    },
    {
        "rule_id": "RULE-003",
        "name": "Residual contamination reprocessing",
        "purpose": "Route moderate+ blood/tissue/organic-residue/debris/bone to REPROCESS.",
        "evidence": "app/services/baseline_comparison_scoring_service.py::recommended_action (contamination_actionable)",
        "applies_to": ["blood", "tissue", "other_organic_residue", "debris", "bone"],
        "priority": "high",
        "version": "1.0",
        "approval_status": "approved",
    },
    {
        "rule_id": "RULE-004",
        "name": "High-retention zone escalation",
        "purpose": "Escalate trace+ contamination in a high-retention zone (serrations, box locks, lumens, hinges, o-ring areas, drill-bit flutes, ratchets, insulation edges) to REPROCESS even at low severity elsewhere.",
        "evidence": "app/services/instrument_zones.py::is_high_retention; baseline_comparison_scoring_service.py::_overall_result",
        "applies_to": ["blood", "tissue", "other_organic_residue", "debris", "bone"],
        "priority": "high",
        "version": "1.0",
        "approval_status": "approved",
    },
    {
        "rule_id": "RULE-005",
        "name": "No-baseline supervisor gate",
        "purpose": "Withhold final scoring and require supervisor review when no approved baseline exists for the instrument.",
        "evidence": "app/services/baseline_comparison_scoring_service.py::analyze_inspection (governance gate)",
        "applies_to": ["all instruments"],
        "priority": "critical",
        "version": "1.0",
        "approval_status": "approved",
    },
    {
        "rule_id": "RULE-006",
        "name": "Baseline mismatch supervisor review",
        "purpose": "Route to SUPERVISOR REVIEW when baseline match score is below 70%.",
        "evidence": "app/services/baseline_comparison_scoring_service.py::recommended_action (baseline_match_score < 0.70)",
        "applies_to": ["all instruments"],
        "priority": "medium",
        "version": "1.0",
        "approval_status": "approved",
    },
    {
        "rule_id": "RULE-007",
        "name": "Repairable structural defect classification",
        "purpose": "Classify a REMOVE FROM SERVICE outcome as a repair candidate only when the defect is crack, corrosion, or insulation damage — never contamination.",
        "evidence": "app/services/pre_sterilization_command_center_service.py::classify_readiness, _REPAIRABLE_ISSUES",
        "applies_to": ["crack", "corrosion", "insulation_damage"],
        "priority": "medium",
        "version": "1.0",
        "approval_status": "approved",
    },
    {
        "rule_id": "RULE-008",
        "name": "Critical finding safety threshold",
        "purpose": "Block a pilot GO decision when any critical finding type's false-negative rate exceeds 5%.",
        "evidence": "app/services/pilot_validation_service.py::CRITICAL_FN_RATE_THRESHOLD, evaluate_go_no_go",
        "applies_to": ["blood", "tissue", "organic_residue", "crack", "missing_component"],
        "priority": "critical",
        "version": "1.0",
        "approval_status": "approved",
    },
    {
        "rule_id": "RULE-009",
        "name": "Incomplete zone coverage flag",
        "purpose": "Flag an inspection's coverage as not_assessed/incomplete/insufficient when required high-risk zones were not tagged as inspected.",
        "evidence": "app/services/inspection_coverage.py::compute_coverage",
        "applies_to": ["all instruments"],
        "priority": "medium",
        "version": "1.0",
        "approval_status": "approved",
    },
    {
        "rule_id": "RULE-010",
        "name": "Human final authority",
        "purpose": "No AI recommendation is a final disposition — every readiness state requires supervisor review or override before an instrument proceeds to packaging.",
        "evidence": "docs/architecture/design-principles.md (Principle 4); app/routes/ai_clinical_review.py",
        "applies_to": ["all instruments"],
        "priority": "critical",
        "version": "1.0",
        "approval_status": "approved",
    },
]


def get_rule(rule_id: str) -> dict | None:
    return next((r for r in CLINICAL_RULE_REGISTRY if r["rule_id"] == rule_id), None)


def rules_applying_to(finding_type: str) -> list[dict]:
    return [r for r in CLINICAL_RULE_REGISTRY if finding_type in r["applies_to"] or "all instruments" in r["applies_to"]]
