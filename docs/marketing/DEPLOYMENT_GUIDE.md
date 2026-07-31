# LumenAI Marketing Site — Deployment Guide

The marketing site ships as part of the existing frontend at `/site/*`. There is
nothing separate to deploy unless you choose to host it independently.

## Build

```bash
cd frontend
npm ci                 # uses the committed package-lock.json (do not change PM)
npm run build          # type-checks + builds; output in frontend/dist/
npm run preview        # serve dist/ locally on :5173 to spot-check /site
```

Then open `http://localhost:5173/site`.

## Environment variables (all optional; safe defaults)

Copy `frontend/.env.example` → `.env`. Marketing-relevant keys:

| Var | Default | Effect |
|---|---|---|
| `VITE_ANALYTICS_PROVIDER` | `none` | `none` = no-op (no keys, no calls). `plausible`/`gtag` call `window.plausible`/`window.gtag` **only if you load that script yourself** in `index.html`. |
| `VITE_CONTACT_ENDPOINT` | *(empty)* | Empty = contact form runs in **mock mode** (no network). Set to your own JSON POST endpoint to enable live delivery. |

No analytics or email credentials belong in the frontend source. The contact
endpoint should be your own serverless function/form service that holds any
secret server-side.

## SPA routing (deep links to /site/...)

`/site/workflow` etc. are client routes. Ensure the host rewrites unknown paths
to `index.html`. This repo already ships `frontend/public/_redirects`
(Netlify/Render style). For nginx: `try_files $uri /index.html;`.

## Hosting options

1. **Same deploy as the app (default):** the marketing pages are already in the
   frontend bundle; deploy the frontend as you do today. `/site` is public.
2. **Separately hosted marketing site:** build the frontend and serve `dist/`
   from a static host (Netlify, Render Static, S3+CloudFront, GitHub Pages). The
   `/site` routes work as-is; link into the app deployment for the login/demo.
3. **Reverse proxy:** route `example.com/site/*` to the static build and other
   paths to the app.

## robots.txt & sitemap

Add these to `frontend/public/` if you want them served at the site root (the
repo does not ship them to avoid overriding host-level config):

`robots.txt`
```
User-agent: *
Allow: /site
Sitemap: https://YOUR_DOMAIN/sitemap.xml
```

`sitemap.xml` — list the public routes: `/site`, `/site/problem`,
`/site/workflow`, `/site/platform`, `/site/architecture`, `/site/security`,
`/site/use-cases`, `/site/video`, `/site/about`, `/site/contact`. Do not include
any authenticated app route.

## Optional: unit tests for the marketing logic

The frontend currently has no test runner configured. To run the shipped
`marketing/lib/*` unit tests, add Vitest (a devDependency; does not touch the
app or its lockfile's runtime deps):

```bash
cd frontend
npm i -D vitest
npx vitest run src/marketing
```

Test files: `src/marketing/lib/*.test.ts` (workflow state machine, contact
schema, analytics guard). Until Vitest is added, the enforced gate is
`npm run build` (type-check + build), which the repo CI already runs.

## Pre-publish security checklist

- [ ] `grep -rInE "dev-token|BEGIN [A-Z ]*PRIVATE KEY|onrender\.com|localhost:8000" frontend/dist` → no secrets/internal URLs in the built bundle. (Note: `VITE_API_BASE_URL` defaults to a backend URL for the app; the marketing pages make no API calls, but confirm you are not shipping internal-only hostnames publicly.)
- [ ] Source maps disabled for public production builds if you host the
      marketing site separately (`build.sourcemap: false`).
- [ ] Contact form in mock mode OR pointed at a vetted endpoint.
- [ ] `PRODUCT_CLAIMS_REVIEW.md` sign-offs complete.
- [ ] No PHI in any demo data or asset (all demo data is synthetic by design).
