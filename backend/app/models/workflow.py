"""v1.7 — Workflow Intelligence & Smart Work Queue.

Three additive tables:
  * InspectionAssignment — who is/was responsible for an inspection. Multiple
    rows per inspection are kept (reassignment history); the latest row is
    the current assignment.
  * WorkflowStateEvent — an append-only, audited log of workflow-state
    transitions (Deliverable 4). The current state of an inspection is the
    `to_state` of its latest event — never inferred by mutating a single
    "current state" column, so the full transition history is always
    reconstructable.
  * WorkflowNotification — an in-app notification queue for technicians,
    supervisors, and managers (Deliverable 10). Distinct from the existing
    Slack/Teams/email `AlertEvent` dispatcher in app/notifications/notifier.py
    (external channels for critical-finding alerts) — this is a per-recipient
    in-app queue for workflow events (assignment, overdue, review required).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Workflow states (Deliverable 4) ─────────────────────────────────────────
WAITING = "Waiting"
ASSIGNED = "Assigned"
IMAGE_CAPTURE = "Image Capture"
AI_ANALYSIS = "AI Analysis"
SUPERVISOR_REVIEW = "Supervisor Review"
RECLEAN = "Reclean"
REPAIR = "Repair"
COMPLETED = "Completed"
CANCELLED = "Cancelled"

WORKFLOW_STATES = [
    WAITING, ASSIGNED, IMAGE_CAPTURE, AI_ANALYSIS, SUPERVISOR_REVIEW,
    RECLEAN, REPAIR, COMPLETED, CANCELLED,
]


class InspectionAssignment(Base):
    __tablename__ = "inspection_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    inspection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    technician: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    assigned_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    note: Mapped[str] = mapped_column(String(500), default="", nullable=False)


class WorkflowStateEvent(Base):
    __tablename__ = "workflow_state_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    inspection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    from_state: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    to_state: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    reason: Mapped[str] = mapped_column(String(500), default="", nullable=False)


class WorkflowNotification(Base):
    __tablename__ = "workflow_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    inspection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    notification_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # A specific person if known, otherwise blank and recipient_role fans out
    # to everyone with that role (rendered as a role-scoped feed, not stored
    # per-person, so it isn't lost when technician assignment changes).
    recipient_role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    recipient_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    message: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
