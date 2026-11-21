"""CV inference result persistence model."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.db.base import Base


class CVInferenceRecord(Base):
    """Persisted CV pipeline result for audit trail and KPI aggregation."""
    __tablename__ = "cv_inference_records"

    id = Column(Integer, primary_key=True, index=True)
    inference_id = Column(String(100), unique=True, nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True, default="default-tenant")

    # Context
    context = Column(String(50), default="inspection", nullable=False)
    provider = Column(String(50), default="mock", nullable=False)
    status = Column(String(20), default="success", nullable=False)

    # Links
    finding_id = Column(Integer, nullable=True, index=True)
    instrument_id = Column(Integer, nullable=True, index=True)

    # Multi-hospital: identifies which facility within a tenant performed the inspection.
    # Populated from X-Facility-ID request header or analysis request context.
    # Falls back to tenant_id when not set (single-hospital tenants).
    facility_id = Column(String(100), nullable=False, index=True, default="")

    # Image
    image_url = Column(Text, default="", nullable=False)
    baseline_image_url = Column(Text, default="", nullable=False)

    # Instrument identity
    instrument_recognized = Column(Boolean, default=False, nullable=False)
    instrument_name = Column(String(255), default="", nullable=False)
    instrument_category = Column(String(100), default="", nullable=False)
    instrument_confidence = Column(Float, default=0.0, nullable=False)
    match_method = Column(String(50), default="", nullable=False)

    # Identifier reads
    barcode_value = Column(String(500), default="", nullable=False)
    qr_value = Column(String(500), default="", nullable=False)
    key_dot_value = Column(String(500), default="", nullable=False)

    # Canonical join key: barcode > qr > key_dot (populated by CV pipeline)
    barcode_instrument_id = Column(String(200), nullable=False, index=True, default="")

    # Scores (0-100, higher = cleaner)
    contamination_score = Column(Float, default=100.0, nullable=False)
    damage_score = Column(Float, default=100.0, nullable=False)
    overall_cleanliness_score = Column(Float, default=100.0, nullable=False)

    # Baseline comparison
    baseline_compared = Column(Boolean, default=False, nullable=False)
    baseline_match_pct = Column(Float, default=0.0, nullable=False)
    baseline_verdict = Column(String(30), default="", nullable=False)

    # Aggregate finding counts (denormalized for fast KPI queries)
    finding_count = Column(Integer, default=0, nullable=False)
    blood_count = Column(Integer, default=0, nullable=False)
    bone_count = Column(Integer, default=0, nullable=False)
    tissue_count = Column(Integer, default=0, nullable=False)
    corrosion_count = Column(Integer, default=0, nullable=False)
    crack_count = Column(Integer, default=0, nullable=False)
    insulation_count = Column(Integer, default=0, nullable=False)
    residue_count = Column(Integer, default=0, nullable=False)

    # Full JSON payload for retrieval
    result_json = Column(Text, default="", nullable=False)

    # R7: Internal object storage key for archived image bytes
    archived_image_key = Column(Text, default="", nullable=False)

    # R12: Provider cost and latency telemetry
    provider_cost_usd = Column(Float, default=0.0, nullable=False)

    # R10: Active learning — flag for human review
    review_required = Column(Boolean, default=False, nullable=False)
    review_annotation = Column(Text, default="", nullable=False)
    review_annotator_id = Column(String(100), default="", nullable=False)
    review_completed_at = Column(DateTime, nullable=True)

    processing_ms = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class CVInferenceProvenance(Base):
    """P4.7.2 — server-issued provenance for ONE trusted inference run.

    A ``CVInferenceRecord`` counts as verified model inference only while exactly
    one row here refers to it, is in the ``trusted`` state, and carries a seal
    that verifies against the server's provenance key AND against the record as
    it is now. Nothing a client sends, and nothing stored in the record's own
    ``result_json``, can stand in for this row.

    Rows are written only by ``app.cv.provenance.issue_provenance`` from inside
    the analysis pipeline. There is no API that creates or edits them.

    The seal (``attestation``) is an HMAC over the run's identity — record id,
    inference id, authenticated tenant, provider, execution status, model
    versions, verified artifact digests — plus a digest of the record's
    operational fields. A row inserted or altered by anything that does not hold
    the server key therefore fails verification, and a record altered after
    sealing no longer matches its row.
    """
    __tablename__ = "cv_inference_provenance"
    __table_args__ = (
        UniqueConstraint("record_id", name="uq_cv_inference_provenance_record"),
        UniqueConstraint("inference_id", name="uq_cv_inference_provenance_inference"),
    )

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(
        Integer, ForeignKey("cv_inference_records.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    inference_id = Column(String(100), nullable=False, index=True)
    # The AUTHENTICATED tenant the run was executed for (never a client claim).
    tenant_id = Column(String(100), nullable=False, index=True)

    provider = Column(String(50), nullable=False)
    execution_status = Column(String(20), nullable=False)
    # Canonical JSON. The artifact digests are the SHA-256 values the provider
    # verified before loading, each of which was an approved pin at issuance.
    model_versions_json = Column(Text, nullable=False, default="{}")
    artifact_digests_json = Column(Text, nullable=False, default="{}")

    # SHA-256 over the record's operational fields at the moment of sealing.
    record_digest = Column(String(64), nullable=False)

    # "trusted" or "revoked". Part of the sealed payload.
    state = Column(String(20), nullable=False, default="trusted", index=True)
    key_id = Column(String(64), nullable=False)
    attestation = Column(String(64), nullable=False)
    issued_at = Column(String(40), nullable=False)

    revoked_at = Column(String(40), nullable=False, default="")
    revoked_by = Column(String(255), nullable=False, default="")
    revoked_reason = Column(String(255), nullable=False, default="")

