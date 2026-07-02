"""Instrument-zone taxonomy + zone-aware retention logic.

SPD reality: contamination and damage hide in specific instrument zones
(serrations, box locks, lumens, drill-bit flutes, o-ring areas, hinges …).
This module maps an instrument to its likely zones, marks high-retention zones,
and supplies the reason + recommended manual check per zone.

The zone is assigned deterministically from the instrument type — this is the
same placeholder-grade heuristic as the rest of the pilot scoring engine, NOT
pixel-level localization. A future CV release will localize the actual region.
"""
from __future__ import annotations

# ── Zone taxonomy (Deliverable 1) ────────────────────────────────────────────
ZONE_TAXONOMY: dict[str, list[str]] = {
    "cutting_working_surface": ["serrations", "grooves", "teeth", "jaws", "cutting edge"],
    "rotary_orthopedic": ["drill-bit flute", "threaded region", "cutting channel", "burr surface"],
    "lumen_scope": ["lumen opening", "inner channel", "o-ring area", "rigid scope port", "lens edge", "sheath connection"],
    "mechanical": ["hinge", "box lock", "joint", "ratchet", "spring area"],
    "handle_external": ["handle seam", "insulation edge", "outer sheath", "surface discoloration area"],
    "unknown": ["unspecified region", "image quality insufficient"],
}

# Zones where residual soil is hard to remove — escalate contamination here.
HIGH_RETENTION_ZONES: set[str] = {
    "serrations", "grooves", "teeth", "cutting edge",
    "drill-bit flute", "threaded region", "cutting channel", "burr surface",
    "lumen opening", "inner channel", "o-ring area", "rigid scope port",
    "biopsy channel", "suction channel", "air/water nozzle",
    "hinge", "box lock", "joint", "ratchet",
    "insulation edge",
}

# Per-zone reason + recommended manual check + inherent zone risk.
ZONE_INFO: dict[str, dict[str, str]] = {
    "serrations": {
        "risk": "high",
        "reason": "Serrations can retain blood and tissue after manual cleaning.",
        "manual_check": "Inspect and brush the serrated surface; repeat cleaning if residue is confirmed.",
    },
    "grooves": {
        "risk": "high",
        "reason": "Grooves trap organic residue that surface cleaning may miss.",
        "manual_check": "Brush the grooves under magnification and re-inspect.",
    },
    "box lock": {
        "risk": "high",
        "reason": "Box locks are enclosed pivot points where soil commonly persists.",
        "manual_check": "Open the box lock, brush the pivot, and re-inspect.",
    },
    "hinge": {
        "risk": "high",
        "reason": "Hinges are protected pivot areas prone to retained soil.",
        "manual_check": "Actuate and brush the hinge; verify it is clean and moves freely.",
    },
    "drill-bit flute": {
        "risk": "high",
        "reason": "Flutes and threaded regions of drill bits are high-retention zones.",
        "manual_check": "Brush the flutes/threads; confirm no residue in the channels.",
    },
    "threaded region": {
        "risk": "high",
        "reason": "Threaded regions retain residue between the threads.",
        "manual_check": "Brush and flush the threads; re-inspect under magnification.",
    },
    "lumen opening": {
        "risk": "high",
        "reason": "Lumens and inner channels are classic retention points requiring focused inspection.",
        "manual_check": "Flush and brush the lumen; borescope the channel if available.",
    },
    "inner channel": {
        "risk": "high",
        "reason": "Inner channels can hold residue that outer cleaning cannot reach.",
        "manual_check": "Flush and brush the channel; re-inspect the lumen.",
    },
    "biopsy channel": {
        "risk": "high",
        "reason": "Flexible endoscope channels require focused inspection because retained soil may remain inside internal pathways.",
        "manual_check": "Flush and brush the biopsy channel end-to-end; borescope the channel if available.",
    },
    "suction channel": {
        "risk": "high",
        "reason": "Suction channels of flexible endoscopes retain soil deep in the internal pathway, out of reach of surface cleaning.",
        "manual_check": "Flush and brush the suction channel; verify flow and re-inspect.",
    },
    "air/water nozzle": {
        "risk": "high",
        "reason": "Air/water nozzles are narrow ports that trap residue and biofilm.",
        "manual_check": "Flush the air/water channel and clean the nozzle; confirm patency.",
    },
    "o-ring area": {
        "risk": "high",
        "reason": "Residue near the o-ring/port area is a common retention point requiring focused inspection.",
        "manual_check": "Inspect around the o-ring/port; clean and re-seat as indicated.",
    },
    "rigid scope port": {
        "risk": "high",
        "reason": "Scope ports collect residue at connection points.",
        "manual_check": "Clean the port and sheath connection; re-inspect.",
    },
    "ratchet": {
        "risk": "high",
        "reason": "Ratchet teeth trap soil between the engagement surfaces.",
        "manual_check": "Brush the ratchet through its range; re-inspect.",
    },
    "insulation edge": {
        "risk": "high",
        "reason": "Insulation edges can harbor soil and signal insulation wear on electrosurgical items.",
        "manual_check": "Inspect the insulation edge for soil and breaches; test insulation integrity.",
    },
    "cutting edge": {
        "risk": "medium",
        "reason": "Cutting edges accumulate residue along the working surface.",
        "manual_check": "Wipe/brush the cutting edge and re-inspect.",
    },
    "surface discoloration area": {
        "risk": "low",
        "reason": "Open surfaces are lower-retention; cosmetic changes here are usually not clinically significant.",
        "manual_check": "Wipe the surface; monitor for progression at the next inspection.",
    },
    "unspecified region": {
        "risk": "low",
        "reason": "No specific high-retention zone identified for this instrument.",
        "manual_check": "Perform a standard visual re-inspection.",
    },
}

