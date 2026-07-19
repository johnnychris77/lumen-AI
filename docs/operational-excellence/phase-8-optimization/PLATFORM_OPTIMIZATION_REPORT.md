# LPR-DIR-019 — Platform Optimization Report (Phase 8)

## Basis and honest framing

**No production runtime data exists** (platform not launched), so this is **not**
a production-profiling-driven optimization report. It is a **code-grounded
optimization backlog** derived from the static + benchmark evidence gathered in
Phases 2–5 (real complexity metrics, real N+1 audit, real pool/worker config,
real startup-path review, real perf benchmark). Production-data-driven tuning
(profiling p95/p99 under real load) is **deferred until after a controlled
launch** and honest instrumentation (Phase 5 OPS-OBS-01).

**Every item below is evidence-based** (per the directive: "all enhancements must
be evidence-based"). None require altering the frozen v1.0 architecture; they are
targeted, mechanical, and independently shippable.

## Optimization opportunities (code-grounded)

| ID | Sev | Opportunity | Evidence | Expected effect |
|---|---|---|---|---|
| OPT-01 | HIGH | **Add DB eager-loading to hot list/detail queries** | Phase 4 DB-05: 0 `selectinload`/`joinedload` in codebase; ORM relationships lazy | Removes N+1 round-trips on list endpoints; largest latency win once under load |
| OPT-02 | HIGH | **Run uvicorn with `--workers` / gunicorn workers per pod** | Phase 4 SCAL-01: Dockerfile starts a single uvicorn worker; no `--workers` | Uses all pod CPUs; raises per-pod throughput without arch change |
| OPT-03 | MED | **Tune SQLAlchemy pool for prod concurrency** | Phase 4: pool size/overflow not sized against worker×replica count | Prevents pool exhaustion / queueing under concurrency |
| OPT-04 | MED | **Enforce dataset-freeze at build time** | Phase 1 AR-17: `dataset_builder` freeze not enforced | Correctness + avoids rebuild churn (efficiency + integrity) |
| OPT-05 | MED | **Make `image_sha256` UNIQUE + resolve dedup TOCTOU** | Phase 1 AR-18: indexed, not unique | Removes duplicate-image race + redundant storage/inference |
| OPT-06 | MED | **Offload heavy work off the request path to the worker** | Phase 4: report/inference/dataset build on request path in places | Lowers API tail latency; smoother p95 |
| OPT-07 | LOW | **Decompose god-module `enterprise_intake.py` (10,558 LOC, F/66)** | Phase 2 SR-02 | Maintainability + smaller import/parse cost |
| OPT-08 | LOW | **Deduplicate `_row_to_dict`×66 / `_actor`×57 / `_tenant`×56 helpers** | Phase 2 SR-01 | Less code to maintain; single correctness surface |
| OPT-09 | LOW | **Add latency histograms + pool/queue gauges** | Phase 5 OPS-OBS-01 | *Prerequisite* to real optimization: you cannot tune what you cannot measure |

## Sequencing

1. **OPT-09 first** — without latency/pool/queue signals, every other tuning claim
   is unverifiable. Instrumentation is the enabler.
2. **OPT-01, OPT-02, OPT-03** — the throughput/latency trio; highest expected win,
   low risk, no arch change.
3. **OPT-04, OPT-05, OPT-06** — correctness-adjacent efficiency.
4. **OPT-07, OPT-08** — maintainability; opportunistic.

## Honest caveat on "expected effect"

The effect column is **directional (mechanism-based), not measured.** N+1 removal,
multi-worker serving, and pool sizing are well-understood wins, but their **actual
magnitude for LumenAI is unknown until measured under real load** — which requires
OPT-09 instrumentation plus the production load test that Phase 4 flagged missing
(PERF-07). No throughput/latency numbers are asserted here because none have been
measured in a production-representative environment.

## Determination

A **concrete, evidence-based optimization backlog exists** and is ready to
execute — but the platform is **not "optimized" in an operational sense**, because
optimization must be validated against real production load, which has not run.
Correct posture: **execute OPT-09 + OPT-01..03 as pre-launch hardening, then
re-profile with real data post-launch.**
