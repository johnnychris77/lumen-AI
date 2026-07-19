# LPR-DIR-019 — Version 1.1 Roadmap (Phase 8)

## Framing

The v1.0 architecture is **frozen**. V1.1 is therefore **hardening + enablement**,
not new-feature expansion (directive constraint: "no uncontrolled feature
development; all enhancements must be evidence-based"). Every item traces to a
**logged, evidence-based finding** from Phases 1–5. The overriding objective of
V1.1 is to **close the production-authorization gate** (1 CRITICAL + 8 HIGH) and
make a **controlled launch** possible.

**This roadmap is planning only. It authorizes no code changes, no deployment, and
no launch.** Execution requires a separately authorized engineering directive.

## Theme 1 — Security remediation (closes the production gate) 🔴

| Item | Finding | Definition of done |
|---|---|---|
| Fail-closed webhook verification | SEC-C-01 | Webhooks reject when secret unset; tenant derived from verified signature, **never** `X-Tenant-Id`; startup fails if secret missing |
| Remove hardcoded secret fallbacks | SEC-H-01 | No `dev-*` secret defaults; secrets required from env/secret store |
| Startup config/secret validation | SEC-H-02 | `Settings.validate()` includes `SECRET_KEY` and **runs at boot**; app fails closed on misconfig |
| Non-root container | SEC-INF-01 | Image runs as unprivileged user |

**Exit for Theme 1 = the CRITICAL and auth-secret HIGHs are closed** — the minimum
to even *consider* production authorization.

## Theme 2 — Observability & incident response (enables unattended run) 🟠

| Item | Finding | Definition of done |
|---|---|---|
| Latency/error/pool/queue metrics | OPS-OBS-01 | `prometheus_client` histograms + per-endpoint p95/p99 + DB-pool/queue gauges |
| Alert rules → SLOs | OPS-OBS-02 | `rule_files` with pages for readiness flaps, error-rate, pool saturation |
| Incident-response + on-call | OPS-INC-01 | IR runbook, on-call rotation, postmortem template, escalation path |
| Distributed tracing (stretch) | OPS-OBS-03 | OpenTelemetry across API→DB→storage |

## Theme 3 — Deployment & resilience 🟠

| Item | Finding | Definition of done |
|---|---|---|
| Real, verified rollout | OPS-DEP-01 | `deploy.yml` executes kubectl + post-deploy smoke gate (not `echo`) |
| Rollback drill | OPS-DEP-02 | One executed app+DB rollback drill, documented |
| Production load test | PERF-07 | Representative load test with published p95/p99 + capacity headroom |
| Multi-worker serving | SCAL-01 / OPT-02 | Workers per pod sized to CPU; pool sized to worker×replica |
| Scheduler leader election | RES-01 | Single scheduler across replicas (leader lock), no duplicate jobs |
| Config drift fix | ENV-01 | k8s and Helm replica counts reconciled |

## Theme 4 — Correctness & efficiency (opportunistic) 🟡

| Item | Finding | Definition of done |
|---|---|---|
| Eager-loading on hot paths | DB-05 / OPT-01 | `selectinload`/`joinedload` on list/detail queries; N+1 removed |
| Dataset-freeze enforcement | AR-17 | Frozen datasets immutable at build time |
| Dedup uniqueness | AR-18 | `image_sha256` UNIQUE; TOCTOU closed |
| Atomic audit write | AR-16 | Audit record + chain update atomic |
| Dependency pinning parity | DH-01 | CI installs fully pinned deps (parity with root) |

## Theme 5 — Ops-enablement instrumentation (unblocks Phase 8 measurement) 🟡

| Item | Finding | Definition of done |
|---|---|---|
| Product-analytics event stream | Phase 8 (analytics gap) | Privacy-preserving, tenant-scoped, **no PHI**; feature-usage + funnels |
| Feedback intake loop | CFB-01/-02 | In-product feedback + survey + feature-request triage into backlog |
| Support index + escalation | SUP-01/-02 | Consolidated authoritative doc index + support→on-call path |

## Sequencing (gate-driven)

```
Sprint 0  Theme 1              → closes CRITICAL + auth HIGHs   (production gate)
Sprint 1  Theme 2 + Theme 3    → detect/respond + real deploy/rollback + load test
Sprint 2  Theme 4 + Theme 5    → efficiency, correctness, Phase-8 instrumentation
Gate      Re-run Go/No-Go (Phase 6 criteria) → only then consider controlled launch
```

## Explicit non-goals for V1.1

- **No** new clinical/AI feature surface (governance frozen).
- **No** trained-model production claims (see `AI_EVOLUTION_REPORT.md`).
- **No** architecture change — all items are targeted and independently shippable.

## Determination

V1.1 is a **hardening-and-enablement roadmap whose primary deliverable is closing
the production-authorization gate.** It is fully **evidence-based** (every item maps
to a logged finding) and introduces **no uncontrolled feature development.**
