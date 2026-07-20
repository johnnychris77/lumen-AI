# OPERATIONAL EVIDENCE INDEX — LPR-DIR-031 / WP-8

Traceable index of every artifact produced/executed under LPR-DIR-031. Each row states what
was **actually executed** vs **not executed**, with provenance (commit, timestamp, operator).

**Commit under execution:** `4299c40` · **Operator:** automated (Claude Code, LumenAI
governance execution) · **Environment:** ephemeral repo sandbox (no managed infra).

## 1. Evidence actually captured this directive (reproducible)
| ID | Artifact | Type | Provenance |
|---|---|---|---|
| EV-31-01 | `evidence/PROVISIONING_PROBE.log` | Executed probe (docker/k8s/cloud/postgres/env) | 2026-07-20T02:33:10Z · `4299c40` |
| EV-31-02 | `evidence/HARNESS_RUN.log` | Executed capability harness — **6/6 pass** | 2026-07-20T02:33:22Z · `4299c40` |
| EV-31-03 | PR #122 CI "Backend tests (PostgreSQL 16)" | Executed (CI) — migrations/tests on Postgres | run 29710326305 (green) |
| EV-31-04 | Tenant-isolation suite (6 passed) | Executed (this session) | `4299c40` |
| EV-31-05 | `.github/workflows/deploy.yml` | Deploy/rollback automation artifact | verified DIR-030 |

## 2. Operational evidence REQUIRED but NOT PRODUCED (no managed environment)
| Required (WP) | Missing artifact | Reason |
|---|---|---|
| WP-2 deploy | deployment ID, rollout log, deployed version, smoke log | no cluster/daemon |
| WP-3 rollback | MTTR, recovery confirmation | no executed deploy to roll back |
| WP-4 backup/DR | managed-DB snapshot, restore transcript, RTO/RPO | no managed Postgres |
| WP-5 observability | metrics, dashboard, alert delivery/ack/resolution | no monitoring/alerting backend |
| WP-6 secrets/TLS | live secret injection/rotation, served cert, HTTPS enforcement | no ingress/secrets store |
| WP-7 incident response | operational drill timeline | no live environment to perturb |

## 3. Evidence-collection standard (for the future live run)
Every operational activity, once a managed environment exists, SHALL capture: logs ·
timestamps · environment identifier · commit SHA · screenshots where applicable · operator ·
explicit verification steps — stored under `docs/version-1.1/pilot-operational-capability/evidence/`
with one subfolder per WP execution and an updated index row here.

## 4. Integrity statement
No deployment ID, RTO/RPO, alert delivery, or screenshot was fabricated. Executed evidence
(EV-31-01..05) is reproducible from committed artifacts; missing operational evidence is
recorded as missing with its blocking reason.
