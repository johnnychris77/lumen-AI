"""v4.2 — LumenAI OS: Project Pulse — Real-Time Operations Center &
Live Clinical Intelligence.

## Reuse map (researched before writing any of this file)

Pulse is the 12th cross-cutting sprint on this branch. Before adding a
single new table, the following was confirmed and is reused directly:

  * **Enterprise/Facility health scores** — `sentinel_dashboard_service.
    run_sentinel_health_snapshot` computes the one canonical
    `enterprise_risk_score`; Atlas's `atlas_dashboard_service.
    compute_facility_intelligence` already calls through to it rather
    than recomputing — Pulse composes both, it does not add a third
    score.
  * **AI health / drift** — `sentinel_ai_health_service.compute_ai_health`
    / `_detect_drift` already track confidence, supervisor agreement,
    false positive/negative rate, and a real (non-mock) drift detector.
    Pulse's AI Operations Monitor extends this with fields that
    genuinely don't exist yet (model version distribution, inference
    latency, confidence distribution — all computed from real
    `Inspection` rows) rather than re-deriving what already exists.
  * **Digital Twin health** — `digital_twin_engine.compute_twin_dashboard`.
  * **Education health** — `competency_service.technician_quality_dashboard`.
  * **Knowledge health** — `knowledge_graph_service.learning_confidence`.
  * **Event bus** — Nexus's `nexus_event_bus_service.publish`/
    `NexusEvent`/`NEXUS_EVENT_TYPES`, extended with five new event types
    this sprint's Live Event Stream needs that didn't already exist
    (`InspectionStarted`, `ImageUploaded`, `AIAnalysisCompleted`,
    `WorkflowExecuted`, `IntegrationSync`) — reused directly, not a
    second event bus.
  * **Workflow monitoring** — Forge's `WorkflowExecution`/
    `WorkflowApprovalInstance` (`app/models/workflow_forge.py`) already
    record execution status, decision path, and approval step state;
    Pulse's Live Workflow Monitoring composes and derives from these
    (current stage, waiting state, responsible user) rather than
    building a parallel execution-tracking table.
  * **Notification delivery** — `app/notifications/notifier.py` already
    has real, working Slack/Teams/Email dispatch functions, and Nexus's
    `nexus_event_bus_service._deliver_webhook` already does generic
    webhook delivery — both reused as-is for Pulse's Notification
    Center. SMS is a genuine gap (confirmed zero existing SMS code) and
    is implemented as an explicitly logged stub, never a fabricated send.
  * **Personalization pattern** — Genesis's `PlatformFavoriteModule`/
    `PlatformRecentModule` established the per-user personalization
    idiom this file's `PulseDashboardLayout` follows.
  * **GPU/CPU utilization** — confirmed nowhere in this codebase (the CV
    pipeline is deterministic, `CV_PROVIDER=mock` by default, no GPU
    runtime metric collection exists anywhere). Pulse's AI Operations
    Monitor reports this as `not_applicable` rather than fabricating a
    number — this system does not run GPU inference.

## The three new tables in this file

Nothing before Pulse modeled a real-time cross-cutting operational alert
(distinct from Atlas's system-scoped `EnterpriseAlert` narrative and
Sentinel's `ClinicalWatchlistEntry` entity-risk tracker — Pulse's alerts
carry evidence/confidence/recommendation/suggested-owner as first-class
fields), a reusable dashboard widget catalog, or a per-user Pulse
dashboard layout — these are the real gaps:

  * `PulseAlert` — a real-time operational alert (Section 5).
  * `PulseWidget` — the Command Widget catalog (Section 12).
  * `PulseDashboardLayout` — per-user widget arrangement (Section 12).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Section 5: Pulse Alert Engine alert types ───────────────────────────────
ALERT_CRITICAL_BLOOD_TREND = "critical_blood_trend"
ALERT_CORROSION_SPIKE = "corrosion_spike"
ALERT_AI_CONFIDENCE_DROP = "ai_confidence_drop"
ALERT_REPEATED_SUPERVISOR_OVERRIDES = "repeated_supervisor_overrides"
ALERT_MISSING_BASELINE = "missing_baseline"
ALERT_REPAIR_SURGE = "repair_surge"
ALERT_COVERAGE_DECLINE = "coverage_decline"
ALERT_KNOWLEDGE_GAP = "knowledge_gap"
PULSE_ALERT_TYPES = [
    ALERT_CRITICAL_BLOOD_TREND, ALERT_CORROSION_SPIKE, ALERT_AI_CONFIDENCE_DROP,
    ALERT_REPEATED_SUPERVISOR_OVERRIDES, ALERT_MISSING_BASELINE, ALERT_REPAIR_SURGE,
    ALERT_COVERAGE_DECLINE, ALERT_KNOWLEDGE_GAP,
]

ALERT_ACTIVE = "active"
ALERT_ACKNOWLEDGED = "acknowledged"
ALERT_RESOLVED = "resolved"
PULSE_ALERT_STATUSES = [ALERT_ACTIVE, ALERT_ACKNOWLEDGED, ALERT_RESOLVED]

# ── Section 3: Enterprise Command Map status colors ─────────────────────────
STATUS_GREEN = "green"
STATUS_YELLOW = "yellow"
STATUS_ORANGE = "orange"
STATUS_RED = "red"
STATUS_GRAY = "gray"
STATUS_COLORS = [STATUS_GREEN, STATUS_YELLOW, STATUS_ORANGE, STATUS_RED, STATUS_GRAY]

# ── Section 12: Command Widget catalog ──────────────────────────────────────
WIDGET_INSPECTION_COUNTER = "inspection_counter"
WIDGET_QUEUE_HEATMAP = "queue_heatmap"
WIDGET_FACILITY_STATUS = "facility_status"
WIDGET_AI_HEALTH = "ai_health"
WIDGET_KNOWLEDGE_GROWTH = "knowledge_growth"
WIDGET_DIGITAL_TWIN_STATUS = "digital_twin_status"
WIDGET_ENTERPRISE_ALERTS = "enterprise_alerts"
WIDGET_TREND_CHART = "trend_chart"
WIDGET_FORECAST_WIDGET = "forecast_widget"
WIDGET_TYPES = [
    WIDGET_INSPECTION_COUNTER, WIDGET_QUEUE_HEATMAP, WIDGET_FACILITY_STATUS, WIDGET_AI_HEALTH,
    WIDGET_KNOWLEDGE_GROWTH, WIDGET_DIGITAL_TWIN_STATUS, WIDGET_ENTERPRISE_ALERTS,
    WIDGET_TREND_CHART, WIDGET_FORECAST_WIDGET,
]

DISCLAIMER = (
    "LumenAI Pulse provides live situational awareness, predictive alerts, and operational "
    "recommendations for Sterile Processing leadership. Pulse does not replace human "
    "decision-making — every alert and score is decision support only, computed from real "
    "operational data, and requires human review before any operational or clinical action."
)


class PulseAlert(Base):
    """A real-time operational alert (Section 5) — distinct from Atlas's
    system-scoped `EnterpriseAlert` narrative and Sentinel's entity-risk
    `ClinicalWatchlistEntry`: this carries evidence/confidence/
    recommendation/suggested-owner as first-class fields."""

    __tablename__ = "pulse_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    facility_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    alert_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False, index=True)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_owner: Mapped[str] = mapped_column(String(100), default="", nullable=False)

    status: Mapped[str] = mapped_column(String(20), default=ALERT_ACTIVE, nullable=False, index=True)
    acknowledged_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PulseWidget(Base):
    """The Command Widget catalog (Section 12)."""

    __tablename__ = "pulse_widgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    widget_key: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    data_source: Mapped[str] = mapped_column(String(150), default="", nullable=False)


class PulseDashboardLayout(Base):
    """A user's personalized Pulse dashboard arrangement (Section 12) —
    follows the same per-user personalization idiom Genesis's
    `PlatformFavoriteModule`/`PlatformRecentModule` already established."""

    __tablename__ = "pulse_dashboard_layouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    layout_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # ordered [{widget_key, x, y, w, h}]
    is_mobile_layout: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
