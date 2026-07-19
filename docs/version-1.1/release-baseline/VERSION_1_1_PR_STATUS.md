# LPR-DIR-025 — Version 1.1 Pull Request Status (Workstream 2)

Status from real merge history (`git log --first-parent origin/main`) + PR state at
verification time. **Merged = commit is an ancestor of `main`** (the only evidence that
counts per the honesty requirement).

## Merged into the release baseline (`main` @ `3c30d8a`)

| PR | Scope | Merge commit | Merged |
|---|---|---|---|
| #118 | Phase 10 controlled-pilot **readiness** docs (LPR-DIR-021) | `dcef2dc` | ✅ |
| #117 | Phase 9 platform-strategy docs (LPR-DIR-020) | `3c30d8a` | ✅ (baseline HEAD) |
| #116 | Phase 8 optimization + V1.1 roadmap docs (LPR-DIR-019) | `7e4a7e7` | ✅ |
| #115 | Phase 7 launch/hypercare docs (LPR-DIR-018) | `3635164` | ✅ |
| #114 | Phase 6 RC-certification docs (LPR-DIR-017) | `1ba9a26` | ✅ |
| #112 | Phase 4 performance docs (LPR-DIR-015) | `d6a6006` | ✅ |
| #111 | Phase 3 security-validation docs + SBOM (LPR-DIR-014) | `59cc704` | ✅ |
| #108 | Pilot Alpha integration-validation docs (LPA-DIR-011) | `1e6103a` | ✅ |
| (#113, #110, #109, …) | Phase 5/2/1 docs | `451a0b9`, `bd94bc5`, `f889d95` | ✅ |

**All merged V1.1-adjacent PRs are documentation/assessment only.** None changed
application code.

## NOT merged (open) — the code-bearing / blocker-relevant PRs

| PR | Scope | Head SHA | State | Notes |
|---|---|---|---|---|
| **#119** | **SEC-C-01 code fix** (webhook fail-closed + tenant binding) + tests + V1.1 docs (LPR-DIR-022) | `f291186` | **open / draft** | CI **green (full suite, SQLite + PG16)** on the branch — but **NOT merged**, so per the honesty requirement **it closes no blocker**. |
| #120 | Controlled-pilot **EXECUTION BLOCKED** report (LPR-DIR-023) | `ee29299` | open / draft | Docs only. |

## Superseded / abandoned
None identified. (Prior local RC tag `lumenai-v1.0.0-rc1` is unpushed and not a PR.)

## Determination
The **only** V1.1 work that changes the release baseline's behavior — the SEC-C-01 fix
(**PR #119**) — is **open, not merged**. Everything merged into `main` is documentation.
Therefore, on merged evidence, **no code-level blocker has been closed in the baseline.**
