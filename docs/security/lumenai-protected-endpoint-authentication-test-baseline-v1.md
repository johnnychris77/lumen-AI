# LumenAI Protected Endpoint Authentication Test Baseline v1

## Status

Ready for engineering implementation.

## Purpose

This document defines the baseline test approach for confirming that protected LumenAI enterprise endpoints require authentication.

This supports the production dev-auth removal plan, RBAC matrix, tenant isolation plan, evidence bundle hardening plan, and production security posture.

## Security Objective

Protected enterprise endpoints must not be accessible anonymously or through public frontend behavior.

## Protected Workflow Areas

Authentication enforcement must apply to:

- CAPA records
- Audit event contents
- Audit chain verification
- Evidence bundle generation
- Evidence bundle download
- Vendor governance records
- Inspection and quality records
- Tenant dashboard metrics
- User and role management
- Enterprise configuration

## Public Exceptions

The following public endpoints may remain unauthenticated because they return safe metadata only:

- `/api/health`
- `/api/public/module-status/vendor`
- `/api/public/module-status/capa`
- `/api/public/module-status/audit`
- `/api/public/module-status/evidence`
- `/api/public/module-status/all`

## Baseline Test Rule

For each protected endpoint:

- Anonymous request should return `401`, `403`, or a safe `404`
- Response must not expose stack traces
- Response must not expose tenant data
- Response must not expose object details
- Response must not expose internal implementation details

## Initial Protected Endpoint Candidates

These endpoints should be reviewed and tested where present:

- `/api/capa`
- `/api/enterprise/audit/events`
- `/api/enterprise/audit/evidence-bundle`
- `/api/enterprise/audit/evidence-bundle/verification-summary`
- `/api/analytics/vendors`
- `/api/history`
- `/api/history/summary`

## Acceptance Criteria

This baseline is complete when:

- Public endpoints return 200 safely.
- Protected endpoints reject anonymous access.
- Error responses are safe.
- No dev-token is required by public pages.
- Protected endpoints are tested in CI or local backend tests.
