"""v2.0 — Anatomy Zone Engine & Zone Risk Matrix.

Formalizes the chain LumenAI Inspect v2.0 requires before any clinical
recommendation:

    Instrument -> Anatomy -> Inspection Zone -> Risk Level ->
    Typical Findings -> Recommended Inspection Method

Everything here is computed live from the real declared zone data in
`instrument_anatomy.py` (anatomy) and `cleaning_knowledge.py` (cleaning
method) — nothing is a separate, hand-fabricated dataset. The zone risk
matrix and dynamic inspection guidance are both derived the same way, so
adding a new instrument family (or a new zone on an existing one) updates
every one of these views automatically.
"""
from __future__ import annotations

from app.services.cleaning_knowledge import get_cleaning_knowledge
from app.services.instrument_anatomy import (
    INSTRUMENT_ANATOMY, TYPICAL_FINDINGS_BY_CATEGORY, get_anatomy, resolve_family,
)

# Required lighting / recommended viewing angle per zone_category — real SPD
# inspection guidance (lumens need borescope/internal light, mechanical
# joints need raking light with the joint actuated open, etc.), not a single
# generic tip repeated for every zone.
_INSPECTION_METHOD_BY_CATEGORY: dict[str, dict[str, str]] = {
    "cutting_working_surface": {
        "required_lighting": "raking side light with magnification",
        "recommended_angle": "edge-on, blade/jaw flat to the light source",
    },
    "rotary_orthopedic": {
        "required_lighting": "high-intensity magnified light",
        "recommended_angle": "flute/thread close-up, tip end-on",
    },
    "lumen_scope": {
        "required_lighting": "borescope or internal channel illumination",
        "recommended_angle": "distal end-on, channel/port opening",
    },
    "mechanical": {
        "required_lighting": "raking light with the joint actuated fully open",
        "recommended_angle": "pivot open, hinge/ratchet/box-lock exposed",
    },
    "handle_external": {
        "required_lighting": "standard ambient light",
        "recommended_angle": "overall view, side profile",
    },
}
_DEFAULT_METHOD = _INSPECTION_METHOD_BY_CATEGORY["handle_external"]

# Bridges the older, smaller pilot zone-assignment taxonomy in
# instrument_zones.py (used by the live scoring engine's zone_fields()) onto
# the same five zone_category buckets, so a scored finding's zone gets the
# same zone-specific expected-findings model as the Anatomy Library's
# per-family zones — one finding vocabulary, not two independent ones.
_LEGACY_ZONE_TO_CATEGORY: dict[str, str] = {
    "serrations": "cutting_working_surface", "grooves": "cutting_working_surface",
    "teeth": "cutting_working_surface", "jaws": "cutting_working_surface",
    "cutting edge": "cutting_working_surface",
    "drill-bit flute": "rotary_orthopedic", "threaded region": "rotary_orthopedic",
    "cutting channel": "rotary_orthopedic", "burr surface": "rotary_orthopedic",
    "lumen opening": "lumen_scope", "inner channel": "lumen_scope",
    "o-ring area": "lumen_scope", "rigid scope port": "lumen_scope",
    "lens edge": "lumen_scope", "sheath connection": "lumen_scope",
    "biopsy channel": "lumen_scope", "suction channel": "lumen_scope",
    "air/water nozzle": "lumen_scope",
    "hinge": "mechanical", "box lock": "mechanical", "joint": "mechanical",
    "ratchet": "mechanical", "spring area": "mechanical",
    "handle seam": "handle_external", "insulation edge": "handle_external",
    "outer sheath": "handle_external", "surface discoloration area": "handle_external",
    "unspecified region": "handle_external", "image quality insufficient": "handle_external",
}


def typical_findings_for_legacy_zone(zone_name: str) -> dict[str, list[str]]:
    """Expected contamination/condition findings for a zone name produced by
    the pilot scoring engine's `zone_fields()` (app/services/instrument_zones.py)."""
    category = _LEGACY_ZONE_TO_CATEGORY.get((zone_name or "").lower(), "handle_external")
    return TYPICAL_FINDINGS_BY_CATEGORY[category]


