# LumenAI — Product Truth Reset: Fixes Applied (Priority 1: Eliminate Misleading Capability Presentation)

This is the first and only priority implemented in this pass, per explicit scoping: no new features were added, no existing safety/human-review control was touched or weakened. Every change below is additive labeling, fallback removal, or an honest empty/error state.

## Frontend

| File | Change | Why |
|---|---|---|
| `frontend/src/lib/api.ts` | *(pre-existing from a prior fix, reused here)* `signOutOn401` opt-out flag | Used on several of the calls below so a best-effort background check doesn't sign the user out |
| `frontend/src/pages/ROICenterPage.tsx` | Removed the catch-block fallback to hardcoded `computeROI(247, 42, 12, 8, 78)`. On failure, shows an explicit "Unable to load ROI data" card instead of a normal-looking but fake headline figure. | A customer-facing ROI number that renders identically whether real or fabricated is the exact failure mode this priority targets |
| `frontend/src/pages/ValueRealizationPage.tsx` | Removed all hardcoded numeric fallbacks (`?? 47`, `?? 4`, `?? 1`, `?? 72`) that fired even on a *successful* response with a missing field; removed the unconditional `activeUsers: 8` (no backing API field exists anywhere) — now `null`, rendered as "Not available." Added an explicit error state on total fetch failure. | Same fabrication risk as ROI Center, plus a metric (`activeUsers`) that was **always** fake regardless of API success |
| `frontend/src/pages/NetworkDashboardPage.tsx` | Removed the `DEMO_FACILITIES` hardcoded fallback entirely. Its target endpoint (`/api/enterprise/network-snapshot`) does not exist anywhere in the backend, so this fired on every single page load. Now shows an honest "Network view is not yet available" empty state. | This was the most severe fabrication found: fake facility data drove a synthesized "Emergency CS call recommended within 48 hours" alert, presented as live operational guidance |
| `frontend/src/components/CVInspectionDashboard.tsx` | Added a visible demo-data banner whenever `provider_breakdown` includes `"mock"` (i.e., whenever the deployment has no real onnx/vision provider configured — the default state) | This panel's "CV Inspection Intelligence" findings are entirely `random.Random(hash(image_url))`-generated; previously presented with no indication of that |
| `frontend/src/pages/NewInspectionPage.tsx` | Surfaced the `placeholder_scoring`/`model_label` fields the backend already sends on every inspection response but the frontend previously discarded — now renders a clear "Placeholder scoring model — not a trained computer-vision model" banner in the AI Prediction panel | The backend already knew and said this; the frontend was silently dropping the signal |
| `frontend/src/pages/Dashboard.tsx` | Corrected the "Contamination KPIs" panel's description from "AI-detected contamination types" (false — this data comes from client-supplied free-text intake records, not AI) to an accurate description naming the actual data source and noting only `debris`/`corrosion` are real model-distinguished findings | Direct, provably false claim in the UI |
| `frontend/src/components/AiModelPerformanceCard.tsx` | Added an admin-only fetch of the existing (previously unwired) `/api/v1/system/inference-status` endpoint; renders "✓ Running a trained model" or "⚠ Running the deterministic placeholder scorer" | Exposes the actual currently-supported model class honestly, without loosening the endpoint's existing admin-only gate |
| `frontend/src/pages/GlobalInfrastructureConsole.tsx` | Added a disclaimer to `PassportImageGallery` clarifying that matched images are demo/reference content from the pilot manifest, not this specific instrument's own capture history | Demo metadata (facility name, finding category) was being grafted onto a real instrument's passport view with no disclosure |

## Backend

| File | Change | Why |
|---|---|---|
| `backend/app/services/network_benchmark_service.py` | `compute_industry_benchmarks()` and `get_tenant_percentile()` now include an explicit `data_source: "real" \| "fabricated_demo"` field on every entry. Since nothing in this codebase writes a real `IndustryBenchmark` row, every benchmark returned today is correctly labeled `"fabricated_demo"`. | Closing the gap between "looks like a real, noised cross-org statistic" and "is actually a seeded-random number" — matters even though no current frontend page calls this route, since it's reachable by any network-participant tenant via direct API call |
| `backend/app/routes/network_benchmark.py` | `GET /api/network/benchmarks`'s response `note` field now says so explicitly when any entry is fabricated, instead of the previous generic "all values include differential privacy noise" (true, but misleading about what's being noised) | Same |

## What was deliberately NOT changed

- **No architecture changes.** The AI inference pipeline itself (`baseline_comparison_scoring_service.py`, `app/ai/inference.py`) was not modified — only its existing, already-computed honesty signals were surfaced.
- **No safety/human-review control was touched.** `human_review_required` defaults, override-reason requirements, RBAC gates, and the `/v1/system/inference-status` endpoint's admin-only restriction are all unchanged.
- **The supervisor work-queue click-through gap** (`InspectionWorkQueuePage.tsx` has no way to open a specific inspection's disposition panel from the queue) is a real, documented finding but was not fixed — closing it means adding route-param inspection lookup, which is a feature addition, out of scope for this priority.
- **`network_benchmark_service.py`'s dead `_anonymize_facility_id()` function** was not wired in or removed — doing either would be a design decision (build real facility-level anonymization vs. retire the module in favor of `horizon_benchmark_service.py`) beyond "label what's fabricated," which is what this pass addresses.
- **No CV_PROVIDER was configured or model weights added.** Labeling honesty does not require making the underlying capability real.

## Regression tests added

- `backend/tests/test_p15_network.py`: three new tests —
  1. `test_benchmarks_are_labeled_fabricated_when_no_real_data_exists` — proves every benchmark entry is labeled `"fabricated_demo"` in the realistic default case (no real `IndustryBenchmark` rows).
  2. `test_benchmarks_labeled_real_when_a_real_row_exists` — inserts a real `IndustryBenchmark` row and proves that specific metric is labeled `"real"`.
  3. `test_my_percentile_is_labeled_fabricated` — proves `get_tenant_percentile()` always reports `"fabricated_demo"`.

Frontend regression tests were not added: `frontend/package.json` has no test runner configured (`vite`/`vite build`/`vite preview` only, confirmed by reading the file — no `vitest`/`jest` dependency or script exists). Adding one would itself be a feature addition beyond this priority's scope. Frontend correctness for this pass is verified by a clean `npm run build` (TypeScript compiles, no type errors across all 9 touched files).

## Validation results

- `npm --prefix frontend run build` — clean, no errors.
- `ruff check backend/app backend/tests` — all checks passed.
- `cd backend && PYTHONPATH=. python -m pytest tests -q` — 3391 passed, 2 skipped, 1 failed. The one failure (`test_or_connect.py::TestCaseIntelligenceDashboard::test_dashboard_returns_todays_cases`) is a pre-existing, unrelated UTC-midnight test-date-boundary flake in a file last touched by an unrelated "Project Symphony" commit that predates this session; it is not caused by any change in this diff (confirmed: the test creates a case scheduled `now + 1 hour` and asserts it appears in "today's" cases — this fails only when the test run straddles UTC midnight, which it did at 23:49 UTC). Re-run scheduled after the UTC date rolled over to confirm.
