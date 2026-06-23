# LumenAI Feature Audit Report
**Date:** 2026-06-23 | **Branch:** claude/tender-johnson-mww1wi | **Tests:** 2,059 passing

---

## Section 1 — Implemented and Visible
*Backend exists · Frontend exists · Route exists · Navigation exists*

| Feature | Backend Route(s) | Frontend Page | Route | Nav Label | Nav Group |
|---------|-----------------|---------------|-------|-----------|-----------|
| **Surgical Readiness Index** | `POST /api/infrastructure/readiness` | `GlobalInfrastructureConsole` (Readiness tab) | `/infrastructure` | Quality Infrastructure | Network Intelligence |
| **Quality Registry** | `GET /api/infrastructure/quality-registry` | `GlobalInfrastructureConsole` (Registry tab) | `/infrastructure` | Quality Infrastructure | Network Intelligence |
| **Global Benchmarking** | `GET /api/standards/benchmarks`<br>`GET /api/enterprise/benchmarks/*`<br>`GET /api/network/benchmarks` | `GlobalStandardsConsole` (Benchmarks tab) | `/global-standards` | Standards & Benchmarks | Network Intelligence |
| **Baseline Governance** | `GET/POST /api/standards/baseline-governance`<br>`GET /api/network/baselines` | `GlobalStandardsConsole` (Standards tab)<br>`ManufacturerBaselinesPage`<br>`BaselineReviewPage` | `/global-standards`<br>`/manufacturer-baselines`<br>`/baseline-review` | Standards & Benchmarks<br>Manufacturer Baselines<br>Baseline Review | Multiple |
| **Recall Signal Engine** | `GET /api/network/recall-signals`<br>`GET /api/global-intelligence/recall-warnings`<br>`POST /api/global-intelligence/recall-warnings/{id}/notify` | `GlobalIntelligenceConsole` (Recall Warnings tab)<br>`NetworkIntelligenceConsole` (Recall Watch tab) | `/global-intelligence`<br>`/network-intelligence` | Global Surgical Intelligence<br>Network Intelligence | Network Intelligence |
| **Research Exchange** | `GET/POST /api/network-intelligence/research/datasets`<br>`GET/POST /api/network-intelligence/research/studies`<br>`GET/POST /api/network-intelligence/research/publications` | `NetworkIntelligenceConsole` (Research tab) | `/network-intelligence` | Network Intelligence | Network Intelligence |
| **Instrument Lifecycle** | `POST /api/infrastructure/instruments/{id}/lifecycle`<br>`GET/POST /api/network-intelligence/lifecycle/*` | `GlobalInfrastructureConsole` (Instruments tab — status display)<br>`NetworkIntelligenceConsole` (Lifecycle tab) | `/infrastructure`<br>`/network-intelligence` | Quality Infrastructure<br>Network Intelligence | Network Intelligence |
| **Executive Intelligence** | `GET /api/executive/dashboard/{role}`<br>`GET /api/executive/summary`<br>`GET /api/network-intelligence/executive/*`<br>`GET /api/intelligence/executive-summary` | `EnterpriseDashboard`<br>`NetworkIntelligenceConsole` (Executive tab) | `/enterprise`<br>`/network-intelligence` | Enterprise<br>Network Intelligence | Enterprise & Growth<br>Network Intelligence |

---

## Section 2 — Implemented but Hidden
*Backend exists · Frontend exists · Not reachable from dashboard navigation*

