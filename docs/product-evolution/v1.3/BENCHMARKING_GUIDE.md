# LumenAI — Benchmarking Guide

Objectives 2 (Multi-Facility Benchmarking) and 3 (Best Practice Discovery) review.

## Multi-facility benchmarking — the 8 required metrics, verified against real code

| Metric | Real cross-facility comparison? | Basis |
|---|---|---|
| Inspection turnaround | **Computed per-tenant, never actually compared across facilities** | `or_connect_service.py`'s `inspection_turnaround_hours` and `beacon_repair_partner_service.py`'s `repair_turnaround` compute a single tenant's own figure — no leaderboard, percentile, or ranking exists |
| Quality performance | **Real, cross-facility** | `atlas_benchmarking_service.py::cross_facility_benchmark()` — genuine DB-backed comparison across facilities in one health system; `benchmark_engine.py` covers the same within one tenant grouped by facility |
| Evidence readiness | **Computed, not benchmarked across facilities** | `veritas_readiness_score_service.py` computes a real score per case; no cross-facility ranking found |
| Workflow efficiency | **No real cross-facility comparison** | `phoenix_learning_engine_service.py` only re-labels a single tenant's own duration-analysis stats as "workflow_efficiency" |
| Training completion | **Real, cross-facility** | `atlas_benchmarking_service.py`'s `training_progress_pct`, reused in `vanguard_benchmarking_service.py`'s knowledge-maturity benchmark |
| Reliability trends | **No real cross-facility comparison** | `benchmark_engine.py::compute_trend_series()` is per-tenant/per-subject, not a facility-vs-facility reliability comparison |
| Repair frequency | **Computed per-tenant/per-vendor, never compared across facilities** | `beacon_repair_intelligence_service.py`'s `repeat_repair_rate`/`avg_turnaround_days` are single-vendor figures |
| Risk distribution | **Real, cross-facility** | `benchmark_engine.py`'s board-report risk-distribution line, real per-hospital `risk_counts` |

**Net finding: 3 of 8 required benchmarking metrics (quality performance, training completion, risk distribution) have genuine, working cross-facility comparison code. The other 5 either don't exist as comparisons at all, or are computed per-facility but never actually placed alongside each other for ranking.** Any Version 1.3 benchmarking feature claiming full 8-metric coverage would be overstating what's currently built.

## The two cross-organization benchmarking engines — one real, one dead code over fabricated data

This is the most important governance finding in this document.

**`network_benchmark_service.py` (Project P15) — its claimed anonymization is dead code, and the data path it protects doesn't exist.** The file implements `_anonymize_facility_id()` (SHA-256 pseudonymization with monthly salt rotation) — but a repo-wide search confirms **this function is never called anywhere, including within its own file.** `compute_industry_benchmarks()` only reads real data if a pre-existing `IndustryBenchmark` row exists, and no code anywhere in the repository ever constructs one — so that branch can never fire, and the function always falls through to a seeded-mock fallback that fabricates values with `random.Random`. **The prior architectural claim that this service applies real pseudonymization to cross-organization data does not hold up under direct trace: there is no real facility data flowing through this function at all today.**

**`horizon_benchmark_service.py` (Project Horizon) is the genuinely real, correctly-anonymized cross-organization engine.** It computes real per-tenant metrics from actual `Inspection`/`InspectionFinding`/`RepairRequest`/`KnowledgeArticle`/`InstrumentFlowRecord` rows for real enrolled organizations, but its public API never returns per-tenant values — only a percentile band (below_p25 … above_p90) plus an aggregate median, with Laplace noise and a real `MIN_FACILITIES = 5` k-anonymity suppression threshold. No facility or tenant identity is ever exposed. This is wired end-to-end into the Collaboration Hub's "Industry Benchmarks" tab and is real, working, privacy-preserving code.

**Recommendation**: any Version 1.3 cross-organization benchmarking feature should build on `horizon_benchmark_service.py`'s pattern (percentile bands, Laplace noise, k≥5 suppression), not `network_benchmark_service.py`'s. If `network_benchmark_service.py` is ever wired to real `IndustryBenchmark` data in the future, its unused `_anonymize_facility_id` function must actually be called at that point — the file's current structure doesn't prevent a raw-facility-ID leak if someone starts writing real rows without also connecting the anonymization step.

## Within-organization vs. cross-organization identity disclosure — mostly handled correctly

- `atlas_benchmarking_service.py` correctly shows real facility names/tenant identity — appropriate since it's scoped to facilities under one health system's own `system_id` (subject to the authorization gap documented in `ENTERPRISE_OPERATIONS.md`).
- `horizon_benchmark_service.py` correctly suppresses all per-tenant identity for cross-organization comparison.
- `olympus_exchange_service.py` correctly gates `source_tenant_id` visibility — only the actual source tenant sees its own identity in a published package.
- `network_benchmark_service.py` is the one file whose anonymization claim doesn't correspond to any executed code path, per the finding above.

## Best Practice Discovery — does not exist

**No code anywhere in this repository identifies a top-performing facility across a network and generates an evidence-backed recommendation to replicate its practices.** Specifically:
- `phoenix_recommendation_engine.py::generate_recommendations()` is real and genuinely evidence-backed, but entirely introspective — it looks at one tenant's own AI drift, low-confidence zones, knowledge gaps, and coaching opportunities, never at other facilities' relative performance.
- The Collaboration Hub's "Roadmap Recommendations" tab is backed by `beacon_advisory_board_service.py::propose_recommendation()` — a **manually human-entered** board-meeting action item (a person types in a title/rationale/target area), not an algorithmically-derived best-practice recommendation.
- The Collaboration Hub's "Industry Benchmarks" tab does produce real ranking data (via the Horizon engine above), but only as anonymized percentile bands — it structurally cannot surface "facility X is the top performer, here's what they do differently," since facility identity is deliberately suppressed by design.

**This is a genuine, unbuilt capability, not a fragmented/hidden one** — unlike most other gaps in this Version 1.3 review, there is no existing code to wire up or consolidate here. Building it would require either (a) a within-organization version (since Atlas already shows real facility identity within one system_id, a "top-performing facility in your health system" feature is buildable today), or (b) a genuinely new anonymized-recommendation-generation layer for cross-organization best-practice discovery, which does not exist in any form.

## Recommendation

1. Do not claim full 8-metric benchmarking coverage — only quality performance, training completion, and risk distribution are genuinely real cross-facility comparisons today.
2. Build any new cross-organization benchmarking on `horizon_benchmark_service.py`'s pattern, not `network_benchmark_service.py`'s.
3. "Best Practice Discovery" as specified in this brief does not exist and would be new work — scope it as a within-organization feature first (buildable from Atlas's already-real facility identity data), before attempting a cross-organization anonymized version.
