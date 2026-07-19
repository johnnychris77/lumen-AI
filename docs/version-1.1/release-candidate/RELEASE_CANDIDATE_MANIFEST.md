# LPR-DIR-026 — Release Candidate Manifest (Workstream 2)

Exact composition of the **Version 1.1 Internal Release Candidate**, from merged evidence
only.

## 1. Release Candidate identity

| Field | Value |
|---|---|
| **RC name** | LumenAI Version 1.1 Internal Release Candidate |
| **Baseline branch** | `main` |
| **RC commit (immutable)** | `5c223450b4065011a52ff2dd244c6c5d91321dcc` |
| **RC short SHA** | `5c22345` |
| **RC merge commit** | Merge of PR #119 (`version-1.1/hardening-release-blockers-v1`) |
| **`git describe`** | `lumenai-v1.0.0-rc1-19-g5c22345` |
| **Build metadata timestamp (this cert run, UTC)** | 2026-07-19T22:41:02Z |

## 2. Composing merge commits (V1.1 program)

The RC is the linear merge history on `main` up to `5c22345`. The Version-1.1 merges
composing it:

```
5c22345  Merge PR #119  SEC-C-01 hardening (ONLY app-code change)
3c30d8a  Merge PR #117  Phase 9 strategy (docs)
1ba9a26  Merge PR #114  Phase 6 RC certification (docs)
d6a6006  Merge PR #112  Phase 4 performance/resilience (docs)
59cc704  Merge PR #111  Phase 3 security validation (docs)
1e6103a  Merge PR #108  Pilot alpha directive 011 (docs)
3635164  Merge PR #115  Phase 7 launch/hypercare (docs)
7e4a7e7  Merge PR #116  Phase 8 platform optimization (docs)
dcef2dc  Merge PR #118  Phase 10 pilot (docs)
451a0b9  Merge PR #113  Phase 5 operational readiness (docs)
bd94bc5  Merge PR #110  Phase 2 engineering integrity (docs)
f889d95  Merge PR #109  Phase 1 architecture freeze (docs)
```
(Earlier history `< f889d95` is the pre-V1.1 v1.0 baseline, unchanged by this program.)

## 3. Application-code content of the RC (delta vs pre-V1.1 baseline)

- **Only** `f291186` (SEC-C-01 fix), delivered via PR #119, changes application code:
  `backend/app/routes/{integrations,billing,billing_webhooks}.py` (+ rewritten security
  tests). Verified: `git merge-base --is-ancestor f291186 5c22345` → **true**.
- All other V1.1 merges are documentation/assessment (no `backend/app` or `frontend/src`
  delta).

## 4. Tags

| Tag | Points to | In RC? | Note |
|---|---|---|---|
| `lumenai-v1.0.0-rc1` | (nearest tag to RC, 19 commits behind) | ancestor | v1.0 RC marker; **not** a V1.1 tag. |
| `v1.1.0` | `5a747af` | **NO** | **Stale/divergent** — not an ancestor of the RC (`git merge-base --is-ancestor 5a747af 5c22345` → false). **Must not be treated as the V1.1 release tag.** |
| `lumenai-v1.0.0` | `7725efd` | ancestor | v1.0 GA marker. |

**No valid Version 1.1 release tag exists.** A `v1.1.*` tag SHALL NOT be cut until the exit
criteria are met (see PILOT_CANDIDATE_ASSESSMENT.md). Note: any `v*` tag push triggers
`release-ghcr.yml` (GHCR image publish) — deliberately not performed.

## 5. Database schema version

| Field | Value |
|---|---|
| **Alembic head revision** | `e7b2f4a86c31` (`e7b2f4a86c31_widen_overflowing_varchar_columns.py`) |
| **Migration files** | 13, single linear chain from `001_initial_schema` → `e7b2f4a86c31` |
| **V1.1 schema delta** | **None** — the SEC-C-01 fix is code-only; adds no migration. |

## 6. Configuration version

- Central `Settings` (`backend/app/core/config.py`); `main.py` startup guards.
- **V1.1 config delta:** the RC introduces three environment-variable contracts required
  by the SEC-C-01 fix: `WEBHOOK_SECRET_{SYSTEM}`, `WEBHOOK_TENANT_{SYSTEM}`, and enforced
  `STRIPE_WEBHOOK_SECRET` (see RELEASE_CONFIGURATION_CERTIFICATION.md). No new feature flag.

## 7. Dependency versions

| Manifest | Lines | sha256 |
|---|---|---|
| `backend/requirements.txt` | 27 top-level | `098cde63713098ae496a79fd6a99464ccba18217c23349e70c4bacfef48c6e85` |
| `backend/requirements-lock.txt` | 100 pinned | `d96ae3a72a4c2ba882c8c9e382fe6fdf4d9858d90a4c31360f85b9686f0dbdde` |
| `frontend/package-lock.json` | (npm lockfile) | `eaa56a3e749b5e3fa5e55360a4f63805cb56920430340dc433fd8cda5eb86c69` |

Key pins: `fastapi==0.136.3`, `cryptography>=41.0.0`, `passlib>=1.7.4`; Python target
`py312`. **V1.1 changed no dependency** (the SEC-C-01 fix uses stdlib `hmac`/`hashlib`).

## 8. SBOM reference

See RELEASE_INTEGRITY_REPORT.md §SBOM. Existing committed SBOMs
(`docs/production-readiness/phase-3-security/SBOM.cyclonedx.json`,
`docs/pilot-zero/directive-002/sbom/backend-sbom.cdx.json`) predate the RC but remain
accurate for backend dependencies because **V1.1 changed no dependency**; the RC-pinned
dependency set is `requirements-lock.txt` @ the sha256 above.

## Determination

The Internal Release Candidate is **exactly `main @ 5c22345`**. Its only V1.1
application-code content is the merged SEC-C-01 fix. Schema head, dependency set, and
configuration surface are all pinned above from the merged baseline.
