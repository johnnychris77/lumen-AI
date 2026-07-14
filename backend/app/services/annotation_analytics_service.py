"""Annotation Database — Section 11: Annotation Analytics.

Every figure here is computed live from real `Annotation`/`AnnotationReview`
rows — never a fabricated or hardcoded metric. Returns `None`/empty
collections where insufficient data exists rather than a misleading zero.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.annotation_database import GROUND_TRUTH_ACTIVE, Annotation, AnnotationReview


def reviewer_agreement(db: Session, *, tenant_id: str) -> dict[str, Any]:
    reviews = (
        db.query(AnnotationReview)
        .filter(AnnotationReview.tenant_id == tenant_id, AnnotationReview.agreement.isnot(None))
        .all()
    )
    if not reviews:
        return {"total_reviewed": 0, "agreement_rate": None, "by_reviewer_pair": {}}

    agreed = sum(1 for r in reviews if r.agreement)
    by_pair: dict[str, list[bool]] = defaultdict(list)
    for r in reviews:
        pair = f"{r.primary_reviewer}|{r.secondary_reviewer}"
        by_pair[pair].append(bool(r.agreement))

    return {
        "total_reviewed": len(reviews),
        "agreement_rate": round(agreed / len(reviews), 4),
        "by_reviewer_pair": {
            pair: round(sum(vals) / len(vals), 4) for pair, vals in by_pair.items()
        },
    }


def reviewer_accuracy(db: Session, *, tenant_id: str) -> dict[str, Any]:
    """Compares each reviewer's submitted label against the annotation's
    final Ground Truth label, where Ground Truth is ACTIVE."""
    reviews = db.query(AnnotationReview).filter(AnnotationReview.tenant_id == tenant_id).all()
    annotations_by_id = {
        a.id: a for a in db.query(Annotation).filter(
            Annotation.tenant_id == tenant_id, Annotation.ground_truth_status == GROUND_TRUTH_ACTIVE,
        ).all()
    }

    correct: dict[str, int] = defaultdict(int)
    total: dict[str, int] = defaultdict(int)
    for r in reviews:
        annotation = annotations_by_id.get(r.annotation_id)
        if annotation is None:
            continue
        gt_label = annotation.primary_observation
        if r.primary_reviewer:
            total[r.primary_reviewer] += 1
            if r.primary_label == gt_label:
                correct[r.primary_reviewer] += 1
        if r.secondary_reviewer:
            total[r.secondary_reviewer] += 1
            if r.secondary_label == gt_label:
                correct[r.secondary_reviewer] += 1

    return {
        reviewer: round(correct[reviewer] / count, 4)
        for reviewer, count in total.items() if count > 0
    }


def common_findings(db: Session, *, tenant_id: str, limit: int = 10) -> list[dict[str, Any]]:
    rows = (
        db.query(Annotation.primary_observation)
        .filter(Annotation.tenant_id == tenant_id, Annotation.primary_observation != "")
        .all()
    )
    counts = Counter(r[0] for r in rows)
    return [{"observation": label, "count": count} for label, count in counts.most_common(limit)]


def finding_distribution(db: Session, *, tenant_id: str) -> dict[str, int]:
    rows = db.query(Annotation.primary_observation).filter(Annotation.tenant_id == tenant_id).all()
    return dict(Counter(r[0] or "unlabeled" for r in rows))


def unknown_frequency(db: Session, *, tenant_id: str) -> dict[str, Any]:
    total = db.query(Annotation).filter(Annotation.tenant_id == tenant_id).count()
    if total == 0:
        return {"total": 0, "unknown_count": 0, "unknown_rate": None}
    unknown_count = db.query(Annotation).filter(
        Annotation.tenant_id == tenant_id, Annotation.unknown_flag.is_(True),
    ).count()
    return {"total": total, "unknown_count": unknown_count, "unknown_rate": round(unknown_count / total, 4)}


def class_balance(db: Session, *, tenant_id: str) -> dict[str, Any]:
    distribution = finding_distribution(db, tenant_id=tenant_id)
    total = sum(distribution.values())
    if total == 0:
        return {"counts": {}, "minority_ratio": None}
    minority_ratio = min(distribution.values()) / total
    return {"counts": distribution, "minority_ratio": round(minority_ratio, 4)}


def dataset_growth(db: Session, *, tenant_id: str) -> dict[str, int]:
    """Real annotation counts grouped by creation date (YYYY-MM-DD) —
    never interpolated or projected."""
    rows = db.query(Annotation.created_at).filter(Annotation.tenant_id == tenant_id).all()
    by_day: Counter = Counter()
    for (created_at,) in rows:
        day = created_at.date().isoformat() if isinstance(created_at, datetime) else str(created_at)[:10]
        by_day[day] += 1
    return dict(sorted(by_day.items()))


def annotation_velocity(db: Session, *, tenant_id: str) -> dict[str, Any]:
    """Average annotations created per reviewer per distinct day they were active."""
    rows = db.query(Annotation.reviewer, Annotation.created_at).filter(Annotation.tenant_id == tenant_id).all()
    by_reviewer_days: dict[str, set] = defaultdict(set)
    by_reviewer_count: Counter = Counter()
    for reviewer, created_at in rows:
        if not reviewer:
            continue
        day = created_at.date().isoformat() if isinstance(created_at, datetime) else str(created_at)[:10]
        by_reviewer_days[reviewer].add(day)
        by_reviewer_count[reviewer] += 1

    return {
        reviewer: round(by_reviewer_count[reviewer] / len(days), 4)
        for reviewer, days in by_reviewer_days.items() if days
    }
