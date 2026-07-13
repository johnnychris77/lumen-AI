# LumenAI — Pilot Lessons Learned (Version 1.1)

This document does not duplicate `docs/pilot/pilot-lessons-learned.md` — it indexes that document (with the honesty caveat established in `docs/product-evolution/CUSTOMER_FEEDBACK_REPORT.md`) and adds the genuinely new lessons learned from this session's own seven-phase review program, which is itself a real, evidence-generating exercise even though it predates any real customer pilot.

## Lessons from the internal dogfooding exercise (`docs/pilot/pilot-lessons-learned.md`)

Treat as real, code-verifiable internal QA findings — not validated hospital-pilot experience (see the caveat in `CUSTOMER_FEEDBACK_REPORT.md`). The most actionable, recurring themes:

1. **The inspection-creation workflow needs consolidation.** The two-step "submit record, then separately upload images" friction (item 2b) is the same root issue this session's own UX review independently found and documented at greater depth: three competing inspection-entry flows with contradictory manual-entry rules (`docs/ux-review/USER_JOURNEYS.md`). This convergent finding — from two independent evidence sources — should raise this item's priority in the Version 1.1 backlog.
2. **Several `Inspection` model fields captured on the form are not persisted** (`facility_name`, `department`, `tray_id`, `instrument_barcode`, `instrument_udi`, `borescope_image_count`, and a formal `related_instrument_id` foreign key) — a real, specific, fixable data-model gap.
3. **The baseline review queue has no priority signal** — consistent with this session's own UX finding that the nav-reachable review screens are largely read-only/low-affordance (`docs/ux-review/USER_JOURNEYS.md`'s Supervisor journey).
4. **Missing reports** (tray-level contamination summary, cycle-count trend, baseline coverage %, review-turnaround time, upload-failure log, week-over-week finding trend, instrument×finding risk heat map) — none require new architecture, only new aggregation views over existing data.
5. **Real deployment issues already fixed** (D-1 through D-7 in the source document) — useful as a "what breaks in practice" record for future onboarding, even though several are already resolved.

## Lessons from this program's own seven-phase review (a legitimate evidence source in its own right)

This session's own documentation program — architecture freeze, clinical validation, UX review, launch readiness, commercial readiness, release management — is itself real "operational observation," "usability study," "performance metrics," "security review," and "clinical validation review" evidence, per this program's own acceptable-source list. Its most significant lessons for Version 1.1 planning:

1. **The most valuable single fix available today is not a new feature — it's making the supervisor approval workflow actually reachable in the UI.** No working approve/return control was found anywhere in the frontend (`docs/ux-review/USER_JOURNEYS.md`), even though the backend enforcement is real and sound. This is the clearest example of "evidence from production" this program can currently offer, even without a real customer pilot — the evidence came from direct code inspection, which the program's philosophy explicitly allows.
2. **Navigation completeness, not new capability, is the highest-leverage usability investment.** 45 of ~90 routes have no sidebar entry (`docs/ux-review/NAVIGATION_ARCHITECTURE.md`) — several of Version 1.1's most-requested-sounding "features" (a working evidence-review tool, a working escalation-tracking tool) already exist in the codebase and only need to be wired into navigation.
3. **Dashboard KPI consolidation is real, scoped, low-risk technical debt**, not a new feature: the same core metrics are independently recomputed across 3-8 screens (`docs/ux-review/DASHBOARD_STANDARDS.md`).
4. **One genuine application bug was found and fixed this cycle** (`enterprise_risk_score` exceeding its documented bound, `docs/release-management/BUG_REGISTER.md`) — a reminder that "measurable outcomes" evidence can come from a rigorous internal regression investigation, not only from field reports.
5. **The AI-specialist collaboration story needs to be told accurately, not aspirationally** — the "Vision → Anatomy → Veritas → Aegis → Vulcan → Sentinel-X → Council → Human Approval" chain does not exist as one automated pipeline (`docs/demo-program/ROLE_BASED_DEMOS.md`). Any Version 1.1 AI-explainability improvement should be scoped against what's actually wired today, not the idealized narrative.

## The central, honest lesson of this document

**The single most important "lesson learned" from this entire pre-launch review program is that LumenAI has extensive, rigorous internal review discipline but zero real customer-pilot evidence yet.** Every one of this program's seven phases converged on variations of the same finding: the engineering is more disciplined than some of the documentation describes it to be, and the biggest remaining gap before Version 1.1 can be genuinely "customer-driven" is simply that no customer has used the product yet. Closing that gap — getting one real, disclosed pilot underway — is the prerequisite lesson this document surfaces above all the specific UI/data/report findings listed above.
