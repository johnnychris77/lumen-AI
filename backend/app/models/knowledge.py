"""v1.8 — Institutional Knowledge & Clinical Memory.

Four additive tables, deliberately distinct from existing knowledge-adjacent
stores rather than overloading them:
  * KnowledgeArticle — user-authored institutional knowledge (best
    practices, local standards, lessons learned, FAQs, teaching points).
    Distinct from `education_library.py` (a fixed, code-generated reference
    for the 12 finding categories) and `InstrumentKnowledge` (manufacturer/
    model technical data) — this is what SPD staff write themselves, with
    governance (author/reviewer/approval/version/archive).
  * ClinicalCase — an auto-saved snapshot of a significant inspection
    (critical finding, supervisor override, or repair/remove-from-service
    outcome), preserving what happened and why for future reference.
  * OrganizationStandard — per-tenant local policy that supplements (never
    replaces) manufacturer IFUs.
  * KnowledgeQueryLog — every question asked of the AI Knowledge Assistant,
    for "most common questions" analytics.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Knowledge article categories ────────────────────────────────────────────
BEST_PRACTICE = "best_practice"
LOCAL_STANDARD = "local_standard"
APPROVED_WORKFLOW = "approved_workflow"
CLINICAL_PEARL = "clinical_pearl"
LESSON_LEARNED = "lesson_learned"
FAQ = "faq"
COMPETENCY_GUIDANCE = "competency_guidance"
MANUFACTURER_CLARIFICATION = "manufacturer_clarification"
TEACHING_POINT = "teaching_point"
# v4.8 — Project Athena additions (Institutional Memory Engine, Section 1):
# the only two memory types the brief names that had no existing home.
SUPERVISOR_EXPERIENCE = "supervisor_experience"
VENDOR_OBSERVATION = "vendor_observation"
REPAIR_OBSERVATION = "repair_observation"

ARTICLE_CATEGORIES = [
    BEST_PRACTICE, LOCAL_STANDARD, APPROVED_WORKFLOW, CLINICAL_PEARL,
    LESSON_LEARNED, FAQ, COMPETENCY_GUIDANCE, MANUFACTURER_CLARIFICATION, TEACHING_POINT,
    SUPERVISOR_EXPERIENCE, VENDOR_OBSERVATION, REPAIR_OBSERVATION,
]

# ── Governance approval states ───────────────────────────────────────────────
DRAFT = "draft"
PENDING_REVIEW = "pending_review"
APPROVED = "approved"
REJECTED = "rejected"
ARCHIVED = "archived"

APPROVAL_STATES = [DRAFT, PENDING_REVIEW, APPROVED, REJECTED, ARCHIVED]

# ── Organization standard types ──────────────────────────────────────────────
INSPECTION_STANDARD = "inspection_standard"
PHOTOGRAPHY_STANDARD = "photography_standard"
COVERAGE_REQUIREMENT = "coverage_requirement"
SUPERVISOR_APPROVAL_THRESHOLD = "supervisor_approval_threshold"
COMPETENCY_REQUIREMENT = "competency_requirement"

STANDARD_TYPES = [
    INSPECTION_STANDARD, PHOTOGRAPHY_STANDARD, COVERAGE_REQUIREMENT,
    SUPERVISOR_APPROVAL_THRESHOLD, COMPETENCY_REQUIREMENT,
]


class KnowledgeArticle(Base):
    __tablename__ = "knowledge_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    author: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    reviewer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    approval_status: Mapped[str] = mapped_column(String(20), default=DRAFT, nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Search facets — JSON-encoded lists kept as text for SQLite/Postgres
    # portability, blank/"[]" unless actually supplied (never fabricated).
    applicable_instruments: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    applicable_findings: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    applicable_manufacturers: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    anatomy_zone: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    procedure: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    specialty: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)

    # Teaching-point specific fields (Deliverable 3) — blank when not a
    # teaching_point-category article.
    common_mistake: Mapped[str] = mapped_column(Text, default="", nullable=False)
    prevention_tip: Mapped[str] = mapped_column(Text, default="", nullable=False)
    references: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # The inspection/override that prompted this article, if any (teaching
    # points and lessons learned are usually born from a real case).
    source_inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # v4.8 — Project Athena. Standard codes this article cites (e.g. AAMI
    # ST79 clauses), JSON-encoded like the other facet lists above — the
    # basis for the Knowledge Trust Score's "Reference Strength" component.
    linked_standards_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)


class ClinicalCase(Base):
    __tablename__ = "clinical_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    inspection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, unique=True)
    instrument_type: Mapped[str] = mapped_column(String(100), default="unknown", nullable=False, index=True)
    finding_type: Mapped[str] = mapped_column(String(40), default="", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    # JSON-encoded snapshot of the AI's findings at save time.
    ai_findings: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    supervisor_corrections: Mapped[str] = mapped_column(Text, default="", nullable=False)
    final_disposition: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    clinical_reasoning: Mapped[str] = mapped_column(Text, default="", nullable=False)
    educational_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    outcome: Mapped[str] = mapped_column(String(50), default="", nullable=False)

    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class OrganizationStandard(Base):
    __tablename__ = "organization_standards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    standard_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class KnowledgeQueryLog(Base):
    __tablename__ = "knowledge_query_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    actor: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    query_text: Mapped[str] = mapped_column(String(1000), nullable=False)
    matched_category: Mapped[str] = mapped_column(String(50), default="", nullable=False)
