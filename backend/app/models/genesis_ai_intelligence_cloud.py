"""v5.3 — LumenAI Network: Project Genesis AI — Global Sterile Processing
Intelligence Cloud.

## Naming disambiguation (read this first)

**"Project Genesis AI" (this file, v5.3) is not "Project Genesis" (v4.0,
`platform_core.py`)** — Genesis (v4.0) is the platform/module/plugin
registry ("Genesis" as in the platform's own origin); Genesis AI (v5.3)
is a sterile-processing intelligence cloud. They share a name prefix by
coincidence of sprint naming, not by relationship — neither table
references the other.

Genesis AI is the 22nd additive sprint, and by a wide margin the most
reuse-heavy: nearly every objective already has a real, working system
behind it from an earlier sprint. Before writing a single new table,
every candidate system was read in full:

  * **Global Instrument Registry (Section 1)** — P15's `RegistryInstrument`
    (`app/models/instrument_registry.py`) is already a real, global,
    network-aggregate instrument registry (manufacturer/model/category,
    anonymized network defect/pass rates, k-anonymity-gated). Genesis AI
    extends it directly with `instrument_family`, `ifu_versions_json`,
    `anatomy_profile_id`, `inspection_zones_json`,
    `digital_twin_template_ref`, `baseline_template_ref`,
    `failure_modes_json`, `repair_guidance`, `knowledge_references_json`
    -- never a second instrument table. The pre-existing service's
    seeded-mock-fallback behavior (`instrument_registry_service.py`) is
    left completely untouched; Genesis AI's own service only ever reads/
    writes the new columns on real rows.
  * **Global Anatomy Registry (Section 2)** — no anatomy-profile
    standardization taxonomy exists anywhere in this codebase (only
    free-text `zone`/`instrument_type` strings on `InspectionFinding`/
    `Inspection`). `AnatomyProfile` is genuinely new.
  * **Clinical Evidence Cloud (Section 3)** — zero new tables. Horizon's
    `ClinicalEvidenceReference`/`RecommendationEvidenceLink`
    (`federated_horizon.py`, v3.4) already cover peer-reviewed literature,
    manufacturer guidance (IFUs), AAMI, AORN, organization SOPs, internal
    validation studies, and already link evidence directly to any
    recommendation-producing row. Reused directly.
  * **Manufacturer Knowledge Portal (Section 4)** — Beacon's
    `beacon_manufacturer_portal_service.py` (v3.5) is read-only analytics
    *for* a manufacturer to view its own instrument population's quality
    trends; nothing lets a manufacturer *publish* version-controlled IFU/
    guidance updates. `ManufacturerKnowledgeUpdate` is genuinely new.
  * **Global Learning Engine (Section 5)** — zero new tables. Horizon's
    `horizon_federated_signal_service.py`/`horizon_ai_improvement_service.py`
    (v3.4, Section 10) already aggregates de-identified signals (finding
    frequency, anatomy trends, instrument failure patterns, coverage
    effectiveness, supervisor agreement, educational effectiveness) and
    already generates advisory hypotheses for human review. Genesis AI's
    "Model performance" and "Workflow effectiveness" dimensions reuse
    Phoenix's `compute_ai_health_score`/`compute_workflow_health_score`
    directly; "Knowledge adoption" is one new lightweight aggregation
    over `KnowledgeArticle.view_count` (no new table).
  * **Research Collaboration Hub (Section 6)** — zero new tables. P20's
    `ResearchDataset`/`ResearchStudy`/`ResearchPublication`
    (`p20_network_intelligence.py`) already implement governance-gated,
    IRB-aware research proposals/studies/datasets/publications, already
    composed into a presentation layer by
    `horizon_research_portal_service.py` (v3.4). Genesis AI adds one
    column, `research_opt_in`, to P24's `AdvisoryConsortiumMember`
    (extended a fourth time, after Beacon/Olympus) for "participation is
    opt-in."
  * **Instrument Intelligence API (Section 7)** — extends Nexus's
    `/api/v1/*` gateway (`nexus_api_gateway.py`, v3.2, already extended by
    Infinity) with new read endpoints composing the systems above --
    never a second versioned API surface.
  * **Clinical Intelligence Exchange (Section 8)** — zero new tables.
    Olympus's `HIXExchangePackage` (v5.1) already packages knowledge/
    workflow/Digital-Twin/education content with governance approval and
    provenance tracking. `HIX_PACKAGE_TYPES` gains one new value,
    `research_dataset`, so P20's research datasets can flow through the
    same exchange pipeline.
  * **Global Standards Observatory (Section 9)** — zero new tables. Composes
    `ManufacturerKnowledgeUpdate` (this file), Apollo's `QualityPolicy`
    version chain (internal policies), P24's `StandardsPublication`
    (industry standards), and Horizon's `ClinicalEvidenceReference`
    (scientific publications) into one recent-changes feed, filtered to
    `observatory_opt_in` participants (Olympus's existing flag -- no
    second opt-in column needed for this one).

## What is genuinely new in this file

Two tables: `AnatomyProfile`, `ManufacturerKnowledgeUpdate`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Global Anatomy Registry (Section 2) ──────────────────────────────────────
ANATOMY_SCISSORS = "scissors"
ANATOMY_FORCEPS = "forceps"
ANATOMY_NEEDLE_HOLDERS = "needle_holders"
ANATOMY_KERRISONS = "kerrisons"
ANATOMY_RONGEURS = "rongeurs"
ANATOMY_DRILL_BITS = "drill_bits"
ANATOMY_RIGID_SCOPES = "rigid_scopes"
ANATOMY_FLEXIBLE_ENDOSCOPES = "flexible_endoscopes"
ANATOMY_POWERED_INSTRUMENTS = "powered_instruments"
ANATOMY_ROBOTIC_INSTRUMENTS = "robotic_instruments"
ANATOMY_IMPLANTS = "implants"
ANATOMY_OTHER = "other"  # "Future expansion" — an explicit escape hatch, never silently rejected
ANATOMY_PROFILE_TYPES = [
    ANATOMY_SCISSORS, ANATOMY_FORCEPS, ANATOMY_NEEDLE_HOLDERS, ANATOMY_KERRISONS, ANATOMY_RONGEURS,
    ANATOMY_DRILL_BITS, ANATOMY_RIGID_SCOPES, ANATOMY_FLEXIBLE_ENDOSCOPES, ANATOMY_POWERED_INSTRUMENTS,
    ANATOMY_ROBOTIC_INSTRUMENTS, ANATOMY_IMPLANTS, ANATOMY_OTHER,
]

# ── Manufacturer Knowledge Portal (Section 4) ────────────────────────────────
UPDATE_IFU = "ifu"
UPDATE_INSPECTION_GUIDANCE = "inspection_guidance"
UPDATE_CLEANING_UPDATE = "cleaning_update"
UPDATE_REPAIR_ADVISORY = "repair_advisory"
UPDATE_DESIGN_REVISION = "design_revision"
MANUFACTURER_UPDATE_TYPES = [
    UPDATE_IFU, UPDATE_INSPECTION_GUIDANCE, UPDATE_CLEANING_UPDATE, UPDATE_REPAIR_ADVISORY, UPDATE_DESIGN_REVISION,
]

MFR_UPDATE_DRAFT = "draft"
MFR_UPDATE_PENDING_REVIEW = "pending_review"
MFR_UPDATE_PUBLISHED = "published"
MFR_UPDATE_STATUSES = [MFR_UPDATE_DRAFT, MFR_UPDATE_PENDING_REVIEW, MFR_UPDATE_PUBLISHED]

DISCLAIMER = (
    "LumenAI Genesis AI provides a governed, privacy-preserving global intelligence cloud for "
    "sterile processing. Organizations retain ownership of their own data; only approved, "
    "de-identified, evidence-based intelligence is shared. Every finding describes a potential "
    "association only, never causation, and requires human review before any action."
)


class AnatomyProfile(Base):
    """A standardized anatomy profile (Section 2) -- the reference
    taxonomy entry every `RegistryInstrument.anatomy_profile_id` and
    `InstrumentKnowledge.instrument_family` conceptually maps onto,
    though neither existing table is altered to enforce a hard FK (both
    predate this taxonomy and use free-text categories elsewhere in the
    codebase already)."""

    __tablename__ = "genesis_ai_anatomy_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    profile_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    standard_terminology_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    zones_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)


class ManufacturerKnowledgeUpdate(Base):
    """A manufacturer-published, version-controlled knowledge update
    (Section 4) -- IFU revisions, inspection guidance, cleaning updates,
    repair advisories, or design revisions. `supersedes_id` forms a real
    version chain, the same pattern already used by `QualityPolicy`
    (Apollo) and `StandardsPublication` (P24). Every update requires
    review before publication -- `status` can only reach `published`
    through an explicit reviewer action.
    """

    __tablename__ = "genesis_ai_manufacturer_knowledge_updates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    manufacturer_tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    update_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0", nullable=False)
    supersedes_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)

    instrument_category: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=MFR_UPDATE_DRAFT, nullable=False, index=True)
    submitted_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    reviewed_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)
