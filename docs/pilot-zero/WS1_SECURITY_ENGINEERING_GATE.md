# Workstream 1 — Security and Engineering Gate

Establishes the trustworthy foundation required before hardware
acquisition (WS2) and dataset development (WS3+). Per the program's
recommendation discipline, this document states assumptions, risks,
dependencies, deliverables, acceptance criteria, and exit criteria — and
records what was implemented versus what requires an administrator.

## Findings that motivated this workstream (evidence, 2026-07-17)

1. **The CI gate has never gated.** Ten workflow files exist, yet PRs
   #98 and #99 produced **zero check runs** despite matching
   `pull_request` triggers — indicating GitHub Actions is disabled at
   the repository level. Additionally `.github/workflows/ci.yml` is
   broken (file ends mid-step with an empty `run:` block) and targets
   Python 3.12, a version the suite has never been run on.
2. **Builds were not reproducible.** Three divergent dependency
   manifests: root `requirements.txt` (stale pins — e.g. fastapi
   0.111.0), `backend/requirements.txt` (mostly unpinned, with
   `psycopg2-binary` listed three times), and the actual tested
   environment. **Docker images were building an untested dependency
   set.**
3. Security posture was manually verified in prior sprints (no
   hardcoded secrets; env-driven config; hashed API keys) but had no
   automated, recurring enforcement.

## Implemented in this change

| Deliverable | Artifact |
|---|---|
| Tested dependency lock | `backend/requirements-lock.txt` — 100 exact pins frozen from the environment that passed the full 3,683-test suite on Python 3.11 (matching the `python:3.11-slim` Docker bases) |
| Single source of truth for builds | root `requirements.txt` is now a **generated copy of the lock** (Dockerfiles consume it unchanged and now build exactly the tested set); `backend/requirements.txt` deduplicated and kept as the human-edited direct-dependency manifest |
| Authoritative gate workflow | `.github/workflows/pilot-zero-gate.yml` — ruff, full backend suite on SQLite, full backend suite on **PostgreSQL 16 with the Alembic up/down/up exercise** (locking in the Foundation lesson: 110 SQLite-masked defects), frontend `npm ci && npm run build`, dependency audit (report-only), gitleaks secret scan |
| Dependency-vulnerability evidence | `pip-audit` against the lock: **no known vulnerabilities**; `npm audit` against `frontend/package-lock.json`: **0 vulnerabilities** (2026-07-17) |

Design decisions, recorded: Python pinned to 3.11 (the tested version);
the dependency audit starts **report-only** so findings surface on every
PR while triage decisions remain explicit — promotion to blocking is an
exit-criteria item below; legacy workflows are left untouched (their
consolidation/removal is follow-up cleanup, not a gate dependency).

## Required administrator actions (cannot be performed from the repository)

1. **Enable GitHub Actions** for the repository (Settings → Actions) —
   without this, no gate exists no matter what the workflows say.
2. **Branch protection on `main`**: require the Pilot Zero Gate jobs
   (lint, backend-tests-sqlite, backend-tests-postgres, frontend-build,
   secret-scan) to pass before merge; require pull requests (no direct
   pushes); dismiss stale approvals on new commits.
3. Confirm the first gate run is green on a real PR.

## Assumptions

* GitHub-hosted runners are acceptable for an internal research program
  (no PHI, no clinical data exists in the repository — verified).
* The frozen venv is the correct canonical environment (it is the only
  environment in which the full suite has ever passed).

## Risks

* **R-WS1-1**: Actions remains disabled → gate is fiction. Severity:
  program-blocking. Mitigation: WS2 (hardware spend) does not start
  until the exit criteria below are met.
* **R-WS1-2**: Lock drift vs. direct manifest (someone edits
  `backend/requirements.txt` without regenerating the lock). Mitigation:
  CI installs **only** from the lock, so unlocked additions fail loudly
  in the gate; regeneration procedure documented in
  `REPRODUCIBLE_BUILDS.md`.
* **R-WS1-3**: Report-only audit ignored. Mitigation: exit criterion
  requires a triage decision converting it to blocking (with a
  documented allowlist mechanism) before WS3 data ever enters the repo
  perimeter.
* **R-WS1-4**: The 10 legacy workflows produce confusing/failing checks
  once Actions is enabled. Mitigation: follow-up cleanup PR
  disabling/removing superseded workflows; only the Pilot Zero Gate is
  designated required.

## Dependencies

None upstream — this is deliberately the first workstream. Downstream:
WS2 (hardware qualification) and all dataset workstreams depend on WS1
exit; the instrument registry (WS4) depends only on WS1.

## Acceptance criteria (verifiable)

- [x] Lock file exists and `pip-audit` runs clean against it (evidence above)
- [x] Root/Docker dependency path builds the tested pin set
- [x] Gate workflow present with SQLite + PostgreSQL + frontend + secret-scan jobs
- [x] Full suite green locally on both engines with the locked set (3,683 passed SQLite; PostgreSQL green per Foundation acceptance)
- [ ] Gate executes on a real PR (blocked on admin enabling Actions)

## Exit criteria (gate to WS2)

1. Actions enabled; Pilot Zero Gate green on ≥1 real PR.
2. Branch protection requiring the gate is active on `main`.
3. Dependency-audit policy decision recorded (blocking threshold +
   allowlist procedure).
4. Legacy-workflow disposition decided (keep/disable each of the 10).

Until these four are true, Workstream 1 is **IMPLEMENTED / NOT EXITED**,
and hardware acquisition does not begin.
