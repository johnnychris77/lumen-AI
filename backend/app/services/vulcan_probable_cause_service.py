"""Project Vulcan, Section 6: Probable Cause Classification.

Every probable cause is a "probable contributor," never a definitive root
cause, and always carries evidence, confidence, at least one alternative
explanation, and a recommended verification step -- per the brief's explicit
instruction not to claim causation.
"""
from __future__ import annotations

from app.models.vulcan_reliability import (
    CAUSE_ASSEMBLY_DAMAGE,
    CAUSE_HANDLING_DAMAGE,
    CAUSE_HEAVY_USE,
    CAUSE_INADEQUATE_DRYING,
    CAUSE_INCOMPLETE_CLEANING,
    CAUSE_MATERIAL_DEGRADATION,
    CAUSE_MOISTURE_EXPOSURE,
    CAUSE_NORMAL_WEAR,
    CAUSE_REPAIR_RECURRENCE,
    CAUSE_SUSPECTED_MANUFACTURING_DESIGN_ISSUE,
    CAUSE_UNKNOWN,
    REPAIR_OUTCOME_FAILURE_RECURRED,
    TAXONOMY_GROUP_CLEANING,
    TAXONOMY_GROUP_CONDITION,
    TAXONOMY_GROUP_INSULATION,
    TAXONOMY_GROUP_MECHANICAL,
    TAXONOMY_GROUP_POWERED_ORTHOPEDIC,
    TAXONOMY_GROUP_SCOPE_SPECIFIC,
    TAXONOMY_GROUP_UNKNOWN,
)

_GROUP_CANDIDATE_CAUSES = {
    TAXONOMY_GROUP_CLEANING: [CAUSE_INCOMPLETE_CLEANING],
    TAXONOMY_GROUP_CONDITION: [CAUSE_MOISTURE_EXPOSURE, CAUSE_INADEQUATE_DRYING, CAUSE_NORMAL_WEAR],
    TAXONOMY_GROUP_MECHANICAL: [CAUSE_HEAVY_USE, CAUSE_HANDLING_DAMAGE, CAUSE_ASSEMBLY_DAMAGE, CAUSE_NORMAL_WEAR],
    TAXONOMY_GROUP_SCOPE_SPECIFIC: [CAUSE_HANDLING_DAMAGE, CAUSE_MATERIAL_DEGRADATION],
    TAXONOMY_GROUP_POWERED_ORTHOPEDIC: [CAUSE_HEAVY_USE, CAUSE_MATERIAL_DEGRADATION],
    TAXONOMY_GROUP_INSULATION: [CAUSE_HANDLING_DAMAGE, CAUSE_MATERIAL_DEGRADATION],
    TAXONOMY_GROUP_UNKNOWN: [CAUSE_UNKNOWN],
}

_ALTERNATIVE_EXPLANATIONS = {
    TAXONOMY_GROUP_CLEANING: "A single missed pass during manual brushing/flushing is also plausible and would not indicate a systemic process issue.",
    TAXONOMY_GROUP_CONDITION: "Lighting or image-angle variation may exaggerate the apparent surface change.",
    TAXONOMY_GROUP_MECHANICAL: "Normal cumulative use over the instrument's service life may account for the same finding without any single damaging event.",
    TAXONOMY_GROUP_SCOPE_SPECIFIC: "Component wear consistent with expected service life may account for the finding independent of any single incident.",
    TAXONOMY_GROUP_POWERED_ORTHOPEDIC: "High-torque procedures naturally accelerate wear on cutting surfaces without indicating a defect.",
    TAXONOMY_GROUP_INSULATION: "Minor surface marking from routine tray handling may resemble early insulation wear without an actual breach.",
    TAXONOMY_GROUP_UNKNOWN: "Insufficient evidence is available to distinguish among possible contributors.",
}

_VERIFICATION = {
    TAXONOMY_GROUP_CLEANING: "Re-inspect after a supervised reclean and compare against the approved baseline images.",
    TAXONOMY_GROUP_CONDITION: "Compare current images with the approved baseline and prior inspection images under consistent lighting.",
    TAXONOMY_GROUP_MECHANICAL: "Manual function check by a supervisor or clinical engineering, comparing to manufacturer tolerance specifications.",
    TAXONOMY_GROUP_SCOPE_SPECIFIC: "Bench test the affected component (o-ring/seal/lens/sheath) against manufacturer specification.",
    TAXONOMY_GROUP_POWERED_ORTHOPEDIC: "Manufacturer or clinical engineering evaluation of the cutting surface against wear tolerance.",
    TAXONOMY_GROUP_INSULATION: "Electrical insulation integrity test before further clinical use.",
    TAXONOMY_GROUP_UNKNOWN: "Recapture images meeting coverage requirements before a probable cause can be assessed.",
}


def classify_probable_causes(
    taxonomy_group: str, *, repair_outcome: str | None = None, recurrence_count: int = 0,
) -> list[dict]:
    """Section 6: probable contributors for one taxonomy group + repair context."""
    candidates = list(_GROUP_CANDIDATE_CAUSES.get(taxonomy_group, [CAUSE_UNKNOWN]))
    if repair_outcome == REPAIR_OUTCOME_FAILURE_RECURRED and CAUSE_REPAIR_RECURRENCE not in candidates:
        candidates.insert(0, CAUSE_REPAIR_RECURRENCE)
    if recurrence_count >= 3 and taxonomy_group == TAXONOMY_GROUP_MECHANICAL:
        candidates.append(CAUSE_SUSPECTED_MANUFACTURING_DESIGN_ISSUE)

    confidence = "high" if recurrence_count >= 3 else "moderate" if recurrence_count >= 1 else "low"
    alternative = _ALTERNATIVE_EXPLANATIONS.get(taxonomy_group, _ALTERNATIVE_EXPLANATIONS[TAXONOMY_GROUP_UNKNOWN])
    verification = _VERIFICATION.get(taxonomy_group, _VERIFICATION[TAXONOMY_GROUP_UNKNOWN])

    return [
        {
            "probable_cause": cause,
            "evidence": f"{recurrence_count} matching finding(s) observed in taxonomy group '{taxonomy_group}'.",
            "confidence": confidence,
            "alternative_explanations": [alternative],
            "recommended_verification": verification,
        }
        for cause in candidates
    ]