# ── Instrument → zone rules ──────────────────────────────────────────────────
# (keyword substrings, contamination_zone, condition_zone). First match wins.
_INSTRUMENT_ZONE_RULES: list[tuple[tuple[str, ...], str, str]] = [
    (("drill", "reamer", "burr", "bit"), "drill-bit flute", "threaded region"),
    # Flexible endoscopes route contamination to their internal channels — checked
    # before the generic rigid-scope rule so they are not mis-zoned to the o-ring.
    (("flexible", "colonoscope", "gastroscope", "bronchoscope", "duodenoscope",
      "enteroscope", "sigmoidoscope", "choledochoscope"), "biopsy channel", "lens edge"),
    (("scope", "endoscope", "arthroscope", "cystoscope", "laparoscop", "ureteroscope"), "o-ring area", "lens edge"),
    (("cannula", "cannulated", "suction", "trocar", "lumen"), "inner channel", "outer sheath"),
    (("forcep", "clamp", "hemostat", "kocher", "needle_holder", "needle holder", "grasper"), "serrations", "box lock"),
    (("scissor", "shear"), "hinge", "cutting edge"),
    (("rongeur", "kerrison", "punch", "biter"), "box lock", "jaws"),
    (("bipolar", "monopolar", "electro", "cautery", "insulat"), "insulation edge", "insulation edge"),
]
_DEFAULT_CONTAM_ZONE = "unspecified region"
_DEFAULT_CONDITION_ZONE = "surface discoloration area"

# Findings treated as contamination (routed to the retention zone).
_CONTAMINATION = {"blood", "tissue", "other_organic_residue", "debris", "bone", "bioburden"}


def resolve_zones(instrument_type: str) -> tuple[str, str]:
    """Return (contamination_zone, condition_zone) for an instrument type."""
    name = (instrument_type or "").lower()
    for keywords, contam, cond in _INSTRUMENT_ZONE_RULES:
        if any(k in name for k in keywords):
            return contam, cond
    return _DEFAULT_CONTAM_ZONE, _DEFAULT_CONDITION_ZONE


def zone_for_finding(instrument_type: str, finding_type: str) -> str:
    """Deterministic zone for a finding on a given instrument."""
    contam_zone, cond_zone = resolve_zones(instrument_type)
    return contam_zone if finding_type in _CONTAMINATION else cond_zone


def _zone_confidence(instrument_type: str, zone: str) -> float:
    """Honest confidence for a *pilot* (non-CV) zone assignment.

    This is NOT vision-derived certainty — it reflects how specifically the
    instrument type resolved to a zone. A recognized instrument mapped to a
    named high-retention zone is more trustworthy than the generic fallback.
    Deliberately capped well below 1.0 because no pixel-level localization
    occurred.
    """
    if zone in (_DEFAULT_CONTAM_ZONE, _DEFAULT_CONDITION_ZONE):
        return 0.35  # generic fallback — instrument did not map to a named zone
    name = (instrument_type or "").lower()
    matched = any(
        any(k in name for k in keywords) for keywords, _c, _cond in _INSTRUMENT_ZONE_RULES
    )
    return 0.7 if matched else 0.5


def zone_fields(instrument_type: str, finding_type: str) -> dict:
    """Pilot zone-assignment output for a finding: probable instrument_zone,
    zone_confidence, zone_reason, recommended_manual_check + the zone's risk.

    ``assignment_method`` is fixed to ``pilot_zone_assignment`` — this is
    deterministic pilot logic from the instrument type/tagged views, NOT computer
    vision segmentation.
    """
    zone = zone_for_finding(instrument_type, finding_type)
    info = ZONE_INFO.get(zone, ZONE_INFO["unspecified region"])
    return {
        "instrument_zone": zone,
        "zone_risk": info["risk"],
        "zone_reason": info["reason"],
        "recommended_manual_check": info["manual_check"],
        "zone_confidence": _zone_confidence(instrument_type, zone),
        "assignment_method": "pilot_zone_assignment",
    }


def is_high_retention(zone: str) -> bool:
    return zone in HIGH_RETENTION_ZONES
