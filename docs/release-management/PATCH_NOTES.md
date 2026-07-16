# LumenAI — Patch Notes

Objective 8/9 review. Real patch notes for the work performed in this Phase 7 (Sustain) cycle, following the version policy's semantic-versioning guidance (patch versions 1.0.x, no feature additions, no architecture changes).

## 1.0.1 — Critical bug fix

**Fixed**: `enterprise_risk_score` (Sentinel's executive dashboard composite risk score) could exceed its documented 0-100 range when the underlying quality score went negative — traced to a missing clamp on one of four risk factors. See `BUG-001` in `docs/release-management/BUG_REGISTER.md` for full root-cause detail.

**Changed files**: `backend/app/services/sentinel_dashboard_service.py` (4 lines).

**Testing**: verified against the specific previously-failing test (`test_sentinel_orchestration.py::TestDashboardAggregation::test_dashboard_returns_expected_shape`) and a full, uncontaminated regression suite run (3381 passed, 2 skipped, 0 failed).

**Regression risk**: minimal — the change only tightens an existing bound that every sibling factor already enforced; no behavior changes for any input that was already within range.

**Rollback**: revert commit `c065c20` if needed; no data migration involved.

## 1.0.1 (continued) — repository hygiene

**Changed**: `.gitignore` extended to cover SQLite journal/WAL/SHM sidecar files (`*.db-journal`, `*.db-wal`, `*.db-shm`) alongside the existing `*.db` pattern, preventing transient local test-database artifacts from appearing as untracked files.

**Changed files**: `.gitignore` (3 lines added).

## Documentation-only changes (no version bump required per this program's own convention)

This cycle also produced the following release-management documentation, none of which changes runtime behavior:
- `docs/release-management/KNOWN_ISSUES.md` — consolidated known-issue index across all prior review phases.
- `docs/release-management/BUG_REGISTER.md` — the register above.
- `docs/release-management/PERFORMANCE_LOG.md` — verified performance findings (N+1 query pattern, no caching layer, inconsistent AI-inference queuing).
- `docs/release-management/SECURITY_UPDATE_LOG.md` — log of the Pillow CVE fix (already applied in an earlier phase) and current security-maintenance process state.
- `docs/release-management/CUSTOMER_FEEDBACK_LOG.md` — honest statement that no real customer feedback exists yet (no pilot has begun).
- `docs/release-management/REGRESSION_REPORT.md` — full investigation and resolution of the 17 pre-existing test failures.
- `docs/release-management/PATCH_APPROVAL_RECORD.md` — the approval record for this cycle's one code change.

## Prior security update (from an earlier phase, restated for continuity)

- **Pillow 12.2.0 → 12.3.0** — resolved 5 disclosed CVEs (PYSEC-2026-2253 through -2257) flagged by CI's blocking `pip-audit` check. Commit `9b6e488`.

## Version numbering note

Per this program's version policy (1.0.1 = critical bug fixes, 1.0.2 = performance, 1.0.3 = security, 1.0.4 = documentation, 1.0.5 = reliability), this cycle's single code fix (a critical dashboard-value bound violation) is versioned **1.0.1**. The performance findings in `PERFORMANCE_LOG.md` are documented but not yet fixed in code — they are candidates for a future 1.0.2 release, not part of this one.
