# LumenAI — Version 1.3 Roadmap

Consolidates the findings across `ENTERPRISE_OPERATIONS.md`, `BENCHMARKING_GUIDE.md`, `NETWORK_ANALYTICS.md`, `CAPACITY_PLANNING.md`, and `ENTERPRISE_DASHBOARDS.md` into a prioritized sequence, per this program's Validation checklist.

## The central pattern across this entire Version 1.3 review

**Nearly every capability this brief asks for already exists in real, working code — built during an earlier phase of this platform's development (Projects Atlas, Vanguard, Horizon, Beacon, Olympus) — but it is fragmented across modules with overlapping scope, inconsistently wired to its own frontend, and in one important case, guarded by an authorization check that was built but never connected.** This mirrors the exact pattern found in every prior phase of this multi-phase review program: LumenAI's problem is consolidation and completion, not a shortage of underlying capability.

## Stage 0 — Security (must precede any other Version 1.3 work in this area) — **complete**

**Closed the `system_id` cross-organization authorization gap** documented in `ENTERPRISE_OPERATIONS.md`. Every Atlas enterprise route previously authorized only on role, never on organizational membership, meaning any authenticated user with an allowed role could view another health system's enterprise data. The fix — wiring the already-built `EnterpriseRoleAssignment`/`atlas_rbac_service` membership check into every data-serving route (Sections 2-9), plus an escalation-prevention check on the role-grant endpoint itself — has been implemented, tested (`TestSystemAccessEnforcement` in `test_atlas_enterprise.py`), and merged. See `ENTERPRISE_OPERATIONS.md`'s "Fixed" section for the full technical detail. Every other item in this roadmap can now safely build on these routes.

## Stage 1 — Fix confirmed runtime bugs (small, isolated, high-value)

- **Fix `/enterprise`'s missing `system_id` path parameter** (`ENTERPRISE_DASHBOARDS.md`) — the page currently always renders empty states despite working backend logic underneath.
- **Retire or rebuild `NetworkDashboardPage.tsx`** (`ENTERPRISE_OPERATIONS.md`) — it presents hardcoded demo data as if live, with a dead API call to a non-existent endpoint.

## Stage 2 — Consolidate fragmented, real capability (no new backend logic required)

- Wire Atlas's already-real cross-facility rollups (facility comparison, digital twin health, quality score, enterprise alerts) into the fixed `/enterprise` page, rather than building new aggregation logic.
- Consolidate Atlas's `SharedKnowledgeArticle` (governed sharing) and Beacon's advisory-board tracker into one documented "Cross-Facility Collaboration" feature area (`NETWORK_ANALYTICS.md`).
- Extend `generate_capacity_planning()` to call the two forecast types it already has access to but doesn't use — staffing (`FORECAST_SUPERVISOR_REVIEW_DEMAND`) and repair workload (`FORECAST_REPAIR_BACKLOG`) — closing 2 of 4 capacity-planning gaps with no new forecasting logic (`CAPACITY_PLANNING.md`).

## Stage 3 — Genuinely new work (no existing code to consolidate)

- **Best Practice Discovery does not exist in any form** (`BENCHMARKING_GUIDE.md`) — scope a within-organization version first (buildable from Atlas's real, non-anonymized facility identity data), before attempting a cross-organization anonymized version.
- A genuine `FORECAST_TRAINING_DEMAND` type, since no training-demand forecasting exists anywhere today.
- "Regional comparisons," "Benchmark reports," and "Improvement reports" as new Vanguard board-packet types (`ENTERPRISE_DASHBOARDS.md`).
- Real cross-facility comparison logic for "workflow efficiency" and "reliability trends" — currently only single-tenant figures exist under these labels (`BENCHMARKING_GUIDE.md`).

## Stage 4 — Governance clarity (documentation/labeling, not code)

- Either wire the existing `EnterpriseRoleAssignment` mechanism into real enforcement points for Enterprise/Regional/Facility/Department administration, or explicitly relabel this vocabulary as organizational personas rather than security tiers (`NETWORK_ANALYTICS.md`) — this decision should be made deliberately, not left ambiguous.
- If `network_benchmark_service.py` is ever wired to real data, its dormant anonymization function must be connected at that time, or the module should be retired in favor of `horizon_benchmark_service.py`'s already-correct pattern (`BENCHMARKING_GUIDE.md`).

## Validation against this program's checklist

| Item | Status |
|---|---|
| ✓ Enterprise dashboards function | **Not yet** — confirmed broken (`/enterprise`'s system_id bug, `NetworkDashboardPage.tsx`'s dead API call) until Stage 1 is complete |
| ✓ Benchmarking respects tenant isolation | **Yes** — Horizon's cross-org benchmarking is correctly anonymized; Atlas's within-org benchmarking is correct in its math and now sits behind the Stage 0 authorization fix |
| ✓ Executive reports generate correctly | **Yes, for the 4 real packet types** — PDF/Excel/PPTX generation is genuinely working; 2-3 of the brief's 6 named report types don't exist yet |
| ✓ Facility comparisons remain accurate | **Yes** — Atlas's facility-comparison logic is real and correct, and now only accessible to callers holding a real organizational scope grant |
| ✓ Permissions enforced | **Yes — Stage 0's authorization gap is fixed and tested** |
| ✓ Performance scales across enterprise deployments | Not evaluated in this review — no enterprise-scale load testing exists anywhere in this codebase (consistent with Phase 1's Production Readiness Scorecard finding of zero load-test infrastructure) |

## Definition of Done — honest status

This program's Definition of Done states Version 1.3 should enable "healthcare systems to operate LumenAI as a coordinated enterprise platform while maintaining security, privacy, governance, and organizational data ownership." **The security/data-ownership half of that statement is now true at the code level** — the `system_id`/`facility_id` authorization gap has been closed and is covered by explicit tests proving both that access is denied without a grant and that it succeeds once one is issued. Every other capability this brief describes is either already real (in fragmented form) or clearly scoped as new work; Stage 0 being complete is what makes it safe to build the rest of this roadmap on these routes.
