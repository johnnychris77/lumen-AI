# LumenAI — Product Capability Maturity Registry

Every entry below is checked against currently running code (not documentation, marketing copy, or intent) as of this Product Truth Reset pass. Statuses use only the six allowed values: **Production, Pilot, Experimental, Scaffolded, Planned, Disabled.**

**Scope boundary, stated honestly**: this matrix covers the mechanisms explicitly named in this program's brief (anonymization, RBAC enforcement, audit controls, dashboard APIs, inspection actions, model invocation, baseline resolution, supervisor review, report generation) plus the AI-inspection and dashboard capabilities this program's earlier passes investigated in depth. It is **not** a re-audit of every route in this ~90-route application — that already exists, incrementally, across `docs/architecture/`, `docs/product-evolution/`, and this session's own recon history. Any capability not listed here has not been re-verified for this program and should not be assumed covered by it.

---

## 1. Model invocation / AI inspection scoring

| Field | Value |
|---|---|
| **Capability** | Per-inspection AI finding generation (the "Submit Inspection & Run AI Analysis" flow) |
| **Owner** | Backend: `app/services/baseline_comparison_scoring_service.py` (`analyze_inspection()`) |
| **Status** | **Experimental** |
| **Implementation evidence** | `baseline_comparison_scoring_service.py:1-21` (module docstring: "THIS IS A DETERMINISTIC PLACEHOLDER — NOT PRODUCTION COMPUTER VISION"); `:299-312` (`_seed_from`/`_pseudo`, SHA-256-derived pseudo-random values); `:1051-1060` (per-KPI probability generation); called from `POST /api/inspections` (`app/routes/inspections.py:426-461`). **Core Inspection Workflow Closure sprint**: added `SUPPORTED_MODEL_CATEGORIES = ("debris", "corrosion")` (`app/ai/inference.py`, single source of truth for what the deployed model actually classifies) and a new `model_result` contract (`_build_model_result()`, `baseline_comparison_scoring_service.py`) attached to every analysis response — it restricts scored `findings` to only `debris`/`corrosion`, and explicitly lists every other KPI (blood/bone/tissue/rust/crack/etc.) in `unsupported_categories`, never assigning them a fabricated probability. `NewInspectionPage.tsx`'s AI Prediction panel now renders this contract directly ("Model Result" section, supported-categories line, per-finding confidence, "Not evaluated by current model" list) |
| **Tests** | `backend/tests/test_baseline_comparison_scoring.py` (27 tests) plus `backend/tests/test_core_inspection_workflow_closure.py::TestHonestModelResultContract` (2 tests: supported categories scored / unsupported categories never fabricated, both baseline-found and no-baseline paths) — all passing |
| **Production availability** | Live in production today — every real user's "New Inspection" submission runs this path |
| **Known limitations** | No trained computer-vision model exists anywhere in this repo. The broader 12-KPI heuristic (`predicted_findings`/`kpi_summary`, used by the "Full KPI detail" section, reports, and dashboards) is unchanged and still scores every KPI identically — the new `model_result` contract is additive, not a replacement, so it narrows what is *presented as a model finding* without touching the older KPI plumbing other features depend on. `placeholder_scoring: true` and `model_label` are still returned on every response for backward compatibility |
| **Next validation requirement** | Train and validate a real computer-vision model against a real, labeled dataset (multi-site blinded reader study, per `docs/clinical-validation/CLINICAL_VALIDATION_PLAN.md`) before this capability can move to Pilot or Production status for its findings themselves (the surrounding workflow — submission, gating, human review — is already Production; only the finding-generation step is Experimental) |

| Field | Value |
|---|---|
| **Capability** | Lower-level single-image inference engine (`LumenAIModel`, YOLO-path) |
| **Owner** | Backend: `app/ai/inference.py` |
| **Status** | **Scaffolded** |
| **Implementation evidence** | `app/ai/inference.py:100-132` (`_deterministic_fallback()`, 4-category output: stain/debris/clean/corrosion); reachable only via `POST /stream/frame` (`app/routes/inspect.py:109`) / queued variant (`app/routes/stream.py:55`) |
| **Tests** | Backend tests exist for the route itself; no frontend integration test, because there is no frontend caller |
| **Production availability** | **Not reachable from any current frontend flow** — confirmed via full-repo grep of `frontend/src` for `stream/frame`/`stream_frame`: zero matches. Real, working code with no live caller today |
| **Known limitations** | Would run the same deterministic-placeholder mode as above if a real model file were absent (which it is by default — `PRODUCTION_INFERENCE_MODE = "deterministic_placeholder"`, `app/ai/inference.py`); disconnected from the UI, so it neither helps nor misleads users today |
| **Next validation requirement** | Decide deliberately whether to wire this route into a frontend flow or retire it — an unreachable code path with no frontend caller and no product decision behind it is exactly the "leave unused mechanism" anti-pattern this program targets, even though (unlike the network-benchmark case) it currently misleads no one since nothing calls it |