| Feature | Backend Route(s) | Frontend Asset | Problem |
|---------|-----------------|----------------|---------|
| **Instrument Passport** | `GET /api/infrastructure/instruments/{id}/passport`<br>`POST /api/infrastructure/instruments/{id}/passport` | `GlobalInfrastructureConsole.tsx` — file exists and is routed at `/infrastructure`, but **no Passport tab is rendered**. The 5 tabs are: Dashboard, Instruments, Readiness, Registry, Forecasts. Passport events are API-only. | No tab/panel in the console exposes passport history. Users cannot browse or log passport events from the UI. |
| **Global Registry (SPD)** | `GET /api/network/registry/lookup`<br>`POST /api/network/registry`<br>`GET /api/network/registry/stats`<br>`GET /api/network/registry/search`<br>`GET /api/network/registry/{udi}/defect-history` | `GlobalInfrastructureConsole.tsx` Quality Registry tab consumes `/api/infrastructure/quality-registry` (P25 aggregate registry). The **SPD instrument registry** at `/api/network/registry` has no UI surface at all. | SPD-level UDI lookup, defect history, and registry search are backend-only. The P25 quality registry tab is a separate aggregate feed. |
| **ManufacturerPortal** | Multiple baseline + intake routes | `ManufacturerPortal.tsx` — page component exists in `frontend/src/pages/` | **No `<Route>` in `main.tsx`.** The file is unreachable. `/vendor-baseline-portal` routes to `VendorBaselinePortalPage.tsx` instead. |
| **VendorIntakePage** | Intake routes | `VendorIntakePage.tsx` — separate page component exists | **No `<Route>` in `main.tsx`.** `/vendor-intake` routes to `VendorIntake.tsx`. Duplicate page, dead file. |

---

## Section 3 — Backend Only
*API exists · No UI*

| Feature | Backend Route(s) | Backend File | UI Status |
|---------|-----------------|--------------|-----------|
| **Knowledge Graph** | `GET /api/intelligence/risk-graph`<br>`GET /api/intelligence/signals`<br>`GET /api/intelligence/emerging-risks`<br>`GET /api/intelligence/investigations`<br>`POST /api/intelligence/run-analysis` | `quality_intelligence.py` | No page, no route, no nav item. `VendorIntelligenceDashboard.tsx` exists as a component but is not mounted anywhere. No graph visualization exists. |
| **Vendor Intelligence** | `GET /api/vendor-intelligence/vendors`<br>`GET /api/vendor-intelligence/vendors/{id}`<br>`GET /api/vendor-intelligence/vendors/{id}/scorecard`<br>`GET /api/vendor-intelligence/vendors/{id}/trends` | `vendor_intelligence.py` | No dedicated page or route. `VendorIntelligenceDashboard.tsx` is a standalone component with no parent page or route mounting it. Not surfaced in `CommercialConsole`. |
| **Anomaly Detection** | `POST /api/network-intelligence/anomaly-detection/run`<br>`GET /api/network-intelligence/anomaly-detection/runs` | `p20_network_intelligence.py` | No UI surface. Anomaly runs are backend-only; results are not displayed in any console. |
| **Manufacturer Intelligence** | `GET /api/network-intelligence/manufacturer-intelligence`<br>`POST /api/network-intelligence/manufacturer-intelligence` | `p20_network_intelligence.py` | No UI surface. Not displayed in `NetworkIntelligenceConsole`. |
| **API Credentials (Industry Utility)** | `GET /api/infrastructure/api-credentials`<br>`POST /api/infrastructure/api-credentials`<br>`POST /api/infrastructure/api-credentials/{id}/revoke` | `p25_infrastructure.py` | No UI surface. `GlobalInfrastructureConsole` has no Credentials tab. Issuance and revocation are API-only. |
| **GSIN Enrollment + DPA** | `POST /api/global-intelligence/enroll`<br>`POST /api/global-intelligence/sign-dpa`<br>`GET /api/global-intelligence/participant-status` | `global_intelligence.py` | No UI surface. `GlobalIntelligenceConsole` does not expose enrollment or DPA signing flows. |
| **Signal Governance Review** | `POST /api/global-intelligence/signals/{id}/review` | `global_intelligence.py` | No UI. Signal review is API-only; `GlobalIntelligenceConsole` displays signals but has no approve/reject workflow. |
| **Digital Quality Twin** | Full twin CRUD + scenarios + simulations + forecasts | `digital_quality_twin.py`<br>`digital_twin.py` | `DigitalTwinDashboard.tsx` exists as a standalone component. Not routed. Not in nav. |
| **Governance Console** | Full governance command center, SLA, reconciliation, packet releases | `governance_console.py`<br>`governance_command_center.py`<br>`governance_sla.py`<br>`governance_reconciliation.py` | No page. No route. No nav item. |
| **Executive Scorecards / KPI** | `GET/POST /api/executive/*`<br>`GET /api/network-intelligence/executive/*` | `executive_scorecards.py`<br>`executive_kpi_snapshots.py`<br>`executive_digest.py` | `ExecutiveQualityReviewPanel.tsx` is a component but no dedicated Executive Intelligence page/route. Content surfaces only via the Enterprise dashboard. |
| **Patient Safety** | Full patient safety event links, harm signals, near-miss correlation | `patient_safety.py` (inferred) | No page, no route, no nav item. |

