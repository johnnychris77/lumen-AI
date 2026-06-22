"""P16: Enterprise hierarchy models — HealthSystem, Market, Region, Facility, Department."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HealthSystem(Base):
    __tablename__ = "enterprise_health_systems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    system_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    system_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hq_region: Mapped[str] = mapped_column(String(100), default="north_america", nullable=False)
    contract_tier: Mapped[str] = mapped_column(String(50), default="enterprise", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    admin_email: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class EnterpriseMarket(Base):
    __tablename__ = "enterprise_markets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    market_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    market_name: Mapped[str] = mapped_column(String(255), nullable=False)
    system_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    region: Mapped[str] = mapped_column(String(100), default="north_america", nullable=False)
    director_email: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class EnterpriseRegion(Base):
    __tablename__ = "enterprise_regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    region_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    region_name: Mapped[str] = mapped_column(String(255), nullable=False)
    market_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    system_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class EnterpriseFacility(Base):
    __tablename__ = "enterprise_hierarchy_facilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    facility_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    facility_name: Mapped[str] = mapped_column(String(255), nullable=False)
    region_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    market_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    system_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    facility_type: Mapped[str] = mapped_column(String(100), default="hospital", nullable=False)
    bed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    onboarding_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    go_live_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class EnterpriseDepartment(Base):
    __tablename__ = "enterprise_hierarchy_departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    department_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    department_name: Mapped[str] = mapped_column(String(255), nullable=False)
    facility_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    department_type: Mapped[str] = mapped_column(String(100), default="spd", nullable=False)
    manager_email: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class OnboardingWorkflow(Base):
    """Tracks onboarding state for facilities, users, vendors, baselines."""
    __tablename__ = "enterprise_onboarding_workflows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workflow_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    workflow_type: Mapped[str] = mapped_column(String(50), nullable=False)  # site|user|vendor|baseline
    target_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    system_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    facility_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    current_step: Mapped[str] = mapped_column(String(100), default="initiated", nullable=False)
    steps_completed: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    assigned_to: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class EnterpriseBaseline(Base):
    """Enterprise-wide baseline with version control and approval workflow."""
    __tablename__ = "enterprise_baselines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    baseline_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    system_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    instrument_type: Mapped[str] = mapped_column(String(100), nullable=False)
    material_type: Mapped[str] = mapped_column(String(100), nullable=False)
    acceptance_criteria: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    approval_status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    approved_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_to: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # list of facility_ids
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    superseded_by: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    change_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class FacilityReadinessScore(Base):
    """Snapshot readiness assessment for a facility."""
    __tablename__ = "enterprise_facility_readiness"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    facility_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    system_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    training_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    adoption_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    baseline_coverage_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    inspection_volume_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    data_quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    readiness_status: Mapped[str] = mapped_column(String(20), default="not_ready", nullable=False)
