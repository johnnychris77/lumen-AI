"""v4.8 — LumenAI OS: Project Athena — Healthcare Knowledge Intelligence &
Institutional Memory.

## Naming disambiguation (read this first)

Before writing any Athena code, every existing knowledge-adjacent surface
was read in full — this codebase already has an extensive institutional-
knowledge ecosystem from v1.8 (Institutional Knowledge & Clinical Memory)
plus the Knowledge Graph (P-era) and Project Forge's workflow engine:

  * **`/api/knowledge`** (`app/routes/knowledge.py`, v1.8) already owns
    this prefix (articles, cases, standards, governance, search,
    assistant, analytics). **`/api/knowledge-graph`** is also taken
    (`app/routes/knowledge_graph.py`). Athena's backend is mounted at
    **`/api/athena`** instead.
  * Frontend routes `/knowledge-center` and `/knowledge-graph` are
    already taken. **`/knowledge-memory`** was confirmed free and is
    Athena's frontend route, per the sprint brief's explicit instruction.
  * **Institutional Memory (Section 1)**: `KnowledgeArticle` (v1.8) +
    `ClinicalCase` (v1.8) + `RootCauseAssignment` (v1.5) +
    `capa_lifecycle_service` (v2.9) + `ContinuousImprovementInitiative`
    (v1.5) + `QualityPolicy` (v4.7, Apollo) already store almost every
    knowledge type the brief names. Athena does not add a parallel
    "memory entry" table — `athena_memory_service.py` composes/normalizes
    across all of them into one searchable view. Only "vendor
    observations" and "repair observations" had no home: added as two new
    `KnowledgeArticle` categories (below) rather than a new store.
  * **Expert Knowledge Capture (Section 2)**: `KnowledgeArticle`'s
    `approval_status` (draft/pending_review/approved/rejected/archived)
    and `knowledge_governance_service.py` already implement the full
    approval workflow. Athena adds no second governance engine — only the
    genuinely new capability, photo/video/voice attachments, via
    `KnowledgeMediaAttachment` (below), since no media-reference field
    existed anywhere on `KnowledgeArticle`.
  * **Experience Graph (Section 3)**: `knowledge_graph_service.py`'s
    `explore()`/`reasoning_chain()` are real but are recomputed-on-read
    aggregations over `Inspection`/`SupervisorReview`/static anatomy
    profiles — there is no persisted node/edge structure. Athena's
    `ExperienceGraphNode`/`ExperienceGraphEdge` are genuinely new, but the
    Finding/Instrument/Anatomy/Recommendation segments of every chain are
    populated by calling `knowledge_graph_service.reasoning_chain()`
    directly rather than re-deriving that logic — only the new Person/
    Experience/Outcome/Evidence/Organization node types are Athena's own.
  * **Institutional Memory Timeline (Section 4)**: `orbit_timeline_
    service.py` exists but is a different domain entirely (OR case
    logistics — Case Scheduled → ... → Procedure Complete). Athena's
    Event → Investigation → CAPA → Education → Policy Change → Outcome →
    Verification → Future Similar Cases timeline is a new composition
    (`athena_memory_timeline_service.py`) over `RootCauseAssignment`,
    `capa_lifecycle_service`, `CompetencyEvent`, `QualityPolicy` version
    history, and `similar_case_finder_service.find_similar_cases` — no
    new table.
  * **Clinical Playbooks (Section 5)**: `workflow_forge.py`'s
    `WorkflowDefinition`/`WorkflowRule` (v4.1) already model a versioned,
    approved, nested-decision-tree workflow with `is_template` and
    `TEMPLATE_CATEGORIES` including `loaner_instrument`, `vendor_tray`,
    and `robotic_instrument`. Athena adds the three missing scenario keys
    (`blood_detection_investigation`, `corrosion_investigation`,
    `joint_commission_preparation`) to that same list and one additive
    column (`linked_standards_json`) rather than a parallel playbook
    model. `CustomerSuccessPlaybook` (a different, unrelated SaaS-renewal
    domain) was checked and confirmed not a real collision.
  * **AI Knowledge Curator (Section 6)**: `knowledge_analytics_service.py`
    already computes `knowledge_gaps()`/`training_opportunities()`/
    `most_common_questions()`. Athena extends this file's pattern with
    new deterministic checks (duplicates, outdated guidance, retirement
    candidates, emerging best practices) in a new `athena_curator_service.
    py` rather than a new analytics engine, and composes the existing
    functions rather than re-deriving them.
  * **Organizational Search (Section 7)**: `knowledge_search_service.
    smart_search()` only covers Articles+Cases. No embeddings/vector
    search/TF-IDF exists anywhere in this codebase (confirmed by grep) —
    consistent with the platform-wide "deterministic, source-grounded,
    zero real LLM integration" convention. Athena's `athena_search_
    service.py` federates the existing smart_search with keyword search
    over Policies/CAPAs/Playbooks/Competency events, each result tagged
    with its source system — still keyword/facet-based, never a
    fabricated semantic layer.
  * **Knowledge Trust Score (Section 8)**: no trust/reputation/evidence-
    quality construct exists anywhere (`beacon_standards_service.py`/
    `p24_standards_service.py` only carry `version`/`status`). Genuinely
    new — computed live from real fields (never persisted as a
    fabricated number), reusing Apollo's `competency_service.
    record_knowledge_contribution`/`CompetencyEvent` log for Contributor
    Reputation rather than re-deriving contribution counts.
  * **Athena Assistant (Section 9)**: `ai_knowledge_assistant_service.
    answer_question()` (v1.8) already implements a deterministic,
    source-cited Q&A assistant. Athena extends it with three new query
    shapes (recurring-investigation lookup, cross-time policy comparison,
    workflow version comparison) rather than a second assistant.
  * **Knowledge Preservation (Section 10)**: no exit-interview, media-
    capture, or workflow-recording system exists anywhere — genuinely
    new. `KnowledgePreservationSession` never claims to perform real
    speech-to-text transcription; `transcript_text` is a human-entered
    or human-reviewed field, matching this codebase's "never fabricate a
    capability" convention.

## Genuinely new tables in this file

  * `KnowledgeMediaAttachment` — a polymorphic (source_type, source_id)
    photo/video/voice reference, attachable to a `KnowledgeArticle`, a
    `WorkflowDefinition` (playbook), or a `KnowledgePreservationSession`.
    Stores a reference/URL and caption/transcript — never a binary blob,
    consistent with `inspection_image_tag.py`'s reference-only pattern.
  * `ExperienceGraphNode` / `ExperienceGraphEdge` — the new Person →
    Experience → Finding → Instrument → Anatomy → Recommendation →
    Outcome → Evidence → Organization relationship graph.
  * `KnowledgePreservationSession` — an exit interview / video capture /
    voice transcription / workflow recording / procedure demonstration
    session, optionally promoted into a structured `KnowledgeArticle`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Media attachments (Section 2 / Section 5 / Section 10) ──────────────────
MEDIA_PHOTO = "photo"
MEDIA_VIDEO = "video"
MEDIA_VOICE = "voice"
MEDIA_TYPES = [MEDIA_PHOTO, MEDIA_VIDEO, MEDIA_VOICE]

# Polymorphic attachment targets.
ATTACH_TO_ARTICLE = "knowledge_article"
ATTACH_TO_PLAYBOOK = "workflow_definition"
ATTACH_TO_PRESERVATION_SESSION = "preservation_session"
ATTACHMENT_SOURCE_TYPES = [ATTACH_TO_ARTICLE, ATTACH_TO_PLAYBOOK, ATTACH_TO_PRESERVATION_SESSION]

# ── Experience Graph node/edge vocabulary (Section 3) ────────────────────────
NODE_PERSON = "person"
NODE_EXPERIENCE = "experience"
NODE_FINDING = "finding"
NODE_INSTRUMENT = "instrument"
NODE_ANATOMY = "anatomy"
NODE_RECOMMENDATION = "recommendation"
NODE_OUTCOME = "outcome"
NODE_EVIDENCE = "evidence"
NODE_ORGANIZATION = "organization"
NODE_TYPES = [
    NODE_PERSON, NODE_EXPERIENCE, NODE_FINDING, NODE_INSTRUMENT, NODE_ANATOMY,
    NODE_RECOMMENDATION, NODE_OUTCOME, NODE_EVIDENCE, NODE_ORGANIZATION,
]

# The canonical chain order the brief specifies — used to validate edges.
NODE_CHAIN_ORDER = [
    NODE_PERSON, NODE_EXPERIENCE, NODE_FINDING, NODE_INSTRUMENT, NODE_ANATOMY,
    NODE_RECOMMENDATION, NODE_OUTCOME, NODE_EVIDENCE, NODE_ORGANIZATION,
]

EDGE_HAS_EXPERIENCE = "has_experience"
EDGE_YIELDED_FINDING = "yielded_finding"
EDGE_FOUND_ON_INSTRUMENT = "found_on_instrument"
EDGE_INSTRUMENT_HAS_ANATOMY = "instrument_has_anatomy"
EDGE_LED_TO_RECOMMENDATION = "led_to_recommendation"
EDGE_PRODUCED_OUTCOME = "produced_outcome"
EDGE_SUPPORTED_BY_EVIDENCE = "supported_by_evidence"
EDGE_EVIDENCE_OWNED_BY_ORG = "evidence_owned_by_organization"
EDGE_RELATIONSHIPS = [
    EDGE_HAS_EXPERIENCE, EDGE_YIELDED_FINDING, EDGE_FOUND_ON_INSTRUMENT, EDGE_INSTRUMENT_HAS_ANATOMY,
    EDGE_LED_TO_RECOMMENDATION, EDGE_PRODUCED_OUTCOME, EDGE_SUPPORTED_BY_EVIDENCE, EDGE_EVIDENCE_OWNED_BY_ORG,
]

# ── Knowledge Preservation session types (Section 10) ────────────────────────
SESSION_EXIT_INTERVIEW = "exit_interview"
SESSION_VIDEO_CAPTURE = "video_capture"
SESSION_VOICE_TRANSCRIPTION = "voice_transcription"
SESSION_WORKFLOW_RECORDING = "workflow_recording"
SESSION_PROCEDURE_DEMONSTRATION = "procedure_demonstration"
PRESERVATION_SESSION_TYPES = [
    SESSION_EXIT_INTERVIEW, SESSION_VIDEO_CAPTURE, SESSION_VOICE_TRANSCRIPTION,
    SESSION_WORKFLOW_RECORDING, SESSION_PROCEDURE_DEMONSTRATION,
]

SESSION_CAPTURED = "captured"
SESSION_TRANSCRIBED = "transcribed"
SESSION_STRUCTURED = "structured"
SESSION_ARCHIVED = "archived"
PRESERVATION_SESSION_STATUSES = [SESSION_CAPTURED, SESSION_TRANSCRIBED, SESSION_STRUCTURED, SESSION_ARCHIVED]

DISCLAIMER = (
    "LumenAI Athena preserves and organizes institutional knowledge already captured elsewhere in the "
    "platform — it does not diagnose, finalize a root cause, or replace clinical judgment. Every "
    "knowledge object, graph relationship, playbook, and trust score is decision support only and "
    "requires human review before it is treated as current or authoritative guidance."
)


class KnowledgeMediaAttachment(Base):
    """A photo/video/voice reference attached to an article, playbook, or
    preservation session (Sections 2, 5, 10) — a reference only, never a
    binary blob, matching `inspection_image_tag.py`'s existing pattern."""

    __tablename__ = "athena_knowledge_media_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    source_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    media_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    url_or_ref: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    caption: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    transcript: Mapped[str] = mapped_column(Text, default="", nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class ExperienceGraphNode(Base):
    """One node in the living Experience Graph (Section 3): Person,
    Experience, Finding, Instrument, Anatomy, Recommendation, Outcome,
    Evidence, or Organization."""

    __tablename__ = "athena_experience_graph_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    node_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(500), nullable=False)

    # What real system this node was derived from, if any — e.g.
    # "competency_event"/"inspection_finding"/"root_cause_assignment"/
    # "capa"/"quality_policy"/"knowledge_article"/"reasoning_chain".
    # Never fabricated — blank when the node is a bare label (e.g. a
    # Person node with no linked record yet).
    source_type: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class ExperienceGraphEdge(Base):
    """One directed relationship between two Experience Graph nodes
    (Section 3)."""

    __tablename__ = "athena_experience_graph_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    from_node_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    to_node_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    relationship: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class KnowledgePreservationSession(Base):
    """An exit interview / video capture / voice transcription / workflow
    recording / procedure demonstration session (Section 10), optionally
    promoted into a structured `KnowledgeArticle` via
    `converted_article_id`. Converts tacit knowledge into organizational
    knowledge — never fabricates a transcript the human didn't provide."""

    __tablename__ = "athena_knowledge_preservation_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    subject_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    subject_role: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    session_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=SESSION_CAPTURED, nullable=False, index=True)

    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    transcript_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    topics_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    converted_article_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    captured_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)
