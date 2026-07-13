# LumenAI — Performance Log

Objective 2 review. Grounded in a direct code audit rather than measured production metrics (no APM/latency instrumentation exists yet, per `docs/commercial-readiness/DEPLOYMENT_GUIDE.md`'s finding that `/metrics` is minimal and no Sentry/Datadog integration exists) — this log states what's verified in code, not fabricated benchmark numbers.

## API response time — one confirmed N+1 query pattern

`app/services/atlas_dashboard_service.py`'s enterprise/Atlas dashboard has a real, compounded N+1: `refresh_all_facility_intelligence()` calls `compute_facility_intelligence()` once per facility, and each call internally issues its own set of tenant-scoped queries across 6 sub-services (`executive_quality_score`, `run_sentinel_health_snapshot`, `compute_ai_health`, `list_open_flags`, `technician_quality_dashboard`, `learning_confidence`). `enterprise_dashboard()` then loops over the same facility list a second time, issuing one additional `db.query(models.Inspection)...` call per facility rather than a single `tenant_id IN (...)` query. For a system with many facilities, this is roughly 7 serialized queries per facility. **This is the one confirmed, fixable N+1 pattern found in this review** — the other three sampled dashboard services (`quality_dashboard_service.py`, `sentinel_dashboard_service.py`, `pulse_command_center_service.py`) operate on data already fetched in a single query per loop, not a query-per-iteration.

## Dashboard loading — no response caching exists anywhere

No `functools.lru_cache`, `cachetools`, or custom in-memory cache was found in `backend/app/services/` or `backend/app/routes/`. Redis is used exclusively as an RQ job queue, never as a response cache. **Every dashboard request — including the N+1-heavy Atlas enterprise dashboard — recomputes fully from scratch on every hit**, with no memoization of expensive, slowly-changing aggregates (e.g., a facility's quarterly quality score, which by definition doesn't change within a request-to-request timeframe).

## Image upload — no findings beyond what Phase 1 already covered

No new upload-path performance issue was found in this review beyond what's already documented; image handling has no PHI/content-scanning overhead added by this program.

## AI inference latency — inconsistent queuing, a real finding

`app/routes/stream.py` correctly enqueues AI inference to RQ (`q.enqueue(run_inspection, ...)`), keeping that endpoint non-blocking. **However, `app/routes/inspect.py`'s `stream_frame` route calls the identical `run_inspection` job function directly and synchronously**, inline in the request/event-loop path — this will block that specific endpoint for the full inference duration (real CV latency if a trained model is present, or the deterministic-fallback latency otherwise, per `docs/clinical-validation/FINDING_TAXONOMY.md`). This is a genuine, verifiable inconsistency: the same job function is treated as async-safe in one route and synchronous in another.

## Database queries — indexing is broadly present but shallow

1,439 `index=True` column declarations exist across 140 model files — foreign-key-like columns (`tenant_id`, `inspection_id`) are broadly single-column indexed. **However, zero composite/multi-column `Index(...)` objects exist anywhere in the model layer.** The N+1-adjacent dashboard queries in `atlas_dashboard_service.py` filter on combinations like `tenant_id` + `score_status`/`disposition`, which currently get no covering composite index and are partly resolved in Python after a broader fetch rather than at the database layer.

## Memory usage, CPU usage, network utilization — no verified findings

No profiling data, load-test results, or resource-utilization measurements exist anywhere in this repository (`docs/production-readiness/PRODUCTION_READINESS_SCORECARD.md` already flagged zero load-test files as a Critical Gap in Phase 1, unchanged since). This log does not fabricate numbers for these categories — they remain unmeasured.

## Rendering — frontend code-splitting is already well-handled

`frontend/src/main.tsx` wraps essentially every one of its ~130+ routes in `React.lazy()` with per-page `Suspense`/error boundaries — this is comprehensive, already-implemented route-level splitting, not a gap. `frontend/vite.config.ts` deliberately groups `recharts`+`d3` into a single stable `vendor-charts` chunk (449 KB / 136 KB gzipped, the largest chunk in the build) specifically to avoid stale-chunk 404s on hard refresh — this is documented, intentional design, not an oversight. The chunk's size reflects the inherent weight of charting libraries used across many analytics pages, not a missed optimization.

## Caching — the central gap this log identifies

There is no caching layer at any level of this application beyond the RQ job queue. This is the single highest-leverage performance improvement available for a future 1.0.2-style patch: memoizing the Atlas enterprise dashboard's per-facility computation (which changes at most once per inspection, not once per request) would resolve both the N+1 query volume and the recomputation-on-every-hit problem in one change.

## Database connection pooling — untuned defaults, two independent engines

`app/db/session.py` creates its SQLAlchemy engine with `pool_pre_ping=True` but no explicit `pool_size`/`max_overflow`, relying on SQLAlchemy's defaults (`pool_size=5`, `max_overflow=10`). A second, independent engine construction exists at `app/routers/auth_simple.py` against the same `DATABASE_URL`, each maintaining its own default-sized pool — under concurrent load this could double effective connection consumption against the same database with no coordinated tuning.

## Recommendation — priority order for future 1.0.x patches

1. Fix the Atlas enterprise dashboard's N+1 query pattern (highest-confidence, highest-impact finding).
2. Move `app/routes/inspect.py`'s `stream_frame` inference call onto the RQ queue, matching `stream.py`'s pattern, for consistent non-blocking behavior.
3. Add a composite index on `(tenant_id, created_at)` (or the equivalent dashboard-filter columns) to support the multi-filter dashboard queries these logs identified.
4. Consolidate the two independently-created SQLAlchemy engines into one, with explicit, tuned pool sizing.
5. Introduce a lightweight in-memory or Redis-backed cache for the most expensive, slowly-changing dashboard aggregates.

None of these require architecture changes or new AI capability — all are patch-level, 1.0.x-appropriate fixes per this program's version policy.
