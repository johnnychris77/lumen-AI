# LumenAI Marketing — Asset Inventory

## Code (frontend/src/marketing/)

| Path | Purpose |
|---|---|
| `MarketingApp.tsx` | `/site/*` route tree |
| `MarketingLayout.tsx` | Header/nav/footer/skip-link |
| `pages.tsx` | Home, Problem, Workflow, Platform, Architecture, Security, UseCases, Video, About, Contact, 404 |
| `lib/content.ts` | Capabilities, specialists, use cases, video scenes, nav |
| `lib/workflowDemo.ts` | Interactive demo state machine + synthetic data |
| `lib/contact.ts` | Zod schema + submit adapter (mock/live) |
| `lib/seo.ts` | Per-page title/description/OG/canonical |
| `lib/analytics.ts` | `track()` no-op-by-default abstraction |
| `components/Logo.tsx` | Wordmark (SVG) |
| `components/primitives.tsx` | Section, headings, CTA row, maturity badge |
| `components/DemoDisclaimer.tsx` | "Demonstration Data — Not for Clinical Use" |
| `components/WorkflowDiagram.tsx` | 10-step workflow + legend |
| `components/EvidencePathDiagram.tsx` | Evidence path SVG |
| `components/WorkflowDemo.tsx` | Interactive demo UI + synthetic borescope SVG |
| `components/DashboardPreview.tsx` | Concept dashboard (recharts, synthetic) |
| `components/SpecialistArchitecture.tsx` | Specialist grid + boundary panel |
| `components/ContactForm.tsx` | Demo-request form |
| `components/VideoStoryboard.tsx` | Interactive video preview |

## Static assets (frontend/public/site/)

| File | Purpose | Status |
|---|---|---|
| `social-card.svg` | 1200×630 Open Graph / social preview; also thumbnail source | ✅ in repo |
| `lumenai-explainer.vtt` | WebVTT captions for the explainer | ✅ in repo |

## Docs (docs/marketing/)

`WEBSITE_OVERVIEW.md`, `CONTENT_GUIDE.md`, `VIDEO_SCRIPT.md`,
`VIDEO_STORYBOARD.md`, `DEPLOYMENT_GUIDE.md`, `ASSET_INVENTORY.md` (this file),
`PRODUCT_CLAIMS_REVIEW.md`. ADR: `docs/adr/0010-public-marketing-site.md`.

## Brand tokens (reused, not duplicated)

Defined in `frontend/src/index.css` `@theme`: primary `#4f46e5` (indigo) +
semantic success/warning/danger/info. The marketing site consumes these via
Tailwind utilities (`bg-primary`, `text-warning`, …) — no separate brand system.

## To be produced before public launch (not in repo)

| Asset | Needed for | How |
|---|---|---|
| `lumenai-explainer.mp4` (+720p) | Video section | Render per `VIDEO_STORYBOARD.md` (Remotion or editor) |
| Voiceover audio | Video | Record `VIDEO_SCRIPT.md` |
| Licensed music bed | Video | Source + record license here |
| Real product screenshots (PHI-scrubbed) | Optional dashboard/section imagery | Capture from demo app with synthetic data |
| Final logo / brand assets | Replace temporary wordmark | Swap `Logo.tsx` + `social-card.svg` |
| `robots.txt`, `sitemap.xml` | SEO | Add to `frontend/public/` (templates in DEPLOYMENT_GUIDE) |

## Placeholders explicitly flagged

- **Logo/wordmark** is a temporary restrained mark, easily replaced.
- **Explainer video** is delivered as script + storyboard + captions + an
  interactive on-site preview; the rendered MP4 is pending media production.
- **Contact delivery** runs in mock mode until `VITE_CONTACT_ENDPOINT` is set.
- **Analytics** is inert until `VITE_ANALYTICS_PROVIDER` is set.
