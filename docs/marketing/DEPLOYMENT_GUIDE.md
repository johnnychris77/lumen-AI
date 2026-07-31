# LumenAI Marketing Site — Deployment Guide

The marketing site can be deployed **two ways** from the same source code:

1. **In-app (default):** mounted at `/site/*` inside the existing frontend
   bundle. Nothing separate to deploy — it ships with the app.
2. **Standalone domain:** a dedicated static build rooted at `/`, so the site
   serves at a clean marketing domain with clean URLs
   (`marketing.example.com/workflow`, not `.../site/workflow`). This is the
   **"deploy on a different domain"** path — see
   [Standalone marketing domain](#standalone-marketing-domain-separate-from-the-app).

Both builds come from the same React components; a build-time base-path switch
(`src/marketing/lib/base.ts` → `mlink()`) rewrites internal links so the code is
identical in either mode.

## Build (in-app, mounted at `/site`)

```bash
cd frontend
npm ci                 # uses the committed package-lock.json (do not change PM)
npm run build          # type-checks + builds; output in frontend/dist/
npm run preview        # serve dist/ locally on :5173 to spot-check /site
```

Then open `http://localhost:5173/site`.

## Build (standalone marketing domain, rooted at `/`)

```bash
cd frontend
npm ci
npm run build:site     # builds ONLY the marketing site; output in frontend/dist-site/
```

`dist-site/` is a self-contained static site with `index.html` at its root and
root-relative asset/link paths. Deploy the **contents of `dist-site/`** to your
marketing host's web root. See
[Standalone marketing domain](#standalone-marketing-domain-separate-from-the-app)
for the full walkthrough.

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
4. **Standalone marketing domain (separate host, clean root URLs):** see the
   dedicated section below.

## Standalone marketing domain (separate from the app)

Use this when the marketing site should live on its **own domain** (e.g.
`www.lumenai.example` or `learn.lumenai.example`), completely separate from the
authenticated app. The app keeps its `/site/*` mount unchanged; this is an
*additional* build, not a replacement.

### 1. Build it

```bash
cd frontend
npm ci
npm run build:site
```

Output is `frontend/dist-site/` and contains **only** these four entries:
- `index.html` at the root (the `build:site` postbuild step renames the Vite
  entry `marketing.html` → `index.html`).
- `assets/` — hashed JS/CSS under `/assets/…` with **root-relative** paths
  (verified: no `/site/` prefix in the standalone bundle).
- `site/` — the only public assets the marketing pages reference
  (`social-card.svg`, `lumenai-explainer.vtt`).
- `_redirects` — an SPA catch-all (`/*  /index.html  200`), written automatically.

Internal links are rooted at `/` (e.g. `/workflow`, `/contact`), because the
standalone build defines `__MARKETING_BASE__ = ""`.

> **Why not the app's `public/`?** The marketing config sets `publicDir: false`
> so the app's `public/` directory is **not** copied. That directory holds
> unrelated static demo pages (`public/portfolio/*`, `public/dashboard/*`) that
> embed internal backend hostnames — they must never land on a public marketing
> domain. The postbuild step copies only `public/site/*`.

### 2. Deploy `dist-site/` to a static host

Upload the **contents** of `dist-site/` to the host's web root. The site is
100% static — no server, no API, no auth.

- **Netlify / Render Static / Cloudflare Pages:** set the build command to
  `npm run build:site` and the publish directory to `frontend/dist-site`.
- **Vercel:** framework = "Other"; build command `npm run build:site`; output
  directory `frontend/dist-site`.
- **S3 + CloudFront:** `aws s3 sync frontend/dist-site s3://YOUR_BUCKET --delete`;
  set the default root object to `index.html`.
- **GitHub Pages / nginx / Apache:** serve `dist-site/` as the docroot.

### 3. SPA deep-link rewrite

Client routes like `/workflow` must fall back to `/index.html`, or a hard
refresh / direct link 404s.

- **Netlify / Render / Cloudflare Pages:** already handled — the build writes
  `dist-site/_redirects` with `/*  /index.html  200`. No action needed.
- **nginx:** `location / { try_files $uri $uri/ /index.html; }`
- **Vercel:** add a rewrite `{ "source": "/(.*)", "destination": "/index.html" }`.
- **S3 + CloudFront:** set the custom error response for 403/404 → `/index.html`
  with HTTP 200.

### 4. Point the app "Sign in" / "Request a demo" links at the app domain

The standalone marketing build is intentionally decoupled from the app. Any CTA
that should reach the authenticated app (login, demo request) links to the app
domain. Set this at build time via the app's public URL if/when those CTAs are
wired to it; the shipped demo is fully self-contained (synthetic data, no API),
so no app connection is required for the site to function.

### 5. Canonical URL, robots, sitemap for the standalone domain

On a dedicated domain the public paths are root-relative (no `/site` prefix):
`/`, `/problem`, `/workflow`, `/platform`, `/architecture`, `/security`,
`/use-cases`, `/video`, `/about`, `/contact`. Add `robots.txt` and `sitemap.xml`
built for **that** domain (see the next section for the `/site`-prefixed variant
used by the in-app deploy).

`robots.txt` (standalone domain):
```
User-agent: *
Allow: /
Sitemap: https://YOUR_MARKETING_DOMAIN/sitemap.xml
```

### What still requires your input to go live

This repo build is deploy-ready, but the actual publish cannot be performed from
this environment (no hosting account, domain, or DNS access). To finalize:

- **Domain name** + **host** (Netlify / Render / Vercel / Cloudflare Pages /
  S3+CloudFront / other) → determines canonical URLs, `robots.txt`, and
  `sitemap.xml` values.
- Optional: a **contact endpoint** (`VITE_CONTACT_ENDPOINT`) if you want live
  demo-request delivery instead of mock mode.
- Optional: an **analytics provider** (`VITE_ANALYTICS_PROVIDER`) and its script.
- **`PRODUCT_CLAIMS_REVIEW.md` sign-off** before the site is publicly linked.

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

- [ ] **In-app build:** `grep -rInE "dev-token|BEGIN [A-Z ]*PRIVATE KEY|onrender\.com|localhost:8000" frontend/dist` → note that `frontend/dist` (the app build) DOES contain `public/portfolio/*` and `public/dashboard/*` demo pages with internal hostnames; that is expected for the app deploy but is exactly why the marketing domain uses the standalone build below.
- [ ] **Standalone marketing build:** `grep -rInE "dev-token|BEGIN [A-Z ]*PRIVATE KEY|onrender\.com|localhost:8000" frontend/dist-site` → must return **nothing**. `dist-site/` excludes the app's `public/` (via `publicDir: false`), so no internal hostnames ship on the marketing domain. (Verified during build.)
- [ ] Source maps disabled for public production builds if you host the
      marketing site separately (`build.sourcemap: false`).
- [ ] Contact form in mock mode OR pointed at a vetted endpoint.
- [ ] `PRODUCT_CLAIMS_REVIEW.md` sign-offs complete.
- [ ] No PHI in any demo data or asset (all demo data is synthetic by design).
