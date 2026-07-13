# LumenAI — Known Issues

Objective 6 (documentation maintenance) companion document. Consolidates real, verified open issues surfaced across this entire multi-phase review program, so a support or engineering team has one place to check rather than re-discovering them independently. Each item cites the document where it was originally found and verified.

## Application defects

- **`enterprise_risk_score` could exceed 100** — fixed this cycle (`BUG-001`, commit `c065c20`). No longer an open issue as of 1.0.1.

## UX / workflow gaps

- **No reachable supervisor approve/return action was found anywhere in the frontend** — the single most significant open item from the UX review (`docs/ux-review/USER_JOURNEYS.md`), reconfirmed in the demo-scripting exercise (`docs/demo-program/ROLE_BASED_DEMOS.md`). Nav-reachable review queues are view-only; components with matching names are orphaned from navigation and, per their own code comments, not the actual approval point.
- **45 of ~90 frontend routes have no sidebar entry** (`docs/ux-review/NAVIGATION_ARCHITECTURE.md`) — includes screens needed for several role-based demos and workflows.
- **Several core KPIs (Total Inspections, Pass Rate, Risk Score) are independently recomputed across 3-8 different dashboard screens**, sometimes from different backend fields (`docs/ux-review/DASHBOARD_STANDARDS.md`) — can cause the same metric to display differently in different places.
- **The design-token migration reached ~9 of ~200 frontend files**; no shared Table/Dialog/EmptyState component exists (`docs/ux-review/DESIGN_SYSTEM.md`).
- **`aria-describedby`/`aria-invalid` are used zero times codebase-wide; no global focus-visible CSS exists** (`docs/ux-review/ACCESSIBILITY_REVIEW.md`).

## Clinical scope limitations (by design, not defects — restated here for visibility)

- **No trained model ships in this repository** — deployed inference emits only `debris`/`corrosion` via a deterministic fallback (`docs/clinical-validation/FINDING_TAXONOMY.md`).
- **Osteotomes are not modeled anywhere** in the instrument taxonomy (`docs/clinical-validation/INSTRUMENT_TAXONOMY.md`).
- **Five to six overlapping, inconsistent finding-type vocabularies coexist** across different services (`docs/clinical-validation/FINDING_TAXONOMY.md`).

## Deployment / infrastructure

- **The root `Dockerfile`'s `CMD` has no default for `$PORT`** — will fail if run standalone without an externally-set env var (`docs/commercial-readiness/DEPLOYMENT_GUIDE.md`).
- **`docker/Dockerfile.worker` is a non-functional placeholder stub**, currently published by the tag-triggered GHCR release pipeline (`docs/commercial-readiness/DEPLOYMENT_GUIDE.md`).
- **Health checks point at `/api/health`/`/health` (unconditional 200-OK stubs), not `/ready` (the one endpoint that actually checks database connectivity)** (`docs/commercial-readiness/DEPLOYMENT_GUIDE.md`).
- **No backup or restore script exists anywhere in this repository**, despite detailed disaster-recovery documentation (`docs/commercial-readiness/DEPLOYMENT_GUIDE.md`).
- **Kubernetes/Helm manifests exist but have never been applied to a real cluster** — not a viable deployment path today (`docs/commercial-readiness/DEPLOYMENT_GUIDE.md`).

## Performance (new this cycle)

- **A confirmed N+1 query pattern in `atlas_dashboard_service.py`'s enterprise dashboard** (`docs/release-management/PERFORMANCE_LOG.md`).
- **No response caching exists at any level of the application.**
- **AI inference is inconsistently queued** — `app/routes/inspect.py`'s `stream_frame` route runs inference synchronously in the request path, unlike `app/routes/stream.py`'s correct RQ-queued equivalent.
- **Zero composite database indexes exist**, despite broad single-column FK indexing.

## Security

- **No secrets-rotation mechanism exists in code** — only manual issue/revoke endpoint pairs (`docs/commercial-readiness/LEGAL_GOVERNANCE_PACKAGE.md`).
- **A security incident-response runbook does not exist** — the security compliance control matrix itself lists this as open, unimplemented work.
- **`docs/regulatory/cybersecurity-readiness.md` claims Dependabot and bcrypt hashing are implemented; neither matches the actual codebase.**

## Legal / commercial

- **BAA, MSA, DPA, Terms of Service, and Privacy Policy are referenced as gating requirements throughout onboarding and compliance documentation, but none has actual agreement text anywhere in this repository** (`docs/commercial-readiness/LEGAL_GOVERNANCE_PACKAGE.md`).
- **At least three internal pricing documents disagree on tier names and dollar figures**; pricing approval is explicitly still "in progress" (`docs/commercial-readiness/PRICING_MODEL.md`).
- **No real product screenshots exist** — the asset directory contains duplicated placeholder images that are, on inspection, screenshots of a markdown instructions file (`docs/commercial-readiness/MARKETING_LAUNCH_PLAN.md`).

## Test infrastructure (new this cycle, not a product issue)

- **`test_sentinel_orchestration.py`'s `TestRiskMonitor`/`TestDigitalTwinMonitoring`/`TestAlertGeneration` classes share one fixed tenant constant with no per-test isolation**, making them order-dependent (`BUG-003` in `docs/release-management/BUG_REGISTER.md`). Recommended for Phase 8 test-hardening.

## FAQ addition for this cycle

*"Why do the docs mention so many open issues — is the platform unstable?"* No — per `docs/commercial-readiness/FINAL_READINESS_REPORT.md`'s verdict, the underlying architecture and patient-safety discipline are genuinely strong; these are precisely-named, individually-scoped gaps identified by a disciplined, honest review process, not symptoms of systemic instability. The regression suite itself is clean (3381 passed, 0 failed, per `docs/release-management/REGRESSION_REPORT.md`).