---

## Section 4 — Documentation Only
*Docs exist · No backend · No frontend*

| Feature / Document | Doc File(s) | Backend | Frontend |
|-------------------|-------------|---------|----------|
| **National SPD Intelligence Network** | `docs/network/national-spd-intelligence-network.md`<br>`docs/network/national-intelligence-platform.md` | Partial: P20 lifecycle and registry routes exist. No "national network" aggregation endpoint. | None |
| **Autonomous Quality Intelligence** | `docs/intelligence/autonomous-quality-intelligence.md` | `quality_intelligence.py` has signals + emerging risks. No autonomous execution/action layer. | None |
| **Mobile Platform** | `docs/mobile/mobile-platform-architecture.md`<br>`docs/mobile/scan-and-capture-architecture.md`<br>`docs/mobile/offline-sync-design.md`<br>`docs/mobile/notification-framework.md` | `mobile.py` exists (API route). Offline sync not implemented. | No mobile app. No PWA. No offline capability. |
| **Computer Vision / CV Inspection** | `docs/architecture/computer-vision-architecture.md`<br>`docs/architecture/cv-data-governance.md` | `cv.py` route exists. `CVInspectionDashboard.tsx` exists as component. | Not routed. No page. |
| **Global Commercialization** | `docs/global/global-commercialization-plan.md`<br>`docs/global/international-integration-matrix.md`<br>`docs/global/regulatory-readiness-matrix.md` | No implementation. P24 regional deployments are seeded stubs. | None |
| **Operations Copilot (full)** | `docs/operations/operations-copilot.md`<br>`docs/operations/autonomous-healthcare-operations.md` | `copilot.py` exists with basic query/recommendation. | `AutonomousOperationsConsole` partially surfaces it. Full copilot (autonomous execution) is doc-only. |

---

## Feature Matrix — The 12 Requested Features

