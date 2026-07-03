"""Phase 15 — Instrument Anatomy Library.

Extensible, data-driven definitions of instrument anatomy so LumenAI reasons the
way SPD professionals inspect: by anatomy, high-risk zone, retention area, and
required image coverage.

Each instrument definition lists its anatomy zones (with per-zone risk +
retention + typical contamination/condition risks), the high-risk subset, the
images required for a complete inspection, recommended image angles, minimum
image count, and recommended manual inspection steps.

This is structured knowledge, not pixel-level detection — a future CV model that
localizes zones drops into the same schema.
"""
from __future__ import annotations

from app.services.instrument_zones import HIGH_RETENTION_ZONES

# Standard contamination / condition risk vocabularies (per zone).
_CONTAM = ["blood", "bone", "tissue", "organic residue", "debris"]
_COND = ["rust", "corrosion", "pitting", "crack", "discoloration", "insulation damage", "missing component", "wear"]


def _zone(name: str, category: str, risk: str, retention: str,
          contamination: list[str] | None = None,
          condition: list[str] | None = None) -> dict:
    return {
        "zone_name": name,
        "zone_category": category,
        "zone_risk_level": risk,          # low / medium / high / critical
        "retention_risk": retention,      # low / medium / high
        "contamination_risks": contamination if contamination is not None else _CONTAM,
        "condition_risks": condition if condition is not None else _COND,
    }


