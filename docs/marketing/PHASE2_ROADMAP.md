# Phase 2 — Executive Demonstration & Commercial Readiness (Roadmap)

Program to bring the marketing/demo layer to an enterprise-SaaS bar. Frozen v1.0
architecture untouched; all work is presentation/demo/docs only.

## Increment 1 — DELIVERED (this PR)
- **Persona-driven Executive Dashboard** (`/executive`): 8 role personas
  (CEO, SPD Director, Technician, Quality, Infection Prevention, Vendor, Biomed,
  Investor) reframing synthetic KPIs; lazy dashboard charts; pervasive
  synthetic-data labeling. (Objectives 3 + 4; anchors 1.)
- **Sales/demo documentation set** (Objective 17): PRODUCT_OVERVIEW, EXECUTIVE_DEMO_GUIDE,
  DEMO_SCRIPT, SALES_PLAYBOOK, PILOT_GUIDE, IMPLEMENTATION_GUIDE, FAQ.
- Route + sitemap + footer wiring; SEO metadata.

## Planned increments (not yet built)
| # | Objective | Notes |
|---|---|---|
| 2 | Guided tours (Executive/Clinical/Technical/AI/Governance) | Onboarding overlay/coach-mark component driving existing pages. |
| 3 | Interactive product walkthrough overlays | Extend the existing `/workflow` demo with step coach-marks. |
| 4 | AI architecture visualization (animated) | Enhance existing `/architecture` page; per-specialist responsibility animation. |
| 5 | Interactive evidence timeline | Animate the existing evidence-path diagram. |
| 6 | Digital twin concept page | New `/digital-twin` with synthetic lifecycle records. |
| 7 | AI specialist explorer | Interactive purpose/inputs/outputs/allowed/forbidden — from repo docs; never imply autonomy. |
| 8 | Product comparison page | vs borescope-only / image storage / spreadsheets — claims-safe. |
| 9 | Customer journey (animated) | evaluate → pilot → deploy → train → routine → improve. |
| 10 | Video experience | Real-video slot already wired (`VITE_EXPLAINER_VIDEO_URL`); + downloadable PDF overview. |
| 11 | Download center | Serve the docs above as downloadable PDFs. |
| 12 | Demo request flow upgrade | Hospital-type field, success page, calendar/CRM placeholders (contact endpoint already isolated). |
| 13 | A11y / perf / SEO hardening | Structured data (Organization/Product), reduced-motion for new animations, image/font tuning. |

## Guardrails (all increments)
Synthetic data only; assistive/human-reviewed language; no outcome/accuracy/
regulatory/savings claims; no autonomous-clinical-decision framing; frozen backend.
