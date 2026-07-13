# LumenAI — Technical Debt Register

23 findings from this review, classified Critical / High / Medium / Low. Every item was verified by direct inspection during this audit (file paths, grep counts, or docstring citations) — none are speculative. IDs are referenced from the other Phase 1 deliverables; treat this register as the canonical numbering.

**Critical = should block or immediately follow the architecture freeze. High = should be scheduled early in Phase 2 (Production Hardening). Medium = should be scheduled in Phase 2 but not blocking. Low = track, revisit opportunistically.**

## Critical

### TD-02 — Untracked schema migration history
- **Issue**: Only 4 Alembic migration files exist for 417 tables across ~25 specialist sprints; the vast majority of schema growth relied on `Base.metadata.create_all()` rather than a tracked migration.
- **Impact**: No `alembic downgrade` path for ~23 sprints' worth of schema changes; production Postgres deployment risk if `create_all()` and actual schema ever drift silently.
- **Recommendation**: Run `alembic revision --autogenerate` against the current model state now, verify it produces an empty diff against the live schema, and require every future model change to go through Alembic (already established as convention for Steward/Oracle — extend it retroactively as a policy, not a one-time fix).
- **Priority**: Before Phase 2 begins.

### TD-09 — Executive dashboard may serve fabricated data
- **Issue**: Vanguard's own model-file docstring explicitly states that `/api/executive/dashboard` and `/api/enterprise/governance-intelligence` are pre-existing surfaces returning mock/fabricated data, which Vanguard deliberately does not build on.
- **Impact**: An executive-facing, decision-influencing dashboard may be showing non-real numbers today, with no UI indication that it's mock data.
- **Recommendation**: Immediately audit both named endpoints; either wire them to real data or add an explicit "demo/sample data" banner until they are. This is a trust issue, not a code-quality issue — treat with urgency disproportionate to its size.
- **Priority**: Immediate — this is user-facing and could mislead a real decision-maker today.

### TD-16 — Dev-auth bypass depends on correct environment configuration
- **Issue**: `ENABLE_DEV_AUTH` gates dev-token auth, but is only safe because `APP_ENV != "production"` is also required — and `APP_ENV` **defaults to `"development"` if the env var is missing entirely** (`os.getenv("APP_ENV", "development")`). A separate, independently-gated bypass also exists in `app/routes/demo.py` (`Bearer dev-token`/`demo-token` accepted whenever `DEMO_MODE=1`, with no `APP_ENV` check at all).
- **Impact**: If a production deployment ever omits `APP_ENV` (misconfiguration, not malice) while `ENABLE_DEV_AUTH=true` is set (e.g. leftover staging config), or if `DEMO_MODE=1` is ever set in production, a hardcoded literal token grants full role-based access with no real credential check — a direct violation of the repository's own non-negotiable security constraint ("Do not reintroduce hardcoded `Bearer dev-token`").
- **Recommendation**: Add a hard startup check that fails loudly if `ENABLE_DEV_AUTH=true` or `DEMO_MODE=1` while any indicator suggests a production deployment (hostname, a required `IS_PRODUCTION` flag with no unsafe default, etc.) rather than relying on `APP_ENV` being set correctly by convention alone.
- **Priority**: Before Phase 2 begins — this is a live security posture gap, not a hypothetical one.

## High

### TD-01 — 16 unregistered route files (~69 dead endpoints)
- **Issue**: `executive_decisions.py`, `tenant_remediations.py`, `governance_packet_exports.py`, `executive_escalations.py`, `executive_kpi_snapshots.py`, `enterprise_access_control.py`, `executive_kpi_scheduler.py`, `portfolio_briefing_deliveries.py`, `portfolio_briefing_schedules.py`, `enterprise_audit.py`, `portfolio_briefing_recurring_scheduler.py`, `executive_briefing_dashboard.py`, `auth.py`, `health.py`, `production_readiness.py`, `reviews.py` — real, working `APIRouter`s never imported into `main.py`.
- **Impact**: ~69 endpoints of dead, unreachable code; unclear whether these represent an abandoned feature (executive reporting) or accidental omission.
- **Recommendation**: Product/eng triage each file: register it, or delete it. Given the naming pattern (`executive_*`, `portfolio_briefing_*`), this looks like one coherent shelved feature area, not scattered cruft — resolve as one decision, not 16 individual ones.
- **Priority**: Early Phase 2.

### TD-11 — Inconsistent tenant-enforcement dependency usage
- **Issue**: 18 route files use the simpler `get_current_user` dependency instead of `require_tenant_roles`, which does not automatically verify tenant membership or scope queries.
- **Impact**: Tenant isolation on these 18 files depends entirely on each route author manually filtering by `tenant_id` — no structural guarantee.
- **Recommendation**: Audit each of the 18 files; either migrate to `require_tenant_roles` or explicitly document why the file is legitimately tenant-agnostic (e.g., true platform-admin routes).
- **Priority**: Early Phase 2 — directly touches the "tenant data isolation must be enforced" non-negotiable constraint.

