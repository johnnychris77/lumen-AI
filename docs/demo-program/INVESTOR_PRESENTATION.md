# LumenAI — Investor Presentation

Structured as the narrative backbone for the 60-minute investor presentation in `docs/demo-program/DEMO_SCRIPT_LIBRARY.md`. Like `docs/demo-program/EXECUTIVE_PRESENTATION.md`, every claim here is scoped to the three existing readiness scorecards rather than presenting a more polished counter-narrative — an investor doing real diligence will find the scorecards in this same repository, so any contradiction is a credibility risk, not just a documentation inconsistency.

## Market framing — an honest gap, stated plainly

**No market-size, TAM/SAM, CAGR, or revenue-projection figures exist anywhere in this repository** (`docs/investor/`, `docs/sales/`, `docs/roadmap/`, `docs/outreach/` were all searched — zero hits). This is worth stating rather than silently inventing a number: any market-sizing figure used in a live investor presentation is an **external estimate the presenter must source and cite separately**, not something this platform's own documentation currently substantiates. Use `docs/outreach/LUMENAI_v1_5_TARGET_CUSTOMER_LIST_AND_OUTREACH_STRATEGY_v1.md`'s qualitative ICP/segment definitions (multi-hospital systems, offsite reprocessing centers, large surgical hospitals) as the real, existing market-framing content instead of a fabricated dollar figure.

## Technical narrative — reuse the existing, sober framing

`docs/investor/technical-narrative.md` is the most reusable, non-inflated technical description already in the repository: an API-driven workflow platform with queue-backed async inference, worker-based processing, persistent inspection history, and Docker/GHCR deployability. Lead the technical section from this document rather than the more inflated status-banner language found elsewhere in `docs/investor/` (see the flag below).

## A pre-existing overclaim pattern in this repository — must not be repeated

Several existing files in `docs/investor/` carry unqualified "Production Validated" / "Investor Ready" status banners (e.g. `ENTERPRISE_GOVERNANCE_SUITE_FINAL_EXECUTIVE_ONE_PAGER_v1.md`, `ENTERPRISE_GOVERNANCE_SUITE_FINAL_INVESTOR_PORTFOLIO_PACKET_v1.md`). **These directly contradict the Production Readiness Scorecard's three Critical Gaps and the Clinical Readiness Scorecard's "no trained model ships" finding.** This document does not repeat that framing. Where those older files cite specific validation numbers (e.g. "18/18 checks passed, 696 audit events"), that is real evidence from a single hosted demo instance's point-in-time validation run — present it as exactly that ("a demo environment validation snapshot"), not as production customer traction or revenue evidence.

## What is genuinely strong and should be led with

- **Architectural reuse discipline is real and verified**: the specialist pattern, naming-disambiguation convention, and shared infrastructure (audit hash-chain, approval-tier system) hold up under direct code inspection, not just self-description — `docs/production-readiness/PRODUCTION_READINESS_SCORECARD.md`'s single strongest finding.
- **Patient-safety discipline is structural, not aspirational**: mandatory override reasons (enforced as a real `ReasonRequiredError`/HTTP 422), `human_review_required` defaulting `True` on 35 model files, no code path anywhere that lets an AI output become an irreversible action without a tier-checked human role — `docs/clinical-validation/CLINICAL_READINESS_SCORECARD.md`.
- **The AI-specialist collaboration architecture is real, gated, and auditable** — not one automatic black-box pipeline, but a set of specialists genuinely wired to call each other when explicitly invoked (Sentinel-X really pulls fresh data from Vulcan/Aegis/Veritas; a Council case convene genuinely invokes five specialists in one call), with every stage requiring an explicit, logged trigger. Present this as a deliberate governance property, using the corrected framing in `docs/demo-program/ROLE_BASED_DEMOS.md`'s Objective 8 section.
- **Vanguard's board-reporting and scenario-planning services are real and disciplined against fabrication** — genuine PDF/Excel/PPTX board-packet generation reusing existing report logic, and a scenario-planning service whose own docstring explicitly disclaims being a fabricated simulator.
- **No unhedged FDA-clearance or "clinically proven" language exists anywhere in the codebase** (`docs/clinical-validation/CLINICAL_READINESS_SCORECARD.md`'s own finding) — this is a real compliance-discipline strength to highlight, not just an absence to note.

## What must be disclosed honestly, not smoothed over

- **No trained model ships today** — deployed inference produces only `debris`/`corrosion`; the fuller 12-13 category taxonomy exists in the scoring/education design layer. Any statement about "what LumenAI detects" must lead with this distinction.
- **Pre-market clinical data is synthetic/mock**, and the planned multi-site blinded reader study has not been conducted.
- **Three Critical Gaps remain before the architecture is unconditionally production-ready**: a dev-auth bypass configuration risk, the possibility an executive dashboard serves mock data with no user-visible indicator, and near-absent database referential integrity/constraint enforcement.
- **A working supervisor approve/return action could not be located anywhere in the product** during the UX review — this is the single most significant open item before pilot deployments can rely on the full human-oversight loop being reachable end-to-end in the UI (the backend enforcement itself is real and sound; the frontend control is the gap).
- **Roughly half the application's screens are undiscoverable from primary navigation** (45 of ~90 routes have no sidebar entry) — a real, fixable UX debt, not an architecture problem.

## Roadmap section

Anchor on `docs/roadmap/PHASE_3_PRODUCT_HARDENING_ROADMAP.md`'s honest current-state-vs-target-state framing (its own language: moving "from a working hosted enterprise demo into a pilot-ready healthcare operations platform"), which already names the dev-token auth risk and the SQLite-to-PostgreSQL migration need as roadmap items rather than hidden gaps. Sequence the roadmap narrative as: (1) close the three Critical Gaps named above, (2) close the supervisor-approval UX gap, (3) complete real instrument photography/image-library population, (4) conduct the multi-site clinical reader study, (5) expand navigation completeness. This sequencing is itself evidence of a disciplined, self-aware engineering organization — a stronger investor signal than a presentation with no acknowledged gaps at all.

## Non-negotiable constraints for this presentation (from `CLAUDE.md`)

- Never claim FDA clearance or regulatory approval, anywhere.
- Never claim causation for a clinical outcome.
- No fabricated market-size, revenue-projection, or customer-traction figures — cite the repository's actual evidence (demo validation snapshots, real seeded data, real architecture) precisely, and label external market estimates as external.
