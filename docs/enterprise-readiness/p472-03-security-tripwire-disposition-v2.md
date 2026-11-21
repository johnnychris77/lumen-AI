# P472-03 — Security Tripwire Disposition Register (v2 — Batch 5)

**PR #181 (DRAFT) · Issue #187** · supersedes `p472-03-security-tripwire-disposition-v1.md` (preserved).
**Rule:** an expected security-tripwire failure is **not** a passing check — a green CI job containing one
is not a passing security gate — and an author-converted tripwire is **not** a closed finding. Every item is
a **release blocker** until a non-author reviewer records a disposition. **No disposition is recorded.**
Review procedures: `p472-03-batch5-independent-review-packages-v1.md`.

## A. Still failing (strict xfail) — 15
| ID | Test | Finding | Blocking until | Disposition |
|---|---|---|---|---|
| RB-T01 | `test_p472_03_application_wide_isolation.py::test_no_route_exhibits[AW-04]` | AW-04 genesis publisher filter | GD-6 + real fix + non-author sweep validation | **PENDING — BLOCKER** |
| RB-T15…T23 | `test_p472_03_batch5_genesis_gd6.py::TestOpenFindings` (9) — GD6-01…09 | Genesis unpublished-content exposure, cross-tenant publish/reject, supersedes linkage, identity disclosure | GD-6 | **PENDING — BLOCKER** |
| RB-T24…T28 | `test_p472_03_batch5_guardianx_gd7.py::TestOpenOwnershipFindings` (5) — GD7-01…05 | GuardianX ledger cross-tenant read/list/verify, reviewer disclosure, source contamination | GD-7 | **PENDING — BLOCKER** |

## B. Author-converted (Batch 4) — 13
RB-T02 … RB-T14 exactly as listed in v1 (findings-file exploit tests ×10, register-driven sweep classes ×3).
**No change in Batch 5; no disposition recorded.** All remain release blockers.

## C. Not executed (not a pass)
Data-dependent skips `test_benchmarking.py:83`, `test_p10_digital_twin.py:317`; on SQLite the PostgreSQL-only
Alembic test. Exact lists per run are in `p472-03-release-gate-evidence-index-v4.md`.

## Determination
15 tripwires still fail; 13 author conversions undispositioned. **28 release blockers. HOLD / NO-GO.**
