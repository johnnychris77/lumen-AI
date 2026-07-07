"""v1.9 — Pilot Site Configuration (Deliverable 4).

One row per tenant. Deliberately separate from `OrganizationStandard`
(v1.8, a list of free-text policy documents supervisors author) — this is
the small set of structured, machine-read settings the pilot's own
workflow guardrails (coverage gating, supervisor review thresholds) and
the Pilot Data Collection Dashboard read directly. Supplements, never
replaces, manufacturer IFUs or the AI's own scoring engines.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PilotSiteConfig(Base):
    __tablename__ = "pilot_site_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, unique=True, index=True)

    facility_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    department: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    # JSON-encoded lists, kept as text for SQLite/Postgres portability.
    enabled_instrument_families: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    required_inspection_zones: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    baseline_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Minimum coverage percent below which an inspection is flagged incomplete.
    minimum_coverage_pct: Mapped[int] = mapped_column(Integer, default=75, nullable=False)
    # Readiness score at/below which a supervisor review is mandatory before
    # packaging, independent of the disposition engine's own recommendation.
    supervisor_review_threshold_score: Mapped[int] = mapped_column(Integer, default=70, nullable=False)

    updated_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
