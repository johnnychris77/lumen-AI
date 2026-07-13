# LumenAI — Architecture Inventory

**Production Readiness Program · Phase 1: Foundation · Codename: Architecture Freeze & System Review**

## Architecture Freeze Declaration

> **LumenAI Version 1.0 Architecture Frozen.**
>
> As of this document, no new agent, module, dashboard, API, or workflow may be added to LumenAI without a formal architecture review against this inventory and the [Technical Debt Register](./TECHNICAL_DEBT_REGISTER.md). This freeze exists to let the platform consolidate before further feature growth — it does not freeze bug fixes, security fixes, or documentation.

This inventory is the baseline that future architecture reviews are checked against. It reflects the codebase as of this audit: **140 model files / 417 tables, 406 service files, 193 route files / 1859 endpoints, 110 frontend pages / 68 shared components, 773 documentation files, 192 test files (~2059 test cases per `CLAUDE.md`), 4 Alembic migrations.**

---

## 1. Frontend

React 18 + TypeScript + Vite, Tailwind v4 with a token-based design system (`frontend/src/index.css`), React Router for client-side routing, `AuthProvider`/`useAuth` for session state, a thin `apiFetch` client (`frontend/src/lib/api.ts`).

- **110 lazy-loaded page components** (`frontend/src/pages/*.tsx`), **68 shared components** (`frontend/src/components/*.tsx`), **15 design-system primitives** (`frontend/src/components/ui/*.tsx`: button, card, badge, alert, input, label, select, textarea, spinner, plus domain primitives like barcode-scanner and baseline-image-upload).
- **105 authenticated routes** declared in `main.tsx`, of which only ~65 have a corresponding entry in `AppShell.tsx`'s `NAV_GROUPS` — **~40 routes are reachable only by direct URL**, not through primary navigation (see Technical Debt Register, Finding TD-04).
- Two routes render outside the authenticated shell: `/login` and `/station` (kiosk/device-key auth).
- Client-side role gating (`ELEVATED_ROLES`/`EXECUTIVE_ROLES`) is explicitly documented in code as UX declutter only — the backend independently authorizes every request.

## 2. Backend

FastAPI + SQLAlchemy 2.0, Python. Entry point `backend/app/main.py` (~1100+ lines, almost entirely router-registration and startup-time model imports). `backend/app/db/models.py` is the de facto model-aggregation surface (189 lines, ~45 import statements across ~30 blocks) — `app/models/__init__.py` is a near-empty legacy stub that only re-exports 4 classes.

- **140 model files / 417 tables** — see [DATABASE_CATALOG.md](./DATABASE_CATALOG.md).
- **406 service files** — the business-logic layer; almost 1:1 with the specialist/module structure (`<specialist>_<capability>_service.py`).
- **193 route files / 1859 endpoint decorators**, mounted at 91+ distinct `/api/*` prefixes — see [API_CATALOG.md](./API_CATALOG.md). **16 route files (~69 endpoints) are defined but never registered in `main.py`** — genuinely dead/unreachable API surface (Technical Debt Register, TD-01).
- Auth: `require_tenant_roles` (tenant-scoped RBAC dependency) used at 635 call sites; a simpler `get_current_user` dependency used in 18 files with no automatic tenant-membership check.

## 3. Database

SQLite locally / Postgres in production, SQLAlchemy 2.0 declarative models. **417 tables** across 140 files. Only **4 Alembic migrations** exist (`001_initial_schema.py`, a large `full_schema_baseline` squash migration, and two recent incremental migrations for Steward and Oracle) — the overwhelming majority of the schema's growth relied on `Base.metadata.create_all()` rather than tracked migrations (Technical Debt Register, TD-02). Two duplicate-class situations exist: `TenantMembership` is defined independently in both `app/models/tenant_membership.py` and inline in `app/db/models.py` (different column sets, same table name); `EnterpriseFacility`/`EnterpriseDepartment` are defined with the same class names but different table names in `enterprise_quality.py` and `enterprise_hierarchy.py`. See [DATABASE_CATALOG.md](./DATABASE_CATALOG.md).

## 4. Vision Engine / Anatomy Engine

**No dedicated "Vision Engine" or "Anatomy Engine" specialist module exists.** This is a genuine ownership gap surfaced by this review, not an oversight in this document:

