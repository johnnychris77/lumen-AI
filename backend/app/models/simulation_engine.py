"""v2.5 — Project Sentinel: Predictive Simulation & Clinical Scenario Engine.

Evaluates multiple possible inspection dispositions (reclean, supervisor
override, repair evaluation, remove from service) before a recommendation is
made, so LumenAI can show *why* one path was chosen over the alternatives.
Remains advisory: every table carries `human_review_required` and a fixed
disclaimer, mirroring the P22 Digital Quality Twin governance pattern — no
scenario output here establishes causation or authorizes an autonomous
clinical decision.

Five additive tables:
  * SimulationRun — one row per scenario-analysis run for an inspection:
    the recommended scenario plus its reasoning/evidence snapshot.
  * ScenarioProjection — one row per evaluated scenario (A-D) within a run:
    likely consequence, rationale, and risk projection for that path.
  * WorkflowImpactProjection — one row per run: estimated effect on the
    inspection queue, OR readiness, repair backlog, and staff workload.
  * InstrumentHealthProjection — one row per physical instrument identity
    (barcode/UDI): health trend, corrosion/damage progression, and expected
    remaining service life.
  * ScenarioOutcome — Outcome Learning: predicted vs. actual disposition,
    for continuously calibrating the engine's recommendations.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Scenario keys (Section 2 — Decision Scenario Builder) ──────────────────
RECLEAN = "reclean"
SUPERVISOR_OVERRIDE = "supervisor_override"
REPAIR_EVALUATION = "repair_evaluation"
REMOVE_FROM_SERVICE = "remove_from_service"

SCENARIO_KEYS = [RECLEAN, SUPERVISOR_OVERRIDE, REPAIR_EVALUATION, REMOVE_FROM_SERVICE]

SCENARIO_LABELS = {
    RECLEAN: "Scenario A — Reclean",
    SUPERVISOR_OVERRIDE: "Scenario B — Supervisor Override",
    REPAIR_EVALUATION: "Scenario C — Repair Evaluation",
    REMOVE_FROM_SERVICE: "Scenario D — Remove From Service",
}

DISCLAIMER = (
    "Simulation output represents potential associations projected from historical inspection "
    "patterns for planning purposes only. It does not establish causation, predict a specific "
    "outcome, or constitute a clinical decision. Human review and approval are required before "
    "any operational or clinical action is taken."
)


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    inspection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    recommended_scenario: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    recommended_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    inputs_snapshot_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class ScenarioProjection(Base):
    __tablename__ = "scenario_projections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    simulation_run_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    inspection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    scenario_key: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    scenario_label: Mapped[str] = mapped_column(String(100), nullable=False)
    likely_consequence: Mapped[str] = mapped_column(Text, default="", nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Section 3 — Risk Projection
    quality_risk: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    operational_impact: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    repeat_inspection_probability: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    repair_likelihood: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    supervisor_workload_impact: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    is_recommended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class WorkflowImpactProjection(Base):
    __tablename__ = "workflow_impact_projections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    simulation_run_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    inspection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    scenario_key: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    # Section 4 — Workflow Impact Analysis
    inspection_queue_impact_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    or_readiness_impact: Mapped[str] = mapped_column(String(30), default="none", nullable=False)
    repair_backlog_impact: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    technician_workload_impact: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    supervisor_workload_impact: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    instrument_availability_impact: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    narrative: Mapped[str] = mapped_column(Text, default="", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class InstrumentHealthProjection(Base):
    __tablename__ = "instrument_health_projections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    # "barcode:<value>" or "udi:<value>" — matches instrument_condition_service's identity key.
    instrument_identity: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    instrument_type: Mapped[str] = mapped_column(String(100), default="unknown", nullable=False)

    # Section 5 — Instrument Health Projection
    health_trend: Mapped[str] = mapped_column(String(30), default="insufficient_data", nullable=False)
    corrosion_progression: Mapped[str] = mapped_column(String(30), default="none_detected", nullable=False)
    damage_progression: Mapped[str] = mapped_column(String(30), default="none_detected", nullable=False)
    inspection_frequency_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    repair_frequency_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_remaining_service_life_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class ScenarioOutcome(Base):
    """Section 8 — Outcome Learning: predicted vs. actual, for calibration."""
    __tablename__ = "scenario_outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    simulation_run_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, unique=True)
    inspection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    predicted_scenario: Mapped[str] = mapped_column(String(30), nullable=False)
    predicted_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    actual_disposition: Mapped[str | None] = mapped_column(String(50), nullable=True)
    actual_scenario: Mapped[str | None] = mapped_column(String(30), nullable=True)
    recorded_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    prediction_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    actual_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
