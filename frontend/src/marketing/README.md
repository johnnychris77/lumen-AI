# LumenAI public marketing site (`/site`)

A marketing, education, and demonstration layer around the LumenAI product. It
does **not** change the product: no production API calls, no shared app state,
all demo data synthetic. Mounted at `/site/*` outside the authenticated
AppShell (see `docs/adr/0010-public-marketing-site.md`).

## Run locally

```bash
cd frontend
npm ci
npm run build && npm run preview   # then open http://localhost:5173/site
# or: npm run dev                    # http://localhost:5173/site
```

## Where things live

- `MarketingApp.tsx` — routes · `MarketingLayout.tsx` — chrome · `pages.tsx` — pages
- `lib/content.ts` — all copy (edit here) · `lib/workflowDemo.ts` — demo logic
- `lib/contact.ts` — form schema/submit · `lib/seo.ts` · `lib/analytics.ts`
- `components/` — diagrams, interactive demo, dashboard, contact form, video
- Static: `../../public/site/social-card.svg`, `../../public/site/lumenai-explainer.vtt`

## Docs

`docs/marketing/` — overview, content guide, video script/storyboard, deployment,
asset inventory, and the **product claims review** (read before changing copy).

## Guardrails

Decision support + evidence governance only. AI is assistive with human review.
No FDA/HIPAA/SOC2/compliance/accuracy/outcome/cost claims. All demo content is
labeled "Demonstration Data — Not for Clinical Use". No PHI, no secrets.

## Tests

`lib/*.test.ts` are Vitest specs. The frontend has no test runner by default;
add one to run them: `npm i -D vitest && npx vitest run src/marketing`. The
enforced gate is `npm run build`.
