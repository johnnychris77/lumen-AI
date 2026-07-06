"""v1.9 — Production Error Logging (Deliverable 7).

A safe, structured log of operational failures — upload failure, AI
analysis failure, baseline lookup failure, role permission failure,
report generation failure. Deliberately narrow: `detail` is a short,
developer-facing failure reason (exception message / HTTP status), never
image bytes, patient/procedure identifiers, or any other PHI. This is
distinct from the existing `AuditLog` (compliance/access trail of
successful actions) and `AlertEvent` (external Slack/Teams/email dispatch
for critical clinical findings) — this is an internal reliability signal.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

UPLOAD_FAILURE = "upload_failure"
AI_ANALYSIS_FAILURE = "ai_analysis_failure"
BASELINE_LOOKUP_FAILURE = "baseline_lookup_failure"
ROLE_PERMISSION_FAILURE = "role_permission_failure"
REPORT_GENERATION_FAILURE = "report_generation_failure"

ERROR_TYPES = [
    UPLOAD_FAILURE, AI_ANALYSIS_FAILURE, BASELINE_LOOKUP_FAILURE,
    ROLE_PERMISSION_FAILURE, REPORT_GENERATION_FAILURE,
]


class PilotErrorLog(Base):
    __tablename__ = "pilot_error_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    error_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # Short, developer-facing reason only — never PHI, never image bytes.
    detail: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    actor_role: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
