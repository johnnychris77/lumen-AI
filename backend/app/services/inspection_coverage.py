"""Phase 15 — Inspection Coverage Engine, missing-image guidance, risk maps.

Given the anatomy of an instrument and the zones the technician actually
captured/inspected, compute a coverage score, quality band, missing required
zones, still-needed image guidance, and a per-zone risk map.

`inspected_zones` are technician-tagged/selected zones (a checklist) — not
CV-detected (that is a future release). The engine is deterministic and honest.
"""
from __future__ import annotations

from app.services.instrument_anatomy import get_anatomy


def _norm(z: str) -> str:
    return (z or "").strip().lower()


def _quality(pct: int, missing_required: int) -> str:
    if missing_required == 0 and pct >= 95:
        return "complete"
    if missing_required == 0 or pct >= 80:
        return "acceptable"
    if pct >= 50:
        return "incomplete"
    return "insufficient"


def compute_coverage(instrument_type: str, inspected_zones: list[str] | None) -> dict:
    """Coverage against the instrument's required high-risk zones.

    When ``inspected_zones`` is None the technician did not tag zones, so coverage
    is reported as ``not_assessed`` (rather than an alarming 0%). An explicit
    (possibly empty) list is assessed normally.
    """
    anatomy = get_anatomy(instrument_type)
    required = anatomy["required_images"]
    if inspected_zones is None:
        return {
            "assessed": False,
            "overall_coverage": None,
            "required_zones": required,
            "inspected": [],
            "inspected_required": [],
            "missing": required,
            "quality": "not_assessed",
            "message": "Zones were not tagged for this inspection — coverage not assessed.",
            "min_images": anatomy["min_images"],
        }
    inspected = inspected_zones
    inspected_norm = {_norm(z) for z in inspected}

    inspected_required = [z for z in required if _norm(z) in inspected_norm]
    missing_required = [z for z in required if _norm(z) not in inspected_norm]

    pct = round(100 * len(inspected_required) / len(required)) if required else 100
    quality = _quality(pct, len(missing_required))

    message = None
    if missing_required:
        message = "Inspection incomplete. Upload additional images for required high-risk zones."

    return {
        "assessed": True,
        "overall_coverage": pct,
        "required_zones": required,
        "inspected": [z for z in anatomy["zone_names"] if _norm(z) in inspected_norm],
        "inspected_required": inspected_required,
        "missing": missing_required,
        "quality": quality,
        "message": message,
        "min_images": anatomy["min_images"],
    }


def missing_image_guidance(instrument_type: str, inspected_zones: list[str] | None) -> list[str]:
    """'Still needed before final decision' view list for missing required zones.
    Empty when zones were not tagged (avoid nagging on untagged inspections)."""
    if inspected_zones is None:
        return []
    anatomy = get_anatomy(instrument_type)
    inspected_norm = {_norm(z) for z in inspected_zones}
    guidance = []
    for zone in anatomy["required_images"]:
        if _norm(zone) not in inspected_norm:
            guidance.append(f"Close-up image of {zone}")
    return guidance


def build_risk_map(instrument_type: str, findings_by_zone: dict[str, list[str]] | None,
                   inspected_zones: list[str] | None) -> list[dict]:
    """Per-zone risk map: zone · required? · inspected? · findings? · zone risk ·
    recommended manual check (text/card form; visual overlays are a future CV
    release — nothing fabricated)."""
    from app.services.instrument_zones import ZONE_INFO

    anatomy = get_anatomy(instrument_type)
    required_norm = {_norm(z) for z in anatomy["required_images"]}
    inspected_norm = {_norm(z) for z in (inspected_zones or [])}
    findings_by_zone = findings_by_zone or {}

    rows = []
    for z in anatomy["zones"]:
        name = z["zone_name"]
        info = ZONE_INFO.get(name.lower(), {})
        rows.append({
            "zone": name,
            "zone_category": z["zone_category"],
            "zone_risk": z["zone_risk_level"],
            "retention_risk": z["retention_risk"],
            "required": _norm(name) in required_norm,
            "inspected": _norm(name) in inspected_norm,
            "findings": findings_by_zone.get(name, []),
            "recommended_manual_check": info.get(
                "manual_check", "Inspect this zone and re-clean if residue is confirmed."
            ),
        })
    return rows
