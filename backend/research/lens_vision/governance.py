"""Research data-USAGE authorization + ground-truth classification.

This is the research-side reuse of the Project Canvas governance controls. A
provenance *classification* is necessary but never sufficient: an image is
research-usable only when the existing rights / quality / PHI / archival /
retention gates pass AND (for clinical data) a separately authorized research-use
scope exists. Ground-truth status is read from the authoritative Annotation
Database, never defaulted.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.annotation_database import GROUND_TRUTH_ACTIVE, Annotation
from app.models.consent_record import ConsentRecord
from app.models.dataset_governance import DatasetRegistryEntry
from app.services.ml.training_eligibility_service import _structural_reason
from app.services.observation_taxonomy import (
    OBSERVATION_INSUFFICIENT_IMAGE,
    OBSERVATION_NO_ABNORMALITY,
    OBSERVATION_UNKNOWN_FOREIGN,
    canonical_observation_category,
)
from research.lens_vision.provenance import (
    PROVENANCE_REAL_CLINICAL,
    sample_provenance_class,
)

# Consent types that authorize a RESEARCH use scope (distinct from clinical
# evidence rights, which is regulatory_evidence). A clinical image may enter a
# research experiment only when the tenant holds one of these, granted and not
# withdrawn.
RESEARCH_USE_CONSENT_TYPES = frozenset({"benchmarking_contribution", "analytics"})

# Ground-truth label status — the four states research must keep distinct.
GT_VERIFIED_NORMAL = "verified_normal"
GT_ABNORMAL = "abnormal"
GT_UNKNOWN = "unknown"
GT_UNLABELED = "unlabeled"

# Retention states that still permit use (bytes present and not purged).
_RETENTION_OK = {"active"}


def research_use_scope_authorized(db: Session, tenant_id: str) -> bool:
    """True iff the tenant holds a granted, non-withdrawn research-use consent.

    This is the *separately authorized research-use scope* required before any
    clinical data may be used in research — verified against a real record, never
    inferred from a caller-supplied flag.
    """
    rec = (
        db.query(ConsentRecord)
        .filter(
            ConsentRecord.tenant_id == tenant_id,
            ConsentRecord.granted.is_(True),
            ConsentRecord.withdrawn_at.is_(None),
            ConsentRecord.consent_type.in_(tuple(RESEARCH_USE_CONSENT_TYPES)),
        )
        .first()
    )
    return rec is not None


def ground_truth_status(db: Session, *, tenant_id: str, retained_image_id: int) -> tuple[str, str | None]:
    """Classify an image's ground-truth state from the authoritative Annotation
    Database (``ground_truth_status == ACTIVE``). Returns ``(status, label)``.

    - ``verified_normal`` — an ACTIVE annotation whose observation is
      ``no_observable_abnormality``.
    - ``abnormal`` — an ACTIVE annotation with a real finding.
    - ``unknown`` — an ACTIVE annotation that is unknown/insufficient (not a
      usable normal or a specific finding).
    - ``unlabeled`` — no ACTIVE annotation exists (never treated as normal).
    """
    ann = (
        db.query(Annotation)
        .filter(
            Annotation.tenant_id == tenant_id,
            Annotation.retained_image_id == retained_image_id,
            Annotation.ground_truth_status == GROUND_TRUTH_ACTIVE,
        )
        .order_by(Annotation.id.desc())
        .first()
    )
    if ann is None:
        return GT_UNLABELED, None
    label = canonical_observation_category(ann.primary_observation or "")
    if not label or label in {OBSERVATION_INSUFFICIENT_IMAGE, OBSERVATION_UNKNOWN_FOREIGN, "unknown_review_required"}:
        return GT_UNKNOWN, label or None
    if label == OBSERVATION_NO_ABNORMALITY:
        return GT_VERIFIED_NORMAL, label
    return GT_ABNORMAL, label


def authorize_research_entry(
    db: Session, entry: DatasetRegistryEntry, *, tenant_id: str, allow_approved_clinical: bool = False,
) -> str | None:
    """Return None when ``entry`` is authorized for research use, else a reason.

    Enforces (reusing Project Canvas controls): tenant match, research-authorized
    provenance, the structural rights/quality/PHI/archival gate, retention, and —
    for clinical data — an opt-in AND a verified research-use scope.
    """
    if entry.tenant_id != tenant_id:
        return "cross_tenant"
    cls = sample_provenance_class({"data_provenance_class": entry.data_provenance_class})

    # Structural usage gate (rights / quality / PHI / archival) + retention.
    structural = _structural_reason(entry)
    if structural is not None:
        return structural
    if (entry.retention_status or "") not in _RETENTION_OK:
        return "retention_not_active"

    # Provenance + clinical research-use scope.
    from research.lens_vision.provenance import RESEARCH_AUTHORIZED_CLASSES
    if cls in RESEARCH_AUTHORIZED_CLASSES:
        return None
    if cls == PROVENANCE_REAL_CLINICAL:
        if entry.provenance_approval_status != "approved":
            return "clinical_not_approved"
        if not allow_approved_clinical:
            return "clinical_research_use_not_opted_in"
        if not research_use_scope_authorized(db, tenant_id):
            return "clinical_research_use_scope_unauthorized"
        return None
    return f"provenance_not_research_authorized:{cls}"
