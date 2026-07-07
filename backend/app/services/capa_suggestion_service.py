"""v1.5 — CAPA Integration (Deliverable 8).

Suggests Corrective and Preventive Actions from real recurring patterns —
repeated findings in the same anatomy zone, repeated condition findings on an
instrument family, or a cluster of low-confidence/low-coverage inspections.
These are suggestions for a human to review and act on (via
POST /api/quality/capa-suggestions/{id}/create), never auto-created CAPAs —
consistent with the platform-wide rule that AI output never bypasses human
review.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.inspection_finding import InspectionFinding
from app.services.instrument_anatomy import resolve_family

# A finding-type/zone or finding-type/family repeated at least this many times
# in the lookback window triggers a suggestion.
_REPEAT_THRESHOLD = 3
_LOOKBACK_DAYS = 90

_CONDITION_TYPES = {"rust", "corrosion", "pitting", "crack", "insulation_damage", "missing_component"}


def generate_capa_suggestions(db: Session, tenant_id: str) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)
    findings = (
        db.query(InspectionFinding)
        .filter(InspectionFinding.tenant_id == tenant_id, InspectionFinding.created_at >= since)
        .all()
    )

    suggestions: list[dict] = []

    # Repeated contamination in the same zone -> cleaning competency review.
    zone_counts: dict[tuple[str, str], int] = defaultdict(int)
    for f in findings:
        if f.finding_type not in _CONDITION_TYPES and f.zone:
            zone_counts[(f.finding_type, f.zone)] += 1
    for (finding_type, zone), count in zone_counts.items():
        if count >= _REPEAT_THRESHOLD:
            suggestions.append({
                "trigger": f"Repeated {finding_type} in {zone}",
                "occurrences": count,
                "recommendation": "Review manual cleaning competency for this anatomy zone.",
                "suggested_title": f"CAPA: Repeated {finding_type} in {zone}",
                "corrective_action": f"Retrain on manual brushing/flushing technique for {zone}.",
                "preventive_action": f"Add {zone} to the guided-capture required-zone checklist and monitor recurrence.",
            })

    # Repeated condition findings on an instrument family -> storage/maintenance.
    family_counts: dict[tuple[str, str], int] = defaultdict(int)
    for f in findings:
        if f.finding_type in _CONDITION_TYPES:
            family_counts[(f.finding_type, resolve_family(f.instrument_type))] += 1
    for (finding_type, family), count in family_counts.items():
        if count >= _REPEAT_THRESHOLD:
            suggestions.append({
                "trigger": f"Repeated {finding_type} on {family}",
                "occurrences": count,
                "recommendation": "Evaluate storage and maintenance practices for this instrument family.",
                "suggested_title": f"CAPA: Repeated {finding_type} on {family}",
                "corrective_action": f"Inspect storage conditions and maintenance schedule for {family}.",
                "preventive_action": f"Add {family} to the preventive-maintenance rotation and monitor recurrence.",
            })

    # Repeated poor image quality (low confidence, incomplete coverage) by technician.
    insp_rows = (
        db.query(models.Inspection)
        .filter(
            models.Inspection.tenant_id == tenant_id,
            models.Inspection.created_at >= since,
            models.Inspection.has_image.is_(True),
            models.Inspection.technician.isnot(None),
        )
        .all()
    )
    by_technician: dict[str, int] = defaultdict(int)
    for r in insp_rows:
        low_confidence = r.confidence is not None and r.confidence < 0.7
        low_coverage = r.coverage_pct is not None and r.coverage_pct < 75
        if low_confidence or low_coverage:
            by_technician[r.technician] += 1
    for technician, count in by_technician.items():
        if count >= _REPEAT_THRESHOLD:
            suggestions.append({
                "trigger": f"Repeated low-confidence/low-coverage inspections by {technician}",
                "occurrences": count,
                "recommendation": "Technician image capture refresher.",
                "suggested_title": f"CAPA: Image capture quality — {technician}",
                "corrective_action": f"Schedule an image-capture refresher for {technician}.",
                "preventive_action": "Add lighting/angle guidance to the guided-capture workflow.",
            })

    suggestions.sort(key=lambda s: s["occurrences"], reverse=True)
    return suggestions


def create_capa_from_suggestion(suggestion: dict, *, owner: str = "Quality / Operations") -> dict:
    """Materialize a chosen suggestion into a real CAPA via the existing
    capa_service — this is the human-review step, never automatic."""
    from app.services.capa_service import create_capa

    return create_capa(
        title=suggestion["suggested_title"],
        source="quality_intelligence_suggestion",
        description=suggestion["trigger"],
        risk_level="medium",
        owner=owner,
        corrective_action=suggestion["corrective_action"],
        preventive_action=suggestion["preventive_action"],
        status="open",
    )
