# LumenAI — Executive Presentation

Objective 6 content, structured as the narrative backbone for the 15-minute executive briefing in `docs/demo-program/DEMO_SCRIPT_LIBRARY.md`. Every claim below is scoped to match the three existing readiness scorecards (`docs/production-readiness/PRODUCTION_READINESS_SCORECARD.md`, `docs/clinical-validation/CLINICAL_READINESS_SCORECARD.md`, `docs/ux-review/UX_SCORECARD.md`) rather than contradicting them with more optimistic ad-hoc language — this is a non-negotiable constraint for this document, not a stylistic preference.

## Opening framing

LumenAI is a decision-**support** platform for sterile processing department (SPD) instrument reprocessing — it surfaces visual evidence of possible contamination or damage, alongside a confidence signal and evidence trail, for a human technician/supervisor to act on. It does not diagnose patients, does not detect pathogens, and does not make an irreversible operational decision autonomously.

## Enterprise KPIs

Present real, live-computed figures from `ExecutiveCommandCenterPage.tsx`/`/api/analytics/kpi-summary`: total inspections, high-risk instruments, open findings, open CAPAs, baseline/passport coverage. **Use one canonical dashboard per KPI** — per `docs/ux-review/DASHBOARD_STANDARDS.md`, the same KPI (e.g. "Total Inspections") is independently recomputed on 3-8 different screens; switching between them mid-presentation risks showing two different numbers for the same metric.

## Risk Reduction, Quality Improvement, Operational Efficiency

Present Sentinel-X's real risk-scoring bands and Vulcan's honestly-hedged progression model as the mechanism behind "risk reduction" — these are genuinely well-designed systems (see `docs/clinical-validation/DIGITAL_TWIN_CLINICAL_MODEL.md`'s conclusion) that never assert a trend from insufficient data. **Do not claim a measured reduction in surgical site infections or patient harm** — no such causal outcome data exists in this codebase; the correct framing is "designed to reduce risk of undetected contamination/damage reaching the OR," not a measured clinical outcome.

## ROI Dashboard — the single most important framing correction

`ROICenterPage.tsx`/`ValueRealizationPage.tsx` compute real inspection/finding/CAPA/baseline-coverage counts from live data, but every dollar figure is that real count multiplied by a **hardcoded industry-benchmark constant** ($28,000/SSI avoided, $5,000/critical finding, $2,500/CAPA, $35/hr labor) — not a measured customer outcome. **State this plainly in the presentation**: *"These are estimated value figures using disclosed, conservative industry benchmarks applied to real platform usage — not measured customer ROI."* Both pages also have a silent fallback to fabricated demo numbers if their live API call fails; confirm the real data path is active before presenting this screen (see `docs/demo-program/DEMO_CHECKLIST.md`).

## Strategic Insights and Executive Brief

Vanguard's board-reporting service genuinely generates PDF/Excel/PowerPoint board packets by reusing the platform's existing executive-report logic (not duplicating it), and its scenario-planning service genuinely calls real endpoints backed by real composed data with an explicit anti-fabrication design (its own docstring disclaims being "a fabricated enterprise-wide what-if simulator"). This is genuinely strong, real capability and should be demonstrated live as a generated-artifact moment.

**Necessary honesty note**: this capability currently lives at `/executive` and `/strategy`, both orphaned from the sidebar navigation in favor of a separate, less complete KPI-only dashboard at `/executive-command-center` (`docs/ux-review/NAVIGATION_ARCHITECTURE.md`). Present Vanguard as "built and functional, being integrated into primary navigation" — not as a tool hospital executives are actively using today, since that would overstate current adoption.

## The honest maturity baseline — reference the scorecards directly

Rather than a separate, softer summary, this presentation should draw its maturity claims directly from the three existing scorecards:
- **Architecture**: coherent and well-reused, with three flagged Critical Gaps (dev-auth bypass configuration risk, a possible mock-data-serving executive dashboard, near-absent database referential integrity) — `docs/production-readiness/PRODUCTION_READINESS_SCORECARD.md`.
- **Clinical**: strong structural patient-safety discipline (mandatory override reasons, `human_review_required` on 35 model files, no irreversible AI-only actions), but **no trained model ships today** — the deployed inference path emits only `debris`/`corrosion` — `docs/clinical-validation/CLINICAL_READINESS_SCORECARD.md`.
- **UX**: the platform's problems are fragmentation and incompleteness, not poor design — half the app's screens are undiscoverable from navigation, and a working supervisor approve/return action could not be located anywhere in the product — `docs/ux-review/UX_SCORECARD.md`.

**Presenting these honestly is a credibility asset, not a liability** — a hospital executive audience is more likely to trust a vendor who names their own gaps precisely than one who claims uniform production-readiness across the board.

## Non-negotiable constraints for this presentation (from `CLAUDE.md`)

- Never claim FDA clearance or regulatory approval, anywhere.
- Never claim causation for a clinical outcome — use "potential association," "possible contributing factor."
- Every AI recommendation shown must be presented as requiring human review, matching the platform's actual `human_review_required` design.
