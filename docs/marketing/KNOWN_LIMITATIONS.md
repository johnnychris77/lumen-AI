# Marketing Website — Known Limitations

**Date:** 2026-08-02

1. **JS test runner — RESOLVED.** vitest is now a dev dependency with
   `npm --prefix frontend test` (`vitest run`). The existing pure-logic tests run
   green (13 passing across `contact.test.ts` + `workflowDemo.test.ts`).
   *Remaining:* no component/DOM tests yet (would need jsdom + testing-library);
   pure-logic coverage only.
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
