# LPR-DIR-022 — Release Blocker Register (Phase 1)

Consolidated inventory of every release-blocking item, classified **Must Fix Before
Pilot** / **Must Fix Before Production** / **Future**, with honest status after this
hardening directive. Some blockers are code-closable in this repository (and are
closed/mitigated here); others require **real infrastructure or real-world engagement**
and **cannot be truthfully closed from a code repository** — those are marked
accordingly, not fabricated.

## Legend
- **CLOSED (code)** — fixed + tested in this directive.
- **OPEN (infra)** — requires a managed environment / execution that cannot be done
  from the repo.
- **OPEN (real-world)** — requires a real site, people, or equipment.

## Register

| ID | Sev | Blocker | Class | Status |
|---|---|---|---|---|
| **SEC-C-01** | CRITICAL | External + billing webhooks fail OPEN on missing secret; tenant from attacker-controllable input → cross-tenant injection | Must Fix Before Pilot | **CLOSED (code)** — fail-closed + server-bound tenant + tests (Phase 2) |
| SEC-H-01 | HIGH | Hardcoded HS256 secret fallbacks | Must Fix Before Production | **PARTIAL** — prod guard `sys.exit`s on default `SECRET_KEY` (`main.py`); full removal of dev fallbacks recommended |
| SEC-H-02 | HIGH | No fail-closed startup secret validation; `Settings.validate()` omits `SECRET_KEY` | Must Fix Before Production | **PARTIAL** — prod SECRET_KEY + AUTH_MODE guards exist at startup; webhook-secret validation now enforced per-request (fail-closed) |
| PERF-07 | HIGH | No production/representative load test executed | Must Fix Before Production | **OPEN (infra)** — no production-representative environment or load tool available in-repo |
| SCAL-01 | HIGH | Single Postgres SPOF + single uvicorn worker/pod | Must Fix Before Production | **OPEN (infra)** — HA Postgres + worker sizing are deployment actions |
| RES-01 | HIGH | In-process APScheduler duplicates across replicas | Must Fix Before Production | **OPEN (infra)** — leader election meaningful only under multi-replica deploy |
| OPS-INC-01 | HIGH | No incident-response/on-call + no alerting | Must Fix Before Production | **OPEN (infra/process)** — alert routing + on-call are environment/process |
| OPS-DEP-01 | HIGH | Production deploy is a stub (echoes kubectl) | Must Fix Before Production | **OPEN (infra)** — real rollout needs a cluster |
| OPS-DEP-02 | HIGH | No executed rollback drill | Must Fix Before Production | **OPEN (infra)** — requires a real deployment to roll back |
| AR-16..18 | MAJOR | Audit atomicity, dataset-freeze enforcement, dedup TOCTOU | Future | OPEN — targeted code items, not pilot-blocking |
| Pilot-site / training / equipment / env | GATE | No site, users, equipment, or managed environment | Must Fix Before Pilot | **OPEN (real-world)** — cannot be satisfied from a repo |

## Summary

- **Critical: 1 → 0 code-closable.** SEC-C-01 is **CLOSED** in this directive
  (implementation + tests + regression).
- **Security HIGHs (SEC-H-01/02):** meaningfully **mitigated** at startup already;
  full hardening recommended but not pilot-blocking on their own.
- **Infra/real-world blockers remain OPEN** and are honestly **not closable from this
  repository** — they gate pilot execution and production regardless of code.

**Honest bottom line:** the one CRITICAL is closed; the remaining release blockers are
predominantly **infrastructure and real-world engagement** items that no code change in
this repo can truthfully mark complete.
