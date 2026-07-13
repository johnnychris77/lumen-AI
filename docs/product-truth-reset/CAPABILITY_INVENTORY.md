# LumenAI — Product Truth Reset: Capability Inventory

Every capability below is checked against the currently running code, not documentation or prior review write-ups. "Evidence" cites the exact file:line that proves or disproves the claim. This inventory covers the AI-inspection pipeline and the dashboards/pages most likely to overstate what the platform actually does — it is not a full re-audit of the ~90-route frontend (that already exists in `docs/architecture/` and `docs/product-evolution/`).

## 1. AI inspection / finding-category detection

| Capability claimed | Reality | Evidence |
|---|---|---|
| "AI-assisted inspection" detects contamination/defect findings from an uploaded image | **Real, but two different placeholder engines — no trained computer-vision model ships in this repo.** | See below |
| Full 12-13 category taxonomy (blood, bone, tissue, debris, corrosion, crack, insulation damage, etc.) is detected | **Not supported by real inference.** Only reachable pathway (`baseline_comparison_scoring_service.analyze_inspection()`) generates every category from a SHA-256-seeded pseudo-random value, boosted only if the technician manually declared that finding | `backend/app/services/baseline_comparison_scoring_service.py:1-21` (module docstring: "THIS IS A DETERMINISTIC PLACEHOLDER — NOT PRODUCTION COMPUTER VISION"), `:1051-1060` (per-KPI pseudo-random probability) |
| A second, lower-level inference path exists (`LumenAIModel._deterministic_fallback()`) | Real code, but **not reachable from any current frontend flow** — grep of `frontend/src` for `stream/frame` / `stream_frame` returns zero matches. Its 4-value category list (`stain`/`debris`/`clean`/`corrosion`) is dead from the UI's perspective. | `backend/app/ai/inference.py:100-132`; reachable only via `POST /stream/frame` (`backend/app/routes/inspect.py:109`) / queued variant (`backend/app/routes/stream.py:55`) |
| The system can tell you whether it's running a trained model or the placeholder | **Yes — a real, honest, admin-gated endpoint already exists** (`get_inference_status()`), but until this change it was never called by any frontend code. | `backend/app/ai/inference_status.py:17-64`, `backend/app/routes/system.py:123-137` (admin-only, intentionally — "operationally sensitive information") |
| Dashboard's finding-category KPI cards ("AI-detected contamination types") | **False as originally worded.** This panel reads `/api/enterprise/findings/kpi-summary`, which keyword-matches `EnterpriseFinding.finding_category` — a **client-supplied free-text field from bulk-intake data**, not AI output. | `backend/app/routes/enterprise_intake.py:10470-10544` (`CATEGORY_KEYWORDS` matched against text), `:377,382` (field is set from `payload.finding_category`, i.e. hospital-supplied intake data) |
| A separate "CV Inspection Intelligence" panel exists | **Real UI, backed by a mock CV provider by default.** `CVRegistry.get_provider()` falls back to `MockCVProvider` (`random.Random(hash(image_url))`-seeded findings) whenever no onnx/openai/roboflow provider is configured — the default state today. | `backend/app/cv/registry.py:18-27`, `backend/app/cv/mock_provider.py:41-52`, called from `frontend/src/components/CVInspectionDashboard.tsx:101` with a hardcoded `tenantId="demo-tenant"` default (`frontend/src/pages/DashboardApp.tsx:506`) |

**Bottom line**: as of this review, **zero finding categories are backed by real, trained-model image analysis** in the pathway users actually exercise. Every "AI finding" a user sees today is either a deterministic hash-derived heuristic, a technician's own manual entry echoed back, or a mock CV provider's random output.

## 2. Enterprise/executive dashboards — real data vs. fabricated fallback

| Page | Capability claimed | Reality | Evidence |
|---|---|---|---|
| ROI Center (`/roi-center`) | Computes ROI from real inspection/CAPA/baseline data | **Real when the API succeeds** (`/api/analytics/kpi-summary`, `/api/analytics/powerbi`, `/api/capa` all exist and are wired) — but previously fell back to hardcoded numbers (247/42/12/8/78) on any failure, with no "this is fake" indicator. **Fixed this pass.** | `frontend/src/pages/ROICenterPage.tsx` (pre-fix: line 127) |
| Value Realization (`/value-realization`) | Same, plus an "Active Users" metric | Same fallback pattern, **worse**: numeric fallbacks (47/4/1/72) fired even on a 200 response if any single field was merely absent, and "Active Users" was **unconditionally hardcoded to 8** with no backing field anywhere in the API. **Fixed this pass** — active users now correctly reports "Not available" since no real source exists. | `frontend/src/pages/ValueRealizationPage.tsx` (pre-fix: lines 54, 167-170, 173); confirmed no `active_users` field anywhere in `backend/app/routes/analytics.py` |
| Network Dashboard (`/network-dashboard`) | Cross-facility health scores for an enterprise account | **The backing endpoint does not exist.** `/api/enterprise/network-snapshot` has zero matches anywhere in `backend/app/routes/`. Every page load silently rendered 4 hardcoded fake facilities ("Memorial Main Campus," etc.) as if live, including a synthesized "Emergency CS call recommended within 48 hours" alert. **Fixed this pass** — now shows an honest "not yet available" state. | `frontend/src/pages/NetworkDashboardPage.tsx` (pre-fix: lines 19-26, 62, 64) |
| CV Inspection Intelligence panel | Real-time CV analytics | Backed by `MockCVProvider` by default (see above), presented with no demo-data indicator. **Labeled this pass.** | `frontend/src/components/CVInspectionDashboard.tsx` |

