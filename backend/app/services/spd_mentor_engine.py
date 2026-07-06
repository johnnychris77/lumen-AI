"""v1.4 — SPD Mentor Engine.

Turns an inspection analysis into an active SPD educator: structured corrective
action chains per finding, anatomy-aware coaching tied to the instrument's
actual high-retention zones, confidence coaching when image quality or
coverage is incomplete, a concise clinical decision summary, and (in Training
Mode) expanded explanations of every finding, the anatomy involved, the
recommendation, and SPD terminology.

This module composes existing Phase 13/14/15 infrastructure
(clinical_mentor.py, instrument_anatomy.py, instrument_zones.py,
inspection_coverage.py) rather than duplicating it — it never replaces
supervisor judgment, and every statement is derived from the actual analysis
result, not fabricated.
"""
from __future__ import annotations

from app.services.clinical_mentor import (
    FINDING_EDUCATION,
    NEXT_ACTIONS,
    STANDARDS_GUIDANCE,
    learning_content,
)
from app.services.baseline_comparison_scoring_service import KPI_LABELS

MENTOR_DISCLAIMER = (
    "This guidance is AI-generated educational support. It does not replace "
    "supervisor judgment or the manufacturer's Instructions For Use (IFU)."
)

IFU_REFERENCE_NOTE = "AAMI ST79 (institution-specific implementation may vary)."

# ── Corrective action chains (Deliverable 2) ─────────────────────────────────
# Ordered, structured step-by-step recommendations per finding type. Derived
# from accepted SPD practice — supervisor verification is the final step for
# every contamination finding; structural findings escalate to remove-from-
# service rather than reprocessing.
CORRECTIVE_ACTION_CHAINS: dict[str, list[str]] = {
    "blood": [
        "Reclean the instrument.",
        "Brush serrations manually.",
        "Flush the lumen.",
        "Repeat visual inspection.",
        "Supervisor verification.",
    ],
    "tissue": [
        "Reclean the instrument.",
        "Brush affected surfaces manually.",
        "Flush any lumens or channels.",
        "Repeat visual inspection.",
        "Supervisor verification.",
    ],
    "other_organic_residue": [
        "Reclean the instrument.",
        "Consider extended enzymatic contact time or a biofilm-directed protocol.",
        "Repeat visual inspection.",
        "Supervisor verification.",
    ],
    "bone": [
        "Reclean the instrument.",
        "Flush and brush cannulated channels with the correct-diameter brush.",
        "Repeat visual inspection.",
        "Supervisor verification.",
    ],
    "debris": [
        "Reclean the instrument.",
        "Identify and remove the particulate source.",
        "Repeat visual inspection.",
        "Supervisor verification.",
    ],
    "rust": [
        "Remove from service.",
        "Evaluate for repair.",
        "Inspect surrounding anatomy.",
        "Document corrosion.",
    ],
    "corrosion": [
        "Remove from service.",
        "Evaluate for repair.",
        "Inspect surrounding anatomy.",
        "Document corrosion.",
    ],
    "pitting": [
        "Remove from service for evaluation if extensive.",
        "Inspect surrounding anatomy.",
        "Document the finding.",
        "Monitor at future inspections if minor.",
    ],
    "crack": [
        "Remove from service immediately.",
        "Notify supervisor.",
        "Repair evaluation.",
    ],
    "insulation_damage": [
        "Remove from service immediately.",
        "Notify supervisor.",
        "Test insulation integrity.",
        "Repair or replace evaluation.",
    ],
    "missing_component": [
        "Remove from service immediately.",
        "Notify supervisor.",
        "Verify against the tray content list and instrument photo.",
        "Complete assembly or replace.",
    ],
    "wear": [
        "Document and monitor.",
        "Compare against prior inspections.",
        "Escalate to supervisor if progressive.",
    ],
    "discoloration": [
        "Document and monitor.",
        "Investigate if progressive or paired with corrosion.",
    ],
}


