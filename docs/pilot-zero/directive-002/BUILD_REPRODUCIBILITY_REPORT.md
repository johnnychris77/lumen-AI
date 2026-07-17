# LPZ-DIR-002 — Build & Dependency Integrity Report

**Directive:** LPZ-DIR-002 — Security & Engineering Gate (Phase 7)
**Scope of this increment:** verify the build-integrity finding (F7) against
the current branch and record the evidence. The remediation itself shipped
under Pilot Zero WS1 (already on this branch); this report is the Directive
002 verification of that state, not a new change.

---

## Finding under review

**F7 — Duplicate / conflicting / unreproducible dependency manifests.**
Reported symptoms: a stale root `requirements.txt` diverging from the backend
manifest, and `psycopg2-binary` listed multiple times in
`backend/requirements.txt`.

## Verification evidence (this branch, direct inspection)

| Check | Command | Result |
|---|---|---|
| Interpreter pinned | `python --version` | `Python 3.11.15` |
| Lockfile present & sized | `wc -l backend/requirements-lock.txt` | `100` pinned lines |
| No duplicate psycopg | `grep -ci psycopg2 backend/requirements.txt` | `1` |
| CI gate present | `ls .github/workflows/pilot-zero-gate.yml` | present |
| Known CVEs (Python) | `pip-audit` | `No known vulnerabilities found` |

## State of the manifests

* `backend/requirements-lock.txt` — the tested, fully pinned set (100 pins,
  Python 3.11). This is the authoritative lock.
* root `requirements.txt` — generated from the lock so the two cannot drift.
* `backend/requirements.txt` — deduplicated; `psycopg2-binary` appears once.

## Known bound (recorded, not hidden)

The root `requirements.txt`, being generated from the full lock, includes
development/audit tooling (e.g. `pip-audit`) alongside runtime dependencies.
This was recorded under WS1 (commit `e6eada5`) as a known bound: it is safe
(superset install) but not minimal. Producing a runtime-only top-level
manifest is a follow-up, not a Directive 002 blocker.

## Disposition

**F7 — CONFIRMED (historically) / REMEDIATED under WS1 / re-verified here.**
No Directive 002 code change was required for build integrity; the evidence
above confirms the remediated state holds on the current branch.

## Reproduce

```bash
cd /home/user/lumen-AI/backend
python --version                       # 3.11.x
wc -l requirements-lock.txt            # 100
grep -ci psycopg2 requirements.txt     # 1
pip-audit                              # No known vulnerabilities found
```