### TD-14 — Duplicate `TenantMembership` class definition
- **Issue**: Defined independently in `app/models/tenant_membership.py` and inline in `app/db/models.py`, mapped to the same table, with different column sets.
- **Impact**: Which class a given file imports silently determines what columns/behavior it gets against the same underlying table — a latent, hard-to-diagnose bug source.
- **Recommendation**: Consolidate to one canonical class; this is a correctness risk, not just a style issue.
- **Priority**: Early Phase 2.

### TD-17 — Missing foreign-key constraints (134 of 140 model files)
- **Issue**: Only 6 files use a real `ForeignKey()`; the other 134 reference related rows via a plain, unconstrained `Integer` column.
- **Impact**: No database-level referential integrity anywhere in the schema outside those 6 files — orphaned child rows are possible with no DB-level detection.
- **Recommendation**: Start with the highest-integrity-value boundaries (audit/governance tables) rather than attempting all 134 files at once.
- **Priority**: Phase 2, incremental.

## Medium

### TD-03 — No dedicated Vision or Anatomy specialist module
- **Issue**: CV inference and anatomy-taxonomy ownership is spread across `cv_inference.py`, `inspection.py`, `app/ai/inference.py`, Genesis AI's `AnatomyProfile`, and the older `anatomy_agent.py`/`instrument_zones.py` — no single owning module for either.
- **Impact**: No naming-disambiguation documentation surface for these two capabilities the way every other specialist has one; future work risks accidentally building a second Vision or Anatomy system without realizing one is "already" (informally) owned elsewhere.
- **Recommendation**: Formally scope Vision/Anatomy as specialists, or formally ratify (in this document set) that they are intentionally cross-cutting infrastructure.
- **Priority**: Phase 2 architecture decision (candidate ADR).

### TD-04 — ~40 of 105 authenticated routes have no navigation entry
- **Issue**: Only ~65 of 105 authenticated frontend routes appear in `AppShell.tsx`'s `NAV_GROUPS`; the rest (including Beacon and Horizon's workspaces) are reachable only by direct URL.
- **Impact**: Real, shipped features may be effectively invisible to users who don't already know the URL.
- **Recommendation**: UX pass to either add nav entries for intentionally-shipped-but-unlinked pages, or confirm and formally deprecate ones that were superseded.
- **Priority**: Phase 2.

### TD-07 — Overlapping risk/monitoring and digital-twin systems
- **Issue**: Three risk/monitoring systems (`simulation_engine.py`, `sentinel_orchestration.py`, `sentinelx_risk.py`) and three digital-twin systems coexist, each independently documented as deliberately distinct.
- **Impact**: User- and operator-facing confusion (two things named "Sentinel"); ongoing maintenance burden of three parallel systems.
- **Recommendation**: Not a bug, but a strong candidate for a consolidation ADR — decide whether all three risk systems remain permanently distinct or should merge.
- **Priority**: Phase 2, product + architecture decision.

### TD-08 — Aegis has no independent specialist status
- **Issue**: Aegis has no model file; its one computation (`vulcan_aegis_integration_service.compute_process_variation_signal`) and its one persisted artifact live entirely inside Vulcan's table, yet 4 other specialists reference it as a first-class specialist name.
- **Impact**: Ambiguous ownership — if Aegis's scope grows, it's unclear whether that growth belongs in Vulcan or a new Aegis module.
- **Recommendation**: Formal decision (ADR) — either promote Aegis to a real specialist or formally ratify it as a permanent Vulcan sub-capability.
- **Priority**: Phase 2 architecture decision.

### TD-10 — Forge's approval chain is a single point of failure for 5 specialists
- **Issue**: `WorkflowApprovalChain` is reused directly by Athena, Phoenix, GuardianX, Olympus, and Infinity.
- **Impact**: A breaking change to Forge's approval-chain shape has a 5x blast radius.
- **Recommendation**: Treat `WorkflowApprovalChain`'s schema as a stable, versioned internal contract; any change needs a coordinated review across all 5 consumers.
- **Priority**: Process change, not code change — adopt now.