# ── Instrument anatomy definitions ───────────────────────────────────────────
# Keyed by canonical instrument family. `match` keywords resolve free-text
# instrument_type onto a family. Extend by adding entries — no manufacturer is
# hardcoded.
INSTRUMENT_ANATOMY: dict[str, dict] = {
    # Flexible endoscopes are declared BEFORE rigid scopes so their specific
    # keywords resolve first (a rigid scope's generic "scope"/"endoscope" match
    # would otherwise swallow them).
    "flexible_endoscope": {
        "category": "flexible endoscope",
        "match": [
            "flexible", "flex scope", "colonoscope", "gastroscope", "bronchoscope",
            "duodenoscope", "enteroscope", "sigmoidoscope", "choledochoscope",
            "flexible ureteroscope", "flexible cystoscope",
        ],
        "zones": [
            _zone("distal end", "lumen_scope", "critical", "high"),
            _zone("bending section", "lumen_scope", "high", "high"),
            _zone("insertion tube", "handle_external", "medium", "medium"),
            _zone("suction channel", "lumen_scope", "critical", "high"),
            _zone("biopsy channel", "lumen_scope", "critical", "high"),
            _zone("air/water nozzle", "lumen_scope", "high", "high"),
            _zone("light guide lens", "lumen_scope", "medium", "medium"),
            _zone("control body", "handle_external", "low", "low"),
        ],
        "required_images": ["distal end", "biopsy channel", "suction channel", "bending section", "control body"],
        "recommended_image_angles": ["distal end-on", "channel opening", "bending section", "control body"],
        "min_images": 4,
        "manual_steps": [
            "Flush and brush the biopsy and suction channels; leak-test the endoscope.",
            "Borescope the internal channels if available — retained soil hides inside pathways.",
            "Inspect the distal end, air/water nozzle, and bending section closely.",
        ],
    },
    "rigid_scope": {
        "category": "rigid endoscope",
        "match": ["rigid scope", "scope", "endoscope", "arthroscope", "cystoscope", "laparoscope camera", "hysteroscope", "ureteroscope"],
        "zones": [
            _zone("distal tip", "lumen_scope", "high", "high"),
            _zone("lens edge", "lumen_scope", "medium", "medium"),
            _zone("o-ring area", "lumen_scope", "high", "high"),
            _zone("light post", "lumen_scope", "medium", "medium"),
            _zone("eyepiece", "handle_external", "low", "low"),
            _zone("working channel", "lumen_scope", "critical", "high"),
            _zone("sheath connection", "lumen_scope", "high", "high"),
            _zone("seal", "lumen_scope", "high", "high"),
        ],
        "required_images": ["distal tip", "o-ring area", "light post", "lens edge", "working channel"],
        "recommended_image_angles": ["distal end-on", "side profile", "port-on"],
        "min_images": 3,
        "manual_steps": [
            "Flush and brush the working channel; borescope if available.",
            "Inspect the o-ring/seal for soil and wear.",
            "Check the distal tip and lens edge under magnification.",
        ],
    },
    "drill_bit": {
        "category": "rotary orthopedic",
        "match": ["drill", "bit", "reamer", "burr"],
        "zones": [
            _zone("tip", "rotary_orthopedic", "high", "high"),
            _zone("flutes", "rotary_orthopedic", "critical", "high"),
            _zone("threaded region", "rotary_orthopedic", "high", "high"),
            _zone("cutting edge", "rotary_orthopedic", "high", "medium"),
            _zone("shank", "handle_external", "low", "low"),
            _zone("hub", "mechanical", "medium", "medium"),
        ],
        "required_images": ["flutes", "threaded region", "tip", "hub"],
        "recommended_image_angles": ["flute close-up", "tip end-on", "shank/hub"],
        "min_images": 3,
        "manual_steps": [
            "Brush the flutes and threaded region; confirm no residue between spirals.",
            "Inspect the cutting tip for wear and residue.",
        ],
    },
    "kerrison_rongeur": {
        "category": "orthopedic biter",
        "match": ["kerrison", "rongeur", "punch", "biter"],
        "zones": [
            _zone("jaw", "cutting_working_surface", "high", "high"),
            _zone("serrations", "cutting_working_surface", "high", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("hinge", "mechanical", "high", "high"),
            _zone("spring", "mechanical", "medium", "medium"),
            _zone("ratchet", "mechanical", "high", "high"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        "required_images": ["jaw", "serrations", "box lock", "hinge", "spring", "ratchet"],
        "recommended_image_angles": ["jaw close-up", "box lock", "hinge/spring"],
        "min_images": 3,
        "manual_steps": [
            "Open the box lock and brush the pivot; actuate the hinge.",
            "Brush the jaw serrations and spring channel.",
        ],
    },
    "scissors": {
        "category": "cutting",
        "match": ["scissor", "shear"],
        "zones": [
            _zone("tip", "cutting_working_surface", "medium", "medium"),
            _zone("blade", "cutting_working_surface", "medium", "medium"),
            _zone("cutting edge", "cutting_working_surface", "medium", "medium"),
            _zone("serration", "cutting_working_surface", "high", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        "required_images": ["blade", "cutting edge", "box lock"],
        "recommended_image_angles": ["blade side", "box lock", "tip close-up"],
        "min_images": 2,
        "manual_steps": [
            "Inspect the cutting edge and tip; brush any serrations.",
            "Open and brush the box lock.",
        ],
    },
    "needle_holder": {
        "category": "grasping",
        "match": ["needle holder", "needle_holder", "needle-holder"],
        "zones": [
            _zone("jaw inserts", "cutting_working_surface", "high", "high"),
            _zone("serrations", "cutting_working_surface", "high", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("ratchet", "mechanical", "high", "high"),
            _zone("tungsten carbide inserts", "cutting_working_surface", "medium", "medium"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        "required_images": ["jaw inserts", "serrations", "box lock", "ratchet"],
        "recommended_image_angles": ["jaw close-up", "box lock", "ratchet"],
        "min_images": 2,
        "manual_steps": [
            "Brush the jaw inserts and serrations.",
            "Open the box lock and brush the ratchet teeth.",
        ],
    },
    "laparoscopic": {
        "category": "MIS / laparoscopic",
        "match": ["laparoscop", "grasper", "maryland", "dissector", "bipolar", "monopolar", "trocar", "cannula"],
        "zones": [
            _zone("distal jaws", "cutting_working_surface", "high", "high"),
            _zone("hinge", "mechanical", "high", "high"),
            _zone("insulation edge", "handle_external", "critical", "high"),
            _zone("shaft", "handle_external", "medium", "medium"),
            _zone("handle seam", "handle_external", "high", "high"),
            _zone("rotation knob", "mechanical", "medium", "medium"),
            _zone("lumen/cannulated channel", "lumen_scope", "critical", "high"),
        ],
        "required_images": ["distal jaws", "insulation edge", "shaft", "handle seam", "rotation knob"],
        "recommended_image_angles": ["distal jaws", "insulation length", "handle seam"],
        "min_images": 3,
        "manual_steps": [
            "Flush the lumen/cannulated channel if present.",
            "Inspect the full insulation length for breaches; test integrity.",
            "Brush the distal jaws and handle seam.",
        ],
    },
    "general_forceps": {
        "category": "grasping / clamping",
        "match": ["forcep", "hemostat", "clamp", "kocher", "mosquito", "kelly", "allis", "babcock", "tissue forcep"],
        "zones": [
            _zone("jaws", "cutting_working_surface", "high", "high"),
            _zone("serrations", "cutting_working_surface", "high", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("hinge", "mechanical", "high", "high"),
            _zone("ratchet", "mechanical", "high", "high"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        "required_images": ["jaws", "serrations", "box lock", "hinge"],
        "recommended_image_angles": ["jaw close-up", "box lock", "hinge/ratchet"],
        "min_images": 2,
        "manual_steps": [
            "Open the box lock and brush the pivot; actuate the hinge and ratchet.",
            "Brush the jaw serrations and re-inspect under magnification.",
        ],
    },
    "default": {
        "category": "general instrument",
        "match": [],
        "zones": [
            _zone("working surface", "cutting_working_surface", "medium", "medium"),
            _zone("hinge/joint", "mechanical", "high", "high"),
            _zone("box lock", "mechanical", "high", "high"),
            _zone("handle", "handle_external", "low", "low"),
        ],
        "required_images": ["working surface", "hinge/joint"],
        "recommended_image_angles": ["overall", "working surface", "joint close-up"],
        "min_images": 1,
        "manual_steps": [
            "Inspect the working surface and any hinge/box lock.",
        ],
    },
}


def list_anatomy_families() -> list[dict]:
    """Summary of every declared anatomy family, for the Anatomy Library page.
    Excludes the ``default`` fallback (that is the generic profile, not a family)."""
    return [
        {
            "family": family,
            "category": defn["category"],
            "zone_names": [z["zone_name"] for z in defn["zones"]],
            "required_images": defn["required_images"],
            "min_images": defn["min_images"],
            "high_risk_zones": [
                z["zone_name"] for z in defn["zones"]
                if z["zone_risk_level"] in ("high", "critical") or z["retention_risk"] == "high"
            ],
        }
        for family, defn in INSTRUMENT_ANATOMY.items()
        if family != "default"
    ]


def resolve_family(instrument_type: str) -> str:
    """Resolve free-text instrument_type onto an anatomy family key."""
    name = (instrument_type or "").lower()
    for family, defn in INSTRUMENT_ANATOMY.items():
        if family == "default":
            continue
        if any(k in name for k in defn["match"]):
            return family
    return "default"


def get_anatomy(instrument_type: str) -> dict:
    """Full anatomy definition for an instrument type."""
    family = resolve_family(instrument_type)
    defn = INSTRUMENT_ANATOMY[family]
    zones = defn["zones"]
    return {
        "family": family,
        "category": defn["category"],
        "zones": zones,
        "zone_names": [z["zone_name"] for z in zones],
        "high_risk_zones": [
            z["zone_name"] for z in zones
            if z["zone_risk_level"] in ("high", "critical") or z["retention_risk"] == "high"
            or z["zone_name"] in HIGH_RETENTION_ZONES
        ],
        "required_images": defn["required_images"],
        "recommended_image_angles": defn["recommended_image_angles"],
        "min_images": defn["min_images"],
        "manual_steps": defn["manual_steps"],
    }


def _zone_description(z: dict) -> str:
    """Human-readable, honest one-liner per zone (from the zone's risk profile)."""
    from app.services.instrument_zones import ZONE_INFO

    info = ZONE_INFO.get(z["zone_name"].lower())
    if info and info.get("reason"):
        return info["reason"]
    retention = z["retention_risk"]
    if retention == "high":
        return f"{z['zone_name'].capitalize()} is a high-retention zone where residual soil can persist after cleaning."
    return f"{z['zone_name'].capitalize()} ({z['zone_category'].replace('_', ' ')}); {z['zone_risk_level']} inherent risk."


def anatomy_profile(
    instrument_type: str,
    manufacturer: str | None = None,
    model: str | None = None,
    instrument_name: str | None = None,
) -> dict:
    """Architecture step 2 — the Anatomy Profile Service.

    Given an instrument's type (and optionally name/manufacturer/model), return
    the full anatomy profile the AI pipeline reasons over: family, anatomy zones,
    required zones, high-risk zones, per-zone descriptions, contamination/condition
    risks, recommended image views, and manual-check steps.

    When the instrument cannot be classified the family resolves to ``unknown``
    and a generic high-risk SPD profile is returned with a supervisor-review
    warning — nothing is fabricated as a specific match.
    """
    # Consider every available identity hint when resolving the family.
    hint = " ".join(x for x in (instrument_type, instrument_name, model, manufacturer) if x)
    family = resolve_family(hint or (instrument_type or ""))
    profile_found = family != "default"
    defn = INSTRUMENT_ANATOMY[family]
    zones = defn["zones"]
    base = get_anatomy(hint or (instrument_type or ""))

    return {
        **base,
        # `family` is a real family key when matched, else the honest "unknown".
        "instrument_family": family if profile_found else "unknown",
        "profile_found": profile_found,
        "manufacturer": manufacturer or "",
        "model": model or "",
        "anatomy_zones": base["zone_names"],
        "required_zones": defn["required_images"],
        "recommended_image_views": defn["required_images"],
        "zone_descriptions": {z["zone_name"]: _zone_description(z) for z in zones},
        "contamination_risks": {z["zone_name"]: z["contamination_risks"] for z in zones},
        "condition_risks": {z["zone_name"]: z["condition_risks"] for z in zones},
        "manual_check_steps": defn["manual_steps"],
        "warning": (
            None if profile_found else
            "Instrument anatomy profile not found. Supervisor review recommended."
        ),
    }