## 3. Cross-organization benchmarking

| Capability claimed | Reality | Evidence |
|---|---|---|
| `network_benchmark_service.py` computes real, k-anonymized cross-facility industry benchmarks | **Fabricated.** Nothing in this codebase ever writes a real `IndustryBenchmark` row, so the "DB-first" check always misses and every call falls through to a seeded-random generator (`rng.uniform(0.6, 0.99)`), then wraps the result in real Laplace noise — making fabricated numbers look statistically legitimate. Its own `_anonymize_facility_id()` SHA-256 function is dead code, never called from anywhere. **Labeled this pass** (`data_source: "fabricated_demo"` now present on every affected response). | `backend/app/services/network_benchmark_service.py:31-34` (dead function), `:81-103` (fallback), confirmed via repo-wide grep: no `IndustryBenchmark(` construction site exists outside its own model/migration |
| `horizon_benchmark_service.py` computes real cross-org benchmarks | **Confirmed genuinely real** — computes from actual per-tenant `Inspection`/`InspectionFinding`/`RepairRequest`/etc. rows, scoped to enrolled tenants, suppresses cohorts below k=5, never fabricates for an inactive tenant. Wired to the Research Portal's "Global Benchmarking" tab. | `backend/app/services/horizon_benchmark_service.py:1-11` (module docstring), `:44-143`; consumed via `horizon_research_portal_service.py:19,55` → `ResearchPortalDashboard.tsx:83,135-148` |
| Frontend surfaces `network_benchmark_service`'s fabricated output as real | **Not currently** — grep of `frontend/src` for `api/network/benchmarks` returns zero matches. The risk is latent (reachable by any network-participant tenant via direct API call, or by a future frontend wiring), not actively misrepresented in the product UI today. | Confirmed via full-repo grep |

## 4. Supervisor approve/return workflow

| Capability claimed | Reality | Evidence |
|---|---|---|
| Prior review (`docs/commercial-readiness/FINAL_READINESS_REPORT.md:35`) stated: "no reachable supervisor approve/return action was found anywhere in the frontend" | **Out of date.** A real, role-gated, DB-committing disposition action exists today: `ReadinessDispositionPanel.tsx` posts to a real backend endpoint that persists the decision, updates workflow state, and saves to the case library. | `frontend/src/components/ReadinessDispositionPanel.tsx:34-42` (real action set: approve/modify/escalate/reclean/repair/remove_from_service/manufacturer_review), `:78-96` (real POST), `backend/app/routes/clinical_readiness.py:179-223` (`db.commit()`, `record_disposition_action`, `save_or_update_case`) |
| The action is reliably reachable as a durable review workflow | **Narrower than "exists."** It only appears in the same browser session as the inspection's own AI-analysis submission — there is no route/query-param handling to load an arbitrary already-submitted inspection back into this panel later. The one page listing inspections awaiting review (`InspectionWorkQueuePage.tsx`) renders a plain, non-interactive table with no click-through into the disposition action. | `frontend/src/pages/NewInspectionPage.tsx` (no `useParams`/`useSearchParams` for loading a past inspection); `frontend/src/pages/InspectionWorkQueuePage.tsx:56-97` (`QueueTable`, no `Link`/`onClick`/button per row) |

This reachability gap is a real, documented finding but is **not** addressed in this pass — it is a workflow-completeness gap, not a false capability claim, and fixing it would mean adding a feature (route-param inspection lookup + queue click-through), which is explicitly out of scope for "eliminate misleading capability presentation."

## 5. Demo/synthetic data labeling — what already exists

Most of the platform's dashboards already follow a real, consistent `data_source: "real" | "mock" | "insufficient"` convention with a visible banner:

| Component | Evidence of correct labeling |
|---|---|
| `InspectionCopilotDashboard.tsx:526-537` | "Showing sample data — no real sessions yet." |
| `RegulatoryComplianceDashboard.tsx:349-359` | "Showing demo data — connect real inspection records..." |
| `PredictiveAnalyticsDashboard.tsx:141-152` | "Demo mode: Showing seeded representative data..." |
| `EnterpriseBenchmarkDashboard.tsx:243-262` | Explicit no-data warning + guidance |
| `DigitalTwinDashboard.tsx:60,66,312` | Raw `data_source` field rendered inline |
| `VendorIntelligenceDashboard.tsx:24,37,69,77,238-239` | Raw `data_source` field rendered inline |

Gaps found and fixed this pass: `CVInspectionDashboard.tsx` (no label at all, despite a hardcoded demo tenant and mock CV provider) and `GlobalInfrastructureConsole.tsx`'s `PassportImageGallery` (grafts demo-manifest metadata — facility name, finding category — onto a *real* instrument's passport page with no disclaimer).

`pilotImageManifest.ts` (all 20 entries `available: false`) and `DemoImageLibraryPage.tsx` were independently verified as an honest, correctly-labeled scaffold — no fix needed there.
