"""v3.1 — Project Atlas: Enterprise Intelligence & Multi-Site Operations.

Builds on top of the existing P16 organization hierarchy
(`app/models/enterprise_hierarchy.py`: HealthSystem -> EnterpriseMarket ->
EnterpriseRegion -> EnterpriseFacility -> EnterpriseDepartment), which
already has full CRUD (`app/routes/enterprise_hierarchy.py`) and already
models "hospital" as a distinct `tenant_id` (`EnterpriseFacility.tenant_id`)
— confirmed by `enterprise_dashboards.py::system_quality_dashboard`, which
already iterates a system's facilities and queries each one's `tenant_id`
independently. Atlas adopts this same convention: one health system spans
multiple tenant_ids (one per hospital), preserving true tenant isolation —
"each facility remains autonomous" — rather than introducing a second,
incompatible sub-tenant facility field alongside the three that already
exist (`Inspection.site_name`, `Inspection.facility_name`,
`CVInferenceRecord.facility_id`). Section 1 (Enterprise Organization Model)
needed no new tables or routes — it's already built; Atlas only adds the
cross-facility intelligence layered on top.

Every aggregation in this module reads counts/rates only (inspection
counts, finding-type counts, agreement rates, article counts) — never
patient-identifying data — so "never expose PHI" holds by construction,
consistent with every other cross-tenant surface in this codebase
(`global_intelligence.py`, `instrument_registry.py`).

Six additive tables:
  * FacilityIntelligenceSnapshot — Section 5, a persisted per-facility
    (per-tenant_id) score snapshot, reused for Section 7's trending.
  * EnterpriseWatchlistEntry — Section 4. Distinct from Sentinel's
    tenant-scoped `ClinicalWatchlistEntry` (which assumes higher
    risk_score = worse): this one is system_id-scoped (spans tenant_ids)
    and carries a `direction` (risk vs. improvement) since "Highest
    Knowledge Growth" and "Fastest Improvement" are positive-trend
    watchlists, not risk flags.
  * SharedKnowledgeArticle — Section 6, a publish-a-copy pattern (the
    source `KnowledgeArticle` is never mutated) with governance fields
    the sprint asks for that don't exist on `KnowledgeArticle` today
    (effective_date, sharing_scope).
  * EnterpriseAlert — Section 8, explainable cross-facility alerts.
  * ExecutiveReport — Section 9, persisted report metadata + export refs.
  * EnterpriseRoleAssignment — Section 10, scopes a role to a system/
    market/facility node in the existing hierarchy — the hierarchy models
    already have single-owner email fields (HealthSystem.admin_email,
    EnterpriseMarket.director_email, EnterpriseDepartment.manager_email);
    this supports the general many-user/many-role case RBAC needs.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Section 4 — Enterprise Watchlist entity types ──────────────────────────
ENTERPRISE_WATCHLIST_HOSPITAL = "hospital"
ENTERPRISE_WATCHLIST_INSTRUMENT_FAMILY = "instrument_family"
ENTERPRISE_WATCHLIST_MANUFACTURER = "manufacturer"
ENTERPRISE_WATCHLIST_FACILITY_REPAIR = "facility_repair"
ENTERPRISE_WATCHLIST_FACILITY_RECLEAN = "facility_reclean"
ENTERPRISE_WATCHLIST_KNOWLEDGE_GROWTH = "knowledge_growth"
ENTERPRISE_WATCHLIST_FASTEST_IMPROVEMENT = "fastest_improvement"
ENTERPRISE_WATCHLIST_EMERGING_TREND = "emerging_trend"
ENTERPRISE_WATCHLIST_ENTITY_TYPES = [
    ENTERPRISE_WATCHLIST_HOSPITAL, ENTERPRISE_WATCHLIST_INSTRUMENT_FAMILY, ENTERPRISE_WATCHLIST_MANUFACTURER,
    ENTERPRISE_WATCHLIST_FACILITY_REPAIR, ENTERPRISE_WATCHLIST_FACILITY_RECLEAN,
    ENTERPRISE_WATCHLIST_KNOWLEDGE_GROWTH, ENTERPRISE_WATCHLIST_FASTEST_IMPROVEMENT, ENTERPRISE_WATCHLIST_EMERGING_TREND,
]
DIRECTION_RISK = "risk"
DIRECTION_IMPROVEMENT = "improvement"

# ── Section 6 — sharing scope ───────────────────────────────────────────────
SHARE_SCOPE_FACILITY = "facility"
SHARE_SCOPE_MARKET = "market"
SHARE_SCOPE_SYSTEM_WIDE = "system_wide"
SHARE_SCOPES = [SHARE_SCOPE_FACILITY, SHARE_SCOPE_MARKET, SHARE_SCOPE_SYSTEM_WIDE]

# ── Section 9 — report audiences and cadence ────────────────────────────────
AUDIENCE_CEO = "ceo"
AUDIENCE_COO = "coo"
AUDIENCE_SPD_DIRECTOR = "spd_director"
AUDIENCE_MARKET_DIRECTOR = "market_director"
AUDIENCE_HOSPITAL_SUMMARY = "hospital_summary"
REPORT_AUDIENCES = [AUDIENCE_CEO, AUDIENCE_COO, AUDIENCE_SPD_DIRECTOR, AUDIENCE_MARKET_DIRECTOR, AUDIENCE_HOSPITAL_SUMMARY]

REPORT_MONTHLY = "monthly"
REPORT_QUARTERLY = "quarterly"
REPORT_ANNUAL = "annual"
REPORT_CADENCES = [REPORT_MONTHLY, REPORT_QUARTERLY, REPORT_ANNUAL]

# ── Section 10 — Enterprise RBAC roles ──────────────────────────────────────
ROLE_REGIONAL_ADMINISTRATOR = "regional_administrator"
ROLE_MARKET_DIRECTOR = "market_director"
ROLE_FACILITY_DIRECTOR = "facility_director"
ROLE_SPD_MANAGER = "spd_manager"
ROLE_SUPERVISOR = "supervisor"
ROLE_TECHNICIAN = "technician"
ROLE_VIEWER = "viewer"
ENTERPRISE_ROLES = [
    ROLE_REGIONAL_ADMINISTRATOR, ROLE_MARKET_DIRECTOR, ROLE_FACILITY_DIRECTOR,
    ROLE_SPD_MANAGER, ROLE_SUPERVISOR, ROLE_TECHNICIAN, ROLE_VIEWER,
]
SCOPE_SYSTEM = "system"
SCOPE_MARKET = "market"
SCOPE_FACILITY = "facility"
ROLE_SCOPES = [SCOPE_SYSTEM, SCOPE_MARKET, SCOPE_FACILITY]

DISCLAIMER = (
    "Project Atlas aggregates counts and rates already computed per facility — it never exposes patient-identifying "
    "data. Every enterprise comparison, benchmark, watchlist entry, and recommendation is a potential association "
    "for leadership awareness, not a causal or clinical determination; human review governs any resulting action, "
    "and each facility's own supervisors and local governance retain full authority over their own operations."
)


class FacilityIntelligenceSnapshot(Base):
    __tablename__ = "atlas_facility_intelligence_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    system_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    facility_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    digital_twin_health_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    supervisor_agreement_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    training_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    knowledge_index: Mapped[float | None] = mapped_column(Float, nullable=True)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class EnterpriseWatchlistEntry(Base):
    __tablename__ = "atlas_enterprise_watchlist_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    system_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    entity_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    entity_value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(20), default=DIRECTION_RISK, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SharedKnowledgeArticle(Base):
    __tablename__ = "atlas_shared_knowledge_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    shared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    system_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_article_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    category: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    approver: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    effective_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sharing_scope: Mapped[str] = mapped_column(String(20), default=SHARE_SCOPE_SYSTEM_WIDE, nullable=False, index=True)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class EnterpriseAlert(Base):
    __tablename__ = "atlas_enterprise_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    system_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    alert_ref: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, default="", nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False, index=True)
    affected_facility_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledged_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class ExecutiveReport(Base):
    __tablename__ = "atlas_executive_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    system_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    report_ref: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    audience: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    cadence: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    period_label: Mapped[str] = mapped_column(String(50), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    generated_by: Mapped[str] = mapped_column(String(255), default="system", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class EnterpriseRoleAssignment(Base):
    __tablename__ = "atlas_enterprise_role_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # a system_id, market_id, or facility_id depending on scope_type
    scope_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    granted_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
