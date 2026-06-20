"""CV inference result persistence model."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

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
