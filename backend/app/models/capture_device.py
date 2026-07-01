"""Capture-device registry for direct borescope-to-LumenAI ingestion.

A capture device is an unattended appliance ("LumenAI Bridge") or a tablet
running the browser capture client that pushes borescope frames straight into
LumenAI over HTTPS — replacing the USB-drive hand-off that hospital IT blocks.

Security:
- The device key is issued ONCE via secrets.token_urlsafe(40) and stored only as
  a SHA-256 hash — never retrievable again (matches the platform's API-key rule).
- Devices are tenant-scoped and can be revoked (active=False).
- Every ingestion authenticates with the hashed key and is audit-logged.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CaptureDevice(Base):
    __tablename__ = "capture_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    tenant_id: Mapped[str] = mapped_column(
        String(100), default="default-tenant", nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Free-text location so leaders know which room/scope this device serves.
    location: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    # SHA-256 of the issued key — the plaintext is shown once and never stored.
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # The inspection role the device acts as (operator by default).
    role: Mapped[str] = mapped_column(String(50), default="operator", nullable=False)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