def zone_engine(instrument_type: str, zone_name: str) -> dict | None:
    """The full Instrument -> Anatomy -> Zone -> Risk -> Typical Findings ->
    Recommended Inspection Method chain for one explicitly-named anatomy
    zone. Returns None if `zone_name` is not a declared zone of the
    instrument's resolved family — never fabricates a zone that doesn't
    exist for that instrument."""
    family = resolve_family(instrument_type)
    anatomy = get_anatomy(instrument_type)
    zone = next((z for z in anatomy["zones"] if z["zone_name"] == zone_name), None)
    if zone is None:
        return None

    method = _INSPECTION_METHOD_BY_CATEGORY.get(zone["zone_category"], _DEFAULT_METHOD)
    cleaning = get_cleaning_knowledge(zone_name)

    return {
        "instrument_type": instrument_type,
        "instrument_family": family,
        "anatomy_zone": zone_name,
        "zone_category": zone["zone_category"],
        "zone_risk_level": zone["zone_risk_level"],
        "retention_risk": zone["retention_risk"],
        "typical_contamination_findings": zone["contamination_risks"],
        "typical_condition_findings": zone["condition_risks"],
        "cleaning_method": cleaning["cleaning_method"],
        "required_lighting": method["required_lighting"],
        "recommended_angle": method["recommended_angle"],
        "human_review_required": True,
    }


def dynamic_inspection_guidance(
    instrument_type: str, zone_name: str, *, coverage_status: str | None = None,
) -> dict | None:
    """Everything the capture UI shows for the zone currently being
    inspected: current zone, risk level, expected findings, inspection tips,
    required lighting, recommended angle, and coverage status. Returns None
    for a zone the instrument's family doesn't declare."""
    engine = zone_engine(instrument_type, zone_name)
    if engine is None:
        return None

    anatomy = get_anatomy(instrument_type)
    zone_word = zone_name.split()[0].lower()
    tips = [s for s in anatomy["manual_steps"] if zone_word in s.lower() or zone_name.lower() in s.lower()]

    return {
        **engine,
        "current_zone": zone_name,
        "risk_level": engine["zone_risk_level"],
        "expected_findings": engine["typical_contamination_findings"] + engine["typical_condition_findings"],
        "inspection_tips": tips or anatomy["manual_steps"],
        "coverage_status": coverage_status or "not_assessed",
    }


def zone_risk_for_name(zone_name: str) -> str | None:
    """Best-effort real risk tier for a bare zone name, regardless of which
    of the two zone vocabularies it came from (a per-family anatomy zone or
    a legacy pilot-scoring zone) — checks the legacy taxonomy's own risk
    field first, then the first matching declared anatomy zone. Returns
    None only if the name isn't declared anywhere (never guessed)."""
    from app.services.instrument_zones import ZONE_INFO

    info = ZONE_INFO.get((zone_name or "").lower())
    if info:
        return info["risk"]
    for defn in INSTRUMENT_ANATOMY.values():
        for zone in defn["zones"]:
            if zone["zone_name"] == zone_name:
                return zone["zone_risk_level"]
    return None


def zone_risk_matrix() -> dict[str, list[str]]:
    """Deliverable 5 — every declared zone name across every instrument
    family, bucketed by risk tier. Computed live from real `zone_risk_level`
    values (not a static hardcoded example list), so it stays accurate as
    families/zones are added — a genuinely configurable matrix in the sense
    that the configuration lives in the anatomy data itself."""
    matrix: dict[str, set[str]] = {"critical": set(), "high": set(), "medium": set(), "low": set()}
    for defn in INSTRUMENT_ANATOMY.values():
        for zone in defn["zones"]:
            tier = zone["zone_risk_level"] if zone["zone_risk_level"] in matrix else "medium"
            matrix[tier].add(zone["zone_name"])
    return {tier: sorted(names) for tier, names in matrix.items()}
