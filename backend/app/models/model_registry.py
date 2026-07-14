"""Phase 17 §5 — Model Registry.

One row per trained model version: what it is, which dataset it came from, how it
scored, its known limitations, and its approval status. This is the source of
truth for the deployment gate — a recommendation may only be driven by a model
whose registry stage permits it.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ModelRegistryEntry(Base):
    __tablename__ = "model_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(
        String(100), default="default-tenant", nullable=False, index=True
    )

    model_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)  # task key
    dataset_version: Mapped[str] = mapped_column(String(100), default="", nullable=False)

    training_date: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    # not_started | training | trained | failed
    training_status: Mapped[str] = mapped_column(String(30), default="not_started", nullable=False)

    # JSON-encoded metrics + limitations (portable across SQLite/Postgres).
    evaluation_metrics: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    known_limitations: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # experimental | pilot | validated | deprecated
    approval_status: Mapped[str] = mapped_column(
        String(20), default="experimental", nullable=False, index=True
    )
    approved_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    release_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Dataset Registry & AI Model Development Foundation — additive fields.
    # Reproducibility: what was trained, how, on what code, and from what
    # frozen dataset (dataset_version above stays the free-text fingerprint;
    # dataset_version_id is the new first-class, freezable entity when one
    # was used).
    architecture: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    framework: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    hyperparameters: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    git_commit: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    dataset_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    training_metrics: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    # Promotion-readiness flags (Section 12) — each must be true, on top of
    # the existing deployment-gate checklist, before app.services.ml.
    # model_promotion.evaluate_full_promotion_readiness() allows a model out
    # of "experimental". Never set true by default; a human/service records
    # them explicitly.
    documentation_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    clinical_review_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metrics_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    model_card_markdown: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Genesis (Production Model Training, Scientific Validation & Model
    # Governance) — additive fields for the Candidate/Validated Candidate
    # promotion ladder, distinct from the approval_status ladder above
    # (experimental/pilot/validated/deprecated governs whether a model may
    # drive a clinical recommendation; candidate_stage below governs where a
    # model sits in the training->validation->deployment pipeline itself).
    training_run_id: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    reviewer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    # pending | approved | rejected
    clinical_review_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    # not_deployed | shadow | deployed
    deployment_status: Mapped[str] = mapped_column(String(20), default="not_deployed", nullable=False)
    # Experimental | Candidate | Validated Candidate | Pilot | Production
    candidate_stage: Mapped[str] = mapped_column(String(30), default="Experimental", nullable=False, index=True)

    error_analysis_reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reproducible_training_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    governance_review_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    calibration_report: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    error_analysis_report: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    artifact_path: Mapped[str] = mapped_column(String(500), default="", nullable=False)

    # Advisor (Phase 7 — Supervised Advisory Pilot & Human-AI Collaboration)
    # §13 — the customer-approval evidence item for the Pilot -> Production
    # gate, distinct from governance_review_completed (internal governance)
    # and clinical_review_board_approved (clinical sign-off). Never
    # defaulted true.
    customer_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    customer_approved_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