| Field | Value |
|---|---|
| **Capability** | Live inference-mode transparency (`get_inference_status()`) |
| **Owner** | Backend: `app/ai/inference_status.py`; Route: `app/routes/system.py:123-137` |
| **Status** | **Production** |
| **Implementation evidence** | `inference_status.py:17-64` — checks at call time whether `ultralytics`/`onnxruntime` are importable and whether a model weights file exists on disk; returns `mode: "trained_model" \| "deterministic_placeholder"` and `ready_for_production: bool` |
| **Tests** | `backend/tests/test_inference_status.py` (passing) |
| **Production availability** | Real, admin-gated (`require_roles("admin")`), and — fixed this pass — now actually called from the frontend (`AiModelPerformanceCard.tsx`, admin-only fetch of `/api/v1/system/inference-status`, rendering "Production — running a trained model" or "Experimental — Not Validated: running the deterministic placeholder scorer") |
| **Known limitations** | Admin-only by design (the endpoint's own docstring calls this "operationally sensitive information"); spd_manager and other roles never see this indicator, which is an intentional scope boundary, not a bug |
| **Next validation requirement** | None — this mechanism does exactly what it claims and is now wired end-to-end |

---

## 2. CV Inspection Intelligence panel (mock provider)

| Field | Value |
|---|---|
| **Capability** | "CV Inspection Intelligence" dashboard panel |
| **Owner** | Backend: `app/cv/registry.py`, `app/cv/mock_provider.py`, `app/routes/cv.py`; Frontend: `frontend/src/components/CVInspectionDashboard.tsx` |
| **Status** | **Experimental** |
| **Implementation evidence** | `app/cv/registry.py:18-27` (`CVRegistry.get_provider()` defaults to `MockCVProvider` whenever no onnx/openai/roboflow provider is configured — the default state today); `app/cv/mock_provider.py:41-52` (`_FINDING_CATALOGUE` generated via `random.Random(hash(image_url))`, not real pixel analysis) |
| **Tests** | Backend tests cover the mock provider's own contract (shape of its output), not real-image accuracy (there is none to test) |
| **Production availability** | Live in the "Legacy" dashboard (`DashboardApp.tsx:506`), hardcoded to `tenantId="demo-tenant"` |
| **Known limitations** | Entirely random per-image output; previously presented with no indicator. Fixed this pass — the panel now shows a "Demonstration Data — Simulated" banner whenever `provider_breakdown` includes `"mock"` |
| **Next validation requirement** | Configure and validate a real `CV_PROVIDER` (onnx/openai/roboflow) against real image data before this can move beyond Experimental |

---

## 3. RBAC enforcement (Atlas enterprise routes)

| Field | Value |
|---|---|
| **Capability** | Organization-scoped authorization for cross-facility enterprise data (`system_id`/`facility_id` scope checks) |
| **Owner** | Backend: `app/routes/atlas_enterprise.py`, `app/services/atlas_rbac_service.py` |
| **Status** | **Production** |
| **Implementation evidence** | `atlas_enterprise.py`'s `_require_scope()` dependency (added and wired in a prior pass of this program) checks `atlas_rbac_service.user_has_scope_access()` against the request path's `system_id`/`facility_id` on every Section 2-9 data-serving route; escalation-prevention on `POST /roles/grant` |
| **Tests** | `backend/tests/test_atlas_enterprise.py::TestSystemAccessEnforcement` (5 tests) — proves access denied without a grant, access granted after one, facility access inherited from a system-level grant, and the escalation path blocked for non-admin leadership roles |
| **Production availability** | Live — every Atlas enterprise route now enforces this |
| **Known limitations** | Covers Atlas's own routes only. `docs/product-evolution/v1.3/NETWORK_ANALYTICS.md` separately documents that `atlas_rbac_service`'s own role vocabulary (`regional_administrator`, etc.) is not itself an enforced role tier distinct from the platform's real 5-role set — routes still gate on the flat `admin`/`spd_manager`/`operator`/`viewer` roles, with the ledger providing scope (organization membership), not a richer role hierarchy |
| **Next validation requirement** | None for the fixed gap itself (closed and tested). If a richer role hierarchy (beyond flat roles + scope) becomes a real product requirement, that is new work, not a gap in what's documented here |

---

## 4. Audit controls

| Field | Value |
|---|---|
| **Capability** | Tamper-evident audit logging |
| **Owner** | Backend: `app/services/enterprise_audit_service.py` (current), `app/audit.py` (deprecated shim) |
| **Status** | **Production** |
| **Implementation evidence** | Every route reviewed in this and prior passes (`network_benchmark.py`, `atlas_enterprise.py`, dozens of others) calls `log_audit_event()`, which the codebase's own `DeprecationWarning` (raised on every call, visible throughout this session's test output) confirms delegates to `record_enterprise_audit_event()` for hash-chained, tamper-evident records — i.e., the deprecated function is a real, working forwarding shim, not dead code |
| **Tests** | `backend/tests/test_audit_writer_migration_hash_chain.py` (referenced across this session, confirms hash-chain integrity) |
| **Production availability** | Live, called on essentially every state-changing route |
| **Known limitations** | The shim (`app/audit.py`) is marked for eventual removal; callers should migrate to `record_enterprise_audit_event()` directly, but this is a housekeeping item, not a functional gap |
| **Next validation requirement** | Complete the migration off the deprecated `app.audit.log_audit_event` shim before it's removed, so no call site breaks silently |

