"""v2.8 — LumenAI OR Connect: Perioperative Coordination Engine.

Codename: Project Symphony. Coordinates quality intelligence across the
surgical scheduling, vendor tray logistics, instrument inspection, repair,
and supervisor-approval workflows that already exist elsewhere in LumenAI —
it does not replace Epic, ReadySet, supply chain, or clinical engineering
systems, it correlates their real state into one Case Readiness Score.

Six additive tables:
  * SurgicalCase — the case itself (procedure/surgeon/facility/OR/schedule).
    `Inspection.case_id` (nullable) links real inspections to a case rather
    than duplicating instrument/finding state here.
  * VendorTray — one tray (vendor-supplied or hospital-owned) needed for a
    case, with a real requested/shipped/received/returned lifecycle.
  * RepairRequest — a repair/replacement ticket for an instrument, optionally
    linked to the case it's blocking.
  * CaseRiskAlert — a detected operational risk for a case (Section 4).
  * CaseNotification — an in-app, role-scoped notification queue for case
    stakeholders (Section 5), mirroring `WorkflowNotification`'s recipient-
    role fan-out pattern but extended to non-SPD OR roles.
  * CaseReadinessScoreRecord — a persisted snapshot of a computed Case
    Readiness Score, so trends can be reported without re-deriving history.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Vendor tray lifecycle ───────────────────────────────────────────────────
TRAY_REQUESTED = "requested"
TRAY_SHIPPED = "shipped"
TRAY_RECEIVED = "received"
TRAY_RETURNED = "returned"
TRAY_STATUSES = [TRAY_REQUESTED, TRAY_SHIPPED, TRAY_RECEIVED, TRAY_RETURNED]

# ── Repair ticket lifecycle ─────────────────────────────────────────────────
REPAIR_PENDING = "pending"
REPAIR_IN_PROGRESS = "in_progress"
REPAIR_RETURNED = "returned"
REPAIR_REPLACED = "replaced"
REPAIR_STATUSES = [REPAIR_PENDING, REPAIR_IN_PROGRESS, REPAIR_RETURNED, REPAIR_REPLACED]

# ── Structured failure cause (added for Project Beacon v3.5, Section 3 & 7) ──
# `repair_type` above was always a free-text label; Beacon's Repair Partner
# Portal and Repair Intelligence sections need a closed vocabulary to group
# and benchmark repair causes across tenants/vendors, so this is a new
# nullable column on the same row rather than a parallel repair-cause table.
FAILURE_CORROSION = "corrosion"
FAILURE_MECHANICAL_WEAR = "mechanical_wear"
FAILURE_ELECTRICAL_FAULT = "electrical_fault"
FAILURE_INSULATION_DEFECT = "insulation_defect"
FAILURE_MISUSE_DAMAGE = "misuse_damage"
FAILURE_MANUFACTURING_DEFECT = "manufacturing_defect"
FAILURE_OTHER = "other"
FAILURE_CATEGORIES = [
    FAILURE_CORROSION, FAILURE_MECHANICAL_WEAR, FAILURE_ELECTRICAL_FAULT,
    FAILURE_INSULATION_DEFECT, FAILURE_MISUSE_DAMAGE, FAILURE_MANUFACTURING_DEFECT, FAILURE_OTHER,
]

# ── Operational risk types (Section 4) ──────────────────────────────────────
RISK_VENDOR_TRAY_NOT_RECEIVED = "vendor_tray_not_received"
RISK_INSPECTION_OVERDUE = "inspection_overdue"
RISK_BASELINE_MISSING = "baseline_missing"
RISK_REPAIR_INCOMPLETE = "repair_incomplete"
RISK_CRITICAL_FINDING_UNRESOLVED = "critical_finding_unresolved"
RISK_SUPERVISOR_REVIEW_PENDING = "supervisor_review_pending"
# Added for v4.5 Project Orbit's Readiness Alert Engine (Section 5) — these
# extend the same `CaseRiskAlert` table/vocabulary rather than Orbit adding a
# second alert table for the same `SurgicalCase` entity.
RISK_MISSING_INSTRUMENT = "missing_instrument"
RISK_MISSING_IMPLANT = "missing_implant"
RISK_HIGH_RISK_DIGITAL_TWIN = "high_risk_digital_twin"
RISK_EQUIPMENT_UNAVAILABLE = "equipment_unavailable"
RISK_KNOWLEDGE_ADVISORY = "knowledge_advisory"
RISK_TYPES = [
    RISK_VENDOR_TRAY_NOT_RECEIVED, RISK_INSPECTION_OVERDUE, RISK_BASELINE_MISSING,
    RISK_REPAIR_INCOMPLETE, RISK_CRITICAL_FINDING_UNRESOLVED, RISK_SUPERVISOR_REVIEW_PENDING,
    RISK_MISSING_INSTRUMENT, RISK_MISSING_IMPLANT, RISK_HIGH_RISK_DIGITAL_TWIN,
    RISK_EQUIPMENT_UNAVAILABLE, RISK_KNOWLEDGE_ADVISORY,
]

# ── Stakeholder roles (Section 5) ───────────────────────────────────────────
ROLE_SPD = "spd"
ROLE_OR_CHARGE_NURSE = "or_charge_nurse"
ROLE_SURGEON = "surgeon"
ROLE_VENDOR_REP = "vendor_rep"
ROLE_CLINICAL_ENGINEERING = "clinical_engineering"
ROLE_SUPPLY_CHAIN = "supply_chain"
# Added for v4.5 Project Orbit's Cross-Department Coordination (Section 4) —
# the three named departments not already covered by the six roles above.
ROLE_INFECTION_PREVENTION = "infection_prevention"
ROLE_QUALITY = "quality"
ROLE_BIOMEDICAL_ENGINEERING = "biomedical_engineering"
STAKEHOLDER_ROLES = [
    ROLE_SPD, ROLE_OR_CHARGE_NURSE, ROLE_SURGEON, ROLE_VENDOR_REP,
    ROLE_CLINICAL_ENGINEERING, ROLE_SUPPLY_CHAIN,
    ROLE_INFECTION_PREVENTION, ROLE_QUALITY, ROLE_BIOMEDICAL_ENGINEERING,
]

DISCLAIMER = (
    "LumenAI OR Connect coordinates quality intelligence across existing scheduling, vendor, "
    "and clinical-engineering systems — it does not replace them and does not make autonomous "
    "clinical or operational decisions. Case readiness, risk, and notification outputs are "
    "decision support only; human review and approval are required before any operational action."
)


class SurgicalCase(Base):
    __tablename__ = "surgical_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    case_ref: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    procedure: Mapped[str] = mapped_column(String(255), nullable=False)
    service_line: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    surgeon: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    facility_name: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    operating_room: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    vendor_name: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)

    supervisor_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supervisor_approved_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    supervisor_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Added for v4.5 Project Orbit's Surgical Timeline (Section 6) — the
    # terminal "Procedure Complete" step needed a real, independently-timed
    # record rather than a fabricated timestamp; additive nullable columns
    # on the existing case row rather than a second case-state table.
    procedure_completed_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    procedure_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class VendorTray(Base):
    __tablename__ = "or_connect_vendor_trays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    case_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tray_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tray_label: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    # blank/"" for a hospital-owned tray; a real vendor name scopes it to the
    # Vendor Collaboration Portal (Section 7) for that vendor only.
    vendor_name: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    is_vendor_tray: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    status: Mapped[str] = mapped_column(String(20), default=TRAY_REQUESTED, nullable=False, index=True)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    delivery_confirmed_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    delivery_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    replacement_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    replacement_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class RepairRequest(Base):
    __tablename__ = "or_connect_repair_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    case_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    inspection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    instrument_identity: Mapped[str] = mapped_column(String(300), default="", nullable=False, index=True)
    vendor_name: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)

    repair_type: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=REPAIR_PENDING, nullable=False, index=True)
    expected_return_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_return_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replacement_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    failure_category: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)


class CaseRiskAlert(Base):
    __tablename__ = "or_connect_risk_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    case_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    risk_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # Added for v4.5 Project Orbit's Readiness Alert Engine (Section 5):
    # "every alert includes recommended next actions" — additive nullable
    # column on the same alert row rather than a second alert table.
    recommended_action: Mapped[str] = mapped_column(Text, default="", nullable=False)

    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledged_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CaseNotification(Base):
    __tablename__ = "or_connect_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    case_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # A specific person if known, otherwise blank and recipient_role fans out
    # to everyone with that role — same idiom as WorkflowNotification.
    recipient_role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    recipient_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    message: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CaseReadinessScoreRecord(Base):
    __tablename__ = "or_connect_readiness_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    case_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    factors_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)
