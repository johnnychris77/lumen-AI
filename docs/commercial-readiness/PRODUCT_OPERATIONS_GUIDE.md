# LumenAI — Product Operations Guide

Objective 8 review. Grounded in a direct code/CI audit — several claims elsewhere in this repository about product-operations maturity do not match what's actually implemented, and this guide states those discrepancies plainly.

## Version management — a real gap

Three inconsistent version identifiers coexist in the live codebase today: `frontend/package.json` reports `0.1.0`; `backend/app/main.py`'s `/health` endpoint reports `"P11"` (a milestone code, not semver); and multiple per-agent version constants across `backend/app/agents/*.py` are hardcoded to `"1.0.0"`. **No `CHANGELOG.md` exists anywhere in the repository.** A real, documented semantic-versioning scheme does exist (`docs/regulatory/software-lifecycle-readiness.md` §7.1: `{major}.{minor}.{patch}` for software, `{major}.{minor}.{patch}-{sha8}` for ML models, sequential Alembic revision for DB schema, SHA256-pinned Docker digests) — **the gap is that the documented scheme and the actual version strings in code have never been reconciled.** Close this gap before using any single version number in customer-facing release notes.

## Release management

`docs/regulatory/software-lifecycle-readiness.md` §7.2 documents a real 9-step release process ending in a git tag `v{major}.{minor}.{patch}`. `.github/workflows/release-ghcr.yml` genuinely triggers on that tag pattern and builds/pushes Docker images to GHCR — **this is real, working deploy-on-tag automation**, one of the few fully-automated pipeline steps found in this entire review. However, tag creation itself is manual (no auto-tagging workflow exists), and — per `docs/commercial-readiness/DEPLOYMENT_GUIDE.md` — the worker image this pipeline builds is currently a non-functional placeholder stub that must be fixed before this release path can be trusted for a real customer release.

## Feature flags — real and working end-to-end

Confirmed: a genuine `FeatureFlag` model (`backend/app/models/feature_flag.py`, table `feature_flags`, tenant-scoped) backs a real service (`platform_admin_service.list_feature_flags()`) exposed via an admin-gated route and rendered in `PlatformAdminDashboard.tsx`'s "Feature Flags" tab. This is a complete, functioning feature-flag system — no gap to flag here.

## Hotfix process

A real hotfix path exists, but it is scoped specifically to security patches: `docs/regulatory/cybersecurity-readiness.md` §8 states emergency patches for Critical CVEs "bypass standard release cycle; deployed via hotfix branch after minimal regression testing." **No general-purpose engineering hotfix runbook exists** for a non-security production defect — this should be authored as a genuine gap, generalizing the existing security-hotfix pattern rather than inventing an unrelated process.

## Bug triage / defect classification

Real and directly reusable: the same P0-P3 severity/response-time table used in `docs/commercial-readiness/SUPPORT_OPERATIONS_MANUAL.md` (`docs/regulatory/software-lifecycle-readiness.md` §8.1) is the defect-classification framework. Note honestly that this document's own "Known Defects at Version 1.0" table (§8.2) is a placeholder template with literal `"[From P12 trace matrix]"` text, not populated with real defect data — do not present this table as a completed defect log in any customer-facing material.

## Backlog prioritization

**No backlog-prioritization framework (RICE, MoSCoW, WSJF, or similar) exists anywhere in this repository.** This is a genuine, unambiguous gap requiring new authorship — there is nothing to consolidate or cite here.

## Change management

`docs/regulatory/software-lifecycle-readiness.md` §8.3's "Change Control Gate" (5-step: impact assessment, regression, risk-file update, regulatory review, documentation update) is real and directly usable as the change-management process for this program.

## Configuration management

Real and centralized: `docs/regulatory/software-lifecycle-readiness.md` §7.3 states plainly — source in Git, infrastructure-as-code in version-controlled K8s manifests, Alembic-versioned DB migrations, pinned (non-`latest`) Docker image tags, environment-specific config via K8s ConfigMaps/Secrets. Corroborated by `docs/data-governance/pilot-data-governance.md`'s statement that secrets are managed via environment variables only, never committed to source control.

## Recommendation — priority order

1. Reconcile the three coexisting version identifiers (P11 / 0.1.0 / 1.0.0) into one real version number and start a `CHANGELOG.md` before any commercial release is announced.
2. Fix the broken worker image in the GHCR release pipeline (also flagged in `DEPLOYMENT_GUIDE.md`).
3. Author a general engineering hotfix runbook, generalizing the existing security-hotfix pattern.
4. Adopt a backlog-prioritization framework — this is a clean-slate gap with no existing partial content to build from.
5. Populate the "Known Defects" table with real data before using it in any regulatory or customer-facing context, or remove the placeholder rows.
