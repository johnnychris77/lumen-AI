# LPR-DIR-015 — Stress & Breaking-Point Report (Phase 4)

## Honesty statement
A controlled stress test to the breaking point requires a production-representative
deployment (multi-worker ASGI + PostgreSQL + object storage) and a load generator,
**neither of which is available here**. Actual saturation/failure thresholds were
**not measured**. This report predicts breaking points from the code/architecture
(so the Phase-5 stress test knows where to look) and validates *graceful-degradation
design* by inspection.

## Predicted breaking points (ranked, unmeasured)

| # | First-to-break under increasing load | Why | Expected symptom |
|---|---|---|---|
| 1 | **Heavy report/packet endpoints** (`enterprise_intake.py` F/66) | CPU-bound on a single uvicorn worker/pod | event-loop blocking → p99 latency spike, then timeouts |
| 2 | **DB connection pool** (default 15/proc, DB-01) | insufficient for burst concurrency | `QueuePool limit ... overflow` / request queueing |
| 3 | **Single PostgreSQL** (SPOF, AR-06) | one instance for all tenants | DB CPU/IO saturation → global slowdown |
| 4 | **N+1 endpoints** (DB-05) as data grows | query count scales with rows | linear DB-load growth per request |
| 5 | **Memory** under many concurrent heavy requests | ~198 MB baseline + per-request buffers (PDF/ZIP) | pod OOM at 1Gi limit |

## Graceful degradation (design-verified)

| Mechanism | Present? | Evidence |
|---|---|---|
| Readiness sheds traffic on DB loss | ✅ | `/ready` returns 503 when DB down → k8s stops routing |
| Soft-dependency isolation | ✅ | storage/config are informational; don't flip readiness |
| Fail-closed on missing deps | ✅ | auth 401, tenant 403, evidence quarantine, unavailable-model safe state (Phase 3) |
| Bounded startup DB retry | ✅ | `main.py` retries DB readiness with attempt logging then hard-fails |
| Rate limiting | ⚠️ | `slowapi` wired **best-effort** (`try/except pass`) — engagement unverified (Phase 3 SEC-API-01) |
| Backpressure / queue offload | ❌ | heavy generation is synchronous on the request path (SCAL-03) |

## Recovery behavior (design-verified)
- On overload easing, stateless pods recover without in-process state loss; `/ready`
  re-greens when the DB recovers.
- No circuit-breaker/bulkhead around the DB or heavy endpoints (STRESS-02, MEDIUM) —
  a saturated DB can cascade to all endpoints; recommend timeouts + bulkheads.

## Findings
| ID | Sev | Finding |
|---|---|---|
| STRESS-01 | MAJOR | Breaking points unmeasured (no stress environment) — deferred with Phase-5 load test |
| STRESS-02 | MEDIUM | No circuit-breaker/bulkhead/timeout policy around DB + heavy endpoints |
| STRESS-03 | MEDIUM | Rate limiter best-effort; not verified to shed load under burst |

**Positive:** graceful-degradation *design* is sound (readiness shedding, soft-dep
isolation, fail-closed, bounded retry); the gaps are load-shedding depth and an
actual measured breaking point.
