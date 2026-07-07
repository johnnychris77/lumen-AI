"""v1.2 — Guided Capture & Coverage Workflow.

Walks a technician through the required images before AI analysis: which
zone to capture next, the recommended camera angle/lighting/focus, and a
plain-language instruction sentence. Built entirely on top of the existing
anatomy library (app/services/instrument_anatomy.py) and Coverage Engine
(app/services/inspection_coverage.py) — no new zone-assignment logic.

Per-zone guidance below is instructional UI copy (camera technique), not a
clinical claim, so it's authored directly rather than derived from data. Zones
without a specific entry fall back to generic, honest guidance keyed off the
zone's category (from instrument_anatomy.py) rather than fabricating
zone-specific detail that was never defined.
"""
from __future__ import annotations

from app.services.inspection_coverage import compute_coverage, missing_image_guidance
from app.services.instrument_anatomy import get_anatomy

# ── Per-zone capture guidance ────────────────────────────────────────────────
# angle: recommended camera position. lighting: lighting setup. focus: what to
# focus on / macro vs. standard. instruction: the plain-language prompt shown
# to the technician (matches the v1.2 spec's example wording where given).
ZONE_CAPTURE_GUIDANCE: dict[str, dict[str, str]] = {
    "o-ring area": {
        "angle": "Close-up, perpendicular to the o-ring/port face",
        "lighting": "Even, diffuse lighting to avoid glare on the seal",
        "focus": "Macro focus on the o-ring seam",
        "instruction": "Capture close-up of o-ring area.",
    },
    "drill-bit flute": {
        "angle": "Side profile, full flute length in frame",
        "lighting": "Direct lighting along the flute to reveal residue in the spirals",
        "focus": "Macro focus, flute threads sharp",
        "instruction": "Capture drill-bit flute under direct lighting.",
    },
    "flutes": {
        "angle": "Side profile, full flute length in frame",
        "lighting": "Direct lighting along the flute to reveal residue in the spirals",
        "focus": "Macro focus, flute threads sharp",
        "instruction": "Capture drill-bit flute under direct lighting.",
    },
    "box lock": {
        "angle": "Jaw open, box lock fully visible",
        "lighting": "Direct lighting into the opened pivot",
        "focus": "Macro focus on the pivot interior",
        "instruction": "Capture box lock with jaw open.",
    },
    "serrations": {
        "angle": "Macro, serration teeth filling the frame",
        "lighting": "Raking side light to show residue between teeth",
        "focus": "Macro focus, teeth in sharp detail",
        "instruction": "Capture serrations at macro distance.",
    },
    "jaw": {
        "angle": "Jaw open, full jaw face visible",
        "lighting": "Direct lighting into the jaw",
        "focus": "Macro focus on the jaw serrations",
        "instruction": "Capture jaw with jaw open, serrations facing the camera.",
    },
    "hinge": {
        "angle": "Side profile with the hinge actuated open",
        "lighting": "Direct lighting into the hinge gap",
        "focus": "Macro focus on the pivot",
        "instruction": "Capture hinge actuated open, pivot fully visible.",
    },
    "distal tip": {
        "angle": "End-on, straight down the shaft",
        "lighting": "Even lighting to avoid tip glare",
        "focus": "Sharp focus on the tip edge",
        "instruction": "Capture distal tip end-on.",
    },
    "distal end": {
        "angle": "End-on, straight down the insertion tube",
        "lighting": "Even lighting to avoid lens glare",
        "focus": "Sharp focus on the distal face",
        "instruction": "Capture distal end end-on.",
    },
    "lens edge": {
        "angle": "Close-up, lens face perpendicular to camera",
        "lighting": "Diffuse lighting to reveal scratches without glare",
        "focus": "Macro focus on the lens rim",
        "instruction": "Capture lens edge in close-up under diffuse light.",
    },
    "threaded region": {
        "angle": "Side profile, threads in full length",
        "lighting": "Direct raking light across the threads",
        "focus": "Macro focus on thread crests",
        "instruction": "Capture threaded region under direct lighting.",
    },
    "biopsy channel": {
        "angle": "Channel opening, straight-on",
        "lighting": "Direct light into the channel opening",
        "focus": "Macro focus at the channel mouth",
        "instruction": "Capture biopsy channel opening straight-on.",
    },
    "suction channel": {
        "angle": "Channel opening, straight-on",
        "lighting": "Direct light into the channel opening",
        "focus": "Macro focus at the channel mouth",
        "instruction": "Capture suction channel opening straight-on.",
    },
    "ratchet": {
        "angle": "Ratchet engaged, teeth visible",
        "lighting": "Raking side light to reveal residue between teeth",
        "focus": "Macro focus on the ratchet teeth",
        "instruction": "Capture ratchet with teeth engaged and visible.",
    },
    "insulation edge": {
        "angle": "Full insulation length, side profile",
        "lighting": "Even lighting along the shaft",
        "focus": "Sharp focus on the insulation-to-metal transition",
        "instruction": "Capture insulation edge along the full shaft length.",
    },
    "working channel": {
        "angle": "Channel opening, straight-on",
        "lighting": "Direct light into the channel opening",
        "focus": "Macro focus at the channel mouth",
        "instruction": "Capture working channel opening straight-on.",
    },
    "sheath connection": {
        "angle": "Close-up on the connection point",
        "lighting": "Direct lighting on the connector",
        "focus": "Macro focus on the connection seam",
        "instruction": "Capture sheath connection close-up.",
    },
}

