"""LumenAI AI Specialist — Project Sentinel-X: Clinical Risk Intelligence &
Patient Safety Agent.

## Naming disambiguation (read this first)

**"Sentinel" already exists as a major, unrelated system in this codebase**
-- "Project Sentinel" v3.0 ("Autonomous Clinical Intelligence Orchestration"):
`app/models/sentinel_orchestration.py` (`SentinelRiskSignal`,
`ClinicalWatchlistEntry`, `DigitalTwinFlag`, `SentinelAlert`,
`SentinelRecommendation`, `SentinelHealthSnapshot`), routes at
`/api/sentinel`, frontend route `/sentinel`, and nine `sentinel_*.py`
services. Project Sentinel-X (this file) is a **different, newer sprint**
and deliberately uses a distinct `sentinelx_` file/model/route prefix
(`/api/sentinelx`) everywhere to avoid any collision or confusion with that
established system -- it never touches or duplicates `sentinel_
orchestration.py`'s tables. The brief's own frontend route (`/risk`) is
used as-is since it does not collide with `/sentinel`.

## What Sentinel-X composes rather than duplicates

  * **Instrument reliability** — `vulcan_reliability_agent_service.
    run_reliability_assessment` / `VulcanReliabilityAssessment`
    (`reliability_score`, `progression`, `recurrence_count`,
    `failure_category`, `anatomy_zone`).
  * **Process variation** — `vulcan_aegis_integration_service.
    compute_process_variation_signal`.
  * **Evidence readiness** — `veritas_evidence_agent_service.
    run_evidence_assessment` / `VeritasEvidenceReadinessAssessment`
    (`readiness_score`, `readiness_category`, `coverage_status`,
    `image_quality_status`).
  * **Education/competency gaps** — `sage_gap_detection_service`/
    `sage_knowledge_gap_service` (repeated corrections/errors as a
    workflow-risk signal).
  * **Digital Twin condition** — the real per-instrument condition trend
    lives in `instrument_condition_service.instrument_condition_history`
    (`condition_trend`: improving/stable/declining/insufficient_data) --
    *not* `digital_twin_engine.py`, which tracks SPD workflow/throughput
    twins, a different concept. Sentinel-X reads `condition_trend` directly
    rather than re-deriving instrument condition.
  * **Knowledge confidence** — `knowledge_graph_service.learning_confidence`
    (`knowledge_confidence`/`clinical_recommendation_confidence`, derived
    live from `SupervisorReview`).
  * **Per-finding data** — `InspectionFinding` (finding_type, zone,
    severity_index), the same shared log Vulcan/Sage/Veritas already read.

## What is genuinely new in this file

Three tables: `SentinelXRiskAssessment` (the composite risk assessment),
`SentinelXPatientSafetyAlert` (proactive alerts, Section 5 -- distinct from
the existing `SentinelAlert` table), `SentinelXSupervisorOverride` (Section
10/13 auditable supervisor overrides).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Section 2: Risk Taxonomy ─────────────────────────────────────────────────
RISK_CATEGORY_PATIENT_SAFETY = "patient_safety"
RISK_CATEGORY_CLINICAL_QUALITY = "clinical_quality"
RISK_CATEGORY_INSPECTION_QUALITY = "inspection_quality"
RISK_CATEGORY_INSTRUMENT_INTEGRITY = "instrument_integrity"
RISK_CATEGORY_WORKFLOW = "workflow"
RISK_CATEGORY_OPERATIONAL = "operational"
RISK_CATEGORY_EDUCATION = "education"
RISK_CATEGORY_COMPLIANCE = "compliance"
RISK_CATEGORY_ENTERPRISE = "enterprise"
RISK_CATEGORIES = [
    RISK_CATEGORY_PATIENT_SAFETY, RISK_CATEGORY_CLINICAL_QUALITY, RISK_CATEGORY_INSPECTION_QUALITY,
    RISK_CATEGORY_INSTRUMENT_INTEGRITY, RISK_CATEGORY_WORKFLOW, RISK_CATEGORY_OPERATIONAL,
    RISK_CATEGORY_EDUCATION, RISK_CATEGORY_COMPLIANCE, RISK_CATEGORY_ENTERPRISE,
]

# ── Section 3: SPD Risk Matrix (per-finding-type weight tiers) ───────────────
RISK_WEIGHT_HIGHEST = "highest"
RISK_WEIGHT_MEDIUM = "medium"
RISK_WEIGHT_LOW = "low"

# Real finding_type strings (this codebase's actual CV/taxonomy vocabulary --
# see baseline_comparison_scoring_service.KPI_LABELS and
# vulcan_reliability.FAILURE_TAXONOMY) mapped onto the brief's three tiers.
SPD_RISK_MATRIX: dict[str, str] = {
    "blood": RISK_WEIGHT_HIGHEST,
    "bone": RISK_WEIGHT_HIGHEST,
    "tissue": RISK_WEIGHT_HIGHEST,
    "other_organic_residue": RISK_WEIGHT_HIGHEST,
    "debris": RISK_WEIGHT_HIGHEST,
    "corrosion": RISK_WEIGHT_HIGHEST,
    "rust": RISK_WEIGHT_HIGHEST,
    "crack": RISK_WEIGHT_HIGHEST,
    "insulation_damage": RISK_WEIGHT_HIGHEST,
    "insulation_breach": RISK_WEIGHT_HIGHEST,
    "missing_component": RISK_WEIGHT_HIGHEST,
    "damaged_o_ring": RISK_WEIGHT_HIGHEST,
    "obstruction": RISK_WEIGHT_HIGHEST,
    "wear": RISK_WEIGHT_MEDIUM,
    "worn_cutting_edge": RISK_WEIGHT_MEDIUM,
    "pitting": RISK_WEIGHT_MEDIUM,
    "loose_joint": RISK_WEIGHT_MEDIUM,
    "damaged_hinge": RISK_WEIGHT_MEDIUM,
    "damaged_ratchet": RISK_WEIGHT_MEDIUM,
    "discoloration": RISK_WEIGHT_LOW,
    "staining": RISK_WEIGHT_LOW,
    "surface_degradation": RISK_WEIGHT_LOW,
}

_RISK_WEIGHT_VALUE = {RISK_WEIGHT_HIGHEST: 3, RISK_WEIGHT_MEDIUM: 2, RISK_WEIGHT_LOW: 1}


def spd_risk_weight(finding_type: str) -> str:
    """Configurable SPD-specific weighting for one finding_type -- unknown
    types default to 'medium' rather than silently 'low', since an
    unrecognized finding should never be under-weighted."""
    return SPD_RISK_MATRIX.get((finding_type or "").strip().lower(), RISK_WEIGHT_MEDIUM)


def spd_risk_weight_value(finding_type: str) -> int:
    return _RISK_WEIGHT_VALUE[spd_risk_weight(finding_type)]


# ── Section 4: Dynamic Risk Scoring bands ────────────────────────────────────
# Higher score = higher risk (the inverse convention of Vulcan's reliability
# score / Veritas's readiness score, both of which score "higher is better").
RISK_LEVEL_VERY_LOW = "very_low"
RISK_LEVEL_LOW = "low"
RISK_LEVEL_MODERATE = "moderate"
RISK_LEVEL_HIGH = "high"
RISK_LEVEL_CRITICAL = "critical"
RISK_LEVELS = [RISK_LEVEL_VERY_LOW, RISK_LEVEL_LOW, RISK_LEVEL_MODERATE, RISK_LEVEL_HIGH, RISK_LEVEL_CRITICAL]


def risk_level(score: float) -> str:
    if score >= 80:
        return RISK_LEVEL_CRITICAL
    if score >= 60:
        return RISK_LEVEL_HIGH
    if score >= 40:
        return RISK_LEVEL_MODERATE
    if score >= 20:
        return RISK_LEVEL_LOW
    return RISK_LEVEL_VERY_LOW


SENTINELX_AGENT_VERSION = "1.0.0"

DISCLAIMER = (
    "Sentinel-X continuously evaluates clinical, operational, and inspection risk before an "
    "instrument proceeds through the pre-sterilization workflow. It does not replace human "
    "clinical judgment -- it prioritizes risk and explains why. Every assessment is "
    "explainable, evidence-based, confidence-scored, auditable, and subject to human review."
)


class SentinelXRiskAssessment(Base):
    """The composite clinical risk assessment (Sections 1, 2, 4) -- composes
    Veritas/Aegis/Vulcan/Sage/Knowledge-Graph/Digital-Twin signal into one
    explainable risk score. Never a replacement for supervisor review
    (`human_review_required` is always True)."""

    __tablename__ = "sentinelx_risk_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    instrument_identity: Mapped[str] = mapped_column(String(300), default="", nullable=False, index=True)
    instrument_family: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    manufacturer_name: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    anatomy_zone: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)
    facility_name: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    service_line: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)

    risk_categories_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), default=RISK_LEVEL_MODERATE, nullable=False, index=True)
    score_breakdown_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    contamination_severity: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    finding_type: Mapped[str] = mapped_column(String(50), default="", nullable=False, index=True)
    recurrence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    digital_twin_condition_trend: Mapped[str] = mapped_column(String(30), default="insufficient_data", nullable=False)

    vulcan_assessment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    veritas_assessment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    reasoning_narrative: Mapped[str] = mapped_column(Text, default="", nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), default="moderate", nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    agent_version: Mapped[str] = mapped_column(String(20), default=SENTINELX_AGENT_VERSION, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class SentinelXPatientSafetyAlert(Base):
    """Proactive patient-safety alert (Section 5) -- distinct from the
    pre-existing `SentinelAlert` (Project Sentinel v3.0). Fires from a real,
    repeated pattern (recurrence_count/escalation), never a single event."""

    __tablename__ = "sentinelx_patient_safety_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    alert_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    instrument_identity: Mapped[str] = mapped_column(String(300), default="", nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), default="moderate", nullable=False)
    narrative: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledged_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SentinelXSupervisorOverride(Base):
    """An auditable supervisor action on a Sentinel-X risk assessment
    (Sections 10, 13) -- Sentinel-X's own risk level is always advisory;
    this is the only place a human-authorized override is recorded."""

    __tablename__ = "sentinelx_supervisor_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    assessment_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    original_risk_level: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    overridden_risk_level: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)

    submitted_by: Mapped[str] = mapped_column(String(255), nullable=False)
    submitted_role: Mapped[str] = mapped_column(String(50), default="", nullable=False)
