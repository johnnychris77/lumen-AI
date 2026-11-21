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

## Decision (implemented)

**Option 1 adopted.** The blocking `npm audit --audit-level=high` step in
`.github/workflows/security-baseline.yml` now runs
`frontend/scripts/audit-allowlist.mjs`, which fails on any high/critical
advisory **except** the explicitly triaged `GHSA-qwww-vcr4-c8h2`, keeping the
gate strict for every other advisory (including any newly-published one). This
mirrors the repo's existing documented-exception pattern
(`pip-audit --ignore-vuln PYSEC-2022-42969` in `deploy.yml`).

The allow-list lives in one place (`audit-allowlist.mjs`) with the justification
inline. **Remove the entry** and let the strict gate reassert itself once a
`react-router-dom` 8.x (or a backported 7.x patch) ships, or once a react-router
v7→v8 migration lands. Until then this advisory is an accepted, documented risk
because the vulnerable RSC/server mode is not used by this client SPA.

---

## 2026-11-18 — `GHSA-fc5q-39xc-vjpf` (picomatch ReDoS, CVE-2026-112366)

**Trigger:** `frontend-security-and-build` began failing on every branch after
this advisory was published (19 Oct 2026, last updated 17 Nov 2026). The
lockfile did not change; the same workflow passed on `main` on 12 Nov.

**Advisory:** High (CVSS 3.1 7.5, availability only), CWE-1333. A glob pattern
made of a repeated single-branch extglob, such as `+(*a)` or `+(*)`, compiles to
a regular expression that backtracks exponentially on a short input.

### Why this is not an upgrade

| Option | Finding |
|---|---|
| Upgrade `picomatch` | **No patched version exists.** The advisory range is `<=4.0.7` and 4.0.7 is the latest release. The advisory lists no patched version. |
| Upgrade `vite` | Installed 8.3.7; latest 8.3.8 and 8.4.0-beta.1 both depend on `picomatch ^4.0.7`. |
| `npm audit fix --force` (downgrade to `vite@6.2.7`) | Rejected. Vite 6.2.7 declares no `picomatch` dependency because it **bundles picomatch inside its own `dist`**. The downgrade would hide the code from the audit, not remove it, and would move the build two major versions backwards. |

### Reachability in this application

Checked on 18 Nov 2026 against the committed lockfile:

- **Reproduced locally.** With the installed 4.0.7, `picomatch("+(*a)")` takes
  about 2.7 s on a 27-character input and `picomatch("+(*)")` about 8.8 s. The
  advisory is real for an attacker-chosen pattern.
- **The attacker must control the pattern.** The patterns Vite uses by default
  (for example `**/.git/**`, `*.{crt,pem}`) match a 5000-character input in
  under 2 ms.
- **picomatch is build tooling only.** `npm ls picomatch` shows it only under
  `vite`, `tinyglobby` and `fdir`. A fresh `npm run build` output contains no
  picomatch code.
- **Production does not run Vite.** `render.yaml` publishes the static
  `frontend/dist`, and all three frontend Dockerfiles copy `dist` into an nginx
  image.
- **No pattern in this repository uses extglob syntax.** `vite.config.ts` and
  `vite.marketing.config.ts` define none, and `src/` does not use
  `import.meta.glob`.

So no untrusted party can supply a pattern. The remaining exposure is a
developer or CI job building a repository whose own config contains a hostile
pattern, which already implies code execution in that build.

Note: `npm audit --omit=dev` still reports the advisory, because
`@vitejs/plugin-react` and `@tailwindcss/vite` are listed under `dependencies`
in `package.json`. That is a packaging detail of how the build is installed, not
evidence that picomatch ships to users.

### Decision

A **conditional** exception for exactly `GHSA-fc5q-39xc-vjpf` in
`frontend/scripts/audit-allowlist.mjs`. Unlike the react-router entry it lapses
by itself (`frontend/scripts/audit-policy.mjs`, tested in
`frontend/tests/auditPolicy.test.mts`):

- **When a fix ships.** As soon as `npm audit` reports a non-breaking fix for
  `picomatch`, the entry stops applying and the gate fails until the dependency
  is upgraded.
- **On the review date, 18 Dec 2026.** After that day the gate fails until the
  entry is re-triaged, whether or not a fix exists.

The gate stays strict for every other advisory. This is a security-policy
change and should be confirmed by a maintainer who did not write it.
