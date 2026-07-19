# LPR-DIR-018 — Change Management Review (Phase 7)

**Basis:** CI/CD + change-control inspection (real, from Phases 1/2/5). This is the one
area with **substantial existing capability** even without a production launch — so it
is assessed on evidence, with production-specific processes marked as gaps.

## Code change management (present, strong)
- **Release approvals:** every change flows through **PRs with required CI gates**
  (ruff, backend tests SQLite+PG16, frontend build, security/dep/secret scans,
  compliance + quality gates). ✅
- **Architecture change control:** v1.0 **frozen** with a Class A/B/C policy
  (`ARCHITECTURE_CHANGE_CONTROL.md`); Class C prohibited. ✅
- **Versioning / release:** `release-ghcr.yml` builds + publishes versioned GHCR
  images on `v*` tags (api + worker). ✅ auditable release record.
- **Release documentation:** `RELEASE_NOTES.md`, `VERSION_1_0.md`. ✅

## Patch / hotfix / minor-release process
- **CM-01 (MEDIUM):** no documented **patch/hotfix runbook** (emergency-change path,
  expedited review, targeted deploy + verify). The code-review spine exists; the
  *operational* fast-path process does not.
- **CM-02 (HIGH, blocking for prod ops):** the **deployment step is a stub**
  (`deploy.yml` echoes kubectl — OPS-DEP-01) and **no rollback drill** exists
  (OPS-DEP-02) — so patches/hotfixes cannot yet be **deployed or rolled back** in a
  verified, repeatable way.

## Maintenance windows
- **CM-03 (MEDIUM):** none defined (Phase 5 OPS-GOV-02). With a single-DB SPOF and
  no HA, maintenance/upgrade windows + tenant notification must be defined pre-launch.

## Production environment approval
- **CM-04 (MEDIUM):** GitHub `environment: staging` approval hook exists; **no
  production environment approval gate** (OPS-DEP-04).

## Configuration change governance
- Central `Settings` + safe-default flags exist, but config changes aren't gated by a
  review workflow distinct from code, and `validate()` isn't invoked at startup
  (SEC-H-02) — a change-safety gap (a bad config change would not fail closed at boot).

## Determination
**Code change-control is production-grade** (PR gates + architecture freeze +
versioned releases). The gaps are **operational change processes** — automated/drilled
deploy + rollback (blocking), patch/hotfix runbook, maintenance windows, prod approval
gate, and startup config validation. These are pre-launch prerequisites, tracked in
the CI backlog.

| ID | Sev | Finding |
|---|---|---|
| CM-02 | HIGH | Deploy stub + no rollback drill → patches/hotfixes not deployable/rollback-drilled (OPS-DEP-01/02) |
| CM-01 | MEDIUM | No patch/hotfix/emergency-change runbook |
| CM-03 | MEDIUM | No maintenance-window policy |
| CM-04 | MEDIUM | No production approval gate |
