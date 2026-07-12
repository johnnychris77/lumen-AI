"""Project Sage, Section 3: Competency Gap Detection.

Identifies possible competency gaps from real, already-validated patterns --
`SupervisorReview` corrections (the ML ground-truth label store, joined to
`Inspection.technician`), `CompetencyEvent` repeated-error counts, and
`Inspection.coverage_pct`. A single isolated correction never creates a gap
(`_MIN_OCCURRENCES = 2`) -- only a repeated pattern does. Every narrative uses
non-punitive language ("targeted education may be beneficial," "competency
verification is recommended," "additional observation may be appropriate")
and never concludes that an individual is incompetent.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.sage_education import (
    COMPETENCY_ANATOMY_ZONE_LABELING_DOC,
    COMPETENCY_DOMAIN_CLINICAL_DECISION,
    COMPETENCY_IMAGE_CAPTURE,
    COMPETENCY_INSPECTION_COVERAGE,
    COMPETENCY_RIGID_VS_FLEXIBLE_SCOPE,
    SCOPE_INDIVIDUAL,
)
from app.models.supervisor_review import SupervisorReview
from app.services.sage_competency_taxonomy_service import competency_for_finding_type

_MIN_OCCURRENCES = 2
_LOW_COVERAGE_THRESHOLD_PCT = 70
_CONFUSION_PAIRS = [("blood", "rust"), ("rust", "corrosion"), ("rust", "discoloration")]

_NARRATIVE_TEMPLATES = {
    "low": "Additional observation may be appropriate.",
    "moderate": "Targeted education may be beneficial.",
    "high": "Competency verification is recommended.",
}


def _confidence_for_count(count: int) -> str:
    if count >= 5:
        return "high"
    if count >= 3:
        return "moderate"
    return "low"


def _reviews_for_technician(db: Session, tenant_id: str, technician: str, window_days: int) -> list[SupervisorReview]:
    since = datetime.now(timezone.utc) - timedelta(days=window_days)
    inspection_ids = [
        row.id for row in db.query(models.Inspection).filter(
            models.Inspection.tenant_id == tenant_id, models.Inspection.technician == technician,
            models.Inspection.created_at >= since,
        )
    ]
    if not inspection_ids:
        return []
    return (
        db.query(SupervisorReview)
        .filter(SupervisorReview.tenant_id == tenant_id, SupervisorReview.inspection_id.in_(inspection_ids))
        .all()
    )


def _make_gap(*, competency_domain, scope_value, instrument_family="", anatomy_zone="", finding_category="",
              occurrence_count, evidence, recommended_education) -> dict:
    confidence = _confidence_for_count(occurrence_count)
    return {
        "competency_domain": competency_domain,
        "scope_type": SCOPE_INDIVIDUAL,
        "scope_value": scope_value,
        "instrument_family": instrument_family,
        "anatomy_zone": anatomy_zone,
        "finding_category": finding_category,
        "occurrence_count": occurrence_count,
        "confidence": confidence,
        "evidence": evidence,
        "narrative": _NARRATIVE_TEMPLATES[confidence],
        "recommended_education": recommended_education,
    }


def detect_missed_anatomy_zones(db: Session, tenant_id: str, technician: str, window_days: int = 90) -> list[dict]:
    """'repeated missed serration images' / 'missing O-ring images' / drill-bit
    flute omissions -- from real `missing_zone_correct == False` corrections."""
    reviews = _reviews_for_technician(db, tenant_id, technician, window_days)
    by_zone: dict[str, list[SupervisorReview]] = defaultdict(list)
    for r in reviews:
        if r.missing_zone_correct is False and r.corrected_missing_zone:
            by_zone[r.corrected_missing_zone].append(r)

    gaps = []
    for zone, rows in by_zone.items():
        if len(rows) < _MIN_OCCURRENCES:
            continue
        families = sorted({r.instrument_family for r in rows if r.instrument_family})
        gaps.append(_make_gap(
            competency_domain=COMPETENCY_ANATOMY_ZONE_LABELING_DOC,
            scope_value=technician, anatomy_zone=zone,
            instrument_family=families[0] if families else "",
            occurrence_count=len(rows),
            evidence={"supervisor_review_ids": [r.id for r in rows], "corrected_missing_zone": zone},
            recommended_education=f"Provide focused review of {zone} inspection and image-capture practice.",
        ))
    return gaps


def detect_anatomy_label_errors(db: Session, tenant_id: str, technician: str, window_days: int = 90) -> list[dict]:
    """Incorrect anatomy-zone labels, grouped by instrument family so rigid-
    scope and flexible-endoscope gaps remain distinct (never merged)."""
    reviews = _reviews_for_technician(db, tenant_id, technician, window_days)
    by_family: dict[str, list[SupervisorReview]] = defaultdict(list)
    for r in reviews:
        if r.zone_correct is False and r.instrument_family:
            by_family[r.instrument_family].append(r)

    gaps = []
    for family, rows in by_family.items():
        if len(rows) < _MIN_OCCURRENCES:
            continue
        domain = (
            COMPETENCY_RIGID_VS_FLEXIBLE_SCOPE
            if family in ("rigid_scope", "flexible_endoscope")
            else COMPETENCY_ANATOMY_ZONE_LABELING_DOC
        )
        gaps.append(_make_gap(
            competency_domain=domain, scope_value=technician, instrument_family=family,
            occurrence_count=len(rows),
            evidence={"supervisor_review_ids": [r.id for r in rows], "instrument_family": family},
            recommended_education=f"Provide focused anatomy-zone review for {family.replace('_', ' ')}.",
        ))
    return gaps


def detect_finding_confusion(db: Session, tenant_id: str, technician: str, window_days: int = 90) -> list[dict]:
    """'frequent confusion between rust and discoloration' / 'blood-versus-
    rust confusion' -- both members of a known confusable pair are each
    individually corrected for the same technician."""
    reviews = _reviews_for_technician(db, tenant_id, technician, window_days)
    incorrect_by_type: dict[str, list[SupervisorReview]] = defaultdict(list)
    for r in reviews:
        if r.finding_correct is False and r.finding_type:
            incorrect_by_type[r.finding_type].append(r)

    gaps = []
    for type_a, type_b in _CONFUSION_PAIRS:
        rows_a, rows_b = incorrect_by_type.get(type_a, []), incorrect_by_type.get(type_b, [])
        combined = rows_a + rows_b
        if len(combined) < _MIN_OCCURRENCES or not rows_a or not rows_b:
            continue
        leaf = competency_for_finding_type(type_a) or type_a
        gaps.append(_make_gap(
            competency_domain=leaf, scope_value=technician, finding_category=f"{type_a}_vs_{type_b}",
            occurrence_count=len(combined),
            evidence={"supervisor_review_ids": [r.id for r in combined], "confusable_pair": [type_a, type_b]},
            recommended_education=f"Provide targeted education distinguishing {type_a} from {type_b}.",
        ))
    return gaps


def detect_low_inspection_coverage(db: Session, tenant_id: str, technician: str, window_days: int = 90) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=window_days)
    rows = (
        db.query(models.Inspection)
        .filter(
            models.Inspection.tenant_id == tenant_id, models.Inspection.technician == technician,
            models.Inspection.created_at >= since, models.Inspection.coverage_pct.isnot(None),
        )
        .all()
    )
    low = [r for r in rows if r.coverage_pct < _LOW_COVERAGE_THRESHOLD_PCT]
    if len(low) < _MIN_OCCURRENCES:
        return []
    return [_make_gap(
        competency_domain=COMPETENCY_INSPECTION_COVERAGE, scope_value=technician,
        occurrence_count=len(low),
        evidence={"inspection_ids": [r.id for r in low], "avg_coverage_pct": round(sum(r.coverage_pct for r in low) / len(low), 1)},
        recommended_education="Provide focused review of inspection coverage requirements and image-capture workflow.",
    )]


def detect_image_capture_issues(db: Session, tenant_id: str, technician: str, window_days: int = 90) -> list[dict]:
    """Poor image focus/lighting/angle: this codebase only measures the
    aggregate `image_view_correct` signal, not focus/lighting/angle
    separately -- never fabricated beyond what is actually tracked."""
    reviews = _reviews_for_technician(db, tenant_id, technician, window_days)
    bad_views = [r for r in reviews if r.image_view_correct is False]
    if len(bad_views) < _MIN_OCCURRENCES:
        return []
    return [_make_gap(
        competency_domain=COMPETENCY_IMAGE_CAPTURE, scope_value=technician,
        occurrence_count=len(bad_views),
        evidence={"supervisor_review_ids": [r.id for r in bad_views]},
        recommended_education="Provide image-capture practice covering lighting, focus, and angle selection.",
    )]


def detect_disposition_errors(db: Session, tenant_id: str, technician: str, window_days: int = 90) -> list[dict]:
    reviews = _reviews_for_technician(db, tenant_id, technician, window_days)
    overridden = [r for r in reviews if r.override_action]
    if len(overridden) < _MIN_OCCURRENCES:
        return []
    return [_make_gap(
        competency_domain=COMPETENCY_DOMAIN_CLINICAL_DECISION, scope_value=technician,
        occurrence_count=len(overridden),
        evidence={"supervisor_review_ids": [r.id for r in overridden]},
        recommended_education="Provide case review of clinical decision support options (reclean/repair/manufacturer evaluation/remove from service).",
    )]


def detect_all_gaps_for_technician(db: Session, tenant_id: str, technician: str, window_days: int = 90) -> list[dict]:
    return (
        detect_missed_anatomy_zones(db, tenant_id, technician, window_days)
        + detect_anatomy_label_errors(db, tenant_id, technician, window_days)
        + detect_finding_confusion(db, tenant_id, technician, window_days)
        + detect_low_inspection_coverage(db, tenant_id, technician, window_days)
        + detect_image_capture_issues(db, tenant_id, technician, window_days)
        + detect_disposition_errors(db, tenant_id, technician, window_days)
    )
