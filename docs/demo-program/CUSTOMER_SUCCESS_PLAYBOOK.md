# LumenAI — Customer Success Playbook

Objective 15 review (Administrator Guide, Director Guide, FAQ, Troubleshooting Guide portions — Technician/Supervisor guides and the Quick Start/Training Workbook live in [TRAINING_GUIDE.md](./TRAINING_GUIDE.md)). This repository already has a large, real customer-success corpus — this playbook's job is to consolidate and reconcile it, not add a third or fourth competing version.

## An honest reconciliation problem, stated up front

Two parallel customer-success document sets already exist — `docs/customer/` (11 files) and `docs/customer-success/` (6 files) — and they **disagree with each other**, not just overlap:
- `docs/customer/customer-onboarding-playbook.md` and `docs/customer-success/customer-onboarding-playbook.md` are two different onboarding timelines (4-week vs. 4-6 week pilot / 6-8 week production).
- **Three different Customer Health Score formulas exist and disagree on weights**: `docs/customer/customer-success-playbook.md` (30/25/20/15/10% weights), `docs/customer-success/customer-health-framework.md` (5-factor, 20% each), and `CustomerSuccessDashboard.tsx`'s own `computeHealth()` function (a third, independently-weighted formula).

**This playbook adopts one canonical version and flags the others as superseded**, rather than silently picking one and leaving the discrepancy for the next reader to discover on their own:
- **Canonical Health Score**: use `docs/customer/customer-success-playbook.md`'s formula (30/25/20/15/10% weights across adoption/inspections/baseline/engagement/completeness) as the documented standard, since it's the most fully-specified of the three. **`docs/customer-success/customer-health-framework.md` and `CustomerSuccessDashboard.tsx`'s `computeHealth()` should be reconciled to match it** — until that reconciliation happens, any customer-facing health score should note it may not match the number quoted in a different document or dashboard.
- **Canonical onboarding timeline**: use `docs/customer-success/customer-onboarding-playbook.md` (the newer, Phase 11-dated version) as canonical, since it's the more recent of the two.

## Administrator Guide

Real, citable content already exists and should be assembled directly from:
- `docs/customer/customer-onboarding-playbook.md`'s SSO/OIDC setup instructions (Azure AD/Okta/Epic), instrument catalog/baseline import steps.
- `PlatformAdminPage.tsx` (`/platform-admin`, orphaned from nav per `docs/ux-review/NAVIGATION_ARCHITECTURE.md` — note this in the guide so an administrator knows to navigate by direct URL) — organization counts, modules, canonical role catalog, feature flags, API keys, connected integrations, audit log.
- `UserManagementPage.tsx` (`/user-management`, nav-visible) for day-to-day role/user administration.
- **Honest caveat to include**: the real, enforced role set is `admin`/`spd_manager`/`operator`/`viewer`/`vendor_user` — but `admin_users.py`'s assignable-role list also includes `supervisor`, which has no independent enforcement elsewhere in the platform (per `docs/ux-review/USER_PERSONAS.md`). An administrator assigning the `supervisor` role should understand it behaves identically to `operator`/`viewer` today, not as a distinct elevated tier.

## Director Guide

- `SubscriptionReadinessPage.tsx` (`/subscription-readiness`) for tier/usage-limit administration (real tier definitions: Hospital/Enterprise/Vendor with concrete facility/user/inspection/baseline/storage limits).
- `DeploymentReadinessPage.tsx` (`/deployment-readiness`) for real live health checks against `/api/health`, KPI summary, infrastructure, and baseline-library endpoints.
- Vanguard's `/executive` and `/strategy` (both orphaned from nav) for enterprise-level reporting and strategic-initiative sign-off — see `docs/demo-program/ROLE_BASED_DEMOS.md` for the honest framing of these screens' current adoption status.
- Reference (don't duplicate) `docs/customer/executive-sponsor-guide.md` and `docs/customer/customer-success-checklist.md`.

## Frequently Asked Questions — genuinely new content, assembled from real fragments

**No standalone customer-facing FAQ document exists in this repository today.** The closest real content is scattered: `TrainingCenterPage.tsx`'s inline per-track FAQ blurbs (Technician/Manager/Vendor/Executive, 2-4 questions each), `docs/pilot/pilot-user-training-guide.md`'s "Common errors" table, and `docs/customer-success/renewal-readiness-guide.md`'s objection-handling table. This playbook assembles them into one place rather than inventing new answers:

- *"Why does the AI say 'human review required' on every result?"* — By design: `human_review_required` defaults `True` on 35 distinct model files across the platform; no AI output is meant to be a final, unreviewed clinical decision (see `docs/clinical-validation/PATIENT_SAFETY_MODEL.md`).
- *"Why can't I approve a finding directly from the review queue?"* — This is a known, real gap under active review, not intended behavior — see `docs/ux-review/USER_JOURNEYS.md`'s Supervisor-journey finding. Direct users to the actual working disposition-recording path available at the time of their pilot.
- *"Does LumenAI have FDA clearance?"* — No. This is a non-negotiable constraint (`CLAUDE.md`): never claim FDA clearance or regulatory approval anywhere in any customer-facing material. The correct answer, per `docs/sales/sales-playbook.md`'s existing objection-handling language, is "our regulatory pathway is under active assessment."
- *"Why do some numbers differ between two dashboards?"* — A known, real finding (see `docs/ux-review/DASHBOARD_STANDARDS.md`): several core KPIs (Total Inspections, Pass Rate, Risk Score) are currently computed independently by different dashboards. Direct the customer to one canonical dashboard per KPI until this is consolidated.
- *"What data does the AI actually detect today?"* — Be direct: the deployed inference path currently emits only `debris`/`corrosion` categories in the absence of a trained model; the fuller 12-13 category taxonomy exists in the scoring/education design layer, not yet in live detection (`docs/clinical-validation/FINDING_TAXONOMY.md`). This must be disclosed, not glossed over, in any FAQ answer about detection scope.

## Troubleshooting Guide

`docs/deployment/TROUBLESHOOTING.md` exists but is **ops/DevOps-only** (API health failures, connection resets, port conflicts) — not customer-facing. This playbook adds a customer-facing layer, assembled from real, known failure modes rather than invented ones:
- Upload/AI-analysis/baseline-lookup/role-permission/report-generation failures are all real, structured failure types already tracked in `PilotErrorLog` (`backend/app/models/pilot_error_log.py`) — a support agent triaging a customer issue should ask which of these five categories applies and check that log.
- Dashboard shows zero/stale data → check whether the demo/pilot tenant's seed data actually populated (cross-reference `docs/demo-program/SYNTHETIC_DATA_GUIDE.md`'s generator inventory) before assuming a platform bug.
- Navigation "can't find a screen" → check `docs/ux-review/NAVIGATION_ARCHITECTURE.md`'s list of 45 orphaned routes before assuming the feature doesn't exist — many real screens require a direct URL today.

## Training Workbook

Moved to [TRAINING_GUIDE.md](./TRAINING_GUIDE.md), alongside the Technician/Supervisor guides and Quick Start, since all four share the same role-based training-matrix backing (`docs/customer/training-matrix.md`) and Sage's competency infrastructure.
