# LPR-DIR-017 — Go / No-Go Decision (Phase 6)

## Official decision

# RELEASE CANDIDATE CERTIFIED — GO WITH CONDITIONS

**Scope of this GO:** it certifies **LumenAI v1.0 RC1 as a frozen baseline for a
hardening cycle** and permits the non-publishing marker tag `lumenai-v1.0.0-rc1`.
**It is NOT a production or clinical deployment authorization.**

**Dual-lens honesty:** measured strictly as a *production go-live* decision, the open
1 CRITICAL + 8 HIGH make it **NO-GO for production today**. Measured as an *RC1
certification* of the completed Phases 1–5 body of work — coherent, evidence-backed,
with every blocker tracked and remediable without redesign — it is **GO WITH
CONDITIONS**. Both statements are true and are stated plainly so the decision cannot
be misread as production authorization.

## Blocking conditions (must ALL close before any production authorization)

| # | Condition | Description | Owner | Severity | Required action | Blocking |
|---|---|---|---|---|---|---|
| C1 | **SEC-C-01** | Webhook fail-open → cross-tenant injection | Security Eng | **CRITICAL** | Require signing secret at startup (fail closed); reject unsigned; bind tenant to verified signature | **YES** |
| C2 | SEC-H-01 | HS256 hardcoded secret fallbacks → token forgery | Security Eng | HIGH | Remove fallback literals | **YES** |
| C3 | SEC-H-02 | No fail-closed startup secret validation | Backend Eng | HIGH | Invoke `validate()` at startup; require secrets; refuse boot if missing | **YES** |
| C4 | PERF-07 | Production load/stress test not executed | SRE | HIGH | Run k6/locust on multi-worker + Postgres; define SLOs | **YES** |
| C5 | SCAL-01 | Single Postgres SPOF + single-worker pods | Infra | HIGH | HA Postgres + multi-worker + pool tuning | **YES** |
| C6 | RES-01 | In-process scheduler duplicates across replicas | Backend Eng | HIGH | Leader election / single scheduler pod | **YES** |
| C7 | OPS-INC-01 | No incident-response/on-call + no alerting | SRE/COO | HIGH | Adopt IR framework + Alertmanager + on-call; run game-day | **YES** |
| C8 | OPS-DEP-01 | Production deploy not automated (stub) | DevOps | HIGH | Wire real rollout + post-deploy verification | **YES** |
| C9 | OPS-DEP-02 | No executed production rollback drill | DevOps | HIGH | Execute + document a rollback drill | **YES** |

## Non-blocking conditions (hardening; track to closure)
AR-16 audit atomicity · AR-17 dataset-freeze enforcement · AR-18 dedup uniqueness ·
SR-01/02 duplication + god-module · CFG-01 config sprawl · DH-01 CI manifest pinning ·
SEC-INF-01 container-as-root · OPS-OBS-01/02 observability depth · ENV-01 IaC
consolidation · BC-01/02 failover + disaster-comms · OPS-GOV-03/04 access-review +
on-call governance · RB-05 runbook reconciliation · SUP-01/02 support index +
escalation · CAP-01 retention policy.

## What is permitted / withheld
- **Permitted:** annotated `lumenai-v1.0.0-rc1` baseline tag (non-publishing);
  continued hardening; a **supervised, human-in-the-loop pilot** (per Directive 010
  GO WITH CONDITIONS) with no autonomous clinical decisions.
- **Withheld:** production deployment; clinical deployment; regulatory claim; any
  `v*` release tag / GHCR production image publish (would trigger `release-ghcr.yml`).

## Re-certification
On closure + re-verification of all 9 blocking conditions (including a passed
production load test and a security re-test confirming SEC-C-01 is closed), a
follow-up certification may issue a production **GO**.
