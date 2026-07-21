# EVIDENCE INTEGRITY AUDIT — LPR-DIR-030 (Workstream 10)

**Scope:** Audit the integrity and provenance of every evidence item relied on by this
verification. Distinguish **current** vs **superseded** evidence, **flaky tests**, **external
CI-service failures**, and **repository defects**. A transient GitHub HTTP 503 SHALL NOT be
represented as a repository secret finding.

## 1. Evidence provenance ledger (reproduced this pass)
| # | Evidence | Provenance | Integrity |
|---|---|---|---|
| 1 | Baseline: HEAD `b96971a`, IRC-1 `5c22345` is ancestor | `git` (local, deterministic) | **CURRENT** |
| 2 | Zero `backend/app` + `frontend/src` delta vs `main` | `git diff --stat` | **CURRENT** |
| 3 | Harness 6/6 (secret/TLS/health/webhook/backup-analog/migration) | `verify_capabilities.py`, re-run | **CURRENT** — see §2 caveat |
| 4 | Tenant isolation 6 passed | `pytest test_cross_hospital_tenant_isolation_security.py` | **CURRENT** |
| 5 | Single alembic head `e7b2f4a86c31` | harness §6 + migration files | **CURRENT** |
| 6 | Secrets hygiene clean | `.gitignore` + tracked-file scan | **CURRENT** |
| 7 | All 13 CI checks green on PR #122 | GitHub check-runs API | **CURRENT** |
| 8 | `deploy.yml` real, 0 stubs | file re-read | **CURRENT** |

## 2. Environment-sensitivity of the harness (integrity caveat — recorded honestly)
On a **freshly reclaimed** container the harness first reported **4/6**, because `fastapi`
and `Pillow` were **not yet installed** — the health (§3) and webhook (§4) checks raise
`ModuleNotFoundError` and are scored FAIL when the app cannot be imported. After installing
the backend dependency set, the **same harness on the same commit reported 6/6**.

**Classification of that 4/6:** an **environment/dependency artifact**, **not** a code
defect and **not** a harness defect. The harness output is only valid evidence **when the
backend dependencies are installed** — a condition this audit states explicitly so the 6/6
result is not over-generalized. Both readings are recorded; the 6/6 (deps present) is the
qualifying one, and it is reproducible.

## 3. Superseded vs current evidence
- The **first-pass** (lighter) LPR-DIR-030 files (`INFRASTRUCTURE_VERIFICATION.md`,
  `EVIDENCE_AUDIT.md`, `OBSERVABILITY_VERIFICATION.md`, `SECURITY_OPERATIONS_VERIFICATION.md`,
  `PILOT_ENTRY_TRACKER_VERIFICATION.md`, `PILOT_GAP_ANALYSIS.md`) are **retained for history**
  but **superseded** by this expanded 16-file set. Where they cite an older head (`66c2e0d`),
  that is **superseded provenance**; the current head is `b96971a` and the conclusions are
  unchanged (still zero app-code delta).
- The authoritative deliverable index is in
  `LUMENAI_V1_1_PILOT_READINESS_VERIFICATION_REPORT.md`.

## 4. Transient CI failures — correctly classified (NOT repository defects)
| Prior CI failure | True cause | Correct classification |
|---|---|---|
| `Secret scan` / `secrets-scan` red earlier | gitleaks action crashed when its GitHub API call returned **HTTP 503** during a GitHub incident — failed **before** scanning | **External CI-service failure.** NOT a secret finding. Both jobs re-run → **green** (01:43 / 01:53). |
| `test_dashboard_returns_todays_cases` intermittent | date-boundary **flake** (seeds a case at `now+1h`; fails only 23:00–23:59 UTC across midnight) | **Flaky test**, not a code defect. Passes off the boundary; not modified (would break the docs-only property). |

Per the directive, the 503 is explicitly **not** represented as a repository secret finding,
and the security scan has since **completed successfully**, satisfying the completion
requirement.

## 5. Fabrication check
- **No** screenshots, dashboards, deployment records, container digests, MTTR/RTO/RPO
  figures, or approval signatures were submitted or fabricated. Absent evidence is marked
  absent, never invented.
- Every accepted item is **re-runnable** from committed artifacts.

## 6. Determination
**Evidence integrity holds.** All accepted evidence is current, reproducible, and correctly
provenanced; superseded items are labeled; transient external/flaky failures are correctly
separated from repository defects; the harness's environment sensitivity is disclosed; no
fabricated evidence exists.
