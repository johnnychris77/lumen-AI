# Frontend Dependency Audit — Remediation & Triage

**Date:** 2026-07-31
**Trigger:** `frontend-security-and-build` CI job (`npm audit --audit-level=high`)
began failing across `main` and all open PRs after new advisories were
published for dependencies already in the repo (not introduced by any recent
change).

## What was remediated (this PR)

| Package | Before | After | Advisories cleared |
|---|---|---|---|
| `postcss` | ^8.5.15 | **^8.5.25** | GHSA-r28c-9q8g-f849 (path traversal in source-map auto-loading) |
| `react-router-dom` | ^7.17.0 | **^7.18.2** | 4 of 5 react-router advisories: open redirect (GHSA-wrjc-x8rr-h8h6), RSC XSS (GHSA-h8fp-f39c-q6mh), constructor injection (GHSA-337j-9hxr-rhxg), inefficient-route-matching DoS (GHSA-chx6-hx7r-mcp5) |

Result: high/critical advisory count reduced from **3 → 1** (and the total
advisory surface from 6 → 1). `npm run build` passes; the app runs on
react-router-dom 7.18.2 (a minor bump within v7; no code changes required — the
app uses stable `BrowserRouter`/`Routes`/`Route`/`Link`/`NavLink`/`Navigate`/
`Outlet`/`useLocation`/`useNavigate` APIs).

## Residual advisory (not fixable without a major migration)

**`GHSA-qwww-vcr4-c8h2` — React Router: RSC Mode CSRF Bypass Allows Action
Execution Before 400 Response.** High. Affects `react-router` core
`7.12.0 – 8.2.0`.

- **Applicability to LumenAI: none in the affected mode.** The advisory concerns
  React Router's **React Server Components (RSC) framework mode**. LumenAI's
  frontend is a **client-side SPA** using `BrowserRouter` (client data mode).
  It does not run React Router in RSC/server mode, so the CSRF-before-400 path
  is not reachable in this application.
- **No non-major forward fix exists for our stack.** The fix landed in
  `react-router` **core 8.3.0** (above the 8.2.0 top of the vulnerable range).
  There is **no `react-router-dom` 8.x** — React Router v8 removes the
  `react-router-dom` package in favor of importing directly from
  `react-router`. `npm audit`'s only automated "fix" is a **downgrade** to
  `react-router-dom@7.11.0`, which is regressive (loses ~6 minor releases of
  fixes) and is therefore **not** recommended.

## Options to fully clear the `npm audit --audit-level=high` gate

1. **Documented audit exception (recommended, lowest risk).** Allow-list exactly
   `GHSA-qwww-vcr4-c8h2` in the blocking audit steps
   (`.github/workflows/security-baseline.yml`, `deploy.yml`) with a comment
   pointing here, while keeping the gate strict for every other advisory. This
   is standard triage for an advisory that provably does not apply, and is a
   security-policy change that should be made deliberately by the maintainers.
2. **React Router v7 → v8 migration (larger, separate effort).** Migrate all
   `from "react-router-dom"` imports to `from "react-router"`, adopt
   `react-router@8.3.0`, and validate the entire app's routing (a major-version
   change across ~100+ files of the frozen frontend). Recommended only as a
   planned, separately-validated upgrade — not as part of a dependency-hygiene
   patch.
3. **Downgrade to `react-router-dom@7.11.0`.** Clears the gate but is regressive
   and reintroduces older bugs. **Not recommended.**

## Recommendation

Land the postcss + react-router-dom 7.18.2 bumps now (real, validated risk
reduction), then adopt **Option 1** (documented allow-list of
`GHSA-qwww-vcr4-c8h2`) unless/until a react-router v8 migration is scheduled.
Re-evaluate when a `react-router-dom` 8.x (or a backported 7.x patch) ships.
