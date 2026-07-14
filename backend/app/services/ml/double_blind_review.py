"""Dataset Registry & AI Model Development Foundation — Section 4.

Primary + independent reviewer, plus adjudication when they disagree.
Distinct from the pre-existing critical-class two-reviewer *count* gate in
``app.routes.ml_images`` (which enforces "two labels exist" before
adjudication is allowed) — this is the formal record of exactly which two
reviewers said what, whether they agreed, and how a disagreement was
resolved and why, which did not previously exist anywhere in this codebase.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.dataset_governance import DoubleBlindReview


class ReviewAlreadySubmittedError(ValueError):
    pass


class ReviewerCannotSelfIndependentError(ValueError):
    pass


class AdjudicationNotRequiredError(ValueError):
    pass


class ReasonRequiredError(ValueError):
    pass


def start_review(db: Session, *, tenant_id: str, dataset_entry_id: int) -> DoubleBlindReview:
    existing = (
        db.query(DoubleBlindReview)
        .filter(DoubleBlindReview.tenant_id == tenant_id, DoubleBlindReview.dataset_entry_id == dataset_entry_id)
        .first()
    )
    if existing is not None:
        return existing
    row = DoubleBlindReview(tenant_id=tenant_id, dataset_entry_id=dataset_entry_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def submit_primary(
    db: Session, *, review: DoubleBlindReview, reviewer: str, label: str, confidence: float | None = None,
) -> DoubleBlindReview:
    if review.primary_submitted_at is not None:
        raise ReviewAlreadySubmittedError("Primary review already submitted for this image.")
    review.primary_reviewer = reviewer
    review.primary_label = label
    review.primary_confidence = confidence
    review.primary_submitted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review)
    return review


def submit_independent(
    db: Session, *, review: DoubleBlindReview, reviewer: str, label: str, confidence: float | None = None,
) -> DoubleBlindReview:
    """Submit the second, independent label. Blind by construction: this
    function never reads or exposes ``primary_label`` to the caller before
    recording the independent one — the route layer must not fetch and
    display the primary label to whoever is about to submit the
    independent one."""
    if review.independent_submitted_at is not None:
        raise ReviewAlreadySubmittedError("Independent review already submitted for this image.")
    if reviewer and reviewer == review.primary_reviewer:
        raise ReviewerCannotSelfIndependentError(
            "The independent reviewer must be a different person from the primary reviewer."
        )
    review.independent_reviewer = reviewer
    review.independent_label = label
    review.independent_confidence = confidence
    review.independent_submitted_at = datetime.now(timezone.utc)

    if review.primary_submitted_at is not None:
        review.agreement = review.primary_label == label

    db.commit()
    db.refresh(review)
    return review


def adjudicate(
    db: Session, *, review: DoubleBlindReview, adjudicator: str, resolution: str, reason: str,
) -> DoubleBlindReview:
    """Resolve a disagreement. Requires a non-empty reason — an
    unexplained override of either reviewer's label is not permitted."""
    if review.agreement is True:
        raise AdjudicationNotRequiredError(
            "Primary and independent reviewers agreed; no adjudication is needed."
        )
    if not reason.strip():
        raise ReasonRequiredError("A reason is required to adjudicate a disagreement.")
    review.adjudicator = adjudicator
    review.resolution = resolution.strip()
    review.reason = reason.strip()
    review.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review)
    return review
