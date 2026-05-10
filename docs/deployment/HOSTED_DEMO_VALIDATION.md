# Hosted Demo Seed + Public Dashboard Validation

## Purpose

This runbook validates a hosted LumenAI backend after deployment.

It confirms:

- API health
- production readiness
- demo data seeding
- dashboard summary
- public dashboard URL
- RBAC enforcement
- audit/access activity

## Required Inputs

Set:

export HOSTED_BASE_URL=https://your-lumenai-api-url
export TOKEN=your-demo-token

## Seed Hosted Demo

scripts/seed-hosted-demo.sh

This runs the existing demo seed script against the hosted API.

## Validate Hosted Demo

scripts/check-hosted-demo.sh

Expected final output:

HOSTED DEMO VALIDATION COMPLETE

## Update Public Landing Page Links

After the backend is hosted, update the public demo links:

HOSTED_BASE_URL=https://your-lumenai-api-url scripts/update-public-demo-links.sh

Then commit and push.

## Public Dashboard URL

https://your-lumenai-api-url/api/executive-briefing-dashboard/view

## Validation Checklist

- [ ] /api/health returns OK
- [ ] /api/production-readiness/config works
- [ ] Demo seed completes
- [ ] Dashboard summary shows non-zero tenant data
- [ ] RBAC viewer write returns 403
- [ ] Executive dashboard opens publicly
- [ ] Landing page links point to hosted dashboard
