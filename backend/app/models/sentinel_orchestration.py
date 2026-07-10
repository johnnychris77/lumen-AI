"""v3.0 — Project Sentinel: Autonomous Clinical Intelligence Orchestration.

NOT to be confused with the earlier "Project Sentinel" (LumenAI Inspect
v2.5, `app/models/simulation_engine.py` — the Predictive Simulation &
Clinical Scenario Engine at `/scenario-analysis`). This is a distinct,
much broader module: a continuous enterprise monitoring layer that watches
inspections, Digital Twins, the Knowledge Graph, workflow, quality, and
enterprise KPIs to proactively surface risk. It is NOT autonomous clinical
decision-making — every signal, watchlist entry, alert, and recommendation
is advisory, explainable, and requires human validation.

Reuses rather than re-derives the risk/trend/scoring math that already
exists elsewhere in this codebase:
  * Recurring-pattern detection reuses `capa_suggestion_service`'s
    threshold/window idiom (`_REPEAT_THRESHOLD`, `_LOOKBACK_DAYS`).
  * AI health reuses `ml/pilot_validation.py`'s `clinical_metrics`/
    `confidence_calibration` (real confusion-matrix math from
    `SupervisorReview` rows), not a fourth reimplementation.
  * Knowledge confidence reuses `knowledge_graph_service.learning_confidence`.
  * The Enterprise Risk Score composes `quality_dashboard_service.
    executive_quality_score` as one input rather than re-deriving
    pass-rate/coverage/agreement math — see `sentinel_dashboard_service.py`
    for why it's a distinct, risk-framed composite rather than a third
    "overall score."

Six additive tables:
  * SentinelRiskSignal — Section 2, a detected recurring risk pattern.
  * ClinicalWatchlistEntry — Section 3, a dynamic high-risk entity flag.
  * DigitalTwinFlag — Section 5, a Monitor/Critical/Escalation tier for one
    physical instrument, derived from real `instrument_condition_history`.
  * SentinelAlert — Section 9, an explainable enterprise alert aggregating
    signals/watchlist/digital-twin/AI-health findings into one feed (no
    unified alert feed existed before this).
  * SentinelRecommendation — Section 8, a typed, reasoned recommended action.
  * SentinelHealthSnapshot — Sections 4/7, a periodic snapshot of AI health,
    Knowledge Graph growth, and the Enterprise Risk Score, for trending.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Section 2 — Continuous Risk Monitor signal types ───────────────────────
SIGNAL_REPEATED_BLOOD = "repeated_blood"
SIGNAL_REPEATED_RUST = "repeated_rust"
SIGNAL_REPEATED_BONE = "repeated_bone"
SIGNAL_REPEATED_CORROSION = "repeated_corrosion"
SIGNAL_REPEATED_DAMAGE = "repeated_damage"
SIGNAL_REPEATED_LOW_CONFIDENCE = "repeated_low_confidence"
SIGNAL_REPEATED_MISSING_COVERAGE = "repeated_missing_coverage"
SIGNAL_REPEATED_SUPERVISOR_OVERRIDES = "repeated_supervisor_overrides"
SIGNAL_REPEATED_REPAIR_REFERRALS = "repeated_repair_referrals"
RISK_SIGNAL_TYPES = [
    SIGNAL_REPEATED_BLOOD, SIGNAL_REPEATED_RUST, SIGNAL_REPEATED_BONE,
    SIGNAL_REPEATED_CORROSION, SIGNAL_REPEATED_DAMAGE, SIGNAL_REPEATED_LOW_CONFIDENCE,
    SIGNAL_REPEATED_MISSING_COVERAGE, SIGNAL_REPEATED_SUPERVISOR_OVERRIDES,
    SIGNAL_REPEATED_REPAIR_REFERRALS,
]

# ── Section 3 — Clinical Watchlist entity types ─────────────────────────────
WATCHLIST_INSTRUMENT = "instrument"
WATCHLIST_ANATOMY = "anatomy"
WATCHLIST_TRAY = "tray"
WATCHLIST_MANUFACTURER = "manufacturer"
WATCHLIST_VENDOR = "vendor"
WATCHLIST_SERVICE_LINE = "service_line"
WATCHLIST_FACILITY = "facility"
WATCHLIST_INSTRUMENT_FAMILY = "instrument_family"
WATCHLIST_ENTITY_TYPES = [
    WATCHLIST_INSTRUMENT, WATCHLIST_ANATOMY, WATCHLIST_TRAY, WATCHLIST_MANUFACTURER,
    WATCHLIST_VENDOR, WATCHLIST_SERVICE_LINE, WATCHLIST_FACILITY, WATCHLIST_INSTRUMENT_FAMILY,
]

# ── Section 5 — Digital Twin monitoring tiers ───────────────────────────────
TWIN_TIER_MONITOR = "monitor"
TWIN_TIER_CRITICAL = "critical"
TWIN_TIER_ESCALATION = "escalation"
TWIN_TIERS = [TWIN_TIER_MONITOR, TWIN_TIER_CRITICAL, TWIN_TIER_ESCALATION]

# ── Section 8 — Recommendation types ────────────────────────────────────────
RECOMMEND_CREATE_BASELINE = "create_baseline"
RECOMMEND_UPDATE_ANATOMY_PROFILE = "update_anatomy_profile"
RECOMMEND_REVIEW_COMPETENCY = "review_competency"
RECOMMEND_UPDATE_SOP = "update_sop"
RECOMMEND_REVIEW_IFU = "review_ifu"
RECOMMEND_EXPAND_KNOWLEDGE_GRAPH = "expand_knowledge_graph"
RECOMMEND_SCHEDULE_EDUCATION = "schedule_education"
RECOMMEND_REVIEW_DIGITAL_TWIN = "review_digital_twin"
SENTINEL_RECOMMENDATION_TYPES = [
    RECOMMEND_CREATE_BASELINE, RECOMMEND_UPDATE_ANATOMY_PROFILE, RECOMMEND_REVIEW_COMPETENCY,
    RECOMMEND_UPDATE_SOP, RECOMMEND_REVIEW_IFU, RECOMMEND_EXPAND_KNOWLEDGE_GRAPH,
    RECOMMEND_SCHEDULE_EDUCATION, RECOMMEND_REVIEW_DIGITAL_TWIN,
]

SEVERITIES = ["low", "medium", "high", "critical"]

DISCLAIMER = (
    "Project Sentinel continuously observes real inspection, Digital Twin, Knowledge Graph, "
    "workflow, and quality data to proactively surface risk before it reaches the operating room. "
    "This is decision support, not autonomous clinical decision-making — every signal, watchlist "
    "entry, alert, and recommendation is a potential association requiring human validation before "
    "any action is taken."
)


class SentinelRiskSignal(Base):
    __tablename__ = "sentinel_risk_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    signal_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    occurrences: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    window_days: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="", nullable=False)

    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ClinicalWatchlistEntry(Base):
    __tablename__ = "sentinel_watchlist_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    entity_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    entity_value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # active | resolved
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DigitalTwinFlag(Base):
    __tablename__ = "sentinel_digital_twin_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    instrument_identity: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    instrument_type: Mapped[str] = mapped_column(String(100), default="unknown", nullable=False)
    tier: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)

    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SentinelAlert(Base):
    __tablename__ = "sentinel_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    alert_ref: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    # risk_monitor | watchlist | ai_health | digital_twin | supervisor_intelligence
    source: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    related_signal_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False, index=True)

    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledged_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class SentinelRecommendation(Base):
    __tablename__ = "sentinel_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    recommendation_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    target_description: Mapped[str] = mapped_column(String(500), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)

    # open | actioned | dismissed
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)
    actioned_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    actioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class SentinelHealthSnapshot(Base):
    __tablename__ = "sentinel_health_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    # 0-100, higher = MORE risk (deliberately inverse framing from the
    # existing 0-100 executive_quality_score, where higher = better quality).
    enterprise_risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    ai_confidence_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    supervisor_agreement_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    false_positive_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    false_negative_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    coverage_quality_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_quality_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    kg_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    kg_sample_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    drift_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    drift_detail: Mapped[str] = mapped_column(Text, default="", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)
