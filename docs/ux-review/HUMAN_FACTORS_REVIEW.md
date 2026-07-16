# LumenAI — Human Factors Review

Objectives 10 (Notifications) and 11 (Human Factors) review. Covers cognitive load, decision fatigue, visual complexity, interruptions, task switching, information overload, and notification/alert-fatigue risk — the two objectives are combined here because the recon findings for both point to the same root cause: independently-built subsystems that never coordinated with each other.

## Notification review — three disconnected alert pipelines, no unified system

There is **no toast system anywhere in the frontend** (zero hits for "toast" across `frontend/src`). The only alerting UI is a bell-icon dropdown (`ui/NotificationPanel.tsx`), fed by `lib/notifications.tsx` — a client-side-only React context that recomputes 7 fixed threshold rules (e.g. "critical findings > 0 AND turnaround > 8h," "baseline coverage < 50%," "customer health score < 40") against two analytics endpoints on a 5-minute poll. Dismissal state lives only in `localStorage`. **This bell icon is not backed by a real persisted notifications table** — it is a derived, client-computed view of KPI thresholds.

Separately, three real, server-persisted alerting subsystems exist, each visible only within its own page:
1. **`escalation_engine.py`** — computes real per-inspection escalation reasons, exposed at `/api/workflow/escalations` and `/api/workflow/notifications` (with a genuine "mark read" endpoint) — **but has zero frontend consumer anywhere.** A repo-wide search for these endpoint paths in `frontend/src` returns nothing.
2. **Pulse operations alerts** (`pulse_alert_service.py`) — real, severity-tagged, persisted alerts (AI-confidence drops, repeated overrides, missing baselines, repair surges) — these do reach the UI, but only inside `PulseCommandCenterDashboard.tsx`'s own "Alerts" tab.
3. **Sentinel-X patient-safety alerts** — also real and persisted, reachable via `SentinelXRiskDashboard.tsx`'s "Patient Safety Alerts" tab, but rendered as a **raw JSON dump** (`<JsonView data={alerts} />`), not a designed alert list.

**Net finding**: a user working anywhere else in the app has no way to know a Pulse or Sentinel-X alert fired unless they specifically navigate to that page's own alerts tab — there is no cross-cutting notification surface. No grouping, deduplication, or digest logic exists anywhere (a repeated zero-hit search for "digest"); each pipeline independently regenerates its full alert set on every poll. Given that related conditions can trigger alerts in more than one pipeline at once (e.g., low AI confidence surfaces as both a client-computed bell-icon alert and a separate Pulse `ALERT_AI_CONFIDENCE_DROP` alert), there is a real, concrete alert-fragmentation/fatigue risk — not from too many alerts in one place, but from the same underlying condition being reported redundantly across three places a user must separately check.

**Recommendation**: this is the single highest-value human-factors fix identified in this review, and it requires no new AI capability — route all three alert sources into the one existing bell-icon `NotificationPanel`, and wire the already-built (but unused) `/api/workflow/escalations`/`/api/workflow/notifications` endpoints into it as a fourth source.

## Cognitive load and visual complexity — driven by dashboard density and duplication

Per [DASHBOARD_STANDARDS.md](./DASHBOARD_STANDARDS.md), several dashboards carry 17-21 distinct widgets on a single screen (`CaseIntelligenceDashboard` 21, `PulseCommandCenterDashboard` 21, `SentinelDashboard` 18, `OracleWorkspace` 18, `MaestroLeadershipWorkspace` 17, `QualityDashboardPage` ~20). This is compounded, not offset, by the KPI-duplication finding in that same document: a user working across 2-3 of these dense dashboards in a session is likely re-reading the same "Total Inspections"/"Critical Findings"/"Pass Rate" figures multiple times, sourced from different endpoints, with no guarantee the numbers agree (the confirmed `network_participants` vs. `total_network_participants` field-name mismatch between two consoles is a concrete instance of this risk materializing).

## Decision fatigue — ambiguity about which screen is "the" screen for a task

[USER_JOURNEYS.md](./USER_JOURNEYS.md) documents that a technician has **3 different sidebar destinations** for creating an inspection, with contradictory rules about manual data entry between them, and a director has **2 near-identically-named "executive" dashboards**, only one of which contains real leadership actions. Both are concrete decision-fatigue risks: the user must guess which of several similarly-named options is the "correct" one for their task, with no in-product signal distinguishing them.

## Interruptions and task switching — the orphaned-route problem compounds this

45 of ~90 routes have no sidebar entry (see [NAVIGATION_ARCHITECTURE.md](./NAVIGATION_ARCHITECTURE.md)), meaning a user who needs one of those screens mid-task must either already know the URL or ask someone — a real, structural task-switching cost that has nothing to do with information design and everything to do with incomplete navigation wiring.

## Information overload and the explainability gap compound each other

Per [UX_GUIDELINES.md](./UX_GUIDELINES.md), "limitations" and "alternative explanations" — exactly the fields designed to help a user *reduce* uncertainty about an AI output — are computed server-side but have no live path to the screen (one component that renders them correctly is simply never mounted; another only prints API-call instructions). A user facing a dense, high-widget-count dashboard is simultaneously deprived of the one field (limitations) that would help them triage what actually needs attention versus what's routine — the two problems (density and thin explainability) compound each other rather than being independent issues.

## Support for safe clinical decision-making — what already works well

Not everything is a gap. Several genuinely good human-factors patterns were confirmed:
- The AI-recommendation "explanation" text (`disposition_engine.py`'s grounded, non-generic rationale) is real and does reach the screen via `ReadinessDispositionPanel.tsx` — this is the kind of "why" transparency Objective 6 asks for, working correctly for at least one of the app's recommendation surfaces.
- Supervisor-handoff visual signaling is real (a distinct banner/badge appears whenever review is required) even though its styling is inconsistent across 5 different components — the underlying behavior (never silently proceeding past a required review) is sound; only the visual polish needs unification.
- `ui/input.tsx`'s automatic `aria-label` derivation and `AppShell.tsx`'s clean semantic HTML show the pattern needed elsewhere already exists somewhere in the codebase — this is a consistency gap to close, not a capability gap to build from scratch.

## Recommendation summary (no new AI capability required for any of these)

1. Unify the three alert pipelines into the existing `NotificationPanel` (highest priority — directly reduces alert-fragmentation risk).
2. Consolidate the duplicated KPI widgets into one shared source per metric (reduces cognitive load and eliminates the metric-drift risk).
3. Resolve the "which screen is the real one" ambiguity for inspection creation and executive dashboards (reduces decision fatigue).
4. Wire the 45 orphaned routes into nav, or deliberately retire superseded ones (reduces task-switching cost).
5. Mount the already-built `VeritasEvidencePanel.tsx` and wire `AIAssuranceCenter.tsx`'s explainability tab to its data (closes the information-overload/explainability compounding gap).
