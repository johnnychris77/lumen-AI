# Marketing Website — Security Review

**Date:** 2026-08-02 • Scope: public marketing site + contact endpoint.

## Findings
| # | Finding | Severity | File | Status |
|---|---|---|---|---|
| 1 | Secrets in source or build | — | — | **PASS** — none found in source or `dist-site/` (scanned for postgres/redis/AWS/JWT/private-key; none). |
| 2 | Contact endpoint open-relay risk | — | `services/contact-endpoint/server.mjs` | **PASS** — fixed destination via `CONTACT_FORWARD_WEBHOOK` env only; submitter cannot choose recipient; CORS locked to `CONTACT_ALLOWED_ORIGIN`; honeypot; per-IP rate limit; 16 KB body cap; validated fields; **no PII in logs**. |
| 3 | False "delivered" when unconfigured | — | `server.mjs` | **PASS** — returns `501` when `CONTACT_FORWARD_WEBHOOK` unset; UI stays in mock mode. |
| 4 | Demo → production data isolation | — | marketing bundle | **PASS** — standalone build is 100% static synthetic content; no app API, no auth, no DB; `publicDir:false` prevents app demo pages leaking onto the domain. |
| 5 | Server-only vars in client bundle | — | build output | **PASS** — only `VITE_*` reach the client; scan shows no baked `VITE_` values or secrets. |
| 6 | Source maps exposed | — | `dist-site/` | **PASS** — no `.map` files shipped. |
| 7 | External-link safety (`rel`) | Low | marketing components | **REVIEW** — verify any `target="_blank"` links carry `rel="noopener noreferrer"`. No user-generated external links are rendered. |

## Security headers — DECLARED (verify live)
`deploy/render/marketing.yaml` sets on the static site: `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`,
`Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`.
**Not yet configured:** `Content-Security-Policy`, `Permissions-Policy`,
`Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy`.

**Required follow-up (owner: deploy):**
`curl -I https://lumenai-opsbridgesolution-com.onrender.com` to confirm the four
declared headers are present on the live response, and decide on adding CSP +
Permissions-Policy (a static SPA can adopt a reasonably strict CSP).
