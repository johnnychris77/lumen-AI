"""v1.4 — Educational Knowledge Library.

Structured SPD education articles for the twelve contamination/condition
categories LumenAI recognizes. Each article is built from the same source of
truth already used by the AI Mentor (clinical_mentor.FINDING_EDUCATION) and
the instrument anatomy library (instrument_anatomy.py) — nothing here is
duplicated content, it is reshaped into a browsable reference.
"""
from __future__ import annotations

from app.services.baseline_comparison_scoring_service import KPI_LABELS
from app.services.clinical_mentor import FINDING_EDUCATION
from app.services.instrument_anatomy import INSTRUMENT_ANATOMY
from app.services.spd_mentor_engine import IFU_REFERENCE_NOTE, corrective_action_chain

# The twelve categories the v1.4 spec enumerates, in spec order. Internal keys
# match clinical_mentor.FINDING_EDUCATION / KPI_LABELS.
CATEGORIES: list[str] = [
    "blood", "bone", "tissue", "other_organic_residue", "debris",
    "rust", "corrosion", "crack", "wear", "pitting",
    "missing_component", "insulation_damage",
]

# instrument_anatomy.py's per-zone contamination_risks/condition_risks lists
# are the same default vocabulary on every zone (no per-zone override is ever
# supplied), so they cannot distinguish "typical" locations for one finding
# type from another. Instead, derive typical locations from what the zone data
# *does* differentiate: contamination/organic findings collect in zones the
# codebase already marks as high-retention; structural/condition findings
# concentrate in zones with high/critical inherent risk. Insulation damage is
# tied to the one zone actually named for it.
_CONTAMINATION_FINDINGS = {"blood", "bone", "tissue", "other_organic_residue", "debris"}


def _typical_anatomy_locations(finding_type: str) -> list[str]:
    """Zone names, across all instrument families, that are typical retention/
    risk sites for this finding type — derived from each zone's own risk
    classification in instrument_anatomy.py."""
    zones: set[str] = set()
    if finding_type == "insulation_damage":
        target = {"insulation edge"}
    else:
        target = None

    for defn in INSTRUMENT_ANATOMY.values():
        for zone in defn["zones"]:
            name = zone["zone_name"]
            if target is not None:
                if name in target:
                    zones.add(name)
                continue
            if finding_type in _CONTAMINATION_FINDINGS:
                if zone["retention_risk"] == "high":
                    zones.add(name)
            else:
                if zone["zone_risk_level"] in ("high", "critical"):
                    zones.add(name)
    return sorted(zones)


def get_article(finding_type: str) -> dict | None:
    """Full knowledge-library article for one finding type."""
    edu = FINDING_EDUCATION.get(finding_type)
    if not edu:
        return None
    return {
        "finding": KPI_LABELS.get(finding_type, finding_type),
        "finding_type": finding_type,
        "definition": edu["definition"],
        "clinical_importance": edu["clinical_significance"],
        "typical_anatomy_locations": _typical_anatomy_locations(finding_type),
        "inspection_tips": edu["supervisor_tips"],
        "cleaning_considerations": edu["typical_causes"],
        "corrective_actions": corrective_action_chain(finding_type),
        "reference": IFU_REFERENCE_NOTE,
    }


def list_articles() -> list[dict]:
    """All twelve knowledge-library articles, spec order."""
    return [a for a in (get_article(k) for k in CATEGORIES) if a is not None]
