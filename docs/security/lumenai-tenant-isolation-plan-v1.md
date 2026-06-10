# LumenAI Tenant Isolation Plan v1

## Status

Ready for engineering implementation.

## Purpose

This document defines the LumenAI tenant isolation approach. Tenant isolation is a core enterprise security requirement because LumenAI may support multiple healthcare organizations, facilities, vendors, and operational teams.

## Security Objective

A user, vendor, auditor, or customer administrator must never be able to access another tenant's data by changing request headers, object IDs, query parameters, or frontend state.

## Protected Tenant-Scoped Resources

Tenant isolation must apply to:

- Audit logs
- CAPA records
- Vendor governance records
- Inspection records
- Quality events
- Evidence bundles
- Evidence exports
- Dashboard metrics
- User-role assignments
- Facility-specific operational data

## Core Rule

Tenant context must be validated server-side.

The backend must not trust frontend-only headers as the source of tenant truth in production.

## Required Controls

1. Authenticated identity must include tenant context.
2. Every tenant-scoped database object must include tenant ID or tenant reference.
3. Queries must filter by authenticated tenant context.
4. Object-level access must verify tenant ownership.
5. Cross-tenant access attempts must return 403.
6. Cross-tenant denial events should be audit logged.
7. Tests must confirm that changing tenant headers cannot bypass isolation.

## Public Endpoint Exception

Public endpoints such as `/api/public/module-status/all` must not return tenant-scoped data. These endpoints are allowed only because they return safe platform-level metadata.

## Test Strategy

Tenant isolation tests should verify:

- Tenant A cannot read Tenant B records.
- Tenant A cannot update Tenant B records.
- Tenant A cannot download Tenant B evidence bundles.
- Vendor A cannot access Vendor B records.
- Auditor access is tenant-scoped.
- Changing `X-Tenant-Id` manually does not grant access.
- Object ID enumeration does not expose data.

## Acceptance Criteria

Tenant isolation is acceptable when:

- Cross-tenant access tests pass.
- Enterprise endpoints enforce tenant context.
- Tenant ID is not trusted from public frontend headers.
- Public endpoints expose no tenant data.
- Denied cross-tenant attempts are logged or ready for audit logging.

## Final Statement

Tenant isolation is required before LumenAI can be described as enterprise-production ready.
