"""P14: SSO configuration model."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TenantSSOConfig(Base):
    __tablename__ = "tenant_sso_configs"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_sso_tenant"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="none")
    oidc_issuer_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    jwks_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    client_id: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    audience: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    redirect_uri: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    groups_claim: Mapped[str] = mapped_column(String(100), nullable=False, default="groups")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