| # | Feature | Backend | Frontend | Route | Nav | Status |
|---|---------|---------|----------|-------|-----|--------|
| 1 | **Global Registry** | ✅ Dual: `/api/network/registry` (SPD UDI) + `/api/infrastructure/quality-registry` (P25 aggregate) | ⚠️ Partial: P25 aggregate surfaced in Quality Registry tab; SPD UDI registry has no UI | `/infrastructure` | ✅ | **Partial — SPD registry backend-only** |
| 2 | **Instrument Passport** | ✅ GET+POST `/api/infrastructure/instruments/{id}/passport` | ❌ No UI tab in any console | `/infrastructure` (no tab) | ✅ (page exists, tab missing) | **Backend Only — no UI surface** |
| 3 | **Surgical Readiness Index** | ✅ `POST /api/infrastructure/readiness` | ✅ Readiness tab in GlobalInfrastructureConsole | `/infrastructure` | ✅ | **Fully Implemented and Visible** |
| 4 | **Recall Signal Engine** | ✅ `/api/network/recall-signals` + `/api/global-intelligence/recall-warnings` + notify endpoint | ✅ Recall Warnings tab (GlobalIntelligenceConsole) + Recall Watch tab (NetworkIntelligenceConsole) | `/global-intelligence`<br>`/network-intelligence` | ✅ | **Fully Implemented and Visible** |
| 5 | **Global Benchmarking** | ✅ `/api/standards/benchmarks` + `/api/enterprise/benchmarks/*` + `/api/network/benchmarks` | ✅ Benchmarks tab in GlobalStandardsConsole | `/global-standards` | ✅ | **Fully Implemented and Visible** |
| 6 | **Research Exchange** | ✅ `/api/network-intelligence/research/datasets` + `/studies` + `/publications` | ✅ Research tab in NetworkIntelligenceConsole | `/network-intelligence` | ✅ | **Fully Implemented and Visible** |
| 7 | **Instrument Lifecycle** | ✅ `POST /api/infrastructure/instruments/{id}/lifecycle` + full P20 lifecycle suite | ⚠️ Partial: status display in Instruments tab; no lifecycle transition UI; P20 Lifecycle tab in NetworkIntelligenceConsole shows benchmarks only | `/infrastructure`<br>`/network-intelligence` | ✅ | **Partial — no lifecycle action UI** |
| 8 | **Knowledge Graph** | ✅ `GET /api/intelligence/risk-graph` + signals + investigations | ❌ No page, no route, no visualization | None | ❌ | **Backend Only — no UI** |
| 9 | **Executive Intelligence** | ✅ `/api/executive/*` + `/api/network-intelligence/executive/*` + `/api/intelligence/executive-summary` | ✅ EnterpriseDashboard + NetworkIntelligenceConsole Executive tab | `/enterprise`<br>`/network-intelligence` | ✅ | **Fully Implemented and Visible** |
| 10 | **Vendor Intelligence** | ✅ `/api/vendor-intelligence/vendors` + scorecard + trends | ❌ VendorIntelligenceDashboard.tsx exists as component but not mounted; no page or route | None | ❌ | **Backend Only — component exists but unrouted** |
| 11 | **Baseline Governance** | ✅ `/api/standards/baseline-governance` (P24) + `/api/network/baselines` (network) | ✅ Standards tab in GlobalStandardsConsole + ManufacturerBaselinesPage + BaselineReviewPage | `/global-standards`<br>`/manufacturer-baselines`<br>`/baseline-review` | ✅ | **Fully Implemented and Visible** |
| 12 | **Quality Registry** | ✅ `GET /api/infrastructure/quality-registry` (P25) | ✅ Quality Registry tab in GlobalInfrastructureConsole | `/infrastructure` | ✅ | **Fully Implemented and Visible** |

---

## Route Inventory

| Route | Component | In Nav | Nav Group | Notes |
|-------|-----------|--------|-----------|-------|
| `/` | Dashboard | ✅ | Overview | |
| `/login` | LoginPage | — | — | Outside AppShell |
| `/operations` | OperationsDashboard | ✅ | Overview | |
| `/analytics` | AnalyticsDashboardPage | ✅ | Overview | |
| `/vendor-intake` | VendorIntake | ✅ | Inspection Intelligence | |
| `/intake-history` | IntakeHistoryPage | ✅ | Inspection Intelligence | |
| `/manufacturer-baselines` | ManufacturerBaselinesPage | ✅ | Inspection Intelligence | |
| `/baseline-review` | BaselineReviewPage | ✅ | Inspection Intelligence | |
| `/vendor-baseline-portal` | VendorBaselinePortalPage | ✅ | Inspection Intelligence | |
| `/inspection/new` | NewInspectionPage | ❌ | — | Accessible but no nav item |
| `/findings` | FindingsQueuePage | ✅ | Quality & Compliance | |
| `/capa` | CapaQueuePage | ✅ | Quality & Compliance | |
| `/accreditation` | AccreditationConsole | ✅ | Quality & Compliance | |
| `/enterprise` | EnterpriseDashboard | ✅ | Enterprise & Growth | |
| `/commercial` | CommercialConsole | ✅ | Enterprise & Growth | |
| `/growth` | GrowthConsole | ✅ | Enterprise & Growth | |
| `/pilot-analytics` | PilotAnalyticsDashboard | ✅ | Enterprise & Growth | |
| `/network-intelligence` | NetworkIntelligenceConsole | ✅ | Network Intelligence | 5 tabs: Overview, Lifecycle, Recall Watch, Research, Executive |
| `/global-intelligence` | GlobalIntelligenceConsole | ✅ | Network Intelligence | 5 tabs: Dashboard, Signals, Registry, Recall Warnings, Regulatory Evidence |
| `/global-standards` | GlobalStandardsConsole | ✅ | Network Intelligence | 5 tabs: Dashboard, Standards, Benchmarks, International, Consortium |
| `/infrastructure` | GlobalInfrastructureConsole | ✅ | Network Intelligence | 5 tabs: Dashboard, Instruments, Readiness, Registry, Forecasts |
| `/autonomous-operations` | AutonomousOperationsConsole | ✅ | Autonomous Operations | |
| `/legacy` | DashboardApp | ❌ | — | Reference only |

