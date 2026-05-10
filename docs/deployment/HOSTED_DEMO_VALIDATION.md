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

Set these only after you have a real hosted backend URL:

export HOSTED_BASE_URL=https://your-real-hosted-api-url
export TOKEN=your-demo-token

## Seed Hosted Demo

scripts/seed-hosted-demo.sh

## Validate Hosted Demo

scripts/check-hosted-demo.sh

Expected final output:

HOSTED DEMO VALIDATION COMPLETE

## Update Public Landing Page Links

After the backend is hosted, update the public demo links:

HOSTED_BASE_URL=https://your-real-hosted-api-url scripts/update-public-demo-links.sh

## Local Validation Instead

For local testing, use:

HOSTED_BASE_URL=http://127.0.0.1:18011 TOKEN=dev-token scripts/check-hosted-demo.sh

## Validation Checklist

- [ ] /api/health returns OK
- [ ] /api/production-readiness/config works
- [ ] Demo seed completes
- [ ] Dashboard summary shows non-zero tenant data
- [ ] RBAC viewer write returns 403
- [ ] Executive dashboard opens publicly
- [ ] Landing page links point to hosted dashboard
