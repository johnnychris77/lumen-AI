"""Phase 15 — Inspection Coverage Engine, missing-image guidance, risk maps.

Given the anatomy of an instrument and the zones the technician actually
captured/inspected, compute a coverage score, quality band, missing required
zones, still-needed image guidance, and a per-zone risk map.

`inspected_zones` are technician-tagged/selected zones (a checklist) — not
CV-detected (that is a future release). The engine is deterministic and honest.
"""
from __future__ import annotations

import json

from app.services.instrument_anatomy import get_anatomy, resolve_family


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


def coverage_dashboard_summary(db, tenant_id: str, recent_limit: int = 20) -> dict:
    """Enterprise Coverage Dashboard — real aggregate coverage stats computed
    from stored inspections (`inspected_zones_json`), never fabricated.

    Inspections where zones were never tagged are excluded from the average
    and status breakdown (they were "not assessed", not zero coverage) but are
    counted separately so the dashboard is honest about assessment gaps.
    """
    from app.db import models

    rows = (
        db.query(models.Inspection)
        .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.has_image.is_(True))
        .order_by(models.Inspection.created_at.desc(), models.Inspection.id.desc())
        .all()
    )

    assessed: list[dict] = []
    missing_tally: dict[str, int] = {}
    status_breakdown = {"complete": 0, "acceptable": 0, "incomplete": 0, "insufficient": 0}
    coverage_by_family: dict[str, list[int]] = {}
    recent: list[dict] = []

    for row in rows:
        try:
            zones = json.loads(row.inspected_zones_json or "null")
        except (TypeError, ValueError):
            zones = None

        cov = compute_coverage(row.instrument_type, zones)
        if len(recent) < recent_limit:
            recent.append({
                "inspection_id": row.id,
                "instrument_type": row.instrument_type,
                "coverage_score": cov["overall_coverage"],
                "coverage_status": cov["quality"],
                "missing": cov["missing"],
                "created_at": row.created_at.isoformat() if row.created_at else None,
            })

        if not cov["assessed"]:
            continue

        assessed.append(cov)
        status_breakdown[cov["quality"]] = status_breakdown.get(cov["quality"], 0) + 1
        for z in cov["missing"]:
            missing_tally[z] = missing_tally.get(z, 0) + 1
        family = resolve_family(row.instrument_type)
        coverage_by_family.setdefault(family, []).append(cov["overall_coverage"])

    average_coverage = (
        round(sum(c["overall_coverage"] for c in assessed) / len(assessed))
        if assessed else None
    )
    average_coverage_by_family = {
        family: round(sum(scores) / len(scores))
        for family, scores in coverage_by_family.items()
    }
    most_commonly_missing_zones = [
        {"zone": zone, "missed_count": count}
        for zone, count in sorted(missing_tally.items(), key=lambda kv: kv[1], reverse=True)
    ][:10]

    return {
        "total_inspections_with_image": len(rows),
        "assessed_count": len(assessed),
        "not_assessed_count": len(rows) - len(assessed),
        "average_coverage": average_coverage,
        "coverage_status_breakdown": status_breakdown,
        "average_coverage_by_family": average_coverage_by_family,
        "most_commonly_missing_zones": most_commonly_missing_zones,
        "recent_inspections": recent,
        "note": (
            "Computed from real inspected_zones_json data. Inspections where zones "
            "were never tagged are excluded from averages (not assessed, not zero)."
        ),
    }