- **Vision**: CV/ML inference logic lives in `app/ai/inference.py` (`LumenAIModel.predict`, no specialist-style documentation), persisted results in `app/models/cv_inference.py` (one-line docstring, no composition/collision documentation), and per-inspection fields spread across the undocumented `app/models/inspection.py`. Nova's agent registry lists a `"vision_agent"` key, but its own service (`nova_core_agent_invocation_service.py`) marks it `reference_only` — Nova doesn't own or wrap a real Vision specialist, it just points at the inference file.
- **Anatomy**: the standardized anatomy taxonomy (`AnatomyProfile`) lives inside Genesis AI's model file (`genesis_ai_intelligence_cloud.py`), documented there as genuinely new because no anatomy-standardization table existed before it. The live per-inspection anatomy-zone *resolution* logic is a separate, older system: Phase 22's `app/agents/anatomy_agent.py` wrapping `app/services/instrument_zones.py`. Every specialist that references "anatomy" (21 model files do) just reads a zone string by field name; none of them own it.

**Recommendation**: formally designate either a real "Vision" and "Anatomy" specialist pair, or explicitly document in one place (this inventory) that these are intentionally cross-cutting capabilities rather than specialists — see Technical Debt Register, TD-03.

## 5. Inspection Engine

`app/models/inspection.py` (`Inspection` — the central record, no docstring, accumulated fields across many phases), `app/models/inspection_finding.py` (per-finding-type log), `app/models/inspection_image_tag.py` (guided-capture metadata), `app/models/cv_inference.py` (CV pipeline persistence). Composed by nearly every specialist as raw material.

## 6. Knowledge Graph

`app/services/knowledge_graph_service.py` (`explore()`, `reasoning_chain()`, `learning_confidence()`) — read by Maestro, Athena, Oracle, Sentinel-X. `app/models/knowledge.py` (`KnowledgeArticle`, `ClinicalCase`, `OrganizationStandard`, `KnowledgeQueryLog`) is the persisted knowledge store; Athena's `ExperienceGraphNode`/`ExperienceGraphEdge` extend it for institutional-memory graph traversal without duplicating the article store.

## 7. Digital Twin Engine(s)

**Three separate "digital twin" systems exist, deliberately distinct in scope** (each documents this in its own file):
- `app/models/digital_twin.py` (P10) — SPD workflow-station/instrument-flow simulation twin.
- `app/models/digital_quality_twin.py` (P22) — unified quality-state forecasting/what-if twin.
- Apollo's `QualityTwinSnapshot` (`apollo_quality.py`) — governance-health digital twin, composed by Oracle's Digital Twin Research rather than re-derived.

## 8. Evidence Engine

Project Veritas (`app/models/veritas_evidence.py`) — baseline governance, evidence provenance/readiness/conflict tracking, training-dataset curation. Composes Aegis's process-variation signal and Vulcan's reliability assessment by reference only.

## 9. Baseline Engine

`app/models/baseline_library.py` (P15 manufacturer/vendor/network baseline library with approval workflow) + `baseline_comparison_scoring_service.py`'s `resolve_baseline`, both consumed by Veritas's baseline-resolution governance layer.

## 10. Workflow Engine

Two generations: the legacy `app/models/workflow.py` (v1.7 — flat AND-only automation via `automation_engine.py`/`automation_rule.py`), and Project Forge (`workflow_forge.py`) — a nested-boolean-condition no-code rule engine with its own approval-chain (`WorkflowApprovalChain`) reused by five other specialists (GuardianX, Olympus, Infinity, Phoenix, Athena) rather than reimplemented each time.

## 11. Risk Engine

Three risk systems coexist, each documenting why it's distinct: legacy "Project Sentinel" (`sentinel_orchestration.py`, v3.0, advisory monitoring), the earlier `simulation_engine.py` (v2.5, predictive scenario engine, also historically called "Project Sentinel"), and Project Sentinel-X (`sentinelx_risk.py`) — the current composite clinical-risk/patient-safety specialist, deliberately prefixed `sentinelx_` and mounted at `/api/sentinelx` (frontend `/risk`) to avoid colliding with the older Sentinel.

## 12. Analytics

`app/models/benchmarking.py` (P5 multi-hospital benchmarking), `vendor_intelligence.py` (P6 vendor/manufacturer intelligence), `quality_intelligence.py` (P21 enterprise risk graph), plus Maestro/Vanguard/Pulse dashboards that read from these rather than maintaining separate analytics stores.

## 13. Authentication

`app/deps.py` — `get_current_user` (JWT via `_decode_jwt`, HS256) and a dev-token bypass gated by `ENABLE_DEV_AUTH` + `APP_ENV != production`. `app/routes/demo.py` has a **second, independently-gated** dev/demo bypass (`Bearer dev-token`/`demo-token` behind `DEMO_MODE=1`) — see Security Review below.

## 14. Authorization