# Fallback guidance by zone category (from instrument_anatomy.py's zone_category).
_CATEGORY_FALLBACK: dict[str, dict[str, str]] = {
    "cutting_working_surface": {
        "angle": "Macro, working surface filling the frame",
        "lighting": "Raking side light to reveal surface residue",
        "focus": "Macro focus on the working edge",
    },
    "rotary_orthopedic": {
        "angle": "Side profile, full length in frame",
        "lighting": "Direct lighting along the length",
        "focus": "Macro focus, cutting surface sharp",
    },
    "lumen_scope": {
        "angle": "End-on or opening straight-on",
        "lighting": "Direct light into the opening",
        "focus": "Macro focus at the opening",
    },
    "mechanical": {
        "angle": "Mechanism actuated/open, pivot visible",
        "lighting": "Direct lighting into the mechanism",
        "focus": "Macro focus on the pivot/joint",
    },
    "handle_external": {
        "angle": "Side profile, full length in frame",
        "lighting": "Even, diffuse lighting",
        "focus": "Standard focus, surface detail visible",
    },
}
_DEFAULT_FALLBACK = {
    "angle": "Overall view, then a close-up",
    "lighting": "Even, diffuse lighting",
    "focus": "Standard focus",
}


def _zone_category(instrument_type: str, zone_name: str) -> str:
    anatomy = get_anatomy(instrument_type)
    for z in anatomy["zones"]:
        if z["zone_name"].lower() == zone_name.lower():
            return z["zone_category"]
    return ""


def zone_capture_guidance(instrument_type: str, zone_name: str) -> dict[str, str]:
    """Camera angle, lighting, focus, and a plain-language instruction for
    capturing one zone. Falls back to category-level generic guidance, then a
    fully generic default — never a fabricated zone-specific claim."""
    key = (zone_name or "").strip().lower()
    if key in ZONE_CAPTURE_GUIDANCE:
        return {**ZONE_CAPTURE_GUIDANCE[key]}

    category = _zone_category(instrument_type, key)
    fallback = _CATEGORY_FALLBACK.get(category, _DEFAULT_FALLBACK)
    return {
        **fallback,
        "instruction": f"Capture close-up of {zone_name}.",
    }


def technician_guidance_sentence(instrument_type: str, zone_name: str) -> str:
    return zone_capture_guidance(instrument_type, zone_name)["instruction"]


def capture_checklist(instrument_type: str, captured_zones: list[str] | None) -> dict:
    """Required / optional / captured / missing / high-risk zones."""
    anatomy = get_anatomy(instrument_type)
    required = anatomy["required_images"]
    all_zones = anatomy["zone_names"]
    optional = [z for z in all_zones if z not in required]
    captured_norm = {z.strip().lower() for z in (captured_zones or [])}

    captured = [z for z in all_zones if z.lower() in captured_norm]
    missing = [z for z in required if z.lower() not in captured_norm]
    high_risk = [
        z for z in all_zones
        if z in anatomy["high_risk_zones"]
    ]

    return {
        "required_zones": required,
        "optional_zones": optional,
        "captured_zones": captured,
        "missing_zones": missing,
        "high_risk_zones": high_risk,
    }


def _next_zone_to_capture(instrument_type: str, checklist: dict) -> str | None:
    """Prioritize missing required zones, high-risk first."""
    missing = checklist["missing_zones"]
    if not missing:
        return None
    high_risk_set = set(checklist["high_risk_zones"])
    ordered = sorted(missing, key=lambda z: z not in high_risk_set)
    return ordered[0]


def guided_capture_panel(instrument_type: str, captured_zones: list[str] | None) -> dict:
    """Architecture step — the Guided Capture Panel payload: instrument
    family, checklist, current zone to capture, and per-zone camera guidance."""
    anatomy = get_anatomy(instrument_type)
    checklist = capture_checklist(instrument_type, captured_zones)
    current_zone = _next_zone_to_capture(instrument_type, checklist)

    guidance = zone_capture_guidance(instrument_type, current_zone) if current_zone else None

    return {
        "instrument_family": anatomy["family"],
        "instrument_category": anatomy["category"],
        **checklist,
        "current_zone": current_zone,
        "recommended_camera_angle": guidance["angle"] if guidance else None,
        "lighting_tips": guidance["lighting"] if guidance else None,
        "focus_tips": guidance["focus"] if guidance else None,
        "example_placeholder_guidance": guidance["instruction"] if guidance else (
            "All required zones captured — no further images needed for coverage."
        ),
        "all_required_captured": current_zone is None,
    }


def coverage_readiness(
    instrument_type: str,
    captured_zones: list[str] | None,
    require_full_coverage: bool = False,
    override_applied: bool = False,
) -> dict:
    """Section 3/5 — coverage score + readiness-for-AI-analysis gate.

    gate_status:
      - "ready": coverage is complete/acceptable, or org policy doesn't
        require full coverage, or a supervisor override was already applied.
      - "draft": coverage is incomplete/insufficient and org policy doesn't
        require full coverage — the technician may still save/proceed.
      - "blocked_pending_override": org policy requires full coverage, the
        coverage is incomplete/insufficient, and no override has been applied.
    """
    coverage = compute_coverage(instrument_type, captured_zones)
    guidance = missing_image_guidance(instrument_type, captured_zones)
    missing_high_risk = [
        z for z in coverage["missing"]
        if z in get_anatomy(instrument_type)["high_risk_zones"]
    ]

    coverage_sufficient = coverage["quality"] in ("complete", "acceptable")

    if coverage_sufficient or not require_full_coverage or override_applied:
        gate_status = "ready"
    else:
        gate_status = "blocked_pending_override"

    return {
        "coverage_score": coverage["overall_coverage"],
        "coverage_status": coverage["quality"],
        "missing_zones": coverage["missing"],
        "missing_high_risk_zones": missing_high_risk,
        "missing_image_guidance": guidance,
        "ready_for_ai_analysis": gate_status == "ready",
        "gate_status": gate_status,
        "require_full_coverage": require_full_coverage,
    }
