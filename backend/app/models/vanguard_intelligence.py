"""v4.6 — LumenAI OS: Project Vanguard — Healthcare Executive
Intelligence & Strategic Decision Platform.

## Naming disambiguation (read this first)

Before writing any Vanguard code, every existing "executive"/"board"/
"governance" surface in this codebase was read in full. Several already
use names Vanguard's brief also uses — none of them are what Vanguard
needs, for the reasons below:

  * **`/api/executive/dashboard/{role}`** (`app/routes/executive.py`) —
    a pre-existing role-KPI endpoint whose own response labels most of
    its output `"data_source": "mock"` (seeded `random.Random` values for
    every role except a rough, hard-coded ROI formula for `cfo`). This is
    not real computed data and is not a foundation Vanguard's Executive
    Scorecards can build on without inheriting fabrication. Vanguard's
    scorecards are mounted at a different prefix (`/api/vanguard`) and
    compute every figure from real rows.
  * **`/api/enterprise/governance-intelligence`**
    (`app/routes/governance_intelligence.py`) — every score in its
    `/summary` response (92, 88, 86, 90) is a **literal hard-coded
    integer** in the route function, not computed from any table. This
    is a genuinely fabricated pre-existing surface. Vanguard's Governance
    Dashboard does not read from or extend this endpoint.
  * **`/api/board-reporting`** (`app/routes/board_reporting.py`) — a
    real, single-fixed-shape weekly report (CSV/XLSX/ZIP) over raw
    `Inspection` rows, with no audience/cadence typing. Vanguard's Board
    Reporting instead extends the audience/cadence-typed
    `atlas_report_service.generate_executive_report`, which already has
    the right shape (`REPORT_AUDIENCES`, `REPORT_CADENCES`) — just no
    PowerPoint export yet.
  * **`benchmark_engine.generate_board_report`** — a second, older,
    CVInferenceRecord-based enterprise rollup lineage (with a
    mock-data-when-`db=None` fallback), parallel to Atlas's real-only
    `atlas_dashboard_service`/`atlas_benchmarking_service` lineage.
    Vanguard composes the Atlas lineage, not this one, so this sprint
    does not create a third parallel rollup.
  * **`portfolio_briefings.py`** — LumenAI's own SaaS customer-portfolio
    board briefing (tenant churn/renewal risk), a completely different
    audience (LumenAI's own leadership, not the hospital's). Not reused,
    not renamed around.

## Reuse map

  * **Enterprise Readiness / Risk / AI Health / Knowledge Growth** —
    `pulse_command_center_service.pulse_command_center`.
  * **Surgical Readiness** — `orbit_executive_service.executive_surgical_operations`.
  * **SPD Quality** — `atlas_dashboard_service.enterprise_dashboard`.
  * **Financial Impact** — `prediction_engine.compute_predictive_dashboard`
    (already computes real `estimated_repair_cost_usd`/
    `estimated_replacement_cost_usd`-based projections and repair-avoidance).
  * **Enterprise Benchmarking (facilities)** —
    `atlas_benchmarking_service.cross_facility_benchmark`.
  * **Board Reporting base** — `atlas_report_service.generate_executive_report`
    plus a new PowerPoint exporter (this sprint), following the same
    `python-pptx` `Presentation()` pattern already used by
    `leadership_packet_exports.py`/`governance_packet_exports.py`.
  * **Executive AI Advisor** — new intents added directly to
    `catalyst_query_engine.py`'s existing deterministic classifier
    (never a second NL engine).
  * **Governance Dashboard** — `governance_command_center.command_center_summary`
    (workflow compliance), `accreditation_engine.compute_regulatory_dashboard`
    (audit readiness), `knowledge_graph_service.learning_confidence`
    (knowledge adoption).

## Genuinely new tables in this file

  * `ExecutiveScorecardSnapshot` — a persisted scorecard snapshot per
    audience (trend history, never re-derived from scratch on read).
  * `BoardReportPacket` — a persisted board packet (one of four named
    types), the export-ready superset atlas_report_service's own
    per-audience report doesn't cover on its own.
  * `StrategicInitiative` — a Strategic Planning Workspace item.
  * `EnterpriseBenchmarkSnapshot` — a persisted benchmark snapshot across
    the six named comparison dimensions.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Section 2: Executive Scorecard audiences ─────────────────────────────────
AUDIENCE_CEO = "ceo"
AUDIENCE_COO = "coo"
AUDIENCE_CNO = "cno"
AUDIENCE_CMO = "cmo"
AUDIENCE_VP_SURGICAL_SERVICES = "vp_surgical_services"
AUDIENCE_QUALITY = "quality"
AUDIENCE_SUPPLY_CHAIN = "supply_chain"
AUDIENCE_SPD_DIRECTOR = "spd_director"
SCORECARD_AUDIENCES = [
    AUDIENCE_CEO, AUDIENCE_COO, AUDIENCE_CNO, AUDIENCE_CMO, AUDIENCE_VP_SURGICAL_SERVICES,
    AUDIENCE_QUALITY, AUDIENCE_SUPPLY_CHAIN, AUDIENCE_SPD_DIRECTOR,
]

# ── Section 7: Board Reporting packet types ──────────────────────────────────
PACKET_MONTHLY_BOARD = "monthly_board_packet"
PACKET_QUARTERLY_REVIEW = "quarterly_executive_review"
PACKET_ANNUAL_STRATEGIC = "annual_strategic_report"
PACKET_QUALITY_COMMITTEE = "quality_committee_report"
BOARD_PACKET_TYPES = [PACKET_MONTHLY_BOARD, PACKET_QUARTERLY_REVIEW, PACKET_ANNUAL_STRATEGIC, PACKET_QUALITY_COMMITTEE]

EXPORT_PDF = "pdf"
EXPORT_PPTX = "pptx"
EXPORT_XLSX = "xlsx"
EXPORT_FORMATS = [EXPORT_PDF, EXPORT_PPTX, EXPORT_XLSX]

# ── Section 5: Strategic Planning initiative types ───────────────────────────
INITIATIVE_SCENARIO_PLANNING = "scenario_planning"
INITIATIVE_CAPITAL_PLANNING = "capital_planning"
INITIATIVE_QUALITY = "quality_initiative"
INITIATIVE_SERVICE_LINE_EXPANSION = "service_line_expansion"
INITIATIVE_CAPACITY_PLANNING = "capacity_planning"
STRATEGIC_INITIATIVE_TYPES = [
    INITIATIVE_SCENARIO_PLANNING, INITIATIVE_CAPITAL_PLANNING, INITIATIVE_QUALITY,
    INITIATIVE_SERVICE_LINE_EXPANSION, INITIATIVE_CAPACITY_PLANNING,
]

INITIATIVE_DRAFT = "draft"
INITIATIVE_UNDER_REVIEW = "under_review"
INITIATIVE_APPROVED = "approved"
INITIATIVE_ARCHIVED = "archived"
INITIATIVE_STATUSES = [INITIATIVE_DRAFT, INITIATIVE_UNDER_REVIEW, INITIATIVE_APPROVED, INITIATIVE_ARCHIVED]

# ── Section 8: Enterprise Benchmarking dimensions ────────────────────────────
BENCHMARK_FACILITIES = "facilities"
BENCHMARK_MARKETS = "markets"
BENCHMARK_SERVICE_LINES = "service_lines"
BENCHMARK_INSPECTION_PROGRAMS = "inspection_programs"
BENCHMARK_INSTRUMENT_HEALTH = "instrument_health"
BENCHMARK_KNOWLEDGE_MATURITY = "knowledge_maturity"
BENCHMARK_TYPES = [
    BENCHMARK_FACILITIES, BENCHMARK_MARKETS, BENCHMARK_SERVICE_LINES,
    BENCHMARK_INSPECTION_PROGRAMS, BENCHMARK_INSTRUMENT_HEALTH, BENCHMARK_KNOWLEDGE_MATURITY,
]

DISCLAIMER = (
    "LumenAI Vanguard composes real, already-computed intelligence from across the platform "
    "into executive-facing views — it does not compute a second copy of any score, and it does "
    "not fabricate financial, clinical, or operational figures the platform does not actually "
    "observe. Every dashboard, scorecard, and report is decision support only and requires "
    "human review before any strategic, financial, or clinical action."
)


class ExecutiveScorecardSnapshot(Base):
    """A persisted scorecard snapshot for one audience (Section 2) —
    trend history, never re-derived from scratch."""

    __tablename__ = "vanguard_scorecard_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    audience: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    facility_id: Mapped[str] = mapped_column(String(100), default="", nullable=False)

    kpis_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class BoardReportPacket(Base):
    """A persisted board reporting packet (Section 7)."""

    __tablename__ = "vanguard_board_report_packets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    packet_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    generated_by: Mapped[str] = mapped_column(String(255), default="system", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class StrategicInitiative(Base):
    """A Strategic Planning Workspace item (Section 5)."""

    __tablename__ = "vanguard_strategic_initiatives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    initiative_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=INITIATIVE_DRAFT, nullable=False, index=True)
    details_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class EnterpriseBenchmarkSnapshot(Base):
    """A persisted benchmark comparison snapshot (Section 8)."""

    __tablename__ = "vanguard_benchmark_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    benchmark_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    results_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)
