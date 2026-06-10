# LumenAI Evidence Bundle Security Checklist v1

## Status

Ready for implementation tracking.

## Authentication

- [ ] Evidence generation requires authenticated identity
- [ ] Evidence download requires authenticated identity
- [ ] Evidence verification for restricted bundles requires authenticated identity
- [ ] Public users cannot access real evidence bundles

## Authorization

- [ ] Customer Admin can access own-tenant evidence
- [ ] Auditor has read-only evidence access
- [ ] Quality Manager has scoped evidence access
- [ ] Vendor User only sees explicitly shared vendor evidence
- [ ] Public Viewer denied real evidence access
- [ ] Demo Reviewer denied real evidence access

## Tenant Isolation

- [ ] Evidence bundle has tenant ID
- [ ] Evidence manifest is tenant-scoped
- [ ] Evidence export is tenant-scoped
- [ ] Tenant A cannot access Tenant B evidence
- [ ] Object ID enumeration does not expose evidence

## Audit Logging

- [ ] Evidence generation creates audit event
- [ ] Evidence download creates audit event
- [ ] Evidence verification creates audit event where appropriate
- [ ] Unauthorized evidence access creates denial event or security log

## Tamper Evidence

- [ ] Manifest hash exists
- [ ] Export hash exists
- [ ] Audit chain verification exists
- [ ] Manifest alteration is detected
- [ ] Evidence content alteration is detected

## Public Safety

- [ ] Public dashboard does not call protected evidence endpoints
- [ ] Public module status uses `/api/public/module-status/evidence`
- [ ] Public verification summary exposes no tenant data
- [ ] Public pages expose no evidence contents

## Final Goal

Evidence bundle workflows are protected, tenant-scoped, audit-logged, tamper-evident, and safe for enterprise review.
