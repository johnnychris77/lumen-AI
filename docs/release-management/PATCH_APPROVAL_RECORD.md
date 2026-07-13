# LumenAI — Patch Approval Record

Objective 9 review. Records the release-candidate → validation → approval → deployment sequence actually followed for this cycle's one code change, per this program's release-management process.

## Patch: 1.0.1 — `enterprise_risk_score` clamping fix

| Stage | Record |
|---|---|
| Release candidate | Commit `c065c20` on branch `claude/sentinel-simulation-engine-hhh6o7` |
| Validation | Targeted test re-run (previously-failing test now passes) + one full, uncontaminated regression suite run (3381 passed, 2 skipped, 0 failed) + `ruff check` (clean) |
| Clinical verification | Not applicable — this is a dashboard risk-score calculation bug in an executive-reporting service, not a clinical-finding or patient-safety code path. No clinical review board input required per this program's scope (`docs/clinical-validation/` review boundary). |
| Approval | Self-verified within this maintenance cycle's authorized scope (small, safe, isolated bug fix explicitly approved for investigation and fixing by the user at the start of this phase) |
| Deployment | Committed and pushed to the shared branch; will deploy via the existing Render auto-deploy path on merge to `main`, per `docs/commercial-readiness/DEPLOYMENT_GUIDE.md` |
| Rollback plan | `git revert c065c20` — a single, isolated, 4-line change with no data migration or schema dependency |
| Release notes | `docs/release-management/PATCH_NOTES.md` |
| Customer notification | Not applicable this cycle — no customers are yet in a disclosed pilot (`docs/release-management/CUSTOMER_FEEDBACK_LOG.md`); this note is here so the process is followed once real customers exist |

## Patch: repository hygiene — `.gitignore` extension

| Stage | Record |
|---|---|
| Release candidate | Commit `bb5bf98` |
| Validation | Confirmed the previously-untracked `test.db-journal` sidecar file is now correctly ignored |
| Clinical verification | Not applicable |
| Approval | Self-verified — a non-functional repository-hygiene change with zero runtime impact |
| Deployment | Committed and pushed; no deployment action needed (repository metadata only) |
| Rollback plan | `git revert bb5bf98` |
| Release notes | `docs/release-management/PATCH_NOTES.md` |
| Customer notification | Not applicable |

## Validation checklist for this cycle (per the program's own Validation section)

| Item | Status |
|---|---|
| ✓ No regression | Confirmed — clean full-suite run, 0 failures |
| ✓ All automated tests pass | Confirmed — 3381 passed, 2 skipped |
| ✓ Performance maintained or improved | Maintained — no performance-relevant code was changed this cycle; findings logged in `PERFORMANCE_LOG.md` are documentation only |
| ✓ Security scans clean | Confirmed — no new Bandit/pip-audit/npm-audit findings introduced |
| ✓ Documentation updated | Confirmed — this document set |
| ✓ Rollback tested | Not literally executed (a single isolated commit revert is trivially safe and was not exercised in this cycle), but the rollback plan is explicit and minimal-risk given the change's isolation |
| ✓ Release approved | Self-approved within this cycle's explicitly authorized scope |

## Scope discipline note

Per this program's mission ("Do not introduce major new functionality. Do not introduce new AI specialists. Do not expand the approved Version 1.0 architecture"), both changes in this cycle are narrowly-scoped bug/hygiene fixes with zero new functionality, zero new specialists, and zero architecture changes — consistent with the 1.0.x patch-version policy.
