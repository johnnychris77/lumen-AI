from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TenantPlan(Base):
    __tablename__ = "tenant_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_name: Mapped[str] = mapped_column(String(100), nullable=False, default="starter")
    monthly_price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    included_inspections: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    included_evidence_exports: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    included_trust_center_exports: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overage_inspection_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overage_evidence_export_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overage_trust_center_export_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
