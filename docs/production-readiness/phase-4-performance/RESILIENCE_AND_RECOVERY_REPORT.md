# LPR-DIR-015 — Resilience & Recovery Report (Phase 4)

**Basis:** design + code inspection at `bd94bc5`, cross-referenced with the Phase 1
`FAILURE_AND_RECOVERY_ARCHITECTURE.md` and foundation DR evidence. Recovery from
each failure mode is assessed by design + the failure-invariant tests.

| Failure mode | Behavior | Recovery | Verified by |
|---|---|---|---|
| **Application restart** | Stateless request handling; DB is SoR; in-process APScheduler restarts | Resume, no in-process state loss | design; startup DB-retry loop |
| **Database outage** | `/ready` → 503 (traffic shed); requests fail closed | k8s stops routing; recovers when DB returns; DR restore | `/ready` code; foundation DR |
| **Storage outage** | Soft dependency — readiness stays green; integrity-hash mismatch → fail-closed read | restore from backup | `/ready` soft-check; foundation |
| **Network interruption** | `pool_pre_ping` recycles dead DB connections; bounded retry | reconnect | `db/session.py` |
| **Authentication failure** | 401 fail-closed | re-authenticate | Phase 3 `test_enterprise_auth` (50/50) |
| **Missing baseline** | comparison inconclusive → escalate | approve/activate baseline | Phase 1 invariants |
| **Unavailable Digital Twin** | fail-closed; no promotion | register identity | Phase 1 |
| **Unavailable candidate model** | safe unavailable-model state; human review | register/certify (future) | Phase 3 `test_candidate_model_training` |
| **Report generation failure** | not produced from partial data | complete governed records | Phase 1 |

## Fail-closed verification
The "absence ≠ success" invariants (evidence, baseline, model, contamination,
unknown-state) are implemented and test-backed (Phase 1 + Phase 3 subset 50/50).
Fail-closed behavior holds across auth, tenant, authorization, evidence, and model
boundaries.

## Resilience gaps (performance/ops lens)

- **RES-01 (MAJOR):** **In-process APScheduler has no leader election** — on restart
  or with 2 replicas, scheduled jobs (prediction, RWE, integration, intelligence,
  global aggregation) run on **every** replica, causing duplicate work and duplicate
  side effects. Needs a distributed lock / single scheduler pod.
- **RES-02 (MEDIUM, carryover AR-16):** audit write is not atomic with the business
  write — on partial failure, committed data can lack a chain entry. Affects
  recovery-time data integrity.
- **RES-03 (MEDIUM):** no circuit-breaker/bulkhead (STRESS-02) — a DB brownout can
  cascade across all endpoints rather than being contained.

## Recovery objectives
Backup/restore + disaster recovery were **executed with measured RTO** in the
foundation phase (10.4 s restore for the exercise dataset); RPO = backup cadence.
See `DISASTER_RECOVERY_REVIEW.md`.

## Assessment
**Failure-mode recovery design is strong and largely test-verified** (fail-closed
everywhere, readiness shedding, bounded retry, DR proven). The resilience conditions
are operational: scheduler leader-election (RES-01), audit atomicity (RES-02), and
load-shedding/bulkheads (RES-03) — all Phase-5 items, no redesign.
