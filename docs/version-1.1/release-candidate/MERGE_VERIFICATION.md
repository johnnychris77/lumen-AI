# LPR-DIR-026 — Merge Verification (Workstream 1)

**Governance rule:** only code that completed the project's required approval + merge
process into the authorized release baseline (`main`) may enter the Release Candidate.
Passing CI on a feature branch is **not** evidence. No forced merges. No assumptions.

**Verification method:** direct `git` inspection of `origin/main` merge history + GitHub
PR metadata (`merged`, `merged_at`, `merged_by`). Merge SHAs and dates below are copied
from `git show -s` on each merge commit.

## Release baseline

- **Baseline branch:** `main`
- **Baseline tip (RC commit):** `5c223450b4065011a52ff2dd244c6c5d91321dcc` (`5c22345`)
- **`git describe`:** `lumenai-v1.0.0-rc1-19-g5c22345`

## Version 1.1 implementation PR verification

Each Version-1.1-adjacent PR was classified as **code** or **docs** by diffing its merge
commit against its first parent restricted to application source
(`git diff <merge>^1 <merge> -- backend/app frontend/src`).

| PR | Title (abbrev) | State | Merge SHA | Merge Date (local) | Approver / Merged by | App-code change? | Evidence |
|---|---|---|---|---|---|---|---|
| #108 | Pilot Alpha Directive 011 | **MERGED** | `1e6103a` | 2026-07-19 | johnnychris77 (via GitHub) | No (docs) | `git diff 1e6103a^1 1e6103a -- backend/app frontend/src` = empty |
| #109 | Phase 1 Architecture Freeze | **MERGED** | `f889d95` | 2026-07-18 | johnnychris77 (via GitHub) | No (docs) | diff empty |
| #110 | Phase 2 Engineering Integrity | **MERGED** | `bd94bc5` | 2026-07-18 | johnnychris77 (via GitHub) | No (docs) | diff empty |
| #111 | Phase 3 Security Validation | **MERGED** | `59cc704` | 2026-07-19 | johnnychris77 (via GitHub) | No (docs) | diff empty |
| #112 | Phase 4 Performance/Resilience | **MERGED** | `d6a6006` | 2026-07-19 | johnnychris77 (via GitHub) | No (docs) | diff empty |
| #113 | Phase 5 Operational Readiness | **MERGED** | `451a0b9` | 2026-07-18 | johnnychris77 (via GitHub) | No (docs) | diff empty |
| #114 | Phase 6 RC Certification | **MERGED** | `1ba9a26` | 2026-07-19 | johnnychris77 (via GitHub) | No (docs) | diff empty |
| #115 | Phase 7 Launch/Hypercare | **MERGED** | `3635164` | 2026-07-19 | johnnychris77 (via GitHub) | No (docs) | diff empty |
| #116 | Phase 8 Platform Optimization | **MERGED** | `7e4a7e7` | 2026-07-19 | johnnychris77 (via GitHub) | No (docs) | diff empty |
| #117 | Phase 9 Strategy | **MERGED** | `3c30d8a` | 2026-07-19 | johnnychris77 (via GitHub) | No (docs) | diff empty |
| #118 | Phase 10 Pilot | **MERGED** | `dcef2dc` | 2026-07-19 | johnnychris77 (via GitHub) | No (docs) | diff empty |
| **#119** | **SEC-C-01 hardening (LPR-DIR-022)** | **MERGED** | **`5c22345`** | **2026-07-19T22:28:14Z** | **johnnychris77** (`merged:true`, `merged_by:johnnychris77`) | **YES** — `backend/app/routes/{integrations,billing,billing_webhooks}.py` (+ tests) | `git diff 5c22345^1 5c22345 -- backend/app frontend/src` = **3 files, +74/−24**; head `f291186` is an ancestor of `5c22345` (`git merge-base --is-ancestor` → true) |

## Open / excluded PRs (NOT in the Release Candidate)

| PR | Title (abbrev) | State | Head SHA | Disposition |
|---|---|---|---|---|
| #120 | LPR-DIR-023 Controlled Pilot — EXECUTION BLOCKED | **OPEN / draft** (`merged:false`) | `ee29299` | **Excluded** — unmerged; docs-only governance record. Not implementation. |
| #121 | LPR-DIR-025 Release Baseline Verification | **OPEN / draft** (`merged:false`) | `613a461` | **Excluded** — unmerged; docs-only governance record. Not implementation. (Its snapshot targets `main @ 3c30d8a`, superseded by the #119 merge.) |

## Rejected / Blocked

- **Rejected implementation PRs:** none identified for Version 1.1.
- **Blocked implementation PRs:** none. The only *execution* that is BLOCKED is the
  controlled pilot (LPR-DIR-023, PR #120) — a real-world gate, not a code merge.

## Determination

- **The single Version 1.1 application-code change (SEC-C-01 fix, PR #119) is MERGED into
  the baseline** and verified present at RC tip `5c22345`.
- All other merged Version-1.1 PRs (#108–#118) are documentation/assessment and add **no
  application code**.
- **No unmerged implementation exists** — the two open PRs (#120, #121) are docs-only
  governance records and are excluded from the RC.

Every implementation PR has been verified. Nothing unmerged was included.
