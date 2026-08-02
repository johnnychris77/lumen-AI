# Marketing Website — Known Limitations

**Date:** 2026-08-02

1. **No JS test runner configured.** `frontend/` has `*.test.ts` files
   (`contact.test.ts`, `workflowDemo.test.ts`) but no vitest/jest and no `test`
   script, so they cannot execute. Adding a runner was deferred to respect the
   "don't add dependencies unless needed / frozen architecture" constraint.
   *Follow-up:* add vitest as a dev dependency + `"test": "vitest run"` in a
   dedicated tooling change.
2. **Automated a11y/perf not scored.** axe, Lighthouse, and Playwright were not run;
   accessibility and performance findings are code-level only.
3. **Live security headers unverified.** Headers are declared in the Render blueprint
   but not confirmed via `curl -I` against production; CSP/Permissions-Policy not yet set.
4. **Contact form is in mock/501 mode** until `CONTACT_FORWARD_WEBHOOK` (contact service)
   and `VITE_CONTACT_ENDPOINT` (static site) are set in the Render dashboard.
5. **Custom domain not yet live.** Serving on `*.onrender.com`; `lumenai.opsbridgesolution.com`
   requires the GoDaddy `lumenai` CNAME → Render.
6. **Privacy policy** is not present as final legal text; any published policy must be
   a clearly-labelled placeholder pending legal review.
7. **Pre-existing app-wide `tsc` errors** (`AIAssuranceCenter.tsx`, `AgentRegistryCenter.tsx`)
   are outside marketing scope and unchanged by this pass.
