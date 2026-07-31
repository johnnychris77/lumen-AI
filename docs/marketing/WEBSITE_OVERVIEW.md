# LumenAI Marketing Website — Overview

A public marketing, education, and demonstration layer for LumenAI. It does not
change the product; it explains and demonstrates it.

## Architecture

- **Type:** public route tree inside the existing frontend (see
  `docs/adr/0010-public-marketing-site.md`).
- **Mount:** `/site/*` in `frontend/src/main.tsx`, placed **before** the
  authenticated `/*` catch-all → no AppShell, no auth guard, lazy-loaded chunk.
- **Stack:** the repo's existing React 18 + Vite 8 + Tailwind 4 +
  react-router 7. **Zero new dependencies** — reuses `recharts`,
  `react-hook-form`, `zod`, `lucide-react`.
- **Isolation:** no production API calls, no shared app state, all demo data
  synthetic (`marketing/lib/*`).

## Source layout (`frontend/src/marketing/`)

```
MarketingApp.tsx         Route tree (/site/*), wraps pages in MarketingLayout
MarketingLayout.tsx      Header nav + mobile menu + footer + skip link
pages.tsx                All page components (Home, Problem, Workflow, …)
lib/
  content.ts             Copy: capabilities, specialists, use cases, video scenes
  workflowDemo.ts        Pure state machine for the interactive demo (synthetic)
  contact.ts             Zod schema + submit adapter (mock/live)
  seo.ts                 useSeo() — title/description/OG/canonical per page
  analytics.ts           track() — no-op unless a provider is configured
components/
  Logo, primitives, DemoDisclaimer, WorkflowDiagram, EvidencePathDiagram,
  WorkflowDemo, DashboardPreview, SpecialistArchitecture, ContactForm,
  VideoStoryboard
```

Public assets: `frontend/public/site/social-card.svg`,
`frontend/public/site/lumenai-explainer.vtt`.

## Pages / routes

| Route | Page | Purpose |
|---|---|---|
| `/site` | Home | Hero, problem teaser, key outcomes, trust band, CTAs |
| `/site/problem` | The Problem | Eight structural inspection challenges + responsible framing |
| `/site/workflow` | How It Works | 10-step workflow, **interactive demo**, evidence-path diagram |
| `/site/platform` | Platform | Capability cards (maturity-tagged), **dashboard preview**, "more than image storage" |
| `/site/architecture` | AI Architecture | 10 specialists with purpose/inputs/outputs/allowed/not-allowed/human-review |
| `/site/security` | Security & Governance | Controls + explicit "what we do not claim" |
| `/site/use-cases` | Use Cases | 10 role-based scenarios |
| `/site/video` | Explainer Video | Storyboard-based interactive preview + doc pointers |
| `/site/about` | About | Vision pillars + pilot CTA |
| `/site/contact` | Contact | Demo-request form (mock/live) |
| `/site/*` | 404 | Friendly not-found |

## Interactive workflow demo

An eight-step clickable state machine (`lib/workflowDemo.ts`): select instrument
→ select sample image → metadata → assistive analysis (confidence) → baseline
compare (side-by-side) → review routing (review-required flag) → record evidence
→ generated report. Deterministic synthetic results per sample; a persistent
"Demonstration Data — Not for Clinical Use" banner is always visible.

## Accessibility

Skip link, semantic headings/landmarks, keyboard-operable controls with visible
focus rings, `aria-pressed`/`aria-expanded`, labeled forms with inline errors,
alt text / `role="img"` on diagrams, `motion-reduce:` on animated transitions,
responsive from ~360px up, and AA-oriented contrast via the design tokens.

## SEO & social

Per-page `<title>`, meta description, canonical, Open Graph + Twitter tags set
by `useSeo()`. Social card at `/site/social-card.svg`. Heading hierarchy is one
`h1` per page. See DEPLOYMENT_GUIDE for sitemap/robots.

## Analytics

`track()` emits `page_view`, `workflow_demo_step`, `workflow_demo_complete`,
`video_play`, `demo_request_click`, `contact_submit`, `cta_click`. No keys in
source; a provider activates only via `VITE_ANALYTICS_PROVIDER`.

## Build & test

`npm --prefix frontend run build` type-checks and builds the site as part of the
normal frontend build (the CI gate). See `docs/marketing/DEPLOYMENT_GUIDE.md`
for optional unit-test wiring and hosting.
