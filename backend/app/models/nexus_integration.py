"""v3.2 — Project Nexus: Connected Healthcare Intelligence Platform.

Mission: LumenAI enriches external hospital-system data with anatomy-aware
clinical intelligence. It does not become the system of record for every
workflow, and it does not fabricate what an external system hasn't actually
sent — every synced record carries real provenance, and a connector that
isn't configured honestly reports zero records rather than inventing them.

## Reuse, not a second integration stack

This codebase already has a substantial P17 "Healthcare Quality & Safety
Ecosystem Integration" layer (`app/models/integrations.py`,
`app/routes/integrations.py`, `app/services/connectors/`) covering CSV/API
import of clinical tracking, quality/safety, and infection-prevention data
from CensiTrac, SPM, and several other named systems, with its own
`ExternalSystemConnection` registry, `BaseConnector` ABC, and nightly
scheduler. Project Nexus is a different axis, not a duplicate of it:

- P17 = *clinical data import* for correlation/quality analysis (PHI-
  stripped event records, quarantine table, correlation candidates).
- Nexus = the *platform integration framework* this sprint asks for:
  connector registry + versioning + health/retry/auth, instrument/tray/
  asset synchronization linked to the Digital Twin, work-queue sync,
  identity/SSO integration with role mapping, an internal typed event
  bus, and a versioned `/api/v1/*` API gateway.

Where the same named system appears in both (CensiTrac, SPM), Nexus's
connector adapters (`app/services/nexus_connectors/adapters.py`) reuse
the existing `BaseConnector` ABC and, where practical, the existing
`CensiTracCSVConnector`/`SPMCSVConnector` implementations rather than
re-parsing the same CSV formats a second time. Epic, Cerner, Oracle ERP,
SAP, CMMS, Active Directory, and SSO (OIDC/SAML) are genuinely new
connector types this sprint adds.

Auth reuse: Nexus's OIDC/Azure AD/Entra ID support plugs into the already
production-capable `app/auth/jwks_validator.py` (JWKS signature
verification) and `app/auth/jwt_validator.py` (claims mapping) rather than
reimplementing JWT verification. SAML has no prior art in this codebase —
Nexus's SAML support is config + claims-mapping only (parses an IdP's
already-verified assertion attributes), not a full cryptographic SAML
Service Provider implementation; this is documented in
`docs/nexus/identity-integration.md` and is not represented as more than
it is.

Secret handling reuses the exact `secrets.token_urlsafe(40)` +
SHA-256-hash-only pattern already used twice in this codebase
(`routes/capture.py`'s device registration, `routes/p25_infrastructure.py`'s
`issue_api_credential`) — a raw connector credential is returned exactly
once at issuance and never stored or retrievable again.

## Nine additive tables

  * NexusConnector — per-tenant registered/enabled connector instance
    (registry + versioning + health fields), distinct from P17's
    `ExternalSystemConnection` (see above).
  * NexusConnectorCredential — issued API credential, key hash only.
  * NexusConnectorErrorLog — connector-level error log (Section 1).
  * NexusSyncRun — one execution of an asset or work-queue sync, with
    retry bookkeeping (attempt_number/max_attempts).
  * NexusSyncedAsset — a synchronized instrument/tray/asset record with
    full provenance, optionally linked to the SPD Digital Twin
    (`InstrumentFlowRecord`) by instrument_id.
  * NexusWorkQueueLink — an optional link between an internal work-queue
    item (inspection/repair/etc.) and its external-system counterpart.
  * NexusIdentityMapping — external directory group -> internal role.
  * NexusEvent — a persisted event-bus event.
  * NexusEventSubscription — a registered event-bus subscriber.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Connector categories & catalog ──────────────────────────────────────────
CATEGORY_SPD_TRACKING = "spd_tracking"
CATEGORY_ERP = "erp"
CATEGORY_CMMS = "cmms"
CATEGORY_EHR = "ehr"
CATEGORY_IDENTITY = "identity"
CATEGORY_SSO = "sso"

AUTH_API_KEY = "api_key"
AUTH_OAUTH2 = "oauth2"
AUTH_OIDC = "oidc"
AUTH_SAML = "saml"
AUTH_SERVICE_ACCOUNT = "service_account"
NEXUS_AUTH_TYPES = [AUTH_API_KEY, AUTH_OAUTH2, AUTH_OIDC, AUTH_SAML, AUTH_SERVICE_ACCOUNT]

# Static registry of connector *types* this platform knows how to build an
# adapter for (Section 2). A `NexusConnector` row is a specific tenant's
# enabled *instance* of one of these catalog entries.
NEXUS_CONNECTOR_CATALOG = [
    {"connector_key": "censitrac", "display_name": "CensiTrac", "category": CATEGORY_SPD_TRACKING, "default_auth_type": AUTH_API_KEY, "default_version": "1.0.0"},
    {"connector_key": "spm", "display_name": "SPM", "category": CATEGORY_SPD_TRACKING, "default_auth_type": AUTH_API_KEY, "default_version": "1.0.0"},
    {"connector_key": "epic", "display_name": "Epic (SMART on FHIR)", "category": CATEGORY_EHR, "default_auth_type": AUTH_OAUTH2, "default_version": "1.0.0"},
    {"connector_key": "cerner", "display_name": "Oracle Health / Cerner", "category": CATEGORY_EHR, "default_auth_type": AUTH_OAUTH2, "default_version": "1.0.0"},
    {"connector_key": "oracle_erp", "display_name": "Oracle ERP Cloud", "category": CATEGORY_ERP, "default_auth_type": AUTH_OAUTH2, "default_version": "1.0.0"},
    {"connector_key": "sap", "display_name": "SAP", "category": CATEGORY_ERP, "default_auth_type": AUTH_OAUTH2, "default_version": "1.0.0"},
    {"connector_key": "cmms", "display_name": "CMMS (Clinical Engineering)", "category": CATEGORY_CMMS, "default_auth_type": AUTH_API_KEY, "default_version": "1.0.0"},
    {"connector_key": "active_directory", "display_name": "Active Directory / Azure AD", "category": CATEGORY_IDENTITY, "default_auth_type": AUTH_SERVICE_ACCOUNT, "default_version": "1.0.0"},
    {"connector_key": "sso_oidc", "display_name": "SSO (OIDC)", "category": CATEGORY_SSO, "default_auth_type": AUTH_OIDC, "default_version": "1.0.0"},
    {"connector_key": "sso_saml", "display_name": "SSO (SAML)", "category": CATEGORY_SSO, "default_auth_type": AUTH_SAML, "default_version": "1.0.0"},
]
NEXUS_CONNECTOR_KEYS = [c["connector_key"] for c in NEXUS_CONNECTOR_CATALOG]

STATUS_ENABLED = "enabled"
STATUS_DISABLED = "disabled"
NEXUS_CONNECTOR_STATUSES = [STATUS_ENABLED, STATUS_DISABLED]

HEALTH_HEALTHY = "healthy"
HEALTH_DEGRADED = "degraded"
HEALTH_ERROR = "error"
HEALTH_UNKNOWN = "unknown"
NEXUS_HEALTH_STATUSES = [HEALTH_HEALTHY, HEALTH_DEGRADED, HEALTH_ERROR, HEALTH_UNKNOWN]

# ── Sync runs ────────────────────────────────────────────────────────────────
RUN_TYPE_INSTRUMENT = "instrument"
RUN_TYPE_TRAY = "tray"
RUN_TYPE_WORK_QUEUE = "work_queue"
RUN_TYPE_IDENTITY = "identity"
NEXUS_SYNC_RUN_TYPES = [RUN_TYPE_INSTRUMENT, RUN_TYPE_TRAY, RUN_TYPE_WORK_QUEUE, RUN_TYPE_IDENTITY]

SYNC_STATUS_RUNNING = "running"
SYNC_STATUS_COMPLETED = "completed"
SYNC_STATUS_FAILED = "failed"
SYNC_STATUS_RETRYING = "retrying"
NEXUS_SYNC_STATUSES = [SYNC_STATUS_RUNNING, SYNC_STATUS_COMPLETED, SYNC_STATUS_FAILED, SYNC_STATUS_RETRYING]
DEFAULT_MAX_SYNC_ATTEMPTS = 3

# ── Work queue sync (Section 4) ─────────────────────────────────────────────
QUEUE_INSPECTION = "inspection"
QUEUE_REPAIR = "repair"
QUEUE_VENDOR_TRAY = "vendor_tray"
QUEUE_LOANER = "loaner"
QUEUE_PENDING_CASE = "pending_case"
NEXUS_QUEUE_TYPES = [QUEUE_INSPECTION, QUEUE_REPAIR, QUEUE_VENDOR_TRAY, QUEUE_LOANER, QUEUE_PENDING_CASE]

SYNC_DIRECTION_IMPORT_ONLY = "import_only"
SYNC_DIRECTION_EXPORT_ENABLED = "export_enabled"
NEXUS_SYNC_DIRECTIONS = [SYNC_DIRECTION_IMPORT_ONLY, SYNC_DIRECTION_EXPORT_ENABLED]

# ── Identity integration (Section 5) ────────────────────────────────────────
# Deliberately this sprint's own six labels, not Atlas's seven-role
# `ENTERPRISE_ROLES` (`app/models/atlas_enterprise.py`) — the sprint names a
# distinct set (Technician/Supervisor/Manager/Director/Administrator/
# Viewer). Kept separate rather than force-fit onto Atlas's hierarchy-scoped
# roles, which serve a different purpose (facility/market/system RBAC
# scoping). `docs/nexus/identity-integration.md` documents the closest
# correspondence for operators who use both.
ROLE_TECHNICIAN = "technician"
ROLE_SUPERVISOR = "supervisor"
ROLE_MANAGER = "manager"
ROLE_DIRECTOR = "director"
ROLE_ADMINISTRATOR = "administrator"
ROLE_VIEWER = "viewer"
NEXUS_IDENTITY_ROLES = [ROLE_TECHNICIAN, ROLE_SUPERVISOR, ROLE_MANAGER, ROLE_DIRECTOR, ROLE_ADMINISTRATOR, ROLE_VIEWER]
DEFAULT_IDENTITY_ROLE = ROLE_VIEWER  # least privilege when no mapping matches

# ── Event bus (Section 6) ────────────────────────────────────────────────────
EVENT_INSPECTION_COMPLETED = "InspectionCompleted"
EVENT_SUPERVISOR_APPROVED = "SupervisorApproved"
EVENT_REPAIR_RECOMMENDED = "RepairRecommended"
EVENT_KNOWLEDGE_UPDATED = "KnowledgeUpdated"
EVENT_BASELINE_PUBLISHED = "BaselinePublished"
EVENT_DIGITAL_TWIN_UPDATED = "DigitalTwinUpdated"
EVENT_ENTERPRISE_ALERT_CREATED = "EnterpriseAlertCreated"
NEXUS_EVENT_TYPES = [
    EVENT_INSPECTION_COMPLETED, EVENT_SUPERVISOR_APPROVED, EVENT_REPAIR_RECOMMENDED,
    EVENT_KNOWLEDGE_UPDATED, EVENT_BASELINE_PUBLISHED, EVENT_DIGITAL_TWIN_UPDATED, EVENT_ENTERPRISE_ALERT_CREATED,
]

SUBSCRIPTION_TARGET_WEBHOOK = "webhook"
SUBSCRIPTION_TARGET_INTERNAL = "internal"
NEXUS_SUBSCRIPTION_TARGET_TYPES = [SUBSCRIPTION_TARGET_WEBHOOK, SUBSCRIPTION_TARGET_INTERNAL]

DISCLAIMER = (
    "Project Nexus synchronizes and links data already present in connected systems — it never fabricates "
    "instrument, work-queue, or identity records that a connector hasn't actually supplied. Every synchronized "
    "record carries source-system provenance; role mappings default to least privilege (Viewer) when no mapping "
    "matches. No external integration bypasses RBAC, audit logging, or supervisor validation."
)


class NexusConnector(Base):
    """A tenant's registered instance of a catalog connector — the registry."""
    __tablename__ = "nexus_connectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    connector_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    auth_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=STATUS_DISABLED, nullable=False, index=True)
    config_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    health_status: Mapped[str] = mapped_column(String(20), default=HEALTH_UNKNOWN, nullable=False, index=True)
    last_health_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


