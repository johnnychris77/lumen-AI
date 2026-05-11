# Public Demo Link Switch + Hosted Dashboard Go-Live Checklist

## Before Go-Live

- [ ] Hosted backend URL is available.
- [ ] /api/health returns OK.
- [ ] /api/production-readiness/config works.
- [ ] Demo seed script has been run against the hosted backend.
- [ ] Hosted dashboard opens in browser.
- [ ] RBAC viewer write returns 403.
- [ ] Public landing page is ready.
- [ ] GitHub Pages workflow is enabled.

## Switch Links

HOSTED_BASE_URL=https://your-real-hosted-api-url scripts/public-demo-go-live.sh

## Rollback

scripts/public-demo-rollback-local.sh
