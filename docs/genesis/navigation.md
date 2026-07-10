# Project Genesis — Unified Navigation

LumenAI OS v4.0 — Sections 4, 5 & 6

## The Platform Launcher (Section 4)

`platform_navigation_service.launcher_view(db, tenant_id, role, actor_email)`
composes:

- **Visible modules** — `visible_modules()` intersects per-tenant
  licensing (`platform_licensing_service.list_licensed_module_keys`)
  with per-role permission (`PlatformModule.permissions_json`) — a
  module only appears if it is *both* licensed for the tenant *and*
  permitted for the caller's role.
- **Recent Applications** — `PlatformRecentModule`, updated via
  `record_recent_access()` whenever the frontend launcher opens a module
  tile (`POST /api/platform/navigation/recent`).
- **Favorites** — `PlatformFavoriteModule`, toggled via
  `POST`/`DELETE /api/platform/navigation/favorites/{module_key}`.
- **Notifications** — `platform_notification_service.unified_notifications`
  (Section 1 Notification Engine, composing `CaseNotification`/
  `WorkflowNotification`/`MobileNotification`).
- **Tasks** — the unread subset of that same unified notification feed.
- **Quick Search / Global Search** — see below (Section 5).

## Global Search (Section 5)

`platform_search_service.global_search(db, tenant_id, query)` is a
genuinely new cross-entity aggregator — no prior endpoint in this
codebase searched across entity types at once (only narrow per-entity
`GET /search` endpoints existed for instrument registry, baselines, and
knowledge articles). It queries, case-insensitively, across:

Digital Twins (`InstrumentFlowRecord`), Inspections, Knowledge
(`KnowledgeArticle` + `BaselineLibraryEntry`), Baselines, Users,
Facilities (`EnterpriseFacility`), Instrument Families
(`RegistryInstrument`), Anatomy (distinct `InspectionFinding.zone`
values), and Research (`ResearchStudy`) — each result tagged with the
module it belongs to, and results grouped by that module in the response.
No relevance score is fabricated beyond a simple substring match.

```
GET /api/platform/search?q=<term>
```

## Universal Activity Feed (Section 6)

`platform_activity_feed_service.universal_activity_feed(db, tenant_id)`
composes this platform's single existing `AuditLog` table (written by
every prior sprint's `_audit(...)` helper) and Nexus's `NexusEvent` bus
into one time-ordered feed. No new event-of-record table was added —
every item already had a durable row before this sprint. Each item is
tagged with the module it belongs to (via an `action_type`/`event_type`
prefix map) so the frontend can link every event back to its own
application.

```
GET /api/platform/activity-feed
```
