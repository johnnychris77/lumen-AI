"""v5.1 — LumenAI Network: Project Olympus — Autonomous Healthcare
Intelligence Network.

## Naming disambiguation (read this first)

Olympus is the 20th additive sprint and deliberately the most
composition-heavy: its mission is to turn a decade of already-built
cross-organization infrastructure into one coherent "network" experience,
not to re-invent any of it. Every existing network/collaboration/
marketplace/governance system was read in full before writing a single
new table:

  * **Network Identity (Section 1)** — P24's `AdvisoryConsortiumMember`
    (`p24_standards.py`) already is a real, tenant-scoped participant
    roster with `organization_type`, `membership_tier` ("Participation
    Level"), `membership_status`, `governance_roles` + `voting_rights`
    ("Governance Profile"). Rather than a second participant table,
    Olympus extends its `organization_type` vocabulary with `"partner"`,
    `"consultant"`, `"educator"` (in `p24_standards.py`'s `VALID_TYPES`
    and `beacon_collaboration_hub_service.py`'s `PARTICIPANT_TYPES`) to
    cover the brief's full participant list, and adds one nullable
    `observatory_opt_in` column for Section 5. "Contribution History" is
    composed live from `KnowledgeContribution` (Horizon),
    `RepairIntelligenceSnapshot`/Advisory Board activity (Beacon), and
    Athena's memory entries — never duplicated into a new log table.
  * **Trust Network (Section 2)** — Athena's `athena_trust_service.py`
    already computes a "Knowledge Trust Score," but it is scored
    per-`KnowledgeArticle`, not per-organization. Nothing anywhere scores
    an *organization's* trustworthiness. `NetworkTrustSnapshot` is
    genuinely new, and its six components are computed by composing real
    signals that already exist: Participation Status
    (`AdvisoryConsortiumMember.membership_status`), Knowledge Quality
    (Athena's per-article trust scores, averaged), Validation History
    (Infinity's certification outcomes), Evidence Contributions (Horizon's
    `ClinicalEvidenceReference`), Peer Recognition (genuinely new -- no
    endorsement/rating construct existed before this table), and
    Governance Compliance (`AdvisoryConsortiumMember.governance_roles` /
    `voting_rights`).
  * **Global Intelligence Exchange + Healthcare Intelligence Exchange
    (Sections 3, 4)** — no table anywhere packages up existing content
    (a knowledge article, a workflow template, a Digital Twin model, a
    benchmark report, ...) for formal, governance-approved, de-identified
    exchange across the network. `HIXExchangePackage` is genuinely new,
    but it never copies the underlying content -- it references it by
    `content_ref_type`/`content_ref_id` and only carries the exchange's
    own governance/de-identification state.
  * **Global Research Observatory (Section 5)** — entirely a
    read-only composition over pre-existing rows: `EmergingTrendAlert`
    and `InstrumentRiskRegistryEntry` (contamination/instrument trends),
    `ContinuousImprovementInitiative` (quality improvement initiatives),
    `StandardsPublication` (inspection science / published research). No
    new table.
  * **AI Model Registry (Section 6)** — nothing in this codebase tracks
    an AI model as a first-class, versioned registry object. Sentinel's
    AI health service reports live operational health; Phoenix's
    `AIInferenceLatencySample` is a performance sample, not a model
    identity. `AIModelRegistryEntry` is genuinely new, with a
    `supersedes_id` self-FK following the same version-chain pattern as
    `QualityPolicy` (Apollo) and `StandardsPublication` (P24).
  * **Certification Registry (Section 7)** — not a new certification
    engine. It is a read-only index across two certification surfaces
    that already exist: Infinity's `MarketplaceListing.certification_status`
    (workflows/knowledge/education published as marketplace listings) and
    the new `AIModelRegistryEntry.certification_status` below -- both
    driven through Forge's `WorkflowApprovalChain` (`forge_approval_service.py`),
    reused here for the fourth time (after Athena, Phoenix, Infinity).
  * **Innovation Marketplace (Section 8)** — Infinity's `MarketplaceListing`
    (`infinity_platform.py`) is already a generic, developer-owned listing
    model with review-gated publication. Olympus extends its
    `LISTING_TYPES` vocabulary with `workflow_pack`, `knowledge_pack`,
    `training_module`, `analytics_dashboard`, `research_dataset`,
    `simulation_template` (`ai_skill` already existed) rather than a
    second marketplace model.
  * **Network Governance Council (Section 9)** — Beacon's
    `AdvisoryBoardMeeting`/`AdvisoryBoardActionItem`/`AdvisoryBoardRecommendation`
    triplet already covers meeting-based product-roadmap governance for
    one industry board; Vanguard's governance is internal, single-org
    executive governance. Neither covers cross-organization case work like
    dispute resolution, ethics review, or version approval. `NetworkGovernanceCase`
    is genuinely new -- a single generic case model with a `case_type`
    discriminator (`participation_review` | `contribution_review` |
    `dispute` | `version_approval` | `ethics_review` | `clinical_oversight`)
    rather than six separate tables, with an optional nullable `meeting_id`
    linking a case to the Beacon meeting where it was discussed.

## What is genuinely new in this file

Four tables: `NetworkTrustSnapshot`, `HIXExchangePackage`,
`AIModelRegistryEntry`, `NetworkGovernanceCase`. Everything else this
sprint touches is an additive extension of an existing model/service
file (documented above and in the corresponding edits), never a
duplicate.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Trust Network (Section 2) ────────────────────────────────────────────────
TRUST_COMPONENTS = [
    "participation_status", "knowledge_quality", "validation_history",
    "evidence_contributions", "peer_recognition", "governance_compliance",
]

# ── Healthcare Intelligence Exchange (Sections 3, 4) ─────────────────────────
HIX_PACKAGE_KNOWLEDGE = "knowledge_package"
HIX_PACKAGE_WORKFLOW_TEMPLATE = "workflow_template"
HIX_PACKAGE_DIGITAL_TWIN_MODEL = "digital_twin_model"
HIX_PACKAGE_INSPECTION_PROTOCOL = "inspection_protocol"
HIX_PACKAGE_EDUCATIONAL_MODULE = "educational_module"
HIX_PACKAGE_BENCHMARK_REPORT = "benchmark_report"
HIX_PACKAGE_ANATOMY_MODEL = "anatomy_model"
HIX_PACKAGE_CONTAMINATION_TREND = "contamination_trend"
HIX_PACKAGE_QUALITY_INSIGHT = "quality_insight"
HIX_PACKAGE_RESEARCH_FINDING = "research_finding"
HIX_PACKAGE_TYPES = [
    HIX_PACKAGE_KNOWLEDGE, HIX_PACKAGE_WORKFLOW_TEMPLATE, HIX_PACKAGE_DIGITAL_TWIN_MODEL,
    HIX_PACKAGE_INSPECTION_PROTOCOL, HIX_PACKAGE_EDUCATIONAL_MODULE, HIX_PACKAGE_BENCHMARK_REPORT,
    HIX_PACKAGE_ANATOMY_MODEL, HIX_PACKAGE_CONTAMINATION_TREND, HIX_PACKAGE_QUALITY_INSIGHT,
    HIX_PACKAGE_RESEARCH_FINDING,
]

HIX_DRAFT = "draft"
HIX_PENDING_GOVERNANCE_REVIEW = "pending_governance_review"
HIX_APPROVED = "approved"
HIX_PUBLISHED = "published"
HIX_REJECTED = "rejected"
HIX_STATUSES = [HIX_DRAFT, HIX_PENDING_GOVERNANCE_REVIEW, HIX_APPROVED, HIX_PUBLISHED, HIX_REJECTED]

# ── AI Model Registry (Section 6) ────────────────────────────────────────────
MODEL_TYPE_VISION = "vision"
MODEL_TYPE_REASONING = "reasoning"
MODEL_TYPE_KNOWLEDGE = "knowledge"
MODEL_TYPE_SIMULATION = "simulation"
AI_MODEL_TYPES = [MODEL_TYPE_VISION, MODEL_TYPE_REASONING, MODEL_TYPE_KNOWLEDGE, MODEL_TYPE_SIMULATION]

VALIDATION_UNVALIDATED = "unvalidated"
VALIDATION_IN_VALIDATION = "in_validation"
VALIDATION_VALIDATED = "validated"
VALIDATION_DEPRECATED = "deprecated"
MODEL_VALIDATION_STATUSES = [
    VALIDATION_UNVALIDATED, VALIDATION_IN_VALIDATION, VALIDATION_VALIDATED, VALIDATION_DEPRECATED,
]

# Reuses Infinity's exact certification-status vocabulary for consistency
# across both certification surfaces in the Certification Registry.
MODEL_CERT_NOT_STARTED = "not_started"
MODEL_CERT_IN_PROGRESS = "in_progress"
MODEL_CERT_CERTIFIED = "certified"
MODEL_CERT_REJECTED = "rejected"
MODEL_CERTIFICATION_STATUSES = [
    MODEL_CERT_NOT_STARTED, MODEL_CERT_IN_PROGRESS, MODEL_CERT_CERTIFIED, MODEL_CERT_REJECTED,
]

# ── Network Governance Council (Section 9) ───────────────────────────────────
CASE_PARTICIPATION_REVIEW = "participation_review"
CASE_CONTRIBUTION_REVIEW = "contribution_review"
CASE_DISPUTE = "dispute"
CASE_VERSION_APPROVAL = "version_approval"
CASE_ETHICS_REVIEW = "ethics_review"
CASE_CLINICAL_OVERSIGHT = "clinical_oversight"
GOVERNANCE_CASE_TYPES = [
    CASE_PARTICIPATION_REVIEW, CASE_CONTRIBUTION_REVIEW, CASE_DISPUTE,
    CASE_VERSION_APPROVAL, CASE_ETHICS_REVIEW, CASE_CLINICAL_OVERSIGHT,
]

CASE_OPEN = "open"
CASE_UNDER_REVIEW = "under_review"
CASE_RESOLVED = "resolved"
CASE_DISMISSED = "dismissed"
GOVERNANCE_CASE_STATUSES = [CASE_OPEN, CASE_UNDER_REVIEW, CASE_RESOLVED, CASE_DISMISSED]

DISCLAIMER = (
    "The LumenAI Healthcare Intelligence Network shares only governance-approved, "
    "de-identified, evidence-based clinical intelligence across participating "
    "organizations. It never exposes another organization's raw data, patient "
    "information, or identity. Every exchange requires human review before "
    "publication, describes potential associations only -- never causation -- "
    "and remains fully auditable."
)


class NetworkTrustSnapshot(Base):
    """A point-in-time trust score for one network participant (Section 2).

    Trust is earned, not assigned: every component below is computed
    live by `olympus_trust_service.py` from real, pre-existing platform
    signals and persisted here only as a historical record, the same
    snapshot pattern already used by `PlatformMaturitySnapshot` (Phoenix)
    and `QualityTwinSnapshot` (Apollo).
    """

    __tablename__ = "olympus_network_trust_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    components_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    overall_trust_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    participation_level: Mapped[str] = mapped_column(String(20), default="", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class HIXExchangePackage(Base):
    """A governed, de-identified exchange package (Sections 3, 4).

    Never copies the underlying content -- `content_ref_type`/
    `content_ref_id` point at the existing row (a `KnowledgeArticle`, a
    `WorkflowDefinition`, a Digital Twin model snapshot id, ...); this
    row only carries the exchange's own governance and de-identification
    state, so the source content is never duplicated across the network.
    """

    __tablename__ = "olympus_hix_exchange_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    source_tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    package_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    content_ref_type: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    content_ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(String(30), default=HIX_DRAFT, nullable=False, index=True)
    no_phi_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    no_identifiable_customer_data_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    governance_case_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submitted_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    reviewed_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class AIModelRegistryEntry(Base):
    """A versioned AI model registry entry (Section 6).

    `supersedes_id` is a nullable self-FK so a new model version forms a
    real chain rather than overwriting history, following the same
    pattern as `QualityPolicy` (Apollo) and `StandardsPublication` (P24).
    Certification reuses Forge's `WorkflowApprovalChain` exactly as
    Infinity's `MarketplaceListing` does.
    """

    __tablename__ = "olympus_ai_model_registry_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    model_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="0.1.0", nullable=False)
    supersedes_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    validation_status: Mapped[str] = mapped_column(String(20), default=VALIDATION_UNVALIDATED, nullable=False, index=True)
    clinical_scope: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    performance_metrics_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    certification_status: Mapped[str] = mapped_column(String(20), default=MODEL_CERT_NOT_STARTED, nullable=False, index=True)
    certification_chain_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    certification_instance_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    registered_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class NetworkGovernanceCase(Base):
    """A Network Governance Council case (Section 9) -- one generic case
    model with a `case_type` discriminator rather than six separate
    tables for participation review, contribution review, dispute
    resolution, version approval, ethics review, and clinical oversight.

    `meeting_id` optionally links a case to the Beacon
    `AdvisoryBoardMeeting` where it was discussed, without requiring one
    -- most cases (e.g. a single contribution review) never need a
    meeting at all.
    """

    __tablename__ = "olympus_network_governance_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    case_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    filed_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    involved_tenant_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    status: Mapped[str] = mapped_column(String(20), default=CASE_OPEN, nullable=False, index=True)
    meeting_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolution: Mapped[str] = mapped_column(Text, default="", nullable=False)
    resolved_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
