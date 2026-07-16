# LumenAI — UX Scorecard

**User Experience Program · Phase 4: Harmony · User Experience, Human Factors & Workflow Optimization**

Objectives 15 (UX Metrics) and 17 (Validation) roll-up. Ratings are **Strong / Adequate / Needs Work / Critical Gap**, each tied to a specific finding in the other 8 documents in this set — no rating here is unsupported.

## Objective 15 — UX metrics: what can and cannot be honestly reported today

This review found **no user-telemetry, analytics, or instrumentation pipeline anywhere in the codebase** capturing the metrics Objective 15 asks for (average inspection time, average approval time, clicks per workflow, task completion rate, navigation depth, error rate, user satisfaction, training time) — no event-tracking library, no analytics SDK call, and no backend table recording per-user workflow timing was found during this or prior reviews. **Fabricating numbers for these metrics would violate this program's own review discipline** (the same discipline that led the Clinical Validation phase to report "no trained model ships" rather than assume one does). Instead, this scorecard reports **structural proxies** derived directly from the code, and flags real instrumentation as a Phase 5 prerequisite for measuring the rest honestly.

| Metric | Real measurement exists? | Structural proxy from this review |
|---|---|---|
| Average inspection time | No | N/A — would require real timing instrumentation |
| Average approval time | No | N/A — moot until a real approve/return action exists (see Human Oversight row below) |
| Clicks per workflow | No | Technician happy path ≈ 3 screens (Login → Dashboard → New Inspection, [USER_JOURNEYS.md](./USER_JOURNEYS.md)) — genuinely efficient where it exists, undermined by 3 competing entry points for the same task |
| Task completion rate | No | N/A |
| Navigation depth | Partial — countable from route/nav structure | 45 of ~90 routes (50%) have zero sidebar path — effectively infinite navigation depth for those screens (unreachable without a direct URL), see [NAVIGATION_ARCHITECTURE.md](./NAVIGATION_ARCHITECTURE.md) |
| Error rate | Partial — countable from state-handling audit | Roughly half of sampled dashboards have no error-state handling at all; where present, wording/implementation is unique per page (51 files, 162 hardcoded-red-color error renderings) — see [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) |
| User satisfaction | No | A "Weekly Pulse Survey" widget exists on `PilotAnalyticsDashboard.tsx` (ease of use / usefulness / recommend), the only real user-sentiment capture found anywhere |
| Training time | No | N/A — no LMS/training-completion tracking tied to actual task performance was found |

**Recommendation**: before the next UX review cycle can report real Objective-15 numbers, add basic client-side event instrumentation (page views, form-submit timestamps, error-boundary triggers) — a small, non-AI addition consistent with this program's scope.

## Objective 17 — validation checklist

