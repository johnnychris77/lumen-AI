# LPR-DIR-019 — Technical Debt Reassessment (Phase 8)

## Basis

Consolidated, evidence-based reassessment of debt carried forward from Phases 1–5.
**No item has been remediated since it was logged** (the v1.0 architecture is
frozen and all prior phases were assessment-only), so this reassessment
**re-confirms** the debt register and **re-prioritizes** it against a controlled
launch. Nothing here is downgraded to make the posture look better (honesty
mandate: "no Critical finding hidden or downgraded").

## Debt register (carried forward — status unchanged)

### CRITICAL (release-blocking) — 1
| ID | Debt | Status |
|---|---|---|
| **SEC-C-01** (=AR-15 / TB-02) | External webhooks (`integrations.webhook_ingest`, `billing.stripe_webhook`) **fail OPEN** when signing secret unset; tenant from attacker-controllable `X-Tenant-Id`; no startup validation → cross-tenant data injection | **OPEN — BLOCKS PRODUCTION** |

### HIGH — 8
| ID | Debt | Status |
|---|---|---|
| SEC-H-01 | Hardcoded HS256 secret fallbacks (`main.py:177`, `core/config.py:5`, `auth_simple.py:37`) | OPEN |
| SEC-H-02 | `Settings.validate()` omits `SECRET_KEY` and is **not invoked at startup** | OPEN |
| PERF-07 | No production/representative load test executed | OPEN |
| SCAL-01 | Single Postgres SPOF + single uvicorn worker/pod (no `--workers`) | OPEN |
| RES-01 | In-process APScheduler duplicates across replicas; no leader election | OPEN |
| OPS-INC-01 | No incident-response / on-call + no alerting (prometheus.yml has no rules) | OPEN |
| OPS-DEP-01 | `deploy.yml` **echoes** kubectl — rollout not actually automated/verified | OPEN |
| OPS-DEP-02 | No executed production rollback drill (only demo rollback runs) | OPEN |

### MAJOR / MEDIUM (selected)
| ID | Debt | Status |
|---|---|---|
| AR-16 | Audit write not atomic | OPEN |
| AR-17 | Dataset-freeze not enforced (`dataset_builder`) | OPEN |
| AR-18 | Dedup TOCTOU — `image_sha256` indexed, not unique | OPEN |
| SR-01 | Helper duplication (`_row_to_dict`×66, `_actor`×57, `_tenant`×56) | OPEN |
| SR-02 | God-module `enterprise_intake.py` (10,558 LOC, F/66) | OPEN |
| DH-01 / SEC-SC-01 | CI installs **unpinned** `backend/requirements.txt` (7/27) vs pinned root (100/100) | OPEN |
| CFG-01 | Config sprawl (~199/215 env reads bypass central `Settings`) | OPEN |
| DB-05 | N+1 — 0 eager-loading | OPEN |
| SEC-INF-01 | Container runs as root | OPEN |
| ENV-01 | k8s `replicas:2` vs Helm `replicas:1` drift | OPEN |
| OPS-OBS-01 | Thin metrics (counter+uptime); no histograms/pool/queue | OPEN |

## Reassessment — has anything changed the priority?

**Yes — the priority ordering tightens against launch, but no severity drops.**

- **SEC-C-01 remains the single gate.** It is the only CRITICAL and is by itself
  sufficient to withhold production authorization. It should be the **first** item
  fixed in any V1.1 hardening sprint (fix: fail-closed webhook verification +
  reject attacker-controllable tenant + startup secret validation).
- **The auth-secret pair (SEC-H-01/-02)** is effectively coupled to SEC-C-01 — the
  same "no startup validation, insecure fallback" root cause. Fix them together.
- **The scale/resilience/observability cluster (SCAL-01, RES-01, OPS-OBS-01/-02,
  OPS-INC-01)** is what separates "supervised pilot" from "unattended production."
  These do **not** block a *controlled, supervised* pilot but **do** block
  general-availability production.
- **Debt has not grown** (no new code shipped), and **positives are stable**: avg
  complexity A (3.34), 3,696 tests / 8,404 assertions, 0 Python/Node CVEs,
  SHA-256-only secret storage, DR RTO 10.4 s.

## Debt-burn-down recommendation (for V1.1 roadmap)

1. **Sprint 0 (blocker):** SEC-C-01 + SEC-H-01/-02 (fail-closed + startup validation).
2. **Sprint 1 (prod-enablement):** OPS-OBS-01/-02 + OPS-INC-01 (metrics + alerts +
   IR), OPS-DEP-01/-02 (real deploy + rollback drill), PERF-07 (load test).
3. **Sprint 2 (resilience/scale):** SCAL-01, RES-01, DB-05/OPT-01, pinning DH-01.
4. **Opportunistic:** AR-16/17/18, SR-01/02, CFG-01, SEC-INF-01, ENV-01.

## Determination

**Technical debt is well-characterized, unremediated, and correctly severity-
ranked.** The register is **honest and complete**; **1 CRITICAL + 8 HIGH remain
open and continue to gate production.** No reassessment justifies downgrading any
finding. The debt is *manageable and sequenced*, not *resolved.*
