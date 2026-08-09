# Marketing Website — Accessibility Review (WCAG 2.1 AA, code-level)

**Date:** 2026-08-02 • Method: source inspection + production build. Automated tools
(axe/Lighthouse/Playwright) were **not** run in this pass.

| Area | Status | Notes |
|---|---|---|
| Skip link | PASS | `Skip to content` → `#main`, visible on focus. |
| Landmarks | PASS | `<header> <nav aria-label> <main id="main"> <footer>` + labelled footer navs. |
| Heading order | PASS | One `<h1>` per page via `SectionHeading as="h1"`; sections use `<h2>/<h3>`. |
| Active route vs focus | **FIXED** | Active = underline/accent + `aria-current`; focus = separate `focus-visible` ring (desktop + mobile). |
| Keyboard focus visibility | PASS/FIXED | Nav links, mobile items, buttons, and CTAs all carry `focus-visible:ring`. |
| Mobile menu | PASS | `aria-expanded`, `aria-controls`, dynamic `aria-label`, closes on route change. |
| Workflow steps for SR | PASS | `<ol aria-label>` with real `<h3>` titles; number badges `aria-hidden`. |
| Decorative icons/SVG | PASS | `aria-hidden` on lucide icons; diagram lists have `aria-label`. |
| Demo disclaimer | PASS | `role="note"`, non-hover, persistent, readable at mobile sizes. |
| Color-only status | REVIEW | Workflow stage badges pair color **with text labels** (good); confirm demo result states also use text, not color alone. |
| Video captions/transcript | REVIEW | `lumenai-explainer.vtt` ships; confirm the player wires captions + provides a transcript. |
| Reduced motion | REVIEW | Animations are minimal; add `prefers-reduced-motion` guards if any transition is non-trivial. |

**Remaining limitation:** no automated a11y score. Recommend running axe + Lighthouse
against the deployed URL before a formal AA sign-off.
