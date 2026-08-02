# LumenAI Marketing Website — Final Production-Readiness Review

**Date:** 2026-08-02 • **Branch:** `claude/sentinel-simulation-engine-hhh6o7` •
**Deployed:** https://lumenai-opsbridgesolution-com.onrender.com •
**Custom domain (configured):** `lumenai.opsbridgesolution.com`

## Scope & constraint
Review + correction pass on the public marketing site only
(`frontend/src/marketing/**`, `frontend/marketing.html`, `frontend/vite.marketing.config.ts`,
`frontend/scripts/postbuild-site.mjs`, `services/contact-endpoint/**`,
`deploy/render/marketing.yaml`). **No** changes to the frozen v1.0 application
architecture (no new specialists, APIs, ranking/baseline/evidence/tenant rules).

## Determination
**CONDITIONALLY READY** — the site is safe to serve; remaining items are
configuration and external-review tasks, not code defects. See
`RELEASE_CHECKLIST.md`.

## Corrections implemented (this pass)
| # | Issue | Correction | File |
|---|---|---|---|
| 1 | Active nav item read as a focus outline (dark rectangle) | Active route now uses a persistent underline + accent (driven by `aria-current`); keyboard focus uses a separate `focus-visible` ring. Desktop + mobile. | `MarketingLayout.tsx` |
| 2 | Workflow sequence direction | Added an explicit "Follow 1 → 10" cue and an "assistive workflow, not autonomous pipeline" note above the diagram. | `pages.tsx` |
| 3 | Human-oversight not restated on the workflow page | Added an oversight panel (assistive analysis; review routing; governed baselines; human-final; not a replacement for IFUs; not autonomous). | `pages.tsx` |
| 4 | No post-workflow CTA | Added "Explore the simulated inspection" (in-page `#demo`) + "Request a product demonstration". | `pages.tsx` |
| 5 | Sticky header could cover `#demo` anchor | Added `scroll-mt-20` to the demo section. | `pages.tsx` |

## Verified already-correct (no change needed)
- **Demo disclaimer** ("Demonstration Data — Not for Clinical Use") is a persistent,
  non-hover `role="note"` present on all synthetic-data surfaces
  (`DemoDisclaimer.tsx`, used in `WorkflowDemo`, `DashboardPreview`, `pages.tsx`).
- **Workflow wording** already matches the requested action-oriented list (Identify /
  Capture / Attach metadata / Validate / Analyze / Compare with baseline / Provisional
  or final ranking / Route for human review / Record evidence / Reports).
- **Floating widget:** the site ships **zero** `position: fixed` widgets. The lightbulb
  overlay seen in browser screenshots is a **browser extension**, not site content.
- **Secrets:** none in source or in `dist-site/` build output (scanned).
- **Semantic structure:** skip-link, `<header>/<main id="main">/<footer>`, labelled
  `<nav>`s, `<ol>` workflow with `<h3>` steps, aria-labels on decorative SVG/icons.

## Validation actually run (see PROOF below)
- `npx tsc --noEmit` — **0 errors in `src/marketing/`** source. (Pre-existing app-wide
  errors in `AIAssuranceCenter.tsx`/`AgentRegistryCenter.tsx` are unrelated and not
  gated by the build; one pre-existing type mismatch lives in the untouched
  `workflowDemo.test.ts`.)
- `npm run build:site` — **success**, `origin=https://lumenai.opsbridgesolution.com`,
  emits `index.html, robots.txt, sitemap.xml, _redirects, 404.html, assets, site`.
- `git diff --check` — clean.
- Secret/leak scan of `dist-site/` — no credentials, no localhost/onrender/staging, no
  `.map` files, no `VITE_` literals.

## NOT run (honest gaps — require tooling/runtime not available in this pass)
- Lighthouse, axe-core, Playwright/browser automation — no runner configured in the
  repo and not executed here. Accessibility/perf claims are **code-level**, not
  tool-scored.
- No unit-test runner (vitest/jest) is configured, so the existing
  `*.test.ts` files cannot execute. See `KNOWN_LIMITATIONS.md`.
- Deployed **response headers** were not fetched live; they are **declared** in
  `deploy/render/marketing.yaml` (see `SECURITY_REVIEW.md`) but must be verified with
  `curl -I` against production.