class NexusConnectorCredential(Base):
    """An issued connector credential. Only the SHA-256 hash is stored."""
    __tablename__ = "nexus_connector_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    connector_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    scopes_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    issued_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NexusConnectorErrorLog(Base):
    """Connector-level error log (Section 1: Error Logging)."""
    __tablename__ = "nexus_connector_error_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    connector_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sync_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    error_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)


class NexusSyncRun(Base):
    """One execution of an asset or work-queue synchronization, with retry bookkeeping."""
    __tablename__ = "nexus_sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connector_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    run_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=SYNC_STATUS_RUNNING, nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=DEFAULT_MAX_SYNC_ATTEMPTS, nullable=False)
    records_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)


class NexusSyncedAsset(Base):
    """A synchronized instrument/tray/asset record with full provenance.

    Optionally linked to the SPD Digital Twin (`InstrumentFlowRecord`,
    `app/models/digital_twin.py`) by `digital_twin_instrument_id`.
    """
    __tablename__ = "nexus_synced_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    connector_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    external_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False)  # instrument|tray
    manufacturer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    model: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    repair_status: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    location: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    service_status: Mapped[str] = mapped_column(String(50), default="", nullable=False)

    digital_twin_instrument_id: Mapped[str] = mapped_column(String(200), default="", nullable=False)

    # Provenance (Section 9: Data Governance)
    source_system: Mapped[str] = mapped_column(String(50), nullable=False)
    conflict_resolution: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    last_conflict_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NexusWorkQueueLink(Base):
    """A link between an internal work-queue item and its external counterpart."""
    __tablename__ = "nexus_work_queue_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    connector_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    queue_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    internal_ref_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    external_ref_id: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    sync_direction: Mapped[str] = mapped_column(String(20), default=SYNC_DIRECTION_IMPORT_ONLY, nullable=False)


class NexusIdentityMapping(Base):
    """External directory/SSO group -> internal role mapping (Section 5)."""
    __tablename__ = "nexus_identity_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    connector_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    external_group: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    mapped_role: Mapped[str] = mapped_column(String(30), nullable=False)
    auto_provision: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class NexusEvent(Base):
    """A persisted event-bus event (Section 6)."""
    __tablename__ = "nexus_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    actor: Mapped[str] = mapped_column(String(255), default="system", nullable=False)
    subscriber_delivery_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class NexusEventSubscription(Base):
    """A registered event-bus subscriber (Section 6)."""
    __tablename__ = "nexus_event_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    connector_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)  # webhook|internal
    target: Mapped[str] = mapped_column(String(500), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
