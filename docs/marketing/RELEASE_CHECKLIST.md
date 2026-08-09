# Marketing Website — Release Checklist

**Date:** 2026-08-02 • Legend: ✅ Completed/Verified • ⚙️ Requires configuration •
🔍 Requires external review • ⏸ Deferred • ⛔ Blocking

| Item | Status |
|---|---|
| No secrets in source or build output | ✅ Verified (scanned) |
| Public demo isolated from production data | ✅ Verified (static synthetic; no API/auth/DB) |
| Primary pages build successfully (`build:site`) | ✅ Verified |
| Navigation works; active state distinct from focus | ✅ Completed |
| Workflow accurate + action-oriented wording | ✅ Verified |
| Human-oversight messaging on workflow page | ✅ Completed |
| Demo disclaimer visible + persistent (non-hover) | ✅ Verified |
| Post-workflow CTA present | ✅ Completed |
| Mobile layout uses responsive/relative units | ✅ Completed (device capture 🔍) |
| Keyboard focus visible across nav/menu/CTAs | ✅ Completed |
| Product claims qualified / no unproven certs | ✅ See PRODUCT_CLAIMS_REVIEW.md (🔍 legal/clinical sign-off) |
| No floating widget overlaps content | ✅ Verified (site ships none) |
| Security headers present on live response | ⚙️ Declared in blueprint; verify `curl -I` |
| CSP / Permissions-Policy | ⚙️ Not set — decide + add |
| Contact form live delivery | ⚙️ Set `CONTACT_FORWARD_WEBHOOK` + `VITE_CONTACT_ENDPOINT` |
| Custom domain `lumenai.opsbridgesolution.com` | ⚙️ Add Render custom domain + GoDaddy CNAME |
| Automated a11y (axe/Lighthouse) | 🔍 Not run |
| JS unit test runner | ⏸ Not configured (see KNOWN_LIMITATIONS) |
| Privacy policy (final legal text) | 🔍 Placeholder pending legal |
| Video captions + transcript wired | 🔍 Verify in player |

**No ⛔ blocking items.** Determination: **CONDITIONALLY READY**.
