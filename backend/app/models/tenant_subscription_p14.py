"""P14: Extended tenant subscription model with billing/HIPAA/GPO fields."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TenantSubscriptionP14(Base):
    """
    Separate table for P14 billing/webhook/HIPAA/GPO fields to avoid
    conflicting with the existing TenantSubscription model.
    """
    __tablename__ = "tenant_subscriptions_p14"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_tsub_p14_tenant"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    stripe_customer_id: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    stripe_subscription_id: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    plan_tier: Mapped[str] = mapped_column(String(50), nullable=False, default="starter")
    subscription_status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # GPO fields
    gpo_contract_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gpo_discount_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # HIPAA BAA fields
    hipaa_baa_signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hipaa_baa_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
