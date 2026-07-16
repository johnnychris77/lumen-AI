# LumenAI — Role-Based Demonstrations

Objectives 2 through 8 review. Each demo below is scripted against real, reachable screens and real backend behavior confirmed in this repository — where the brief's expected flow doesn't match what the product currently supports, that gap is stated plainly rather than scripted around silently, since presenting a broken flow live is worse than describing an honest limitation. Persona-to-role mappings are carried forward from `docs/ux-review/USER_PERSONAS.md`; journey detail is carried forward from `docs/ux-review/USER_JOURNEYS.md`.

## SPD Technician demonstration (Objective 3)

**Scenario as scripted**: Receive Instrument → Capture Images → AI Inspection → Evidence Review → Finding Explanation → Supervisor Submission.

**What actually runs**: Login → Dashboard (`/`) → **New Inspection** (`/inspection/new`, `NewInspectionPage.tsx`) — one scrolling form, not a wizard, with a real in-page 5-step guide strip. Instrument identification (8 fields) → Inspection Images (guided capture panel shows next zone, live coverage %) → submit → an inline `AIPredictionPanel` replaces the form with real findings, probability %, severity, and an SPD Risk Impact badge.

**Honest staging note for the demo script**: use **only** the "New Inspection" entry point. Two other sidebar destinations (`Borescope Capture`, `Upload Inspection Image`) exist and superficially look like alternate paths into the same scenario, but per `docs/ux-review/USER_JOURNEYS.md` they have inconsistent rules about whether finding-category/risk-level is AI-derived or manually entered — using either of them mid-demo risks contradicting what was just said on the "New Inspection" screen. Stay on one flow for the entire technician demo.

