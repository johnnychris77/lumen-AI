# LumenAI — User Journeys

Objective 2 review. Journeys are traced against the actual routed pages/components in `frontend/src/main.tsx` and `frontend/src/components/layout/AppShell.tsx`, not an idealized flow diagram — every step below cites a real file.

## Technician: login → receive instrument → capture images → AI inspection → review findings → submit

**The nav-intended happy path is genuinely efficient — roughly 3 screens:**
1. **Login** — `pages/LoginPage.tsx` (`/login`, outside `AppShell`).
2. **Dashboard** (`/`, `pages/Dashboard.tsx`) — lands here post-login, or clicks "New Inspection."
3. **New Inspection** — `pages/NewInspectionPage.tsx` (`/inspection/new`, 1,545 lines). One long scrolling form (not a multi-step wizard), with its own in-page workflow strip: *"1. Identify Instrument → 2. Upload Image → 3. AI Baseline Check → 4. AI Prediction → 5. Supervisor Review (if no baseline)."* Sections: Facility & Assignment, Tray Information, Instrument Identification (8 fields), Inspection Images (required + optional borescope, per-image zone/view/quality tagging, a "save as draft" escape hatch), Manual Observations. A single submit button runs image upload then the inspection-record POST in sequence; on success, an `AIPredictionPanel` renders **inline on the same page** — no navigation to a separate results screen.

The page's own copy is explicit that finding-category and risk-level are AI-determined, not technician-entered (lines 620-644, 1065-1073 per recon).

**The concrete problem: two more sidebar destinations do the same job differently.**
- `pages/CapturePage.tsx` (`/inspection/capture`, nav label "Borescope Capture") — a separate live-camera capture UI with its own independent `instrumentType`/`facility`/`barcode` state, disconnected from the New Inspection form's state.
- `pages/InspectionImageUploadPage.tsx` (`/inspection-image-upload`, nav label "Upload Inspection Image") — a third independent form with its own instrument-identity fields, plus `capture_device`/`capture_angle`/`image_quality_rating` — and, in direct contradiction of New Inspection's stated model, this form **does** collect `finding_category` and `risk_level` from the technician via a manual dropdown, submitted verbatim to `POST /api/inspections`.

A technician who uses this nav entry instead of "New Inspection" is asked to manually enter the exact two fields the other flow says are AI-determined and off-limits to manual entry. This is the single clearest "duplicate data entry / confusing navigation" finding in this review, and it's a **navigation defect, not a content defect** — no new AI capability is needed to fix it, only consolidating three routes into one flow or clearly differentiating their purpose in the nav labels themselves.

"Review findings" nominally happens on `FindingsQueuePage.tsx` (`/findings`) or `InspectionWorkQueuePage.tsx` (`/inspection-work-queue`) — see the Supervisor journey below for why neither of these currently supports a real review action.

## Supervisor: review queue → evidence review → approve/return → update digital twin

This is the journey with the most significant gap found in the whole Phase 4 review.

1. **Review Queue** — nav item → `/findings` (`FindingsQueuePage.tsx`). This screen is **read-only**: every row's "Review →" action is a generic `Link` to `/inspection-work-queue` (line 133 per recon) — it does not deep-link to the specific inspection a supervisor clicked.
2. **Smart Work Queue** — `/inspection-work-queue` (`InspectionWorkQueuePage.tsx`, 166 lines, read in full). Renders 7 sectioned tables (Pending, High-Risk, OR Priority, Vendor Trays, Loaner Instruments, Repeat Inspections, Supervisor Reviews, Repair Holds) with **zero `onClick`, button, or `Link` on any row**. A supervisor cannot open an individual inspection or take a disposition action from this screen — it is purely informational, despite being the two nav-reachable destinations most likely to be described internally as "the review queue."
3. **Baseline Review** (the closest thing to a real approve/return screen, gated `ELEVATED_ROLES`) — `/baseline-review` → `BaselineReviewPage.tsx`, whose own on-page copy tells supervisors to *"review each baseline's acceptable condition notes and IFU reference before approving."* The component it renders, `BaselineReviewQueue.tsx` (539 lines, read in full), has **no approve/reject button anywhere** — it is a read-only metrics/table view. It also hardcodes request headers (`"X-LumenAI-Role": "viewer"`, `"X-LumenAI-Actor": "john-demo"`) rather than using the logged-in user's real identity.
4. **Evidence review** — `components/VeritasWorkspace.tsx` (route `/veritas`) is the component whose name and stated purpose ("evaluates whether an inspection has sufficient, reliable, and governed evidence... does not independently approve an instrument") most closely matches "evidence review" — but **`/veritas` has no sidebar nav entry at all** (an orphaned route, per [NAVIGATION_ARCHITECTURE.md](./NAVIGATION_ARCHITECTURE.md)). Its 5 tabs each render a GET response as raw `<pre>{JSON.stringify(...)}</pre>` — no formatted view, no approve/return control.
5. **"Steward" / disposition tracking** — `components/StewardWorkspace.tsx` (route `/steward`, also orphaned). Its own header comment is explicit it is *not* a clinical approval tool: *"Steward converts approved decisions... into governed implementation plans — it never approves clinical or operational decisions itself, only executes and monitors what an appropriate human role already authorized."*
6. **Digital twin update** — `/digital-twin` (`DigitalTwinDashboard`, also orphaned from nav) — see [DASHBOARD_STANDARDS.md](./DASHBOARD_STANDARDS.md) for what this screen actually shows (facility-throughput twin, not instrument-condition history).

