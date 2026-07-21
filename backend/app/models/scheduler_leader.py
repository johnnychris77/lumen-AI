"""RES-01 — scheduler leader-election lease.

The background schedulers (predictions, RWE, integrations, quality
intelligence, global aggregation) must run on exactly one replica. Running
them on every replica double-executes jobs — duplicate emails, duplicate
aggregation writes, and races. This single-row-per-lock table backs a
lease-based leader election: a replica holds leadership only while its lease is
unexpired, and a standby can claim it once the lease lapses (automatic failover
within the TTL).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SchedulerLeader(Base):
    """One row per named lock. `holder` owns the lock until `expires_at`."""

    __tablename__ = "scheduler_leader"

    lock_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    holder: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
