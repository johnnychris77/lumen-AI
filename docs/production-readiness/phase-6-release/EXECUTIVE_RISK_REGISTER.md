# LPR-DIR-017 — Executive Risk Register (Phase 6)

Consolidated, deduplicated view of all open risks across Phases 1–5, with
**release-blocking** determination. Baseline `bd94bc5`.

## CRITICAL

| ID | Description | Owner | Blocks release? | Required action |
|---|---|---|---|---|
| **SEC-C-01** (AR-15/TB-02) | External-integration webhooks fail open when signing secret unset; tenant from `X-Tenant-Id` header → **cross-tenant data injection on a public write** | Security Eng | **YES** | Require signing secret at startup (fail closed); reject unsigned; bind tenant to verified signature, not header |

## HIGH (all release-blocking)

| ID | Description | Owner | Required action |
|---|---|---|---|
| SEC-H-01 | Hardcoded HS256 secret fallbacks → JWT forgery if `SECRET_KEY` unset | Security Eng | Remove fallback literals |
| SEC-H-02 | No fail-closed startup secret/config validation | Backend Eng | Invoke `validate()` at startup; require secrets; refuse boot if missing |
| PERF-07 | Production load/stress test not executed | SRE | Run k6/locust on multi-worker + Postgres; SLOs |
| SCAL-01 | Single PostgreSQL SPOF + single-worker pods | Infra | HA Postgres + multi-worker + pool tuning |
| RES-01 | In-process scheduler duplicates across replicas | Backend Eng | Leader election / single scheduler pod |
| OPS-INC-01 | No incident-response/on-call/postmortem + no alerting | SRE/COO | Adopt IR framework + Alertmanager + on-call; game-day |
| OPS-DEP-01 | Production deploy not automated (`deploy.yml` stub) | DevOps | Wire real rollout + post-deploy verify |
| OPS-DEP-02 | No executed production rollback drill | DevOps | Execute + document a rollback drill |

## MEDIUM (not release-blocking; hardening)
AR-16 audit-write atomicity · AR-17 dataset-freeze enforcement · AR-18 dedup TOCTOU ·
SR-01/SR-02 duplication + god-module · CFG-01 config sprawl · DH-01/SEC-SC-01 CI
manifest pinning · SEC-INF-01 container-as-root · OPS-OBS-01/02 observability depth ·
ENV-01 IaC drift · BC-01/BC-02 failover + disaster-comms · OPS-GOV-03/04
access-review + on-call governance · MON-01/02 SLOs/alerts · RB-01/02/04/05 runbook
gaps + drift · SUP-01/02 support index + escalation · CAP-01 retention policy.

## LOW / OBSERVATION
Dedup uniqueness (SEC-L-01) · MD5 non-security use · silent excepts · allowlisted SQL
· CORS credentials · Actions SHA-pinning · WAL/PITR · Directive 005 doc
consolidation · deprecated audit shim.

## Executive summary of risk
- **Release-blocking: 1 CRITICAL + 8 HIGH.** All are pre-existing, code/evidence-
  confirmed, tracked, and remediable — **none requires architecture redesign.**
- The **theme** is "secure-by-default + production-operations not yet closed": secret
  startup validation, HA provisioning + a real load test, and operational processes
  (incident/deploy/rollback). Closing this blocking set converts the RC to a
  production-authorizable release.
- No release-blocking risk is **hidden or downgraded** (honesty mandate upheld).
