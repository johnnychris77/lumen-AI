# ADR 0010 — Public marketing site as an isolated route in the existing frontend

- **Status:** Accepted
- **Date:** 2026-07-23
- **Context tags:** marketing, frontend, architecture-boundary

## Context

We need a production-quality public marketing, education, and demonstration
website for LumenAI (home, problem, workflow + interactive demo, platform, AI
architecture, security, use cases, video, about, contact). The LumenAI v1.0
architecture is **frozen**: no new production APIs, no duplicated business
logic, no second source of truth, no change to auth / tenant-isolation /
evidence-integrity / ranking behavior.

Three options were considered:

1. **A public route tree inside the existing frontend** (React 18 + Vite 8 +
   Tailwind 4 + react-router 7), mounted outside the authenticated AppShell.
2. A **separate `website/` app** in the repo (own package.json / lockfile).
3. A **standalone static site** linking to the demo app.

## Decision

**Option 1.** The marketing site lives at `frontend/src/marketing/**` and is
mounted at `/site/*` in `frontend/src/main.tsx`, as a **public route placed
before** the authenticated `/*` catch-all, so it renders with **no AppShell and
no auth guard**. It is lazy-loaded as its own chunk (`MarketingApp`).

## Rationale

- **Lowest risk & directly validatable.** It reuses the repo's real toolchain,
  so the existing `npm run build` (the CI gate) type-checks and builds it. No
  new package manager, lockfile, or dependency was introduced — the site uses
  only libraries already present (`recharts`, `react-hook-form`, `zod`,
  `lucide-react`, `react-router-dom`).
- **Respects the freeze.** The marketing tree makes **zero** production API
  calls and holds **no** shared app state. All demo content is synthetic and
  isolated in `marketing/lib/*`. Auth, routing of the app, tenant isolation, and
  evidence behavior are untouched — the only router change is one additive
  public route.
- **Isolation without tooling duplication.** A separate `website/` app (option
  2) would duplicate build config and a lockfile and could drift from the design
  system; a standalone static site (option 3) would lose the shared tokens and
  components. Option 1 keeps one design system and one build.

## Consequences

- Marketing pages ship in the same repo/bundle but are code-split; they cost
  nothing until `/site` is visited.
- The site can be deployed as part of the existing frontend, or the `/site`
  routes can be reverse-proxied / statically hosted separately later without
  code changes (see `docs/marketing/DEPLOYMENT_GUIDE.md`).
- Because it is unauthenticated and public, everything under `/site` is treated
  as public content: synthetic demo data only, no secrets, a persistent
  "Demonstration Data — Not for Clinical Use" label on all simulated output.

## Boundaries preserved

No new specialists, engines, models, or tables. No change to core ranking,
baseline governance, evidence integrity, or tenant isolation. The contact form
uses a configurable external endpoint or a safe mock mode — never an embedded
mail relay or credential.
