"""v3.3 — Project Insight: Predictive Clinical Intelligence & Quality Forecasting.

Mission: forecast quality trends, operational risk, and instrument health
using historical inspections, Digital Twins, Knowledge Graph relationships,
enterprise analytics, and validated clinical data — assisting leaders in
proactive decision-making while preserving human authority over
operational and clinical actions.

## Extend, don't duplicate

This codebase already has substantial forecasting infrastructure Insight
composes rather than re-derives:

- **`app/services/prediction_engine.py`** (P7) already forecasts
  instrument failure probability (30/90/180-day), contamination
  recurrence, repair cost, recall/tray risk — with `EvidenceFactor` lists
  and a DB-aggregation-first / seeded-deterministic-fallback pattern.
  Insight's Instrument Failure Forecasting (Section 2) calls into this
  rather than re-deriving failure probability, and adds what P7 doesn't
  have: corrosion-progression / recurring-damage *trend* projection and
  instrument-level removal-from-service likelihood aggregated over time.
- **`app/services/digital_quality_twin_service.py`** (P22) already
  forecasts `projected_quality_score`/`projected_risk_level` at 30/60/90-
  day horizons (`QualityForecast`) with `association_reason` and a
  disclaimer. Insight's Predictive Digital Twin Analytics (Section 6)
  extends this with a 7-day and rolling-annual horizon and adds repair/
  retirement likelihood and a lifecycle risk tier, which P22 doesn't
  compute.
- **`app/services/finding_trend_service.py`** (v1.5) already buckets real
  `InspectionFinding` rows by daily/weekly/monthly/quarterly/yearly
  granularity across the 12-category finding taxonomy. Insight's Quality
  Trend Forecasting (Section 3) uses this as its historical time series
  and adds the actual forward projection (linear trend extrapolation)
  finding_trend_service doesn't do.
- **`app/services/competency_intelligence_service.py`** (Quality Guardian
  v2.9) already derives `CompetencyOpportunity` rows from supervisor-
  correction and image-quality-issue patterns. Insight's Predictive
  Education Engine (Section 4) calls this directly for those signal
  types and adds two genuinely new ones this codebase doesn't compute
  yet: a missed-anatomy-zone trend and a coverage-decline trend.
- **`app/services/atlas_report_service.py`** (Atlas v3.1) established the
  CSV (`csv.DictWriter`)/XLSX (`openpyxl.Workbook`)/PDF
  (`reportlab.pdfgen.canvas.Canvas`) export pattern this module reuses
  for Executive Forecast Reports (Section 9), all in-memory.

## Never fabricated

Every forecast in this module is computed from real historical rows
(`InspectionFinding`, `Inspection`, `SupervisorReview`, `RepairRequest`)
via deterministic trend math (`app/services/insight_forecast_math.py`) —
never a seeded-random mock. When a metric has too few historical data
points to fit a meaningful trend, the forecast reports
`"insufficient_data"` as a known limitation and a correspondingly low
confidence, rather than inventing a number — the same principle CLAUDE.md
and every prior sprint in this codebase has followed.

## Six additive tables

  * QualityTrendForecast — Section 3: one forecast per (tenant, metric,
    horizon), with historical series, confidence interval, and a full
    Section-10 explainability envelope.
  * OperationalForecast — Section 5: workload/demand/backlog/
    availability/peak-period forecasts.
  * InstrumentLifecycleForecast — Sections 2 & 6: per-instrument-type
    failure/corrosion/damage/retirement trajectory.
  * PredictiveEducationSignal — Section 4's two new signal types (the
    existing `CompetencyOpportunity` types are read directly, not
    duplicated into this table).
  * PredictiveRecommendation — Section 8: evidence/confidence/reasoning/
    suggested-action recommendations derived from the four forecast
    tables above.
  * ExecutiveForecastReport — Section 9: persisted report metadata +
    summary JSON, cadence-typed (weekly/monthly/quarterly/annual).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Horizons (Section 3, 5, 6) ──────────────────────────────────────────────
HORIZON_7_DAY = "7_day"
HORIZON_30_DAY = "30_day"
HORIZON_90_DAY = "90_day"
HORIZON_ROLLING_ANNUAL = "rolling_annual"
INSIGHT_HORIZONS = [HORIZON_7_DAY, HORIZON_30_DAY, HORIZON_90_DAY, HORIZON_ROLLING_ANNUAL]
HORIZON_DAYS = {HORIZON_7_DAY: 7, HORIZON_30_DAY: 30, HORIZON_90_DAY: 90, HORIZON_ROLLING_ANNUAL: 365}

# ── Quality trend metrics (Section 3) ───────────────────────────────────────
METRIC_BLOOD = "blood"
METRIC_BONE = "bone"
METRIC_DEBRIS = "debris"
METRIC_RUST = "rust"
METRIC_CORROSION = "corrosion"
METRIC_DAMAGE = "damage"
METRIC_COVERAGE_COMPLIANCE = "coverage_compliance"
METRIC_SUPERVISOR_WORKLOAD = "supervisor_workload"
METRIC_INSPECTION_THROUGHPUT = "inspection_throughput"
QUALITY_TREND_METRICS = [
    METRIC_BLOOD, METRIC_BONE, METRIC_DEBRIS, METRIC_RUST, METRIC_CORROSION, METRIC_DAMAGE,
    METRIC_COVERAGE_COMPLIANCE, METRIC_SUPERVISOR_WORKLOAD, METRIC_INSPECTION_THROUGHPUT,
]
# Metrics where an *increasing* trend is the adverse direction (used by the
# recommendation engine to decide which direction warrants a flag).
ADVERSE_WHEN_INCREASING = {METRIC_BLOOD, METRIC_BONE, METRIC_DEBRIS, METRIC_RUST, METRIC_CORROSION, METRIC_DAMAGE, METRIC_SUPERVISOR_WORKLOAD}
ADVERSE_WHEN_DECREASING = {METRIC_COVERAGE_COMPLIANCE}

TREND_INCREASING = "increasing"
TREND_DECREASING = "decreasing"
TREND_STABLE = "stable"
TREND_DIRECTIONS = [TREND_INCREASING, TREND_DECREASING, TREND_STABLE]

# ── Operational forecasts (Section 5) ───────────────────────────────────────
FORECAST_INSPECTION_WORKLOAD = "inspection_workload"
FORECAST_SUPERVISOR_REVIEW_DEMAND = "supervisor_review_demand"
FORECAST_REPAIR_BACKLOG = "repair_backlog"
FORECAST_INSTRUMENT_AVAILABILITY = "instrument_availability"
FORECAST_HIGH_RISK_PROCEDURE_PREP = "high_risk_procedure_prep"
FORECAST_PEAK_INSPECTION_PERIODS = "peak_inspection_periods"
OPERATIONAL_FORECAST_TYPES = [
    FORECAST_INSPECTION_WORKLOAD, FORECAST_SUPERVISOR_REVIEW_DEMAND, FORECAST_REPAIR_BACKLOG,
    FORECAST_INSTRUMENT_AVAILABILITY, FORECAST_HIGH_RISK_PROCEDURE_PREP, FORECAST_PEAK_INSPECTION_PERIODS,
]

# ── Instrument lifecycle (Sections 2 & 6) ───────────────────────────────────
LIFECYCLE_RISK_LOW = "low"
LIFECYCLE_RISK_MODERATE = "moderate"
LIFECYCLE_RISK_HIGH = "high"
LIFECYCLE_RISK_CRITICAL = "critical"
LIFECYCLE_RISK_TIERS = [LIFECYCLE_RISK_LOW, LIFECYCLE_RISK_MODERATE, LIFECYCLE_RISK_HIGH, LIFECYCLE_RISK_CRITICAL]

# ── Predictive education (Section 4) ────────────────────────────────────────
SCOPE_TECHNICIAN = "technician"
SCOPE_DEPARTMENT = "department"
EDUCATION_SCOPE_TYPES = [SCOPE_TECHNICIAN, SCOPE_DEPARTMENT]

SIGNAL_MISSED_ANATOMY_ZONE_TREND = "missed_anatomy_zone_trend"
SIGNAL_COVERAGE_DECLINE_TREND = "coverage_decline_trend"
EDUCATION_SIGNAL_TYPES = [SIGNAL_MISSED_ANATOMY_ZONE_TREND, SIGNAL_COVERAGE_DECLINE_TREND]

# ── Recommendations (Section 8) ─────────────────────────────────────────────
RECOMMENDATION_QUALITY_TREND = "quality_trend_action"
RECOMMENDATION_OPERATIONAL_CAPACITY = "operational_capacity_action"
RECOMMENDATION_INSTRUMENT_LIFECYCLE = "instrument_lifecycle_action"
RECOMMENDATION_EDUCATION = "education_action"
RECOMMENDATION_TYPES = [
    RECOMMENDATION_QUALITY_TREND, RECOMMENDATION_OPERATIONAL_CAPACITY,
    RECOMMENDATION_INSTRUMENT_LIFECYCLE, RECOMMENDATION_EDUCATION,
]
RECOMMENDATION_STATUSES = ["open", "actioned", "dismissed"]

# ── Executive forecast reports (Section 9) ──────────────────────────────────
CADENCE_WEEKLY = "weekly"
CADENCE_MONTHLY = "monthly"
CADENCE_QUARTERLY = "quarterly"
CADENCE_ANNUAL = "annual"
REPORT_CADENCES = [CADENCE_WEEKLY, CADENCE_MONTHLY, CADENCE_QUARTERLY, CADENCE_ANNUAL]

DISCLAIMER = (
    "Project Insight forecasts are modeled projections computed from real historical inspection, Digital Twin, "
    "and quality data — never fabricated when data is insufficient, in which case the forecast reports that "
    "limitation explicitly. Every forecast is a potential association for leadership awareness, not a causal or "
    "clinical determination; human review governs any resulting action, and forecasts do not replace operational "
    "or clinical decision-making."
)


class QualityTrendForecast(Base):
    """Section 3: a forward projection for one quality metric at one horizon."""
    __tablename__ = "insight_quality_trend_forecasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    metric: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    horizon: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    historical_series_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    forecast_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    trend_direction: Mapped[str] = mapped_column(String(20), default=TREND_STABLE, nullable=False)

    data_sources_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    contributing_factors_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    historical_comparison_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    known_limitations_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class OperationalForecast(Base):
    """Section 5: workload/demand/backlog/availability/peak-period forecasts."""
    __tablename__ = "insight_operational_forecasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    forecast_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    horizon: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    forecast_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    forecast_detail_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    confidence_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    data_sources_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    contributing_factors_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    known_limitations_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class InstrumentLifecycleForecast(Base):
    """Sections 2 & 6: per-instrument-type failure/corrosion/damage/retirement trajectory."""
    __tablename__ = "insight_instrument_lifecycle_forecasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    instrument_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    corrosion_progression_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    recurring_damage_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    repair_recurrence_likelihood: Mapped[float | None] = mapped_column(Float, nullable=True)
    removal_from_service_likelihood: Mapped[float | None] = mapped_column(Float, nullable=True)

    health_score_trajectory_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    repair_likelihood: Mapped[float | None] = mapped_column(Float, nullable=True)
    retirement_likelihood: Mapped[float | None] = mapped_column(Float, nullable=True)
    lifecycle_risk_tier: Mapped[str] = mapped_column(String(20), default=LIFECYCLE_RISK_LOW, nullable=False, index=True)

    confidence_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    data_sources_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    known_limitations_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class PredictiveEducationSignal(Base):
    """Section 4's two new signal types — existing CompetencyOpportunity types
    are read directly from competency_intelligence_service, not duplicated here."""
    __tablename__ = "insight_predictive_education_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    scope_type: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    signal_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    trend_direction: Mapped[str] = mapped_column(String(20), default=TREND_STABLE, nullable=False)
    confidence_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    evidence_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    recommendation_text: Mapped[str] = mapped_column(Text, default="", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class PredictiveRecommendation(Base):
    """Section 8: evidence/confidence/reasoning/suggested-action recommendations."""
    __tablename__ = "insight_predictive_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    recommendation_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    confidence_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_action: Mapped[str] = mapped_column(Text, nullable=False)

    source_type: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)
    actioned_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    actioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class ExecutiveForecastReport(Base):
    """Section 9: cadence-typed executive forecast report."""
    __tablename__ = "insight_executive_forecast_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    report_ref: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    cadence: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    period_label: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    generated_by: Mapped[str] = mapped_column(String(255), default="system", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)