def corrective_action_chain(finding_type: str) -> list[str]:
    """Ordered corrective-action steps for a single finding type."""
    return CORRECTIVE_ACTION_CHAINS.get(finding_type, ["Supervisor review recommended."])


def corrective_actions_for_result(result: dict) -> list[dict]:
    """Structured corrective-action recommendation per actionable finding."""
    out = []
    for f in result.get("predicted_findings", []):
        if f["severity_index"] < 1:
            continue
        finding_type = f["type"]
        out.append({
            "finding": KPI_LABELS.get(finding_type, finding_type),
            "steps": corrective_action_chain(finding_type),
        })
    return out


# ── Anatomy-aware coaching (Deliverable 3) ───────────────────────────────────
# Canned coaching phrasing for instrument families with well-known SPD lore.
# Falls back to a generated sentence from the instrument's own anatomy zones
# for families without a specific canned phrase — never fabricated per-family
# detail beyond what instrument_anatomy.py already defines.
_FAMILY_COACHING_PHRASES: dict[str, list[str]] = {
    "kerrison_rongeur": [
        "Kerrison jaw serrations are high-retention anatomy zones.",
        "Open the box lock and actuate the hinge during inspection — soil hides in the pivot.",
    ],
    "rigid_scope": [
        "Rigid scope O-ring regions frequently retain organic material.",
        "Inspect the working channel and seal closely; these are high-retention zones.",
    ],
    "drill_bit": [
        "Drill-bit flutes require careful brushing.",
        "Threaded regions between the flutes are a common site for retained residue.",
    ],
    "needle_holder": [
        "Needle-holder box locks should be opened during inspection.",
        "Jaw inserts and serrations are high-retention anatomy zones.",
    ],
}


def anatomy_coaching(result: dict) -> list[str]:
    """Anatomy-aware coaching sentences for the instrument being inspected."""
    anatomy = result.get("instrument_anatomy") or {}
    family = anatomy.get("family", "default")
    messages = list(_FAMILY_COACHING_PHRASES.get(family, []))

    if not messages:
        category = anatomy.get("category", "instrument")
        for zone in anatomy.get("zones", []):
            if zone.get("retention_risk") == "high" or zone.get("zone_name") in anatomy.get("high_risk_zones", []):
                messages.append(
                    f"{category.capitalize()} {zone['zone_name']} is a high-retention anatomy zone."
                )
    return messages


def _zone_description(zone_name: str) -> str:
    from app.services.instrument_zones import ZONE_INFO

    info = ZONE_INFO.get(zone_name.lower())
    if info and info.get("reason"):
        return info["reason"]
    return f"{zone_name.capitalize()} — inspect closely per the instrument's anatomy profile."


# ── AI confidence coaching (Deliverable 7) ───────────────────────────────────
_LOW_CONFIDENCE_THRESHOLD = 0.7
_LOW_COVERAGE_THRESHOLD = 75


def confidence_coaching(result: dict) -> dict | None:
    """Coaching for the technician when confidence is limited by image
    quality or incomplete inspection coverage. Returns None when confidence
    and coverage are both adequate — nothing to coach."""
    confidence = result.get("confidence")
    coverage = result.get("inspection_coverage") or {}
    coverage_pct = coverage.get("overall_coverage")
    coverage_assessed = coverage.get("assessed", False)

    low_confidence = confidence is not None and confidence < _LOW_CONFIDENCE_THRESHOLD
    low_coverage = coverage_assessed and coverage_pct is not None and coverage_pct < _LOW_COVERAGE_THRESHOLD
    not_assessed = not coverage_assessed

    if not (low_confidence or low_coverage or not_assessed):
        return None

    suggestions: list[str] = []
    if not_assessed or low_coverage:
        suggestions.append("Capture additional images.")
        suggestions.append("Capture missing anatomy zones.")
    if low_confidence:
        suggestions.append("Improve lighting.")
    suggestions.append("Request supervisor review.")

    return {
        "message": (
            "Confidence is limited because image quality and inspection "
            "coverage are incomplete."
        ),
        "suggestions": suggestions,
    }