**Highlight checklist mapped to real UI**:
- Image quality → `GuidedCapturePanel`'s live coverage % and per-image quality tagging (good/acceptable/poor/unusable).
- Anatomy recognition → zone badge + zone reason shown per finding, with the honest caveat (state if asked) that this is a keyword/heuristic match, not pixel-level localization (`instrument_zones.py`'s own docstring, confidence capped at 0.70).
- Evidence → the "Evidence Used" card in `ClinicalDecisionPanel.tsx` (baseline match %, risk drivers).
- Confidence → shown as a percentage + text label on the finding cards.
- Recommendations → `ReadinessDispositionPanel.tsx`'s disposition label plus its grounded, non-generic explanation text (this is real and does render — confirmed working, per `docs/ux-review/UX_GUIDELINES.md`).

**What NOT to promise**: a visual bounding-box/heatmap overlay on the instrument image. This does not exist anywhere in the codebase — `ClinicalDecisionPanel.tsx`'s own UI states "(heatmaps / bounding boxes not fabricated)." If asked, say zone is shown as a text/badge label today, with visual overlay named as a roadmap item.

## SPD Supervisor demonstration (Objective 4) — requires a scripted workaround

**Scenario as scripted**: Inspection Queue → Evidence Review → Digital Twin → Risk Review → Approve → Audit Trail.

**The critical finding, carried forward from `docs/ux-review/USER_JOURNEYS.md`**: this review could not locate a reachable, working "approve this finding / return to technician" button anywhere in the product. The nav-reachable queues (`/findings`, `/inspection-work-queue`) are view-only with no click-through to an individual record's disposition action. `/baseline-review`'s own copy tells supervisors to approve/reject, but the component behind it has no such control. The components most plausibly meant for this (`Veritas Workspace` at `/veritas`, `Steward Workspace` at `/steward`) are both orphaned from the sidebar and, per their own code comments, are explicitly not the clinical approval point.

**This is not a demo-scripting problem to paper over — it should be surfaced as a pre-demo engineering priority.** Until a real approve/return control exists and is reachable, the honest options for this specific demo beat are:
1. Narrate the disposition/explanation the AI already produced (`ReadinessDispositionPanel.tsx`'s clinical rationale — this part is real and works) and describe supervisor sign-off as "the point where a human reviews this before the instrument proceeds," without demonstrating a live click that doesn't exist.
2. If an approve control is added before a scheduled demo, update this script to walk through it live and remove this caveat.

**What does work today for this scenario**: Digital Twin (frame around `digital_quality_twin_service.py`'s forecast/scenario views, which have a real synthetic-data path — not Apollo's, which needs real history). Risk Review → Sentinel-X's Risk Dashboard (`/risk`, orphaned from nav — navigate by direct URL in the demo) shows real, persisted patient-safety alerts, though rendered as raw JSON in `SentinelXRiskDashboard.tsx` per `docs/ux-review/UX_GUIDELINES.md` — narrate over this rather than pause on the raw-JSON view. Audit Trail → the platform's real, independently-verifiable SHA-256 hash-chained audit log (confirmed in `docs/production-readiness/ARCHITECTURE_INVENTORY.md`) is a genuine strength and should be shown, not just described.

## SPD Manager and Market Director demonstration (Objective 5)

**Scenario as scripted**: Enterprise Dashboard → Facility Comparison → Operational Health → Risk Heatmap → Quality Trends → Digital Twin Analytics → Council Recommendations → Leadership Priorities.

**Real screens to use**: `/executive-command-center` for the Enterprise Dashboard beat (KPI cards, real data), `/network-dashboard` for facility comparison, `/quality-dashboard` for quality trends. For "Council Recommendations," navigate directly to `/council` (orphaned from nav, per `docs/ux-review/NAVIGATION_ARCHITECTURE.md`) — this is real: `council_orchestration_service.convene()` genuinely invokes 5 specialists in sequence when a leadership-role user calls it, and `council_human_decision_service.finalize_decision` genuinely records the final human call. For "Leadership Priorities," use Maestro's Leadership Workspace (`/maestro`, also orphaned) — its priority/recommendation data is a real read-and-synthesize layer over other specialists' pre-computed output (confirmed: Maestro's own docstring states "nothing here is computed fresh").

**Honest framing for "Digital Twin Analytics" at this altitude**: this maps most naturally to Apollo's governance-health twin (department/facility-level), which — unlike the instrument-level twin used in the technician/supervisor demos — has **no numeric confidence field** and needs real inspection/accreditation history to populate meaningfully. Seed enough real inspection volume before this demo beat, or substitute `digital_quality_twin_service.py`'s facility-level forecast view, which has a genuine synthetic fallback.

**Navigation note**: `/council`, `/maestro`, `/strategy`, and `/executive` (Vanguard's real Executive Intelligence Center) are all orphaned from the sidebar nav (per `docs/ux-review/NAVIGATION_ARCHITECTURE.md`). A live demo must navigate to these by direct URL — do not assume the presenter can click their way there from the sidebar without rehearsal.

## Enterprise Executive demonstration (Objective 6)

**Present**: Enterprise KPIs, Risk Reduction, Inspection Throughput, Quality Improvement, Operational Efficiency, Strategic Insights, ROI Dashboard, Executive Brief.

**Real backing, with one important caveat on ROI figures**: `ROICenterPage.tsx`/`ValueRealizationPage.tsx` fetch real inspection/finding/CAPA/baseline-coverage counts from live endpoints, but the dollar-value figures are those real counts multiplied by **hardcoded industry-benchmark constants** ($28,000/SSI, $5,000/critical finding, $2,500/CAPA, $35/hr labor) — not measured customer outcomes. **Present these explicitly as "estimated value using disclosed industry benchmarks applied to real usage counts," never as "measured ROI."** Both pages also silently fall back to fabricated demo numbers if their API calls fail, with no visible indicator — rehearse this screen before a live demo to confirm the real data path is actually rendering, not the silent fallback.

**"Executive Brief"** → Vanguard's `vanguard_board_reporting_service.py` genuinely generates PDF/Excel/PowerPoint board packets by reusing (not duplicating) `atlas_report_service`'s executive report — this is real and worth demonstrating live as a generated-artifact moment. **"Strategic Insights"** → `StrategicPlanningPage.tsx` (`/strategy`) genuinely calls real `/api/vanguard/strategy/generate/{type}` endpoints backed by real composed data (no fabricated projection, per the service's own docstring) — this is the one screen in the whole executive journey with a real, working leadership action (approve/archive an initiative), and per `docs/ux-review/USER_JOURNEYS.md` it's currently orphaned from nav. Feature it deliberately in this demo since it's both real and otherwise undiscoverable.

**Do not present Vanguard's Executive Intelligence Center as "in daily use by hospital executives today"** — it is real and functional, but the UX review confirmed it's orphaned from primary navigation in favor of a separate KPI-only duplicate at `/executive-command-center`. Frame it as "built and available," not "actively adopted."

## Manufacturer demonstration (Objective 7)

**Show**: Manufacturer Portal, Instrument Registry, Baseline Governance, Reliability Trends, Failure Analytics, Digital Twin History, Research Collaboration.

**Real screens**: `VendorBaselinePortalPage.tsx`/`VendorIntake.tsx` (Manufacturer Portal), `/global-registry` (Instrument Registry), `/baseline-review` (Baseline Governance — but see the Supervisor demo's caveat: this screen is read-only despite its copy implying an approve/reject action; for a manufacturer audience, narrate the governance *policy*, e.g. IFU-reference review, rather than clicking a control that isn't there), `InstrumentForensicsWorkspace.tsx` (`/instrument-forensics`, orphaned from nav — Reliability Trends/Failure Analytics). **Honest caveat for this last screen**: Vulcan's condition-progression data (`insufficient_history`/`rapidly_worsening`/etc.) is currently rendered as raw, unstyled JSON in this component — narrate the progression states verbally from the data rather than relying on the screen to visually tell the story, per `docs/ux-review/UX_GUIDELINES.md`. Research Collaboration → `/collaboration` or `/research` (both orphaned; direct URL navigation required).

## System Administrator demonstration

**Real screens**: `UserManagementPage.tsx` (`/user-management`, nav-visible), `PlatformAdminPage.tsx` and `PlatformHealthPage.tsx` (both `/platform-admin`, `/platform-health`, orphaned from nav — direct URL). Cover: role assignment (note honestly that the assignable-role set in `admin_users.py` includes `supervisor`, which doesn't appear in the core dev-auth role map — see `docs/ux-review/USER_PERSONAS.md`'s role-fragmentation finding, worth a one-line acknowledgment if a technical administrator asks about it), audit log entries (real, hash-chained), feature flags, connected integrations.

## Infection Prevention, OR Leadership, Quality Department, Research Partner

These four personas do not have a purpose-built, nav-reachable screen (per `docs/ux-review/USER_PERSONAS.md`). Script them as **guided tours through existing dashboards** rather than a dedicated "demo," and say so:
- **Infection Prevention** — contamination-trend widgets on `QualityDashboardPage.tsx`/`CIOSDashboard.tsx`, plus Sentinel-X's Patient Safety Alerts tab (`/risk`, orphaned).
- **OR Leadership** — `SurgicalReadinessDashboard.tsx` (`/surgical-readiness`, nav-visible) is a genuine, purpose-built screen for this persona and should anchor the demo.
- **Quality Department** — `QualityDashboardPage.tsx` (nav-visible, ~20 widgets — the densest quality screen) is the primary anchor; mention `QualityManagementCenterPage.tsx`/`QualityCommandCenterPage.tsx` exist but are orphaned, so don't promise the audience they can find them via the sidebar unassisted.
- **Research Partner** — `ResearchPortalPage.tsx` (`/research`, orphaned) shows global trend summaries and published knowledge contributions; Oracle's Research Workspace (`/oracle`, also orphaned) is the deeper research-hypothesis tool, appropriate for a more technical academic audience.

## AI Specialist collaboration demonstration (Objective 8) — the single most important honesty correction in this document

**The brief's literal chain — "Vision → Anatomy → Veritas → Aegis → Vulcan → Sentinel-X → Council → Human Approval" as one automatic pipeline — does not exist anywhere in this codebase.** This was directly verified by tracing the actual inspection-creation code path. Presenting it as one seamless automated flow would be a factual misrepresentation live in front of a technical audience (a manufacturer engineer or academic researcher is exactly the audience likely to ask "show me that request trace"). The real, honest picture:

- **"Vision"** (the trained CV model class, `app/ai/inference.py`) is **dead code** as far as inspection creation is concerned — it's never called by the real route. A separate deterministic placeholder (`baseline_comparison_scoring_service.analyze_inspection`, self-described as "NOT production computer vision") generates findings instead.
- **"Anatomy"** genuinely does run inline, synchronously, in the same request as inspection creation (`instrument_zones.py`'s `zone_fields()`/`is_high_retention()`).
- **Veritas, Vulcan, and Sentinel-X are NOT automatically triggered** by inspection creation — each has its own dedicated `POST /assess`-style route that must be explicitly called.
- **A real chain does exist, but only inside Sentinel-X's own code**: `sentinelx_risk_agent_service.run_risk_assessment()` synchronously calls Vulcan, then Aegis (a computed signal living inside Vulcan's table, not a standalone specialist — confirmed, no "Aegis" model class exists anywhere), then Veritas — but only when a human explicitly requests a Sentinel-X assessment.
- **A real 5-specialist chain also exists inside Council**: `council_orchestration_service.convene()` genuinely invokes Vulcan, Veritas, Sentinel-X (which itself re-invokes Vulcan/Aegis/Veritas), Aegis, and Maestro in one synchronous function call — but this requires two prior manual API calls (`open_case`, then `convene`) and is fully human-triggered, decoupled from inspection creation and from Vision/Anatomy entirely.
- **Maestro does not call other specialists' compute functions at all** — its own docstring states "nothing here is computed fresh," it only reads pre-computed summaries.

**How to honestly present Objective 8**: *"These specialists are wired to genuinely call each other when explicitly invoked — Sentinel-X really does pull fresh data from Vulcan, Aegis, and Veritas when you request a risk assessment; convening a Council case really does invoke five specialists in one call. But there is no single, automatic request that runs from image upload all the way to human sign-off — each stage is a deliberate, separately-triggered step, which is itself a safety property: nothing proceeds without an explicit call at every stage."* This framing is both accurate and turns the finding into a legitimate safety-and-governance talking point rather than a gap to hide.