**Net finding**: a genuine, reachable "approve this finding / return to technician" action could not be located anywhere in this codebase. The two nav-reachable "review" screens are view-only, the nav-reachable governance screen (`/baseline-review`) is view-only despite its own copy implying otherwise, and the three components whose names most plausibly match the brief's "evidence review"/"approve" step are all orphaned from the sidebar and, per their own code comments, explicitly not the clinical decision point. This is the most consequential UX finding in this review — it directly affects the platform's core "human review required" safety model (see `docs/clinical-validation/HUMAN_OVERSIGHT_MODEL.md`): if a real approve/return action exists, it should be made reachable and unambiguous; if it genuinely does not exist as UI today, that should be treated as the top implementation priority for the next phase, not assumed to be present.

## Director/Executive: enterprise dashboard → operational health → risk review → leadership actions

1. **Enterprise dashboard** — nav "Command Center" → `/executive-command-center` (`ExecutiveCommandCenterPage.tsx`). A KPI-card dashboard (16 stat cards across 4 sections) fetched via `Promise.allSettled` from 4 separate endpoints; cards link out to Findings/CAPA/Analytics pages.
2. **Operational health** — "Surgical Readiness" (`/surgical-readiness`) and "Global Registry" (`/global-registry`), both in the Executive nav group.
3. **Risk review** — "Risk Signals" nav item → `/quality-intelligence`, in the Analytics nav group.
4. **Leadership actions** — this is where the actual Vanguard leadership platform lives, and it is **entirely orphaned from navigation**:
   - `/executive` → `ExecutiveIntelligenceCenter.tsx`. Its own header comment states: *"Frontend route `/executive`, API prefix `/api/vanguard` — deliberately distinct from the pre-existing `/api/executive` mock-KPI endpoint"* — the codebase itself flags that two unrelated "executive" surfaces coexist. Tabs (Executive Intelligence, Scorecards by audience, Financial, Operational, Benchmarking, Governance, AI Advisor) are all rendered as raw `<pre>{JSON.stringify(...)}</pre>` blocks — no charts, no formatting.
   - `/strategy` → `StrategicPlanningPage.tsx` — "Project Vanguard, Section 5: Strategic Planning Workspace." This is the **one screen in the entire director/executive journey with a genuine leadership action**: generate a strategy by initiative type, then change its status (`draft`/`under_review`/`approved`/`archived`) via a dropdown that calls `PATCH /api/vanguard/strategy/initiatives/{id}/status`. It is invisible from the sidebar.

**Net finding**: the director/executive journey the brief described is split across two near-identically-named dashboards (`/executive-command-center`, nav-visible, KPI-only vs. `/executive`, orphaned, the "real" one with actual leadership content), and the one screen with an actual approve/archive leadership action (`/strategy`) is undiscoverable without a direct URL. A director using only the sidebar would never find it.

## Cross-journey summary of concrete gaps (for [UX_SCORECARD.md](./UX_SCORECARD.md))

| Gap | Journey affected | Fix category |
|---|---|---|
| 3 overlapping inspection-creation flows with contradictory manual-entry rules | Technician | Consolidate/clarify navigation, no new AI needed |
| Nav-reachable review queues have zero click-through to act on a record | Supervisor | Add real actions to existing screens, or surface the orphaned ones that already have them |
| Evidence-review and disposition-tracking tools exist but are unreachable from nav | Supervisor | Add nav entries |
| Two near-duplicate "executive" dashboards, only one reachable | Director/Executive | Consolidate or clearly differentiate; add nav entry for the real one |
| The one screen with a genuine leadership action is orphaned | Director/Executive | Add nav entry |