### TD-12 — No API versioning or deprecation convention
- **Issue**: No route file uses versioned prefixes (except Nexus's `/api/v1/*`) or `deprecated=True`.
- **Impact**: No safe path to evolve any of the 1859 endpoints without a breaking change to every existing consumer.
- **Recommendation**: Adopt a versioning convention before the next breaking API change is needed, not after.
- **Priority**: Phase 2, before it's needed urgently.

### TD-13 — Specialist routes take raw `dict` bodies instead of Pydantic models
- **Issue**: Nearly all specialist `POST`/`PATCH` routes accept a plain `dict` parameter rather than a typed Pydantic request model.
- **Impact**: No request-shape validation at the framework level (validation happens only inside the service, after the fact); OpenAPI schema for request bodies is uninformative (`{}`) for most of the API surface.
- **Recommendation**: Not urgent to retrofit all ~1800 endpoints, but any *new* route post-freeze should use typed request models — codify this in the architecture-review checklist this freeze establishes.
- **Priority**: Policy for new code; opportunistic retrofit for existing code.

### TD-15 — GuardianX and Beacon model tables lack `tenant_id`
- **Issue**: `guardianx_assurance.py` and `industry_collaboration.py` are the only two named-specialist model files without a `tenant_id` column, unlike every other specialist.
- **Impact**: Unclear if this is intentional (cross-tenant by design) or a gap, given both specialists are otherwise operated per-tenant in their UI.
- **Recommendation**: Confirm with the owning team whether this is deliberate; document the decision either way.
- **Priority**: Phase 2, quick confirmation.

### TD-18 — No database-level `CheckConstraint`s; only 3 files use `UniqueConstraint`
- **Issue**: Every enum-like string field across all 417 tables is validated only in Python service code; almost no natural uniqueness requirements (e.g., one membership row per tenant+user) are enforced by the database.
- **Impact**: A direct SQL write or a future service that bypasses the validated constructor path can insert invalid enum values or duplicate rows with no database objection; known race-condition class (concurrent check-then-insert) is open wherever a unique constraint is missing.
- **Recommendation**: Add `UniqueConstraint`s to the handful of tables where a race condition would have real consequences (tenant membership, API key issuance) first.
- **Priority**: Phase 2.

### TD-19 — No test coverage measurement tooling configured
- **Issue**: No `pytest-cov`/`coverage` entry in `requirements.txt` or `pyproject.toml`; true code coverage % is unknown.
- **Impact**: Can't quantify how much of the ~1859 endpoints / 406 services is actually exercised by the ~2059 test cases.
- **Recommendation**: Add `pytest-cov` and establish a baseline coverage number before setting any coverage gate.
- **Priority**: Phase 2.

### TD-20 — No dedicated load, performance, or end-to-end test suite
- **Issue**: `docs/platform/load-testing-plan.md` exists as a planning document, but no corresponding executable load-test file exists in `backend/tests/`; no filenames match "e2e" or "performance" at all.
- **Impact**: Production-readiness claims about scalability are currently unverified by any automated test.
- **Recommendation**: Build at least one executable load test against the highest-traffic endpoints (per API_CATALOG's top-25 list) before claiming production scalability.
- **Priority**: Phase 2, before scalability claims are made externally.

## Low

### TD-05 — Unstandardized role vocabulary beyond the core 4-role RBAC
- **Issue**: A few services reference ad hoc role strings (`"technician"`, `"supervisor"`, `"biomed"`) alongside the canonical `admin`/`spd_manager`/`operator`/`viewer`/`vendor_user` set.
- **Impact**: Low — these appear to be descriptive/display strings in a few services rather than enforced RBAC roles, but worth confirming none of them are silently used in an actual authorization check.
- **Recommendation**: Grep-audit these specific strings for any authorization-relevant usage; if purely descriptive, no action needed.
- **Priority**: Low, quick check.

### TD-06 — Reporting/briefing has no single owning module
- **Issue**: Report/briefing/packet functionality is spread across ~15 small, independently-evolving table sets with no unifying "Reporting Engine."
- **Impact**: Maintenance overhead of many small similar-shaped systems; unclear consolidated ownership.
- **Recommendation**: Consider a future consolidation, not urgent.
- **Priority**: Low.

### TD-21 — CORS configuration is a recurring regression risk
- **Issue**: `allow_credentials=True` combined with an origin regex; the code comments confirm this was previously wildcarded to `*.onrender.com` (a real, already-fixed vulnerability) before being pinned to the exact frontend host.
- **Impact**: Low today (currently correctly configured), but any future loosening of `CORS_ORIGINS`/the regex would reopen credentialed cross-origin access.
- **Recommendation**: Add an automated test asserting the CORS origin allowlist doesn't regress to a wildcard.
- **Priority**: Low, but cheap to add a regression test now.

### TD-22 — Stale/incomplete `__all__` exports and near-empty `app/models/__init__.py`
- **Issue**: `app/db/models.py`'s `__all__` lists only 6 names despite 45 import lines pulling in 100+ classes; `app/models/__init__.py` only re-exports 4 legacy classes and is effectively dead as an aggregation surface.
- **Impact**: Cosmetic/maintainability only — doesn't affect runtime behavior since imports work regardless of `__all__` correctness.
- **Recommendation**: Either maintain `__all__` properly or remove it to stop implying a contract that isn't kept.
- **Priority**: Low.

### TD-23 — Duplicate `EnterpriseFacility`/`EnterpriseDepartment` class names
- **Issue**: Same class names, different table names, in `enterprise_quality.py` and `enterprise_hierarchy.py`.
- **Impact**: Import-confusion risk (`from X import EnterpriseFacility` silently resolves to different schemas depending on which module), though not a data-integrity risk since the table names differ.
- **Recommendation**: Rename one pair for clarity (e.g. `EnterpriseHierarchyFacility`) at a low-risk moment.
- **Priority**: Low.
