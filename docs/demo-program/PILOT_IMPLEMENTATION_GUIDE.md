# LumenAI — Pilot Implementation Guide

Objective 14 review. LumenAI already has a large, real pilot-readiness corpus under `docs/pilot/` (37 files) and real backing infrastructure in the backend. **This document indexes and consolidates that existing material rather than duplicating it** — per the same reuse discipline established in `docs/clinical-validation/CLINICAL_VALIDATION_PLAN.md` and `docs/ux-review/` for prior phases.

## Real backing infrastructure (not aspirational)

- **`PilotSiteConfig`** (`backend/app/models/pilot_config.py`) — one row per tenant: enabled instrument families, required inspection zones, `baseline_required` (default True), `minimum_coverage_pct` (default 75), `supervisor_review_threshold_score` (default 70). See `docs/pilot/pilot-site-configuration.md`.
- **`PilotStatus`** (`backend/app/models/pilot.py`) — real 90-day pilot-lifecycle tracking: `pilot_start_date`/`pilot_end_date`, `agreed_kpis`/`current_kpis` (JSON), a genuine conversion gate (`conversion_ready = days_remaining <= 15 and met_count >= 4`, computed in `pilot_service.py`).
- **`PilotErrorLog`** (`backend/app/models/pilot_error_log.py`) — structured, PHI-free operational failure logging (upload/AI-analysis/baseline-lookup/role-permission/report-generation failure types).
- **`/api/pilot-validation/*`** (`backend/app/routes/pilot_validation.py`) — dashboard, safety queue, go/no-go, and report endpoints, all computed from real `SupervisorReview` ground-truth rows. Docstring: "Nothing is fabricated."
- **`/api/pilot-analytics/*`** (`backend/app/routes/pilot_analytics.py`, 1190 lines) — contamination trends, inspection efficiency, CAPA effectiveness, baseline adoption, ROI, clinical outcomes, executive scorecard, quarterly review, CSV/PDF export, and the pulse survey backing.

## Pilot success criteria — already real, cite directly

`docs/pilot/pilot-success-metrics.md` (v1.0) already defines the full framework this objective asks for:
- Adoption/Data Quality/Operational Value/User Satisfaction metric tables with numeric targets (e.g. WAU ≥80%, field completeness ≥95%).
- A **Pilot Go/No-Go Scorecard**: weighted Pass/Fail across 4 categories, "Pass ≥ 3 of 4 categories" to proceed to commercial conversion.
- A metrics reporting schedule.

Use this document as-is; do not author a second, competing success-criteria framework.

## Pilot implementation sequence — already real, cite directly

`docs/pilot/pilot-launch-runbook.md` and `docs/pilot/LUMENAI_v1_4_ENTERPRISE_PILOT_EXECUTION_PLAN_v1.md` already document: a Pre-Launch Checklist (T-14 days: infra, tenant provisioning, BAA/DPA, integration verification), a Launch Day checklist with abort criteria, and daily/weekly monitoring templates. The v1.4 execution plan explicitly lists what's **excluded** from pilot scope today: no PHI ingestion, no EHR integration.

`docs/pilot/deployment-verification-checklist.md` gives concrete, curl-level go-live verification steps.

## Training plan

Reference `docs/pilot/pilot-user-training-guide.md` (v1.0) — already has a Quick Start plus full role-based workflows for SPD Technician, SPD Educator, SPD Manager, Vendor Representative, and QI Reviewer, including a "Common errors" table and the correct hedged language ("Analytics show *potential associations*... not confirmed defect causes"). Cross-reference `docs/customer/training-matrix.md`'s role-based requirements table and Project Sage's real competency-taxonomy/adaptive-learning-plan/microlearning-generator capability (`docs/agents/sage/*.md`) as the platform-side mechanism behind ongoing training, not a separate LMS story. Full detail lives in [TRAINING_GUIDE.md](./TRAINING_GUIDE.md) — this section only indexes it.

## Support model and escalation process

- **Support tiers/cadence** are already documented in `docs/customer/customer-success-playbook.md` (CSM tier/cadence model: Starter/Professional/Enterprise/Health System) — cite directly.
- **Escalation governance mechanism**: Steward's action-lifecycle state machine (`docs/agents/steward/action-lifecycle.md`) provides the real, generic governed-tracking infrastructure behind any escalation (`DRAFT → PENDING_APPROVAL → APPROVED → ... → CLOSED`, role-authority-tier gated), and its 5-point closure-governance criteria (`docs/agents/steward/closure-governance.md`) is a genuine, code-enforced (HTTP 422 on failure) mechanism. Note this is a generic action-governance framework, not a pilot-specific support desk — the customer-facing escalation tiers themselves live in the customer-success playbook above.
- **`PilotErrorLog`** provides the real, structured technical-failure logging a support team would triage from.

## Feedback collection

`backend/app/routes/pilot_analytics.py`'s `/survey/submit` + `/survey/summary` endpoints back the pulse survey referenced in `docs/pilot/pilot-success-metrics.md` §5.1 — this is real, not aspirational. `PilotAnalyticsDashboard.tsx`'s "Weekly Pulse Survey" widget (ease of use / usefulness / recommend) is the live UI for it.

## Weekly review cadence

`docs/pilot/pilot-launch-runbook.md`'s daily/weekly monitoring templates plus `pilot-success-metrics.md`'s reporting schedule already define this cadence — reference rather than re-author.

## Exit criteria

`pilot_service.py`'s `conversion_ready` gate (≤15 days remaining, ≥4 of the agreed KPIs met) is the real, code-enforced exit/conversion criterion. `pilot-success-metrics.md`'s Go/No-Go Scorecard is the qualitative complement.

## What genuinely needs new authorship for this phase

Everything above is real and should be indexed, not recreated. The one gap this recon surfaced: **no single canonical document currently cross-references all of the above into one linear "start here" implementation path** — `docs/pilot/` has 37 files with real, valuable, but scattered content. This guide's contribution is exactly that index — pointing a new pilot-implementation team to the 6 documents/services above in sequence (site config → success metrics → launch runbook → training guide → support/escalation model → feedback/exit criteria) rather than requiring them to discover the 37-file corpus unassisted.
