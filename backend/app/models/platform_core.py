"""v4.0 — LumenAI OS: Project Genesis — Platform Foundation & Modular
Architecture.

## What this file does and does NOT do

Genesis's mission is to "transform LumenAI from a single application into
a modular operating system." A literal rewrite — deleting and re-homing
every existing engine, route, and page into isolated packages — would
touch nearly every one of this codebase's 174+ files and 2800+ tests in
one sprint, which is neither safe nor how any of the eight prior
cross-cutting sprints (Sentinel, Symphony, Guardian, Atlas, Nexus,
Insight, Horizon, Beacon) operated. Every one of them was additive:
new tables, new services composing what already existed, new routes,
never a rewrite of existing engines.

Genesis follows that same precedent. It is the **composition and
registration layer** on top of everything that already exists:

  * **Identity/RBAC** — composes the four pre-existing, independent
    authz systems (`app/authz.py`, `app/enterprise_auth.py`,
    `app/auth/context.py::role_to_permissions`,
    `app/services/atlas_rbac_service.py`/`EnterpriseRoleAssignment`)
    into one canonical, read-only role catalog. It does not replace any
    of them — every existing `require_roles(...)` call site keeps working
    exactly as before.
  * **Tenant/Organization Management** — reads P16's existing
    `app/models/enterprise_hierarchy.py` (HealthSystem → Market → Region
    → Facility → Department) directly. No second hierarchy.
  * **Feature Flags** — reuses `app/models/feature_flag.py`/
    `app/entitlements.py` directly. No second flag table.
  * **Licensing** — extends `app/entitlements.py`'s per-tenant plan/
    entitlement resolution with a genuinely new concept entitlements
    didn't have: a per-tenant, per-*module* (Inspect/Twin/Knowledge/...)
    license row (`PlatformModuleLicense` below) — the module concept
    itself is new in this sprint, so there was nothing to reuse here.
  * **Audit Engine** — reuses `app/audit.py::log_audit_event` /
    `AuditLog` directly for every Genesis action. No second audit store.
  * **Notification Engine** — composes existing notification sources
    (`CaseNotification`, `WorkflowNotification`, `MobileNotification`)
    into one read-only unified feed in `platform_notification_service.py`.
    No new notification table.
  * **Event Bus** — reuses Nexus's `nexus_event_bus_service.publish` /
    `NexusEvent` / `NEXUS_EVENT_TYPES` directly (extended with a handful
    of new platform-level event types), rather than a second bus.
  * **Configuration** — this genuinely did not exist anywhere in this
    codebase before Genesis (confirmed: only narrow per-purpose config
    stores like `TenantSSOConfig`/`PilotSiteConfig` existed) — so
    `PlatformConfiguration` below is a real new additive table.

## The five genuinely new tables in this file

Nothing before Genesis modeled a "module" as a first-class object, a
per-tenant module license, a generic per-tenant/global configuration
key-value store, a plugin registration record, or per-user
favorite/recent module tracking — these are real gaps this sprint fills:

  * `PlatformModule` — the module registry (Inspect/Twin/Knowledge/
    Analytics/Command/Connect/Academy/Research/Developer/Marketplace),
    each describing which of this codebase's *already-existing* routes/
    pages it corresponds to (see `platform_module_registry_service.py`'s
    seed data) — a mapping/description layer, not a code relocation.
  * `PlatformModuleLicense` — per-tenant module entitlement.
  * `PlatformConfiguration` — per-tenant (or global, `tenant_id == ""`)
    key/value configuration store.
  * `PlatformPlugin` — the plugin registration surface (Section 8). This
    is a metadata registry a future module announces itself into
    (routes/menus/permissions/widgets/dashboards/reports it wants to
    contribute) — it is NOT a dynamic code-loading/sandboxed execution
    engine; no plugin code is ever imported or run by this table. Being
    explicit about that boundary here rather than overclaiming a
    capability this sprint does not actually build.
  * `PlatformFavoriteModule` / `PlatformRecentModule` — per-user launcher
    personalization (Section 4).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── The ten named modules (Section 3) ───────────────────────────────────────
MODULE_INSPECT = "inspect"
MODULE_TWIN = "twin"
MODULE_KNOWLEDGE = "knowledge"
MODULE_ANALYTICS = "analytics"
MODULE_COMMAND = "command"
MODULE_CONNECT = "connect"
MODULE_ACADEMY = "academy"
MODULE_RESEARCH = "research"
MODULE_DEVELOPER = "developer"
MODULE_MARKETPLACE = "marketplace"
MODULE_KEYS = [
    MODULE_INSPECT, MODULE_TWIN, MODULE_KNOWLEDGE, MODULE_ANALYTICS, MODULE_COMMAND,
    MODULE_CONNECT, MODULE_ACADEMY, MODULE_RESEARCH, MODULE_DEVELOPER, MODULE_MARKETPLACE,
]

LICENSE_ENABLED = "enabled"
LICENSE_DISABLED = "disabled"
LICENSE_TRIAL = "trial"
LICENSE_STATUSES = [LICENSE_ENABLED, LICENSE_DISABLED, LICENSE_TRIAL]

PLUGIN_DRAFT = "draft"
PLUGIN_ACTIVE = "active"
PLUGIN_DISABLED = "disabled"
PLUGIN_STATUSES = [PLUGIN_DRAFT, PLUGIN_ACTIVE, PLUGIN_DISABLED]

DISCLAIMER = (
    "LumenAI Platform Core composes and governs the applications, intelligence services, and "
    "administrative controls already present in this system. It does not itself make autonomous "
    "clinical or operational decisions. Every module remains subject to the RBAC, audit, and "
    "governance controls already enforced by the underlying application it registers."
)


class PlatformModule(Base):
    """A registered application module (Section 3)."""

    __tablename__ = "platform_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    module_key: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    nav_icon: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    routes_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON list of existing frontend route paths
    permissions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON list of roles permitted
    settings_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    documentation_url: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    is_core: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    release_channel: Mapped[str] = mapped_column(String(20), default="stable", nullable=False)  # stable/beta


class PlatformModuleLicense(Base):
    """Per-tenant module entitlement (Section 1 Licensing / Section 9)."""

    __tablename__ = "platform_module_licenses"
    __table_args__ = (UniqueConstraint("tenant_id", "module_key", name="uq_platform_module_license"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    module_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=LICENSE_ENABLED, nullable=False, index=True)
    granted_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class PlatformConfiguration(Base):
    """Per-tenant (or global, when `tenant_id == ""`) configuration
    key/value store (Section 1 Configuration)."""

    __tablename__ = "platform_configurations"
    __table_args__ = (UniqueConstraint("tenant_id", "config_key", name="uq_platform_configuration"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    tenant_id: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    config_key: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    config_value: Mapped[str] = mapped_column(Text, default="", nullable=False)
    updated_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class PlatformPlugin(Base):
    """A registered plugin (Section 8) — the metadata surface a future
    module announces itself into. This table never causes any code to be
    imported or executed; it is a registration/catalog record only."""

    __tablename__ = "platform_plugins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    plugin_key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="0.1.0", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=PLUGIN_DRAFT, nullable=False, index=True)

    registered_routes_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    registered_menus_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    registered_permissions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    registered_widgets_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    registered_dashboards_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    registered_reports_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    # v5.0 — Project Infinity Plugin SDK (Section 3): the remaining
    # extension-point types the SDK names that this table didn't yet
    # have. Still metadata-only — no code is ever imported or run from
    # any of these columns, same as the fields above.
    registered_workflow_nodes_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    registered_ai_skills_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    registered_notifications_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    registered_commands_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    registered_analytics_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    # Links this plugin registration to the third-party developer/listing
    # that published it, if any — blank/null for LumenAI's own core
    # modules (`is_core=True` on `PlatformModule`).
    developer_account_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    marketplace_listing_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    registered_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class PlatformFavoriteModule(Base):
    """A user's favorited module (Section 4)."""

    __tablename__ = "platform_favorite_modules"
    __table_args__ = (UniqueConstraint("tenant_id", "actor_email", "module_key", name="uq_platform_favorite"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    module_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)


class PlatformRecentModule(Base):
    """Tracks a user's most recently accessed modules (Section 4)."""

    __tablename__ = "platform_recent_modules"
    __table_args__ = (UniqueConstraint("tenant_id", "actor_email", "module_key", name="uq_platform_recent"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    module_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