# ── Clinical decision summary (Deliverable 8, concise form) ──────────────────
def clinical_decision_summary(result: dict, overall: str) -> dict:
    coverage = result.get("inspection_coverage") or {}
    supervisor_review = "Recommended" if overall in {
        "SUPERVISOR REVIEW", "REPROCESS", "REMOVE FROM SERVICE",
    } else "Not required"

    return {
        "instrument": result.get("instrument_type") or "Unknown instrument",
        "inspection_coverage": coverage.get("overall_coverage"),
        "findings": result.get("findings_summary") or "No actionable findings detected.",
        "risk": result.get("risk_level"),
        "recommendation": result.get("recommended_action"),
        "supervisor_review": supervisor_review,
    }


# ── SPD education cards (Deliverable 4) ──────────────────────────────────────
def education_card(finding_type: str) -> dict | None:
    edu = FINDING_EDUCATION.get(finding_type)
    if not edu:
        return None
    return {
        "finding": KPI_LABELS.get(finding_type, finding_type),
        "clinical_significance": edu["clinical_significance"],
        "recommended_practice": edu["spd_response"],
        "reference": IFU_REFERENCE_NOTE,
    }


def education_cards_for_result(result: dict) -> list[dict]:
    out = []
    for f in result.get("predicted_findings", []):
        if f["severity_index"] < 1:
            continue
        card = education_card(f["type"])
        if card:
            out.append(card)
    return out


# ── Training Mode (Deliverable 6) ────────────────────────────────────────────
TERMINOLOGY: dict[str, str] = {
    "baseline match": "How closely the instrument's current condition matches its approved reference (baseline) image or record.",
    "retention zone": "An anatomy region — such as a serration, lumen, box lock, or hinge — where soil is mechanically difficult to remove and easy to miss visually.",
    "IFU": "Instructions For Use — the manufacturer's official reprocessing and inspection instructions for a specific device.",
    "disposition": "The recommended next step for an instrument after inspection (e.g. PASS, REPROCESS, REMOVE FROM SERVICE).",
    "coverage": "The percentage of an instrument's required high-risk anatomy zones that were actually photographed/inspected.",
    "supervisor review": "A second, qualified review of an instrument before it is released, required whenever cleanliness or condition is uncertain.",
}


def training_mode_explanations(result: dict, overall: str) -> dict:
    """Expanded, always-explain content for onboarding/competency building:
    every finding, the anatomy involved, the recommendation, and terminology."""
    anatomy = result.get("instrument_anatomy") or {}
    return {
        "every_finding": learning_content(result),
        "anatomy_explained": [
            {"zone": zone_name, "explanation": _zone_description(zone_name)}
            for zone_name in anatomy.get("zone_names", [])
        ],
        "recommendation_explained": {
            "disposition": overall,
            "next_actions": NEXT_ACTIONS.get(overall, []),
            "standards_guidance": STANDARDS_GUIDANCE.get(overall, ""),
        },
        "terminology": [
            {"term": term, "definition": definition}
            for term, definition in TERMINOLOGY.items()
        ],
    }


# ── Assembly ──────────────────────────────────────────────────────────────
def build_spd_mentor(result: dict, overall: str, *, training_mode: bool = False) -> dict:
    """Assemble the full v1.4 SPD Mentor payload."""
    payload = {
        "disclaimer": MENTOR_DISCLAIMER,
        "corrective_actions": corrective_actions_for_result(result),
        "anatomy_coaching": anatomy_coaching(result),
        "confidence_coaching": confidence_coaching(result),
        "clinical_decision_summary": clinical_decision_summary(result, overall),
        "education_cards": education_cards_for_result(result),
        "training_mode": training_mode,
    }
    if training_mode:
        payload["expanded_explanations"] = training_mode_explanations(result, overall)
    return payload