**Pages with no route (dead files):**
- `ManufacturerPortal.tsx` — no route in main.tsx
- `VendorIntakePage.tsx` — no route; `/vendor-intake` uses `VendorIntake.tsx` instead

---

## Page Inventory

| File | Type | Routed | Nav Item | Notes |
|------|------|--------|----------|-------|
| `AccreditationConsole.tsx` | Page | ✅ `/accreditation` | ✅ | |
| `AnalyticsDashboardPage.tsx` | Page | ✅ `/analytics` | ✅ | |
| `AutonomousOperationsConsole.tsx` | Page | ✅ `/autonomous-operations` | ✅ | |
| `BaselineReviewPage.tsx` | Page | ✅ `/baseline-review` | ✅ | |
| `CapaQueuePage.tsx` | Page | ✅ `/capa` | ✅ | |
| `CommercialConsole.tsx` | Page | ✅ `/commercial` | ✅ | |
| `Dashboard.tsx` | Page | ✅ `/` | ✅ | |
| `DashboardApp.tsx` | Page | ✅ `/legacy` | ❌ | Reference only |
| `EnterpriseDashboard.tsx` | Page | ✅ `/enterprise` | ✅ | |
| `FindingsQueuePage.tsx` | Page | ✅ `/findings` | ✅ | |
| `GlobalInfrastructureConsole.tsx` | Page | ✅ `/infrastructure` | ✅ | Missing Passport tab |
| `GlobalIntelligenceConsole.tsx` | Page | ✅ `/global-intelligence` | ✅ | Missing enrollment/DPA/review UI |
| `GlobalStandardsConsole.tsx` | Page | ✅ `/global-standards` | ✅ | |
| `GrowthConsole.tsx` | Page | ✅ `/growth` | ✅ | |
| `IntakeHistoryPage.tsx` | Page | ✅ `/intake-history` | ✅ | |
| `LoginPage.tsx` | Page | ✅ `/login` | — | |
| `ManufacturerBaselinesPage.tsx` | Page | ✅ `/manufacturer-baselines` | ✅ | |
| `ManufacturerPortal.tsx` | Page | ❌ **no route** | ❌ | Dead file |
| `NetworkIntelligenceConsole.tsx` | Page | ✅ `/network-intelligence` | ✅ | |
| `NewInspectionPage.tsx` | Page | ✅ `/inspection/new` | ❌ | No nav item |
| `OperationsDashboard.tsx` | Page | ✅ `/operations` | ✅ | |
| `PilotAnalyticsDashboard.tsx` | Page | ✅ `/pilot-analytics` | ✅ | |
| `VendorBaselinePortalPage.tsx` | Page | ✅ `/vendor-baseline-portal` | ✅ | |
| `VendorIntake.tsx` | Page | ✅ `/vendor-intake` | ✅ | |
| `VendorIntakePage.tsx` | Page | ❌ **no route** | ❌ | Duplicate/dead file |

**Routed components (not pages):**
| File | Notes |
|------|-------|
| `CVInspectionDashboard.tsx` | No route |
| `DigitalTwinDashboard.tsx` | No route |
| `EnterpriseBenchmarkDashboard.tsx` | No route |
| `VendorIntelligenceDashboard.tsx` | No route — blocks Vendor Intelligence Section 3 gap |