| Criterion | Status | Basis |
|---|---|---|
| ✓ Minimal clicks | **Partial** | The one traced happy path (Technician) is genuinely short (~3 screens), but 3 competing entry points for the same task undercut this — [USER_JOURNEYS.md](./USER_JOURNEYS.md) |
| ✓ Consistent navigation | **Not met** | 45 of ~90 routes are unreachable from the sidebar; 6 pages double-render breadcrumbs — [NAVIGATION_ARCHITECTURE.md](./NAVIGATION_ARCHITECTURE.md) |
| ✓ Intuitive terminology | **Not met** | Two near-identical "executive" dashboards; the technician-facing capture flows disagree on whether finding-category/risk-level are AI- or human-entered — [USER_PERSONAS.md](./USER_PERSONAS.md), [USER_JOURNEYS.md](./USER_JOURNEYS.md) |
| ✓ Responsive layouts | **Partial** | Real but shallow — 45% of files use responsive prefixes, but most dashboards are fixed desktop grids; "Pulse mobile view" is the same desktop layout with a few breakpoints, not a distinct mobile UI — [MOBILE_EXPERIENCE.md](./MOBILE_EXPERIENCE.md) |
| ✓ Explainable AI | **Partial** | Finding/evidence/confidence/recommended-action are genuinely surfaced; limitations and alternative-explanations are computed but have no live path to the screen; human-review-required is static copy, not bound to the real per-record flag — [UX_GUIDELINES.md](./UX_GUIDELINES.md) |
| ✓ Accessible interfaces | **Not met** | `aria-describedby`/`aria-invalid` used zero times codebase-wide; no global focus-visible CSS; 3 confirmed keyboard-trap components — [ACCESSIBILITY_REVIEW.md](./ACCESSIBILITY_REVIEW.md) |
| ✓ Role-based dashboards | **Partial** | Real role-gating exists in `AppShell.tsx`, but the underlying role system itself is fragmented across 4 disagreeing vocabularies, and several personas (Supervisor, Market Director, Infection Prevention) have no distinct enforced role at all — [USER_PERSONAS.md](./USER_PERSONAS.md) |
| ✓ Efficient inspection workflow | **Partial** | The primary flow (`NewInspectionPage.tsx`) is well-designed in isolation (guided capture, coverage gating, inline AI results); undermined by 2 duplicate, less-capable competing flows — [UX_GUIDELINES.md](./UX_GUIDELINES.md) |
| ✓ Effective supervisor review | **Critical Gap** | No reachable, working "approve this finding / return to technician" action was found anywhere in the codebase — the nav-reachable queues are view-only, and the components with review logic in their name are orphaned from nav and, per their own code, explicitly not the approval point — [USER_JOURNEYS.md](./USER_JOURNEYS.md) §Supervisor journey |
| ✓ Clear executive reporting | **Partial** | Real KPI dashboards exist and are richly built, but the "real" leadership platform (Vanguard's `/executive`, `/strategy`) is orphaned from nav in favor of a KPI-only duplicate, and core KPIs are recomputed inconsistently across 6-8 screens — [DASHBOARD_STANDARDS.md](./DASHBOARD_STANDARDS.md), [USER_JOURNEYS.md](./USER_JOURNEYS.md) |

## Dimension ratings (roll-up)

| Dimension | Rating | Basis |
|---|---|---|
| Navigation architecture | **Needs Work** | 45/90 routes orphaned; no search/quick-actions; dual breadcrumb rendering on 6 pages |
| Dashboard design | **Needs Work** | 68 dashboards inventoried; 5-8 core KPIs independently re-derived across 3-8 screens each, including one confirmed field-name mismatch |
| Design system consistency | **Needs Work** | Token migration reached ~9 of ~200 files; no shared Table/Dialog/EmptyState component; two competing Alert components |
| Accessibility | **Needs Work** | `aria-describedby`/`aria-invalid` never used; no global focus-visible styling; 3 keyboard-trap components |
| Inspection experience | **Adequate** | The primary flow is well-built in isolation; undermined by 2 duplicate competing entry points with contradictory data-entry rules |
| AI explainability | **Adequate** | 5 of 7 required fields reach the screen reliably; limitations and alternative-explanations are computed but not wired to any live UI |
| Digital twin experience | **Needs Work** | Vulcan's instrument-progression data (the richest twin dataset) is rendered as raw unstyled JSON with no chart, trend line, or legend anywhere |
| Mobile/device support | **Needs Work** | Responsive layout exists but is shallow and inconsistent; a real backend mobile API has zero frontend consumer; barcode scanning is Chromium-only with no fallback |
| Notifications / alert fatigue | **Critical Gap** | Three disconnected alert pipelines (client-computed bell icon, Pulse-only alerts, Sentinel-X-only raw-JSON alerts) with no unified surface and no dedup/digest logic |
| Human oversight / supervisor review | **Critical Gap** | No reachable, working approve/return action found anywhere — the most consequential single finding in this review |

## Overall assessment

**LumenAI's UX problems are overwhelmingly problems of fragmentation and incompleteness, not problems of poor individual design.** Nearly every screen examined during this review — the New Inspection form, the design tokens, the AI-explainability data model, the alert pipelines — is well-built in isolation. The recurring pattern across all 9 recon areas is the same: **multiple independently-built solutions to the same problem coexist without ever being reconciled**, and roughly half the application's screens are invisible from the navigation that's supposed to surface them.

**The single most urgent finding is the Supervisor-review gap** (Human Oversight / effective supervisor review, both rated Critical Gap above): this program's own mission statement asks that the platform be "role-based" and support "effective supervisor review," and this review could not locate a working, reachable approve/return action anywhere in the codebase. Because LumenAI's clinical safety model depends on human review being a real, exercised gate (see `docs/clinical-validation/HUMAN_OVERSIGHT_MODEL.md`), this UX gap is not merely a convenience issue — it is the same finding the clinical review flagged from the backend side, now confirmed from the frontend side as well. This should be the first item addressed in the next phase.

**The second-most urgent finding is the notification fragmentation** — three real, separately-built alert systems with no shared surface, directly working against the "reduce alert fatigue" objective this program set for itself.

**None of the fixes identified in this review require new AI capability, and none require the frozen architecture to be modified** — every recommendation in this document set is a navigation-wiring change, a shared-component consolidation, or a markup/attribute-level accessibility fix, consistent with this program's explicit scope boundary.
