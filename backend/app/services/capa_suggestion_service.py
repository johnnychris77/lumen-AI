"""v1.5 — CAPA Integration (Deliverable 8).

Suggests Corrective and Preventive Actions from real recurring patterns —
repeated findings in the same anatomy zone, repeated condition findings on an
instrument family, or a cluster of low-confidence/low-coverage inspections.
These are suggestions for a human to review and act on (via
POST /api/quality/capa-suggestions/{id}/create), never auto-created CAPAs —
consistent with the platform-wide rule that AI output never bypasses human
review.

v4.7 — Project Apollo additive detectors (Section 2 of the Apollo brief):
repeat repairs, supervisor overrides, AI confidence decline, inspection
failures, and customer complaints. Each reuses an existing store
(`RepairRequest`, `SupervisorReview`, `sentinel_ai_health_service`,
`Inspection.disposition`, `CustomerComplaint`) rather than adding a new
detection data model — consistent with this file's existing pattern of
composing real recurrence counts, never a fabricated score.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.apollo_quality import CustomerComplaint
from app.models.inspection_finding import InspectionFinding
from app.models.or_connect import RepairRequest
from app.models.supervisor_review import SupervisorReview
from app.services.instrument_anatomy import resolve_family

# A finding-type/zone or finding-type/family repeated at least this many times
# in the lookback window triggers a suggestion.
_REPEAT_THRESHOLD = 3
_LOOKBACK_DAYS = 90

_CONDITION_TYPES = {"rust", "corrosion", "pitting", "crack", "insulation_damage", "missing_component"}

# Apollo detectors reuse the same repeat threshold/lookback window as the
# pre-existing detectors above for consistency.
_FAILURE_DISPOSITIONS = {"REPROCESS", "REMOVE FROM SERVICE"}


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

    # v4.7 Apollo — repeated repairs on the same instrument identity.
    repair_rows = (
        db.query(RepairRequest)
        .filter(RepairRequest.tenant_id == tenant_id, RepairRequest.created_at >= since)
        .all()
    )
    repair_counts: dict[str, int] = defaultdict(int)
    for rr in repair_rows:
        if rr.instrument_identity:
            repair_counts[rr.instrument_identity] += 1
    for instrument_identity, count in repair_counts.items():
        if count >= _REPEAT_THRESHOLD:
            suggestions.append({
                "trigger": f"Repeated repairs on {instrument_identity}",
                "occurrences": count,
                "recommendation": "Evaluate this instrument for retirement or root-cause failure analysis.",
                "suggested_title": f"CAPA: Repeat repairs — {instrument_identity}",
                "corrective_action": f"Perform a root-cause review of recurring repair requests for {instrument_identity}.",
                "preventive_action": "Evaluate instrument for retirement/replacement and monitor repair recurrence.",
            })

    # v4.7 Apollo — repeated supervisor overrides/disagreements by technician.
    review_rows = (
        db.query(SupervisorReview)
        .filter(SupervisorReview.tenant_id == tenant_id, SupervisorReview.created_at >= since)
        .all()
    )
    override_counts: dict[str, int] = defaultdict(int)
    for rv in review_rows:
        if rv.agreement == "disagree" or rv.override_action:
            override_counts[rv.reviewer_name or "unknown"] += 1
    for reviewer_name, count in override_counts.items():
        if count >= _REPEAT_THRESHOLD:
            suggestions.append({
                "trigger": f"Repeated supervisor overrides recorded by {reviewer_name}",
                "occurrences": count,
                "recommendation": "Review AI recommendation quality and technician training for the overridden findings.",
                "suggested_title": f"CAPA: Repeated supervisor overrides — {reviewer_name}",
                "corrective_action": "Review the overridden AI recommendations and underlying inspections for a common cause.",
                "preventive_action": "Track override rate going forward and escalate if recurrence continues.",
            })

    # v4.7 Apollo — AI confidence decline (reuses sentinel_ai_health_service's
    # real drift detection rather than re-deriving it).
    from app.services.sentinel_ai_health_service import _detect_drift

    drift_detected, drift_detail = _detect_drift(db, tenant_id)
    if drift_detected:
        suggestions.append({
            "trigger": "AI confidence/agreement drift detected",
            "occurrences": 1,
            "recommendation": "Investigate the AI health drift signal before it affects clinical decisions.",
            "suggested_title": "CAPA: AI confidence decline",
            "corrective_action": f"Investigate root cause of drift: {drift_detail}",
            "preventive_action": "Re-baseline AI health monitoring after root cause is addressed and monitor recurrence.",
        })

    # v4.7 Apollo — repeated inspection failures (REPROCESS/REMOVE FROM
    # SERVICE disposition) on the same instrument type.
    failure_rows = (
        db.query(models.Inspection)
        .filter(
            models.Inspection.tenant_id == tenant_id,
            models.Inspection.created_at >= since,
            models.Inspection.disposition.in_(_FAILURE_DISPOSITIONS),
        )
        .all()
    )
    failure_counts: dict[str, int] = defaultdict(int)
    for r in failure_rows:
        failure_counts[r.instrument_type or "unknown"] += 1
    for instrument_type, count in failure_counts.items():
        if count >= _REPEAT_THRESHOLD:
            suggestions.append({
                "trigger": f"Repeated inspection failures (reprocess/remove-from-service) on {instrument_type}",
                "occurrences": count,
                "recommendation": "Review manufacturing/cleaning/handling process for this instrument type.",
                "suggested_title": f"CAPA: Repeated inspection failures — {instrument_type}",
                "corrective_action": f"Investigate process contributing to reprocess/remove-from-service dispositions for {instrument_type}.",
                "preventive_action": f"Add {instrument_type} to enhanced monitoring and re-audit after corrective action.",
            })

    # v4.7 Apollo — repeated customer complaints on the same instrument type.
    complaint_rows = (
        db.query(CustomerComplaint)
        .filter(CustomerComplaint.tenant_id == tenant_id, CustomerComplaint.created_at >= since)
        .all()
    )
    complaint_counts: dict[str, int] = defaultdict(int)
    for c in complaint_rows:
        complaint_counts[c.instrument_type or "unknown"] += 1
    for instrument_type, count in complaint_counts.items():
        if count >= _REPEAT_THRESHOLD:
            suggestions.append({
                "trigger": f"Repeated customer complaints on {instrument_type}",
                "occurrences": count,
                "recommendation": "Review customer complaint detail for a common contributing factor.",
                "suggested_title": f"CAPA: Repeated customer complaints — {instrument_type}",
                "corrective_action": f"Review complaint records and link relevant ones to this CAPA for {instrument_type}.",
                "preventive_action": "Monitor complaint recurrence and close the loop with the reporting source.",
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