`app/tenant_authz.py` — `require_tenant_roles(*roles)` dependency factory: resolves identity from a JWT/dev-token (never from headers), resolves `tenant_id`/`tenant_name` from `x-tenant-id`/`x-tenant-name` headers, and requires a matching enabled `TenantMembership` row before checking role membership. RBAC roles: `admin`, `spd_manager`, `operator`, `viewer`, `vendor_user` (plus some ad hoc role strings like `"technician"`/`"supervisor"`/`"biomed"` used in a few services — an unstandardized vocabulary, see Technical Debt Register TD-05).

## 15. Audit

`app/services/enterprise_audit_service.py` — genuine SHA-256 hash-chained, per-resource append-only audit log (`event_hash`, `previous_event_hash`), independently verifiable via `audit_chain_verification_service.py`. The legacy `app/audit.py` is deprecated and now delegates to this service.

## 16. API Gateway

Project Nexus (`nexus_integration.py`) — connector registry, sync engine, SSO/identity mapping, typed event bus (`NexusEvent`/`NexusEventSubscription`), `nexus_credential_service.py` (secret-key issuance pattern reused by 4+ other specialists). Distinct from the older `integrations.py` (P17), which is a one-way CSV/API import layer for external quality-safety systems (CensiTrac/SPM-style), not a gateway.

## 17. Notification Engine

`app/models/alert_event.py` (Slack/Teams/email dispatch log), `notification_template.py`, `digest_subscription.py`/`digest_delivery.py`, frontend `NotificationPanel.tsx` + `lib/notifications.tsx` (client-derived alert center over dashboard KPIs, not a push system).

## 18. Reporting

A large, loosely-coordinated set of report/briefing/packet models: `leadership_packet*.py`, `generated_briefing.py`, `portfolio_briefing.py`, `executive_scorecard.py`, `account_review_*.py`, `saved_report.py`/`report_run.py`, `distribution_list.py`/`distribution_recipient.py`. No single "Reporting Engine" module owns all of these — each report *type* has its own small table set (Technical Debt Register, TD-06).

## 19. Marketplace

Project Infinity (`infinity_platform.py`) — developer accounts/API keys, marketplace listings/installations/revenue events, sandbox sessions, partner licenses. Extends Genesis's (v4.0 platform core) `PlatformPlugin` rather than a second plugin-registration table.

## 20. Infrastructure

P25 (`p25_infrastructure.py`) — instrument digital identity, surgical readiness score, instrument passport events, global quality registry, industry API credentials. Frontend routes `/infrastructure` and `/instrument-passport`.

## 21. AI Specialists

25 named specialist subsystems (each with its own model file, service group, route file, and frontend workspace) plus the 3 legacy "P-number" platform sprints and the un-owned Vision/Anatomy/Aegis capabilities. Full detail in [AI_SPECIALIST_CATALOG.md](./AI_SPECIALIST_CATALOG.md): Council, Maestro, Oracle, Steward, Vulcan, Sage, Veritas, Sentinel-X, Apollo, Athena, Phoenix, GuardianX, Genesis AI, Nova, Olympus, Infinity, Beacon, Forge, Pulse, Catalyst, Orbit, Vanguard, plus legacy Sentinel/Insight/Guardian/Symphony/Atlas/Horizon.

## 22. Council

Project Council (`council_leadership.py`) — convenes existing specialists' real assessments into a single dissent-preserving human-decision record. Runs no independent analysis of its own; see the AI Specialist Catalog for its full composition list.

## 23. Execution Services

Project Steward (`governed_action.py`) is the governed execution layer for decisions already approved elsewhere (by Council, CAPA, Sentinel-X, etc.) — implementation planning, phased rollout, verification, benefits realization, closure. It never re-decides anything; it only executes and measures what a human already authorized.

---

## Cross-Cutting Notes

- **Naming-disambiguation convention**: ~20 of the newer specialist model files include an explicit "naming disambiguation" docstring section citing prior systems they must not collide with or duplicate. This is a real, working internal convention — it caught real potential collisions (Council vs. Olympus's Network Governance Council, Sentinel-X vs. legacy Sentinel, Catalyst vs. the P9 Copilot, Apollo vs. five pre-existing quality systems) before they happened. It did not, however, catch the two duplicate-class situations noted in §3.
- **"Aegis" has no model file** — it is a service-layer computation (`vulcan_aegis_integration_service.compute_process_variation_signal`) whose one persisted artifact lives inside Vulcan's own table. It is referenced as a first-class specialist name throughout Council/Steward/Maestro/Sentinel-X's vocabularies but has no independent data store or specialist status.