---

## 5. Cross-organization anonymization / benchmarking

| Field | Value |
|---|---|
| **Capability** | National SPD Intelligence Network industry benchmarks (P15) |
| **Owner** | Backend: `app/services/network_benchmark_service.py`, `app/routes/network_benchmark.py` |
| **Status** | **Disabled** *(changed this pass — was previously fabricating data)* |
| **Implementation evidence** | Nothing in this codebase ever writes a real `IndustryBenchmark` row (confirmed via repo-wide grep of construction sites). Fixed this pass: `compute_industry_benchmarks()` and `get_tenant_percentile()` now return `data_source: "insufficient_data"`, `suppressed: true`, and `null` values instead of the seeded-random fabrication they previously returned. The dead `_anonymize_facility_id()` SHA-256 function (never called by anything) was removed entirely |
| **Tests** | `backend/tests/test_p15_network.py` — `test_benchmarks_report_insufficient_data_when_none_is_real`, `test_benchmarks_labeled_real_when_a_real_row_exists`, `test_my_percentile_reports_insufficient_data` (all passing) |
| **Production availability** | Routes remain live (`GET /api/network/benchmarks`, `/benchmarks/my-percentile`) but now correctly report no data rather than fabricated data. Confirmed via grep that no current frontend page calls these routes, so the fix closes a latent risk (direct API callers) rather than an active UI misrepresentation |
| **Known limitations** | Computing 6 real cross-tenant metrics (contamination_rate, inspection_pass_rate, baseline_adoption_rate, instrument_quality_score, vendor_performance_score, override_rate) from real `NetworkParticipant` activity does not exist — this is real, new engineering work, deliberately not built in this pass per "do not add features" |
| **Next validation requirement** | Either build real per-tenant aggregation for these 6 metrics (mirroring `horizon_benchmark_service.py`'s already-correct, k-anonymized pattern) and re-promote to Pilot/Production, or formally retire this module in favor of Horizon |

| Field | Value |
|---|---|
| **Capability** | Cross-organization benchmarking (Horizon / Research Portal) |
| **Owner** | Backend: `app/services/horizon_benchmark_service.py` |
| **Status** | **Production** |
| **Implementation evidence** | `horizon_benchmark_service.py:1-11` (module docstring: "Every percentile is computed from real per-tenant values among enrolled organizations... never a seeded-random mock"); `:44-143` (`_per_tenant_values()` queries real `Inspection`/`InspectionFinding`/`RepairRequest`/`KnowledgeArticle`/`InstrumentFlowRecord` rows scoped to `horizon_participation_service.list_enrolled_tenant_ids`); k=5 anonymity enforced (`suppressed = n < MIN_FACILITIES`) |
| **Tests** | Covered under the Horizon test suite (referenced in `docs/product-evolution/v1.3/BENCHMARKING_GUIDE.md`) |
| **Production availability** | Live, wired to `ResearchPortalDashboard.tsx`'s "Global Benchmarking (percentiles, never raw org data)" tab |
| **Known limitations** | None found this pass |
| **Next validation requirement** | None |

---

## 6. Baseline resolution

| Field | Value |
|---|---|
| **Capability** | Manufacturer/vendor/hospital baseline lookup and matching for inspection scoring |
| **Owner** | Backend: `app/services/baseline_comparison_scoring_service.py` (`resolve_baseline()`), `app/models/baseline_library.py`, `app/models/enterprise_quality.py` |
| **Status** | **Production** |
| **Implementation evidence** | `resolve_baseline()` (`baseline_comparison_scoring_service.py:402-426`) performs genuine SQLAlchemy queries against `BaselineLibraryEntry` (`:319-341`) and `EnterpriseVendorBaselineSubscription` (`:344-399`), matching on `instrument_category`/`baseline_type`/`approval_status`, prioritized manufacturer → vendor → hospital. `supervisor_review_required` is set directly from the real query's `analysis_status` result (`app/routes/inspections.py:451-461`), not seeded or random |
| **Tests** | `backend/tests/test_baseline_comparison_scoring.py` and `backend/tests/test_manufacturer_baseline_flow.py` (27 tests, passing) — exercise real DB rows through `resolve_baseline()` and the full `/api/inspections` call chain |
| **Production availability** | Live — every real inspection submission resolves against these real tables |
| **Known limitations** | A separate, unrelated admin-browsing endpoint (`GET /api/network/baselines`, `app/routes/baseline_library.py:42-60`) falls back to `_mock_baselines()` seeded data when the table is empty -- this is a display convenience for an admin search UI, not part of the `resolve_baseline()` path that inspection scoring actually uses. It already labels itself `data_source: "mock"`/`"insufficient_data"`, and the one consumer (`PilotDashboardCards.tsx`'s KPI tiles) now surfaces that label as a "Demonstration Data" tag (fixed this pass, along with a separate fabricated `342`/`315`/`27` fallback in `baseline_stats()` that returned hardcoded counts whenever the table was empty -- now returns real, possibly-zero counts) |
| **Next validation requirement** | None outstanding for this finding |

---

## 7. Supervisor review / disposition action

| Field | Value |
|---|---|
| **Capability** | Supervisor approve/modify/escalate/reclean/repair/remove-from-service/manufacturer-review disposition action |
| **Owner** | Frontend: `frontend/src/components/ReadinessDispositionPanel.tsx`; Backend: `app/routes/clinical_readiness.py` |
| **Status** | **Production** |
| **Implementation evidence** | `ReadinessDispositionPanel.tsx:34-42` (real 7-action set), `:51-53` (real role gate: `admin`/`spd_manager`), `:78-96` (real `POST /api/inspections/{id}/disposition-action`); `clinical_readiness.py:179-241` — persists via `db.commit()`, calls `workflow_state_service.record_disposition_action()` and `save_or_update_case()`. **Core Inspection Workflow Closure sprint**: added an explicit finalize guard — a disposition action on an inspection already in a terminal workflow state (`Completed`/`Cancelled`) now returns `409 Conflict` instead of silently re-finalizing it; added a `disposition_action_{action}` audit event (previously this entire route had zero audit calls); the frontend panel's `load()`/`submitAction()` now have real loading/error states (previously a fetch failure silently rendered nothing) |
| **Tests** | Backend route tests confirm the persistence chain (role gate, reason requirement, DB commit); `backend/tests/test_core_inspection_workflow_closure.py::TestDispositionActionAuditAndFinalization` (audit event persisted, cannot act on an already-finalized inspection, original AI output not overwritten) and `::TestCrossTenantAccessDenied` (disposition-action denied across tenants) |
| **Production availability** | Live, and genuinely wired end-to-end — not a stub |
| **Known limitations** | **Reachability gap** (documented, not fixed — would require new route-param/queue-linking work, out of scope for "no new features"): the panel only appears in the same browser session as the inspection's own AI-analysis submission. `InspectionWorkQueuePage.tsx`'s "Supervisor Reviews" table (`:56-97`) has no click-through into this panel — a supervisor can see that review is needed but cannot navigate there from the queue. A prior internal review (`docs/commercial-readiness/FINAL_READINESS_REPORT.md:35`) incorrectly stated this action didn't exist at all; it does exist, just with this narrower reachability than a durable review-queue workflow implies |
| **Next validation requirement** | If closing the reachability gap becomes a priority, it requires: (a) route-param/query-param handling in `NewInspectionPage.tsx` to load an arbitrary already-submitted inspection, and (b) a click-through link from `InspectionWorkQueuePage.tsx`'s queue rows — both are feature additions, correctly out of scope for this pass |

---

## 8. Report generation

| Field | Value |
|---|---|
| **Capability** | Atlas executive reports (PDF/Excel/CSV) and Vanguard board packets (PDF/Excel/PPTX) |
| **Owner** | Backend: `app/services/atlas_report_service.py`, `app/services/vanguard_board_reporting_service.py` |
| **Status** | **Production** |
| **Implementation evidence** | `atlas_report_service.py:48-100` pulls real DB-derived summaries (`atlas_dashboard_service.enterprise_dashboard()`, real per-tenant `Inspection` aggregates, `:106-141`); export builders use real `csv.DictWriter`/`openpyxl.Workbook`/`reportlab.pdfgen.canvas` (`:120-188`) rendering the stored, real data — no hardcoded content found. `vanguard_board_reporting_service.py:78-215` — same pattern, reusing the Atlas pipeline plus `vanguard_executive_intelligence_service`, rendering via real `reportlab`/`openpyxl`/`python-pptx` |
| **Tests** | `backend/tests/test_atlas_enterprise.py::test_generate_report_and_export`, `backend/tests/test_vanguard_intelligence.py::test_board_packet_exports_produce_bytes` / `test_api_board_report_pdf_endpoint` — all passing |
| **Production availability** | Live, real data end-to-end |
| **Known limitations** | **Test-coverage gap, not a code gap**: no backend test opens/parses the generated PDF/XLSX/PPTX/CSV bytes to assert actual content — tests check HTTP status, content-type, a PDF magic-number check, and byte-length only (confirmed via repo-wide grep for `load_workbook`/`PdfReader`/`Presentation(` — zero matches). The generation mechanism itself is genuinely real; the test suite just doesn't prove it as rigorously as it could |
| **Next validation requirement** | Add at least one test per format that parses the generated file (`openpyxl.load_workbook`, a PDF text extractor, `pptx.Presentation()`) and asserts real field values appear in it — strengthens existing Production status with stronger evidence, doesn't change the status itself |

---

## 9. Dashboard APIs — fabricated fallback removal (this program's earlier pass)

| Field | Value |
|---|---|
| **Capability** | ROI Center, Value Realization, Network Dashboard |
| **Owner** | Frontend: `ROICenterPage.tsx`, `ValueRealizationPage.tsx`, `NetworkDashboardPage.tsx` |
| **Status** | ROI Center / Value Realization: **Pilot** (real backing APIs, honest error states). Network Dashboard: **Disabled** (backing API doesn't exist) |
| **Implementation evidence** | ROI/Value Realization: `/api/analytics/kpi-summary`, `/api/capa`, `/api/analytics/powerbi` all exist and are wired (`app/routes/analytics.py`, `app/routes/capa.py`); fixed this program's earlier pass to show honest error states instead of hardcoded fallback numbers (247/42/12/8/78, 47/4/1/72) on failure. Network Dashboard: `/api/enterprise/network-snapshot` does not exist anywhere in `backend/app/routes/` (confirmed via grep); fixed to show an honest "Not Available in Current Model" empty state instead of 4 hardcoded fake facilities |
| **Tests** | No frontend test runner exists in this repo (`frontend/package.json` has no `vitest`/`jest`); verified via clean `npm run build` (TypeScript compiles) |
| **Production availability** | ROI/Value Realization live with real data when the backing calls succeed. Network Dashboard's page is live but always shows the honest empty state today, since its backing endpoint doesn't exist |
| **Known limitations** | ROI Center/Value Realization are labeled Pilot rather than Production because their headline `$` figures are explicitly hedged as "conservative estimates" from fixed industry-benchmark multipliers (`$28k avg SSI cost`, etc.), not measured financial outcomes — this is disclosed in-page but is a real limitation on what "Production" would imply |
| **Next validation requirement** | Network Dashboard: build the real `/api/enterprise/network-snapshot` endpoint (new work, correctly out of scope for this pass) before re-enabling. ROI/Value Realization: validate the benchmark multipliers against real customer outcome data before calling the estimates anything stronger than "conservative estimate" |

---

## 10. Core Inspection Workflow (end-to-end) — Sprint 2, "Core Inspection Workflow Closure"

| Field | Value |
|---|---|
| **Capability** | The full canonical workflow: technician creates inspection → uploads image → runs the currently-deployed model → receives an honest, scope-limited result → submits for review → supervisor confirms/corrects/finalizes with a governed reason and action; viewer blocked from all of it, backend-enforced |
| **Owner** | Frontend: `NewInspectionPage.tsx`, `ReadinessDispositionPanel.tsx`; Backend: `app/routes/inspections.py`, `app/routes/clinical_readiness.py`, `app/services/baseline_comparison_scoring_service.py`, `app/services/workflow_state_service.py` |
| **Status** | **Pilot** |
| **Implementation evidence — checked against every Pilot criterion** | (1) Frontend action exists — `/inspection/new` form, real submit, real Supervisor Disposition Workspace. (2) Backend action exists — `POST /api/inspections`, `POST /api/inspections/upload-images`, `POST /api/inspections/{id}/disposition-action`, all real. (3) Actual model is invoked — `analyze_inspection()` runs synchronously on every image submission; its output is now honestly scoped via `model_result` (Section 1). (4) Result is persisted — `Inspection` row + `InspectionFinding` rows + append-only `WorkflowStateEvent` rows. (5) Supervisor review works — `DispositionOverride` rows persisted separately from the original AI snapshot, reason required for every non-approve action, terminal-state finalize guard added this sprint (409 on re-disposition). (6) RBAC enforced — `require_inspection_runner`/`require_roles` on every route, backend-checked (not just UI-hidden); a real cross-tenant read gap in `GET /inspections/{id}` (silently skipped the tenant filter for any dev-auth-style user with no `tenant_id` attribute) was found and fixed this sprint. (7) Audit events exist — `inspection_created`/`inspection_analysis_succeeded`/`inspection_analysis_failed`/`inspection_image_uploaded`/`disposition_action_{action}`, all added or confirmed this sprint. (8) Automated tests pass — `backend/tests/test_core_inspection_workflow_closure.py` (11 new tests) plus the full existing suite, 3403 passed / 2 skipped / 0 failed. (9) Manual acceptance script exists — `docs/remediation/core-inspection-workflow-acceptance.md` (8 scenarios); Scenario 1's core UI claims (Model Result section, supported/unsupported category rendering, Experimental banner, Supervisor Disposition Workspace) were live-verified via a headless-Chromium Playwright drive against real dev servers in this sprint, not just read from code |
| **Tests** | `backend/tests/test_core_inspection_workflow_closure.py` (11 tests: honest model-result contract ×2, analysis-failure safety ×1, image-upload integrity ×2, disposition-action audit/finalization ×3, cross-tenant denial ×2, viewer-cannot-transition ×1); existing `test_inspection_role_permissions.py`, `test_clinical_readiness.py`, `test_ai_clinical_review.py`, `test_workflow_intelligence.py` unaffected (81+105 passing) |
| **Production availability** | Live — this is the same code path every real inspection submission already runs; nothing here is a separate demo/staging build |
| **Known limitations** | No trained CV model (see Section 1 — this is why the finding-generation step itself stays Experimental even though the surrounding workflow is Pilot). No frontend test runner exists in this repo (no `vitest`/`jest`/`@testing-library`) — frontend behavior is verified via `npm run build` (TypeScript) plus a live Playwright drive against real dev servers and the manual acceptance script, not new automated frontend test files; introducing a whole new frontend test framework was judged out of scope as new tooling/infrastructure, not a workflow fix. The supervisor-disposition reachability gap (Section 7) and the unwired `LumenAIModel`/YOLO engine (Section 1) remain open, documented limitations. `analyze_inspection()`'s deterministic-placeholder pipeline has no real failure mode of its own (it's pure Python with no external dependency), so the "model unavailable" safety path (analysis exceptions degrade to an honest `analysis_unavailable` result instead of crashing) is proven via test-injected failure (`monkeypatch`), not an observed real-world outage |
| **Next validation requirement** | Promote to Production once a real trained model replaces the deterministic placeholder (Section 1's own next-validation item) and a human reviewer has walked the manual acceptance script end-to-end and checked off all 8 scenarios |

---

## Lumen Decision Engine & Observation Doctrine

|---|---|
| **Capability** | Governed, policy-aware recommendation layer sitting on top of the existing inspection-scoring pipeline: probability-based observation taxonomy, org-configurable Baseline Decision Policy with a resolution hierarchy, an unconditional contamination-safety override, exception-based supervisor escalation, an unknown-finding learning loop, and a persisted, immutable Result Contract |
| **Owner** | Backend: `app/services/lumen_decision_engine.py`, `app/services/observation_taxonomy.py`, `app/services/policy_resolution_service.py`, `app/services/baseline_decision_policy_service.py`, `app/services/policy_simulation_service.py`, `app/services/unknown_finding_service.py`, `app/models/lumen_decision_engine.py`, `app/routes/lumen_decision_engine.py`; Frontend: `frontend/src/components/DecisionEnginePanel.tsx` |
| **Status** | **Pilot** |
| **Implementation evidence** | (1) Wired into the real inspection-submission path — `POST /api/inspections` calls `build_decision()` immediately after `analyze_inspection()` and returns `response["decision"]`. (2) Persisted — `LumenDecisionRecord` rows, immutable original-observation fields, separate `technician_*`/`supervisor_*` follow-through columns. (3) Policy governance is real and role-gated — `admin`/`spd_manager` only, draft→pending_approval→approved→active lifecycle, verified 403 for `operator`/`viewer`. (4) Policy resolution hierarchy is real — model → instrument_family → anatomy_zone → department → facility → health_system → LumenAI default, cross-tenant isolated. (5) Contamination safety override is unconditional in code, not policy data — verified against a policy with a 0.01 pass threshold. (6) Unknown-finding loop opens a real `UnknownFindingReview` row and forces supervisor review. (7) Policy simulation is read-only — verified record count unchanged before/after. (8) Audit — every decision and every human follow-through writes a `record_enterprise_audit_event` row. (9) Automated tests — `backend/tests/test_lumen_decision_engine.py` (19 tests covering all of Section 18's 22 checklist items, several items covered by more than one test). |
| **Tests** | `backend/tests/test_lumen_decision_engine.py` |
| **Production availability** | Live on the same inspection-submission path every real inspection already runs |
| **Known limitations** | "Condition remains after recleaning" is not yet an automated re-check hook (see `docs/decision-engine/SUPERVISOR_ESCALATION_MODEL.md`); Digital Twin trend is honestly reported as `not_available` rather than wired to a real trend computation; the frontend 4-panel view is additive alongside the pre-existing `ClinicalDecisionPanel`, not a replacement of it |
| **Next validation requirement** | A human reviewer walks a real inspection through both the new `DecisionEnginePanel` and the policy-publish workflow end-to-end before this is considered pilot-ready UI, not just backend-verified |

---

## Findings Register — carried forward, not yet fixed

These are real findings from this pass's evidence-gathering that don't yet have a corresponding fix, listed here for traceability per the Definition of Done ("a reviewer can identify... its actual maturity status" even where the status is "known gap, not yet addressed"):

1. ~~`GET /api/network/baselines`'s mock-data fallback has no UI label~~ — **fixed this pass** (see Section 6 above: `PilotDashboardCards.tsx` now surfaces the backend's own `data_source` label, and `baseline_stats()`'s separate `342`/`315`/`27` fabricated fallback was removed).
2. The lower-level `LumenAIModel`/YOLO inference engine (`app/ai/inference.py`) has no frontend caller and no explicit product decision to wire it in or retire it.
3. The supervisor disposition action's reachability gap (Section 7 above) — real and wired, but not durably linkable from the review queue.
4. ~~`GET /api/inspections/{id}` silently skipped its tenant filter for any authenticated user whose user object carries no `tenant_id` attribute (true for every dev-auth identity), allowing cross-tenant reads by ID~~ — **fixed this sprint** (Core Inspection Workflow Closure): now falls back to the request's tenant header exactly like `create_inspection` does, closing a real cross-tenant read gap discovered while writing the cross-tenant test in `test_core_inspection_workflow_closure.py`.
5. No frontend automated-test runner exists in this repo (no `vitest`/`jest`/`@testing-library` in `frontend/package.json`) — frontend behavior for this and prior Product Truth Reset passes has been verified via `npm run build` plus live Playwright drives against real dev servers, not via a committed frontend test suite. Introducing a test framework was judged out of scope for a workflow-closure sprint; if a future sprint wants automated frontend regression coverage, that's new tooling work, not a bug fix.
