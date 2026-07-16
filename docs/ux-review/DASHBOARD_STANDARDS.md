# LumenAI — Dashboard Standards

Objective 4 review. LumenAI has at least **68 distinct dashboard-like pages** enumerated during this review (via `frontend/src/pages/`, cross-referenced against `frontend/src/main.tsx`'s router) — a scale that itself is the review's headline finding: this is not a handful of role-specific views but a very large, loosely-coordinated set of independently-built screens.

## Orphaned dead code found during inventory

`pages/AuditCommandCenterEvidencePage.jsx` is a fully-built 6-KPI-card dashboard (Validation Status, Checks Passed, Failed/Warnings, Toolkit Version, Audit Events, High-Value Events) that is **not imported or routed anywhere in `main.tsx`** — confirmed via a repo-wide reference search returning zero hits outside the file itself. It should either be wired into the router and nav, or removed as dead code.

## Representative dashboard inventory (see recon transcript for the full 68-row table)

| Dashboard | Route | Audience | Widget count | State handling |
|---|---|---|---|---|
| Dashboard (main) | `/` | General overview | 12 stat cards | Spinner + error state |
| Sentinel (risk) | `/sentinel` (orphaned) | Executive/risk officer | 18 widgets | None found |
| Pulse Command Center | `/pulse` (orphaned) | Ops/executive real-time | 21 widgets | None found |
| Case Intelligence | `/case-intelligence` (orphaned) | Clinical eng/OR exec | 21 widgets — densest in the app | "No data" empty state, error text |
| Quality Dashboard | `/quality-dashboard` | Quality manager | ~20 widgets | "No data" empty state only |
| Pre-Sterilization Command Center | `/pre-sterilization-command-center` | SPD supervisor | ~20 widgets | "Failed to load" text only |
| Maestro Leadership Workspace | `/maestro` (orphaned) | Director/leadership | 17 widgets | None found |
| Oracle Workspace | `/oracle` (orphaned) | Research/data scientist | 18 widgets | "No data" empty state |

Widget density varies from a handful (Platform Health: 7 one-line labels) to 20+ (Case Intelligence, Sentinel, Pulse, Quality Dashboard) — see [HUMAN_FACTORS_REVIEW.md](./HUMAN_FACTORS_REVIEW.md) for the cognitive-load implication of the densest screens.

## Redundant widgets — the clearest, most citable finding for this objective

The same core operational KPI is independently re-implemented as a separate stat card, under an identical or near-identical label, pulling from different backend fields, across many different screens:

- **"Total Inspections"** — identical label in at least 7 files: `ExecutiveCommandCenterPage.tsx`, `InspectionReadinessPage.tsx`, `ExecutiveAdoptionPage.tsx`, `Dashboard.tsx`, `NetworkDashboardPage.tsx`, `AnalyticsDashboardPage.tsx`, `PilotAnalyticsDashboard.tsx`, plus `components/PilotDashboardCards.tsx`.
- **"Critical Findings"** — identical label in at least 6 files: `InspectionReadinessPage.tsx`, `ROICenterPage.tsx`, `NetworkDashboardPage.tsx`, `ValueRealizationPage.tsx`, `ExecutiveQualityReviewPanel.tsx`, `SentinelDashboard.tsx`.
- **"Pass Rate"** — identical/near-identical label across at least 6 dashboards, including two different field names for what's presented as the same metric: `NetworkIntelligenceConsole.tsx` ("Network Pass Rate p50", "Your Pass Rate"), `GlobalStandardsConsole.tsx` ("Inspection Pass Rate"), `QualityDashboardPage.tsx`, `AtlasDashboard.tsx`, `InspectionCopilotDashboard.tsx`, `VendorIntelligenceDashboard.tsx`.
- **"Enterprise Risk Score"** — an identical section title duplicated verbatim across two separate executive dashboards: `SentinelDashboard.tsx` and `AtlasDashboard.tsx`.
- **"Network Participants"** — identical label, but pulling from two different backend fields on two different consoles: `GlobalIntelligenceConsole.tsx` (`data.network_participants`) vs. `GlobalStandardsConsole.tsx` (`data.total_network_participants`) — a real risk that the two screens could disagree on the same displayed number.
- **"Override Rate"** — appears in 3 files: `PilotValidationPage.tsx`, `AiModelPerformanceCard.tsx`, `AtlasDashboard.tsx`.
- **"Risk Score" as a bare widget/column label** — appears in at least 8 additional files beyond the "Enterprise Risk Score" case: `Dashboard.tsx`, `InstrumentPassportPage.tsx`, `QualityIntelligencePage.tsx`, `GlobalIntelligenceConsole.tsx`, `AutonomousOperationsConsole.tsx`, `EnterpriseIntakeHistoryPanel.tsx`, `CapaPredictiveRiskCards.jsx`, `MaestroLeadershipWorkspace.tsx`, `PredictiveAnalyticsDashboard.tsx`.

**This is a real, quantifiable duplication, not the normal cross-referencing expected in a multi-specialist platform.** At least 5-8 core KPIs are re-derived independently on 3-8 screens each — the risk is not just visual redundancy but genuine metric drift (the "Network Participants" case above shows two different backend field names already feeding what users would read as the same number).

## Near-duplicate governance dashboards

`GovernanceCenterDashboard.tsx` (`/governance`, orphaned) and `CollaborationGovernanceDashboard.tsx` (`/collaboration-governance`, orphaned) share the same 3-4 widget shape (Federated Network Participation / Pending Contribution Approvals / Governance Audit Trail) pulling from different data sources — a second, smaller-scale instance of the same duplication pattern.

## Loading / error / empty states — inconsistent across the inventory

Cross-referencing this recon against [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md): of the screens sampled, roughly half show **no loading, error, or empty-state markers at all** (`SurgicalReadinessDashboard.tsx`, `SupervisorCoachingDashboard.tsx`, `CommercialConsole.tsx`, `GrowthConsole.tsx`, `AccreditationConsole.tsx`, and most of the orphaned Vanguard/Pulse/Sentinel-family screens). Where states do exist, wording and implementation vary page-by-page — "Failed to load," "Failed to load intelligence dashboard," "Network error," and "Could not load that case" are each hand-written per screen rather than drawn from a shared error-state component (there isn't one — see [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md)).

## Recommendation

1. **Consolidate the ~6 duplicated core KPIs into a single shared source of truth** (a shared hook/component reading one canonical field per KPI) rather than each dashboard independently computing "Total Inspections" or "Pass Rate" from its own endpoint call. This alone would resolve the majority of the redundant-widget findings above without touching any AI logic.
2. **Wire the orphaned dashboard routes into the nav** (see [NAVIGATION_ARCHITECTURE.md](./NAVIGATION_ARCHITECTURE.md)) or retire genuinely superseded ones (e.g. reconcile `/governance` vs. `/collaboration-governance`).
3. **Adopt a shared loading/error/empty-state component** (none exists today) so state handling is uniform across all ~68 dashboards rather than per-page reinvention.
