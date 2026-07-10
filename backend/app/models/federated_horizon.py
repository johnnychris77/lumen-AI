"""v3.4 — Project Horizon: Federated Clinical Intelligence & Global Learning Network.

Mission: the world's first federated clinical intelligence network for
sterile processing. Hospitals remain completely isolated; patient
information never leaves the organization; institution-specific
workflows remain local. Only validated, de-identified, governance-
approved clinical inspection intelligence may contribute to global
learning.

## This is the 4th cross-tenant intelligence system in this codebase —
## consolidate, don't duplicate

Before this sprint, three parallel cross-tenant/network intelligence
systems already existed, each with its own k-anonymity floor:

  * **P15** (`app/services/network_benchmark_service.py`,
    `app/models/network_benchmark.py`) — `IndustryBenchmark`/
    `NetworkParticipant`, percentile-band benchmarking (p25/p50/p75/p90),
    `MIN_FACILITIES = 5`, Laplace noise, SHA-256 monthly-salt facility
    pseudonymization.
  * **P20** (`app/models/p20_network_intelligence.py`) — National SPD
    Registry, Instrument Lifecycle Intelligence, Recall Early Warning,
    **Research Data Exchange** (`ResearchDataset`/`ResearchStudy`/
    `ResearchPublication`, already governance-gated and IRB-aware), and
    Executive Intelligence. Its own `IntelligenceSharingAgreement` is
    already exactly an org-level opt-in participation agreement.
  * **P23 "GSIN"** (`app/models/global_intelligence.py`,
    `app/services/global_aggregation_job.py`) — `GSINParticipant`
    enrollment, `GlobalIntelligenceSignal`/`InstrumentRiskRegistryEntry`/
    `GlobalRecallEarlyWarning`, `GLOBAL_K_THRESHOLD = 10`,
    `EARLY_WARNING_K = 5`, Laplace differential privacy
    (`LAPLACE_EPSILON = 0.05`).

Project Horizon does **not** add a fifth org-participation model or a
second percentile engine. It reuses:

  * `GSINParticipant` + `IntelligenceSharingAgreement` together, via
    `horizon_participation_service.enroll_organization` — a federated
    participant needs both GSIN's technical/DPA gate and P20's sharing-
    scope agreement; Horizon composes the two into one enrollment action
    rather than adding a third.
  * `GLOBAL_K_THRESHOLD`/`EARLY_WARNING_K` from `global_aggregation_job.py`
    for every new k-anonymity gate in this module — imported directly,
    never redefined.
  * `network_benchmark_service`'s percentile-band + Laplace-noise pattern
    for Section 5's new benchmark metrics — same math, new metric names.
  * P20's already-built `ResearchDataset`/`ResearchStudy`/
    `ResearchPublication` CRUD for the Section 7 Research Portal — Horizon
    only adds the presentation layer (`/research` page,
    `horizon_research_portal_service.py`) composing what P20 already
    computes, plus Horizon's own new signal/benchmark/trend data.

What genuinely does not exist anywhere in this codebase before this
sprint, and is what this module actually adds:

  * True **cross-organization** (not just cross-facility-within-one-
    Atlas-health-system, and not just numeric signals) knowledge content
    contribution, with approval + versioning (Section 3).
  * A **Global Knowledge Graph** layer above the existing strictly-per-
    tenant Knowledge Graph (`app/services/knowledge_graph_service.py`,
    "Phase 21" — there is no prior "Project Cortex" anywhere in this
    codebase; this doc uses that name only because the sprint brief does,
    and extends the existing Phase 21 reasoning engine, which is the
    closest real system to it) (Section 2).
  * A **Clinical Evidence Repository** linking AI recommendations across
    every existing recommendation-producing engine to peer-reviewed/AAMI/
    AORN/manufacturer/internal-SOP references — only a narrow finding-
    category-to-regulatory-clause mapping (`app/models/regulatory.py`)
    existed before (Section 8).
  * Cross-tenant **emerging trend notification** — Atlas's own
    `ENTERPRISE_WATCHLIST_EMERGING_TREND` only recurs within one health
    system's own facilities; nothing before this detected/notified a
    pattern recurring across unrelated organizations (Section 6).
  * A federated feedback loop suggesting (never auto-applying) local
    improvements to Knowledge Graph, Clinical Reasoning, Zone
    Intelligence, Digital Twins, and Prediction Models from approved
    global knowledge (Section 10).

## Six additive tables
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Section 3: Knowledge Contribution ───────────────────────────────────────
CONTRIBUTION_ANATOMY_GUIDANCE = "anatomy_guidance"
CONTRIBUTION_BEST_PRACTICE = "best_practice"
CONTRIBUTION_SUPERVISOR_RECOMMENDATION = "supervisor_recommendation"
CONTRIBUTION_DIGITAL_TWIN_INSIGHT = "digital_twin_insight"
CONTRIBUTION_FAILURE_PATTERN = "failure_pattern"
CONTRIBUTION_EDUCATIONAL_CONTENT = "educational_content"
CONTRIBUTION_TYPES = [
    CONTRIBUTION_ANATOMY_GUIDANCE, CONTRIBUTION_BEST_PRACTICE, CONTRIBUTION_SUPERVISOR_RECOMMENDATION,
    CONTRIBUTION_DIGITAL_TWIN_INSIGHT, CONTRIBUTION_FAILURE_PATTERN, CONTRIBUTION_EDUCATIONAL_CONTENT,
]

# Same string values as app/models/knowledge.py's approval states, kept
# identical on purpose (not imported, to avoid coupling a federated
# cross-tenant table's lifecycle to a tenant-scoped one) — "every
# contribution requires approval."
DRAFT = "draft"
PENDING_REVIEW = "pending_review"
APPROVED = "approved"
REJECTED = "rejected"
ARCHIVED = "archived"
CONTRIBUTION_APPROVAL_STATES = [DRAFT, PENDING_REVIEW, APPROVED, REJECTED, ARCHIVED]

# ── Section 4: Federated Learning Signals ───────────────────────────────────
SIGNAL_FINDING_FREQUENCY = "finding_frequency"
SIGNAL_ANATOMY_TREND = "anatomy_trend"
SIGNAL_INSTRUMENT_FAILURE_PATTERN = "instrument_failure_pattern"
SIGNAL_COVERAGE_EFFECTIVENESS = "coverage_effectiveness"
SIGNAL_SUPERVISOR_AGREEMENT = "supervisor_agreement"
SIGNAL_EDUCATIONAL_EFFECTIVENESS = "educational_effectiveness"
FEDERATED_SIGNAL_CATEGORIES = [
    SIGNAL_FINDING_FREQUENCY, SIGNAL_ANATOMY_TREND, SIGNAL_INSTRUMENT_FAILURE_PATTERN,
    SIGNAL_COVERAGE_EFFECTIVENESS, SIGNAL_SUPERVISOR_AGREEMENT, SIGNAL_EDUCATIONAL_EFFECTIVENESS,
]

# ── Section 5: Global Benchmarking metric names (new, distinct from P15's) ──
BENCHMARK_METRICS = [
    "kerrison_blood_finding_rate", "corrosion_trend", "coverage_trend",
    "repair_referral_rate", "knowledge_maturity_index", "training_maturity_index",
]

# ── Section 6: Emerging Trend Detection ─────────────────────────────────────
TREND_NEW_CORROSION_PATTERN = "new_corrosion_pattern"
TREND_NEW_CONTAMINATION_LOCATION = "new_contamination_location"
TREND_UNEXPECTED_ANATOMY_RISK = "unexpected_anatomy_risk"
TREND_MANUFACTURER_QUALITY_TREND = "manufacturer_quality_trend"
TREND_EMERGING_INSPECTION_CHALLENGE = "emerging_inspection_challenge"
EMERGING_TREND_TYPES = [
    TREND_NEW_CORROSION_PATTERN, TREND_NEW_CONTAMINATION_LOCATION, TREND_UNEXPECTED_ANATOMY_RISK,
    TREND_MANUFACTURER_QUALITY_TREND, TREND_EMERGING_INSPECTION_CHALLENGE,
]

# ── Section 8: Clinical Evidence Repository ─────────────────────────────────
EVIDENCE_PEER_REVIEWED = "peer_reviewed"
EVIDENCE_MANUFACTURER_GUIDANCE = "manufacturer_guidance"
EVIDENCE_AAMI = "aami"
EVIDENCE_AORN = "aorn"
EVIDENCE_ORG_SOP = "org_sop"
EVIDENCE_INTERNAL_VALIDATION_STUDY = "internal_validation_study"
EVIDENCE_TYPES = [
    EVIDENCE_PEER_REVIEWED, EVIDENCE_MANUFACTURER_GUIDANCE, EVIDENCE_AAMI,
    EVIDENCE_AORN, EVIDENCE_ORG_SOP, EVIDENCE_INTERNAL_VALIDATION_STUDY,
]

# ── Section 10: Global AI Improvement target systems ────────────────────────
IMPROVEMENT_TARGET_KNOWLEDGE_GRAPH = "knowledge_graph"
IMPROVEMENT_TARGET_CLINICAL_REASONING = "clinical_reasoning"
IMPROVEMENT_TARGET_ZONE_INTELLIGENCE = "zone_intelligence"
IMPROVEMENT_TARGET_DIGITAL_TWINS = "digital_twins"
IMPROVEMENT_TARGET_PREDICTION_MODELS = "prediction_models"
IMPROVEMENT_TARGETS = [
    IMPROVEMENT_TARGET_KNOWLEDGE_GRAPH, IMPROVEMENT_TARGET_CLINICAL_REASONING,
    IMPROVEMENT_TARGET_ZONE_INTELLIGENCE, IMPROVEMENT_TARGET_DIGITAL_TWINS, IMPROVEMENT_TARGET_PREDICTION_MODELS,
]

DISCLAIMER = (
    "Project Horizon publishes only de-identified, aggregated, k-anonymity-gated intelligence contributed by "
    "opted-in organizations. No patient information, facility identity, or customer-identifiable data is ever "
    "shared. Every global signal, benchmark, trend, and knowledge contribution is a potential association for "
    "awareness, not a causal or clinical determination; human review and organizational governance remain central "
    "to all shared knowledge, and every participant retains full ownership of its own operational data."
)


class KnowledgeContribution(Base):
    """Section 3: a true cross-organization knowledge contribution.

    `source_tenant_id` is retained for governance/audit only — it is
    never exposed in any public/cross-org read; de-identification means
    other organizations see the approved content, never who submitted it.
    """
    __tablename__ = "horizon_knowledge_contributions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    contribution_ref: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    source_tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    contribution_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    supersedes_ref: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    superseded_by_ref: Mapped[str] = mapped_column(String(40), default="", nullable=False)

    approval_status: Mapped[str] = mapped_column(String(20), default=PENDING_REVIEW, nullable=False, index=True)
    submitted_by: Mapped[str] = mapped_column(String(255), nullable=False)
    approved_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class FederatedLearningSignal(Base):
    """Section 4: aggregate learning signal categories GSIN's instrument-
    centric schema doesn't cover — same k-anonymity gate, new dimensions."""
    __tablename__ = "horizon_federated_learning_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    signal_category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    scope_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(50), default="global", nullable=False)

    tenant_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    trend_direction: Mapped[str] = mapped_column(String(20), default="stable", nullable=False)

    k_anonymity_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class EmergingTrendAlert(Base):
    """Section 6: a pattern recurring across multiple unrelated
    organizations — distinct from Atlas's intra-health-system emerging-
    trend watchlist. `notified_tenant_ids_json` tracks which enrolled
    participants have been notified."""
    __tablename__ = "horizon_emerging_trend_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    trend_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    tenant_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="monitoring", nullable=False, index=True)
    notified_tenant_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    acknowledged_tenant_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class ClinicalEvidenceReference(Base):
    """Section 8: a citable clinical evidence reference. `tenant_id` is
    blank for globally-visible evidence (peer-reviewed literature, AAMI/
    AORN standards, manufacturer guidance) and set to a specific tenant
    only for that org's own private internal SOPs/validation studies."""
    __tablename__ = "horizon_clinical_evidence_references"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    evidence_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    citation_text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    publication_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    added_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class RecommendationEvidenceLink(Base):
    """Section 8: links any existing recommendation-producing row (e.g. a
    Sentinel recommendation, Atlas alert, Insight recommendation, or CAPA)
    to one or more clinical evidence references. `source_type` is a
    free-form label naming which engine's recommendation this links —
    generic by design so it never needs a schema change to cover a new
    recommendation engine."""
    __tablename__ = "horizon_recommendation_evidence_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    source_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    evidence_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    relevance_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    linked_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class GlobalKnowledgeGraphEdge(Base):
    """Section 2: one aggregated, k-anonymity-gated edge in the Global
    Federated Knowledge Graph — sits above the existing strictly-per-
    tenant Knowledge Graph (`knowledge_graph_service.py`). Node/
    relationship type strings follow that module's existing
    `NODE_TYPES`/`RELATIONSHIP_TYPES` taxonomy rather than inventing a
    parallel one."""
    __tablename__ = "horizon_global_knowledge_graph_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    source_node_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    source_node_value: Mapped[str] = mapped_column(String(255), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(60), nullable=False)
    target_node_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    target_node_value: Mapped[str] = mapped_column(String(255), nullable=False)

    tenant_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    k_anonymity_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)
