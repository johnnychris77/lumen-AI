"""v4.5 — LumenAI OS: Project Orbit — Perioperative Intelligence &
Surgical Readiness Platform.

## Naming disambiguation (read this first)

Two existing systems already use the phrase "surgical readiness" before
this sprint:

  * **P25's `SurgicalReadinessScore`** (`app/models/p25_infrastructure.py`,
    table `p25_readiness_scores`, mounted at `/api/infrastructure`) — an
    *instrument-quality* readiness index scoped to facility/tray/
    enterprise (instrument availability, contamination status, inspection
    compliance, CAPA backlog health, sterilization cycle compliance).
  * **`frontend/src/pages/SurgicalReadinessDashboard.tsx`** at the
    frontend route `/surgical-readiness` — a thin, mostly client-side
    demo page (heuristic scoring over `/api/analytics/kpi-summary`,
    `/api/baseline-library`, `/api/infrastructure/instruments`, with a
    hard-coded demo tray table and fabricated fallback numbers on fetch
    failure).

Orbit's "Surgical Readiness Score" is a **different axis entirely** — it
is *per scheduled case*, spanning Patient Procedure → Case Cart →
Instrument Trays → Individual Instruments → Implants → Equipment → Staff
→ Environmental → Clinical readiness — not instrument-quality scoped.
To avoid conflating the two:

  * Orbit's backend API is mounted at `/api/orbit` (never
    `/api/infrastructure`, which stays P25's).
  * The existing `/surgical-readiness` frontend route is **kept** (its
    prior page was thin/decorative, not a real backend-driven system) and
    rewritten in place to be Orbit's real, case-scoped dashboard — this is
    a conscious replacement, not an accidental overwrite.
  * P25's `SurgicalReadinessScore` is left completely untouched and is
    reused as one *input* to Orbit's `individual_instrument_score`
    dimension where a facility-level P25 score is available, never
    recomputed a second way.

## "Project Helix" — does not exist in this codebase

Orbit's brief asks for a "Readiness Simulation" capability "using Project
Helix." A repository-wide, case-insensitive search for "helix" before
writing this file returned zero matches — no such system exists anywhere
in this codebase. Rather than fabricate a fake integration with a
nonexistent system, `orbit_simulation_service.py` (this sprint) implements
the readiness-simulation capability as new code, extending the same
case-scoped pattern Sentinel's single-inspection `simulation_engine_service.py`
already established (`generate_scenarios`, `project_workflow_impact`) up to
case/OR scope. See `docs/orbit/readiness-engine.md` for the full note.

## Reuse map

  * **Case identity, vendor trays, repairs, risk alerts, notifications,
    readiness score history, timeline, executive dashboard** —
    `app/models/or_connect.py` (`SurgicalCase`, `VendorTray`,
    `RepairRequest`, `CaseRiskAlert`, `CaseNotification`,
    `CaseReadinessScoreRecord`) and `or_connect_service.py`
    (`compute_case_readiness_score`, `build_case_timeline`,
    `detect_operational_risks`, `executive_dashboard`) — Orbit's every new
    table below FKs to `SurgicalCase.id` rather than inventing a second
    "scheduled case" concept. `RISK_TYPES` and `STAKEHOLDER_ROLES` in
    `or_connect.py` were extended (not duplicated) for Orbit's new alert
    types and the three additional coordinating departments.
  * **Procedure Knowledge** — `app/models/knowledge.py`'s
    `KnowledgeArticle` already has `procedure`/`specialty`/`anatomy_zone`/
    `applicable_instruments`/`applicable_findings`/`applicable_manufacturers`
    fields; Orbit's Procedure Knowledge queries these directly rather than
    creating a second procedure-knowledge table.
  * **Digital Twin status** — `digital_twin_engine.compute_twin_dashboard`.
  * **Anatomy/failure-mode knowledge** — `anatomy_risk_service`,
    `knowledge_graph_service.reasoning_chain`.

## Genuinely new tables in this file

Nothing before Orbit modeled a case cart, an implant, loaner (non-tray)
equipment, per-staff case readiness, environmental/OR-room readiness, a
composite multi-dimension readiness snapshot, or a case-scoped what-if
simulation run — confirmed real gaps:

  * `CaseCart` — one case cart per case, assembly/verification status.
  * `ImplantRecord` — implants required/available for a case.
  * `LoanerEquipment` — non-tray loaner equipment (scopes/powered devices),
    reusing `or_connect.py`'s tray lifecycle vocabulary
    (`TRAY_REQUESTED`/`TRAY_SHIPPED`/`TRAY_RECEIVED`/`TRAY_RETURNED`)
    since the lifecycle semantics are identical.
  * `StaffReadinessRecord` — per-staff assignment/competency status for a case.
  * `EnvironmentalReadinessRecord` — OR-room environmental checklist.
  * `SurgicalReadinessSnapshot` — the persisted 9-dimension composite score.
  * `ReadinessSimulationRun` — a persisted case-scoped what-if projection.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Case Cart lifecycle ──────────────────────────────────────────────────────
CART_NOT_STARTED = "not_started"
CART_ASSEMBLING = "assembling"
CART_ASSEMBLED = "assembled"
CART_VERIFIED = "verified"
CART_COMPLETE = "complete"
CART_STATUSES = [CART_NOT_STARTED, CART_ASSEMBLING, CART_ASSEMBLED, CART_VERIFIED, CART_COMPLETE]

# ── Implant availability ─────────────────────────────────────────────────────
IMPLANT_AVAILABLE = "available"
IMPLANT_BACKORDERED = "backordered"
IMPLANT_MISSING = "missing"
IMPLANT_VERIFIED = "verified"
IMPLANT_STATUSES = [IMPLANT_AVAILABLE, IMPLANT_BACKORDERED, IMPLANT_MISSING, IMPLANT_VERIFIED]

# ── Staff competency status ──────────────────────────────────────────────────
STAFF_READY = "ready"
STAFF_NEEDS_REVIEW = "needs_review"
STAFF_NOT_ASSIGNED = "not_assigned"
STAFF_STATUSES = [STAFF_READY, STAFF_NEEDS_REVIEW, STAFF_NOT_ASSIGNED]

# ── Simulation scenario types (Section 9) ────────────────────────────────────
SCENARIO_CASE_TIME_SHIFT = "case_time_shift"
SCENARIO_INSTRUMENT_UNAVAILABLE = "instrument_unavailable"
SCENARIO_VENDOR_TRAY_DELAYED = "vendor_tray_delayed"
SIMULATION_SCENARIO_TYPES = [SCENARIO_CASE_TIME_SHIFT, SCENARIO_INSTRUMENT_UNAVAILABLE, SCENARIO_VENDOR_TRAY_DELAYED]

DISCLAIMER = (
    "LumenAI Orbit provides perioperative readiness intelligence centered on instrument "
    "inspection, quality, and operational coordination. It does not replace OR scheduling, "
    "sterilization management, or EHR systems, and it does not make autonomous clinical or "
    "operational decisions. Every readiness score, alert, and simulation is decision support "
    "only and requires human review before any operational action."
)


class CaseCart(Base):
    """One case cart per `SurgicalCase` (Section 1 — Case Cart dimension)."""

    __tablename__ = "orbit_case_carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    case_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(20), default=CART_NOT_STARTED, nullable=False, index=True)
    item_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    verified_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    verified_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class ImplantRecord(Base):
    """An implant required for a `SurgicalCase` (Section 1 — Implants dimension)."""

    __tablename__ = "orbit_implant_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    case_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    implant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    lot_number: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=IMPLANT_AVAILABLE, nullable=False, index=True)
    sterility_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LoanerEquipment(Base):
    """Non-tray loaner equipment (powered devices, scopes) for a
    `SurgicalCase` (Section 1 — Equipment dimension). Reuses `or_connect.py`'s
    tray lifecycle vocabulary (`TRAY_REQUESTED`/`TRAY_SHIPPED`/
    `TRAY_RECEIVED`/`TRAY_RETURNED`) since the lifecycle semantics are
    identical to a vendor tray's."""

    __tablename__ = "orbit_loaner_equipment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    case_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    equipment_name: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor_name: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="requested", nullable=False, index=True)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StaffReadinessRecord(Base):
    """A staff assignment/competency status for a `SurgicalCase` (Section 1
    — Staff Readiness dimension)."""

    __tablename__ = "orbit_staff_readiness"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    case_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    staff_name: Mapped[str] = mapped_column(String(255), nullable=False)
    staff_role: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=STAFF_NOT_ASSIGNED, nullable=False, index=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class EnvironmentalReadinessRecord(Base):
    """An OR-room environmental readiness check for a `SurgicalCase`
    (Section 1 — Environmental Readiness dimension). This is a checklist
    LumenAI records, not a facilities/BMS integration this codebase has —
    checklist fields are honestly self-reported/manually verified."""

    __tablename__ = "orbit_environmental_readiness"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    case_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    operating_room: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    room_turnover_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    equipment_calibrated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supplies_stocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class SurgicalReadinessSnapshot(Base):
    """The persisted 9-dimension composite Surgical Readiness Score for a
    `SurgicalCase` (Section 1) — a trend-history snapshot, following the
    same idiom as `CaseReadinessScoreRecord` (never re-derived from
    history, only appended to)."""

    __tablename__ = "orbit_readiness_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    case_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    patient_procedure_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    case_cart_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    instrument_tray_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    individual_instrument_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    implant_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    equipment_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    staff_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    environmental_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    clinical_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    factors_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class ReadinessSimulationRun(Base):
    """A persisted case-scoped what-if readiness simulation (Section 9).
    Genuinely new — no prior "Project Helix" system exists in this
    codebase (confirmed by repository-wide search); this extends Sentinel's
    single-inspection `simulation_engine_service.py` pattern up to case
    scope rather than reusing or fabricating a different prior system."""

    __tablename__ = "orbit_simulation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    case_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    scenario_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    scenario_params_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    projected_impact_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)
