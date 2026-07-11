"""v5.0 — LumenAI OS: Project Infinity — Healthcare AI Platform &
Developer Ecosystem.

## Naming disambiguation (read this first)

Infinity is the 19th additive sprint, and by far the widest in surface
area (platform, marketplace, billing, security). Every existing
platform/marketplace/billing/API-versioning system was read in full
before writing any code:

  * **App/plugin registry**: Genesis's `platform_core.py` (v4.0) already
    has `PlatformModule`/`PlatformModuleLicense`/`PlatformPlugin` — the
    latter explicitly documented as "no plugin code is ever imported or
    run by this table," a metadata-only registration surface with
    `registered_routes_json`/`registered_menus_json`/
    `registered_widgets_json`/`registered_dashboards_json`/
    `registered_reports_json`. Infinity extends `PlatformPlugin` with the
    five extension-point types the Plugin SDK names that it didn't yet
    have (workflow nodes, AI skills, notifications, commands, analytics)
    plus a link to a `DeveloperAccount`/`MarketplaceListing`, rather than
    a second plugin-registration table. `MODULE_DEVELOPER`/
    `MODULE_MARKETPLACE` module keys already reserved by Genesis are
    reused as-is — Infinity does not invent new module keys.
  * **Module Licensing (Section 8)**: `PlatformModuleLicense` (Genesis)
    already tracks per-tenant module entitlement (enabled/disabled/
    trial). Infinity composes it directly for "Module Licensing" — no
    second license-per-module table.
  * **Workflow marketplace**: Forge's `WorkflowDefinition.
    marketplace_status` (`private/pending_review/published`,
    `forge_marketplace_service.py`) is a real, narrow marketplace for
    workflow templates only — no generic listing/author/pricing
    abstraction. Infinity's `MarketplaceListing` is a genuinely new,
    generic model for AI Skills and Applications, but reuses the exact
    same three-state naming for consistency.
  * **Versioned Public API**: Nexus's `/api/v1/*` gateway
    (`nexus_api_gateway.py`, v3.2) is already the "first genuinely
    versioned API prefix in this codebase," with dual bearer/API-key
    auth (`require_gateway_auth`) covering Instruments/Inspections/
    Digital-Twins/Knowledge/Enterprise. Infinity extends that same
    router with the remaining named systems (Identity/Organizations/
    Users/Analytics/Pulse/Sentinel/Forge/Catalyst/Orbit/Apollo/Athena/
    Phoenix) — it does not stand up a second versioned gateway.
  * **Secret API keys**: `nexus_credential_service.py`'s
    `secrets.token_urlsafe(40)` + SHA-256-hash-only pattern (raw key
    shown exactly once, never stored) is reused verbatim for
    `DeveloperApiKey` — a new model because it is issued to a
    `DeveloperAccount`, not a `NexusConnectorCredential`'s connector_id,
    but the issuance/validation logic is byte-for-byte the same pattern.
  * **Certification Program (Section 7)**: Forge's `WorkflowApprovalChain`/
    `WorkflowApprovalInstance` (v4.1, `forge_approval_service.py`) stores
    an arbitrary ordered list of role-string steps — already reused by
    Athena (v4.8) and Phoenix's 6-stage Continuous Validation (v4.9).
    Infinity reuses it a third time with 7 named gates (Security/
    Performance/Clinical Safety/Explainability/Accessibility/
    Documentation/Governance) — no new approval-chain model.
  * **Identity for third parties**: `TenantMembership`/`tenant_authz.py`
    model internal tenant staff only, resolved from a bearer JWT. Growth's
    `StrategicPartnership` (P-era) is commercial/BD metadata with no
    authentication linkage. Neither fits "a third-party developer
    building an app" — `DeveloperAccount` is a genuinely new, first-class
    identity, deliberately distinct from `TenantMembership`.
  * **Billing**: P14's `TenantPlan`/`PaymentEvent`/`TenantUsageCounter`
    are entirely inspection-volume subscription billing. There is no
    existing home for Enterprise/Partner licensing terms or marketplace
    revenue sharing — `PartnerLicense` and `MarketplaceRevenueEvent` are
    genuinely new.
  * **Sandbox**: `pilot_config.py`/`pilot_error_log.py` (v1.9) are a
    different, older "pilot" concept (customer/site sales-pilot
    configuration) — zero collision. `DeveloperSandboxSession` is
    genuinely new: an isolated, synthetic tenant scope for third-party
    development/testing/validation/certification with no production
    impact.

## Genuinely new tables in this file

  * `DeveloperAccount` / `DeveloperApiKey` — third-party developer
    identity and credentials, distinct from internal `TenantMembership`.
  * `MarketplaceListing` — a generic AI-Skill/Application listing,
    versioned, with a certification-chain link (reusing Forge's
    approval-chain primitive) and a pricing model.
  * `MarketplaceInstallation` — which tenant installed which listing.
  * `MarketplaceRevenueEvent` — marketplace revenue-sharing ledger.
  * `DeveloperSandboxSession` — an isolated dev/test/validation/
    certification session, scoped to a synthetic tenant_id, never
    production.
  * `PartnerLicense` — enterprise/partner commercial licensing terms,
    distinct from Genesis's per-module `PlatformModuleLicense`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Developer / partner org categories (mirrors the Application
# Marketplace's 7 named app categories, Section 5) ───────────────────────────
DEV_TYPE_HOSPITAL = "hospital"
DEV_TYPE_MANUFACTURER = "manufacturer"
DEV_TYPE_REPAIR_VENDOR = "repair_vendor"
DEV_TYPE_ACADEMIC = "academic"
DEV_TYPE_RESEARCH = "research"
DEV_TYPE_ENTERPRISE = "enterprise"
DEV_TYPE_CONSULTING = "consulting"
DEVELOPER_TYPES = [
    DEV_TYPE_HOSPITAL, DEV_TYPE_MANUFACTURER, DEV_TYPE_REPAIR_VENDOR, DEV_TYPE_ACADEMIC,
    DEV_TYPE_RESEARCH, DEV_TYPE_ENTERPRISE, DEV_TYPE_CONSULTING,
]

DEVELOPER_ACTIVE = "active"
DEVELOPER_SUSPENDED = "suspended"
DEVELOPER_STATUSES = [DEVELOPER_ACTIVE, DEVELOPER_SUSPENDED]

# ── Marketplace listing types + AI Skill categories (Section 4) ─────────────
LISTING_TYPE_AI_SKILL = "ai_skill"
LISTING_TYPE_APPLICATION = "application"
# Added for Project Olympus (v5.1) Section 8 — Innovation Marketplace reuses
# this exact listing model/certification/installation/revenue pipeline for
# its broader set of publishable content, rather than a second marketplace.
LISTING_TYPE_WORKFLOW_PACK = "workflow_pack"
LISTING_TYPE_KNOWLEDGE_PACK = "knowledge_pack"
LISTING_TYPE_TRAINING_MODULE = "training_module"
LISTING_TYPE_ANALYTICS_DASHBOARD = "analytics_dashboard"
LISTING_TYPE_RESEARCH_DATASET = "research_dataset"
LISTING_TYPE_SIMULATION_TEMPLATE = "simulation_template"
# Added for Project Nova (v5.4) Section 8 — Agent Marketplace reuses this
# exact listing model/certification/installation/revenue pipeline for
# installable agents, rather than a second marketplace.
LISTING_TYPE_INSPECTION_AGENT = "inspection_agent"
LISTING_TYPE_RESEARCH_AGENT = "research_agent"
LISTING_TYPE_MANUFACTURER_AGENT = "manufacturer_agent"
LISTING_TYPE_EDUCATION_AGENT = "education_agent"
LISTING_TYPE_COMPLIANCE_AGENT = "compliance_agent"
LISTING_TYPE_SIMULATION_AGENT = "simulation_agent"
LISTING_TYPES = [
    LISTING_TYPE_AI_SKILL, LISTING_TYPE_APPLICATION, LISTING_TYPE_WORKFLOW_PACK,
    LISTING_TYPE_KNOWLEDGE_PACK, LISTING_TYPE_TRAINING_MODULE, LISTING_TYPE_ANALYTICS_DASHBOARD,
    LISTING_TYPE_RESEARCH_DATASET, LISTING_TYPE_SIMULATION_TEMPLATE,
    LISTING_TYPE_INSPECTION_AGENT, LISTING_TYPE_RESEARCH_AGENT, LISTING_TYPE_MANUFACTURER_AGENT,
    LISTING_TYPE_EDUCATION_AGENT, LISTING_TYPE_COMPLIANCE_AGENT, LISTING_TYPE_SIMULATION_AGENT,
]

SKILL_CATEGORY_INSPECTION = "inspection"
SKILL_CATEGORY_KNOWLEDGE = "knowledge"
SKILL_CATEGORY_FORECAST = "forecast"
SKILL_CATEGORY_REPORTING = "reporting"
SKILL_CATEGORY_RESEARCH = "research"
SKILL_CATEGORY_EDUCATION = "education"
SKILL_CATEGORIES = [
    SKILL_CATEGORY_INSPECTION, SKILL_CATEGORY_KNOWLEDGE, SKILL_CATEGORY_FORECAST,
    SKILL_CATEGORY_REPORTING, SKILL_CATEGORY_RESEARCH, SKILL_CATEGORY_EDUCATION,
]

# Mirrors Forge's exact marketplace_status naming (workflow_forge.py) for
# consistency across this codebase's marketplace concepts.
LISTING_PRIVATE = "private"
LISTING_PENDING_REVIEW = "pending_review"
LISTING_PUBLISHED = "published"
LISTING_STATUSES = [LISTING_PRIVATE, LISTING_PENDING_REVIEW, LISTING_PUBLISHED]

PRICING_FREE = "free"
PRICING_SUBSCRIPTION = "subscription"
PRICING_ONE_TIME = "one_time"
PRICING_REVENUE_SHARE = "revenue_share"
PRICING_MODELS = [PRICING_FREE, PRICING_SUBSCRIPTION, PRICING_ONE_TIME, PRICING_REVENUE_SHARE]

CERT_NOT_STARTED = "not_started"
CERT_IN_PROGRESS = "in_progress"
CERT_CERTIFIED = "certified"
CERT_REJECTED = "rejected"
CERTIFICATION_STATUSES = [CERT_NOT_STARTED, CERT_IN_PROGRESS, CERT_CERTIFIED, CERT_REJECTED]

# ── Certification Program gates (Section 7) — the 7 named steps driven
# through the reused Forge WorkflowApprovalChain primitive. ──────────────────
GATE_SECURITY = "security"
GATE_PERFORMANCE = "performance"
GATE_CLINICAL_SAFETY = "clinical_safety"
GATE_EXPLAINABILITY = "explainability"
GATE_ACCESSIBILITY = "accessibility"
GATE_DOCUMENTATION = "documentation"
GATE_GOVERNANCE = "governance"
CERTIFICATION_GATES = [
    GATE_SECURITY, GATE_PERFORMANCE, GATE_CLINICAL_SAFETY, GATE_EXPLAINABILITY,
    GATE_ACCESSIBILITY, GATE_DOCUMENTATION, GATE_GOVERNANCE,
]

INSTALLATION_INSTALLED = "installed"
INSTALLATION_DISABLED = "disabled"
INSTALLATION_STATUSES = [INSTALLATION_INSTALLED, INSTALLATION_DISABLED]

# ── Developer Sandbox (Section 9) ────────────────────────────────────────────
SANDBOX_DEVELOPMENT = "development"
SANDBOX_TESTING = "testing"
SANDBOX_VALIDATION = "validation"
SANDBOX_CERTIFICATION = "certification"
SANDBOX_PURPOSES = [SANDBOX_DEVELOPMENT, SANDBOX_TESTING, SANDBOX_VALIDATION, SANDBOX_CERTIFICATION]

SANDBOX_ACTIVE = "active"
SANDBOX_EXPIRED = "expired"
SANDBOX_TERMINATED = "terminated"
SANDBOX_STATUSES = [SANDBOX_ACTIVE, SANDBOX_EXPIRED, SANDBOX_TERMINATED]

# ── Billing & Licensing (Section 8) ──────────────────────────────────────────
LICENSE_TYPE_MODULE = "module"
LICENSE_TYPE_ENTERPRISE = "enterprise"
LICENSE_TYPE_PARTNER = "partner"
PARTNER_LICENSE_TYPES = [LICENSE_TYPE_MODULE, LICENSE_TYPE_ENTERPRISE, LICENSE_TYPE_PARTNER]

PARTNER_LICENSE_ACTIVE = "active"
PARTNER_LICENSE_EXPIRED = "expired"
PARTNER_LICENSE_REVOKED = "revoked"
PARTNER_LICENSE_STATUSES = [PARTNER_LICENSE_ACTIVE, PARTNER_LICENSE_EXPIRED, PARTNER_LICENSE_REVOKED]

REVENUE_EVENT_SUBSCRIPTION = "subscription_charge"
REVENUE_EVENT_ONE_TIME = "one_time_purchase"
REVENUE_EVENT_USAGE = "usage_fee"
REVENUE_EVENT_TYPES = [REVENUE_EVENT_SUBSCRIPTION, REVENUE_EVENT_ONE_TIME, REVENUE_EVENT_USAGE]

DISCLAIMER = (
    "LumenAI Infinity extends the platform to trusted third-party developers and partner "
    "organizations under governed certification, licensing, and sandboxing controls. No "
    "marketplace listing, plugin, or extension ever executes third-party code inside this "
    "platform's core process, and no listing reaches production tenants without passing every "
    "certification gate and receiving explicit human approval."
)


class DeveloperAccount(Base):
    """A third-party developer/partner organization's identity (Sections
    1, 5) — deliberately distinct from `TenantMembership`, since a
    developer building an app is not necessarily tenant staff."""

    __tablename__ = "infinity_developer_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    organization_name: Mapped[str] = mapped_column(String(255), nullable=False)
    developer_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=DEVELOPER_ACTIVE, nullable=False, index=True)
    sandbox_only: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    approved_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DeveloperApiKey(Base):
    """A developer's API credential (Section 1 Authentication) — the
    exact `secrets.token_urlsafe(40)` + SHA-256-hash-only pattern already
    established in `nexus_credential_service.py`; the raw key is returned
    exactly once at issuance and never stored or retrievable again."""

    __tablename__ = "infinity_developer_api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    developer_account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    scopes_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    sandbox_only: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MarketplaceListing(Base):
    """One AI Skill or Application listing (Sections 4, 5) — a generic
    model distinct from Forge's workflow-only marketplace. Certification
    is tracked via a linked Forge `WorkflowApprovalChain`/`Instance`
    (`certification_chain_id`/`certification_instance_id`), never a
    second approval-chain model."""

    __tablename__ = "infinity_marketplace_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    developer_account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    listing_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(30), default="", nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="0.1.0", nullable=False)

    status: Mapped[str] = mapped_column(String(20), default=LISTING_PRIVATE, nullable=False, index=True)
    pricing_model: Mapped[str] = mapped_column(String(20), default=PRICING_FREE, nullable=False)
    price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)

    certification_status: Mapped[str] = mapped_column(String(20), default=CERT_NOT_STARTED, nullable=False, index=True)
    certification_chain_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    certification_instance_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    manifest_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class MarketplaceInstallation(Base):
    """Which tenant installed which listing (Section 5 — "Organizations
    choose which apps to install")."""

    __tablename__ = "infinity_marketplace_installations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    listing_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    installed_version: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=INSTALLATION_INSTALLED, nullable=False, index=True)
    installed_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class MarketplaceRevenueEvent(Base):
    """One marketplace revenue-sharing ledger entry (Section 8) — a
    genuinely new billing construct; no revenue-sharing concept existed
    anywhere in P14's inspection-volume billing infrastructure."""

    __tablename__ = "infinity_marketplace_revenue_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    listing_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    gross_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    developer_share_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    platform_share_cents: Mapped[int] = mapped_column(Integer, nullable=False)


class DeveloperSandboxSession(Base):
    """An isolated development/testing/validation/certification session
    (Section 9), scoped to a synthetic `sandbox_tenant_id` — never a real
    production tenant. `sandbox_tenant_id` is generated with a fixed
    prefix so it can never collide with, or be mistaken for, a real
    tenant_id."""

    __tablename__ = "infinity_developer_sandbox_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    developer_account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    listing_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sandbox_tenant_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    purpose: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=SANDBOX_ACTIVE, nullable=False, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PartnerLicense(Base):
    """Enterprise/partner commercial licensing terms (Section 8) —
    distinct from Genesis's per-module `PlatformModuleLicense`, which
    only carries an enabled/disabled/trial flag, not commercial terms."""

    __tablename__ = "infinity_partner_licenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    developer_account_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    license_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    licensed_module_keys_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    terms: Mapped[str] = mapped_column(Text, default="", nullable=False)
    revenue_share_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default=PARTNER_LICENSE_ACTIVE, nullable=False, index=True)
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expiration_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