---

## API Inventory (Key Feature Routes)

| Domain | Prefix | Endpoints | File |
|--------|--------|-----------|------|
| Infrastructure (P25) | `/api/infrastructure` | GET/POST instruments, lifecycle, readiness, passport, quality-registry, api-credentials, forecasts, dashboard, platform-stats | `p25_infrastructure.py` |
| Global Intelligence (P23) | `/api/global-intelligence` | signals, risk-registry, recall-warnings, participant-status, regulatory-evidence, dashboard, contribute, enroll, sign-dpa, notify, network-stats, signals/{id}/review | `global_intelligence.py` |
| Standards (P24) | `/api/standards` | quality-standards, baseline-governance, benchmarks, regional-deployments, api-partners, consortium, publications, dashboard, ecosystem-overview | `p24_standards.py` |
| Network Intelligence (P20) | `/api/network-intelligence` | registry, sharing-agreements, aggregate-snapshots, lifecycle/*, recall-early-warning, anomaly-detection, manufacturer-intelligence, research/*, executive/* | `p20_network_intelligence.py` |
| Recall Signals | `/api/network/recall-signals` | list, my-exposure, get, escalate | `recall_signals.py` |
| SPD Registry | `/api/network/registry` | lookup, create, stats, search, defect-history | `instrument_registry.py` |
| Network Benchmarks | `/api/network` | opt-in, opt-out, benchmarks, my-percentile, participants | `network_benchmark.py` |
| Enterprise Benchmarks | `/api/enterprise/benchmarks` | hospitals, vendors, rollup, executive-dashboard, trends, reports, kpi-summary | `benchmarking.py` |
| Quality Intelligence | `/api/intelligence` | signals, emerging-risks, investigations, recommendations, executive-summary, run-analysis, risk-graph, quality-dashboard | `quality_intelligence.py` |
| Vendor Intelligence | `/api/vendor-intelligence` | vendors list/detail, scorecard, trends | `vendor_intelligence.py` |
| Baseline Library | `/api/network/baselines` | list, create, search, stats, get, approve | `baseline_library.py` |
| Executive | `/api/executive` | dashboard/{role}, cfo/pdf, summary | `executive.py` |

---

## Navigation Gaps

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| **Instrument Passport** has no UI tab | Passport history inaccessible to users | Add "Passport" tab to `GlobalInfrastructureConsole` consuming `GET /api/infrastructure/instruments/{id}/passport` |
| **Knowledge Graph** has backend (`/api/intelligence/risk-graph`) but no page | Entire quality intelligence signal graph is invisible | Create page or add tab to `GlobalIntelligenceConsole` or `NetworkIntelligenceConsole` |
| **Vendor Intelligence** has backend + component but no route | `VendorIntelligenceDashboard.tsx` exists unused | Add page route `/vendor-intelligence` and nav item in Enterprise & Growth |
| **GSIN Enrollment + DPA** is API-only | Users cannot self-enroll in Global Surgical Intelligence Network from UI | Add enrollment flow to `GlobalIntelligenceConsole` |
| **API Credentials** management is API-only | Industry utility keys cannot be issued or revoked from UI | Add Credentials tab to `GlobalInfrastructureConsole` |
| **SPD Registry** (`/api/network/registry`) has no UI | UDI lookup, defect history, registry search all inaccessible | Add Registry Search tab to `NetworkIntelligenceConsole` or `GlobalInfrastructureConsole` |
| **ManufacturerPortal.tsx** is a dead file | Wasted component, potential confusion | Either add route `/manufacturer-portal` or delete file |
| **VendorIntakePage.tsx** is a dead duplicate | Confusion with `VendorIntake.tsx` | Delete or merge |
| **Digital Quality Twin** has backend + component but no route | Twin simulation/scenario capability entirely hidden | Add route `/digital-twin` and nav item |
| **`/inspection/new`** has no nav item | New inspections only reachable via direct URL | Add nav item or button in Dashboard / Operations |
