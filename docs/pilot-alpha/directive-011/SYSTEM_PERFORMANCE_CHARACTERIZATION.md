# LPA-DIR-011 — System Performance Characterization

**Purpose:** characterize **engineering** performance only. **No clinical
performance is reported.** Measurements are from the controlled integration run and
prior foundation evidence; where a metric requires production-scale load or
physical acquisition, it is marked **not characterized (deferred)** rather than
estimated.

## Observed (this review)

| Metric | Observation | Basis |
|---|---|---|
| **Integration test wall-time** | 130 tests in **51.9 s** (fresh DB) | This review's integration subset |
| **Per-test mean** | ~0.40 s/test incl. DB + API setup | Derived from the run |
| **End-to-end API path (train→register→promote)** | Completes within the test timeout; no timeout/hang | `test_candidate_model_training` API E2E |
| **Audit chain verification** | Completes; hash-chain verify is linear in events | Audit tests |
| **Database performance (test tier)** | SQLite fresh-DB; no lock/timeout failures | Integration run |

## Deferred (require production-scale / physical setup)

| Metric | Why deferred |
|---|---|
| **Pipeline latency (real acquisition→report)** | Needs physical lab (Directive 010 LRR-1) |
| **Image processing time** | Needs lab-acquired images |
| **Inference time (governed model)** | No Directive-009-governed model exists |
| **Storage performance (object storage at scale)** | Foundation object storage documented; scale test pending |
| **Database performance (PostgreSQL at load)** | PostgreSQL configurable authoritative DB verified functionally; load test pending |
| **API response time / throughput / queue** | Needs load harness + production tier |
| **System resource utilization** | Needs production-representative environment |

## Foundation evidence (prior, cited)

* **Backup/restore + DR:** executed with **measured RTO/RPO** (`docs/foundation/
  {BACKUP_RESTORE,DISASTER_RECOVERY}.md`).
* **Readiness probe:** `/ready` with per-dependency checks (DB hard-gate).
* **Object storage + PostgreSQL:** functionally verified by real runs (foundation).

## Determination

**ENGINEERING PERFORMANCE CHARACTERIZED (controlled tier).** The integrated system
runs the governed pipeline promptly and without hangs at the test tier, with a
verified audit chain and documented recovery objectives. Production-scale latency/
throughput and real acquisition/inference timing are **deferred** to a
production-representative environment and the physical lab — not estimated. No
clinical performance is reported.
