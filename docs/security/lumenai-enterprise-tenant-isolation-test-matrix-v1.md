# LumenAI Enterprise Tenant Isolation Test Matrix v1

## Status

Ready for engineering implementation.

## Purpose

This document defines the tenant-isolation test matrix for LumenAI enterprise workflows. It expands tenant isolation beyond public endpoint leakage prevention and defines how CAPA, audit, vendor governance, evidence bundle, inspection, and dashboard endpoints should be tested for cross-tenant access prevention.

## Security Objective

A user from Tenant A must not be able to read, update, export, or infer Tenant B data by changing:

- `X-Tenant-Id`
- object IDs
- query parameters
- route parameters
- frontend state
- role headers
- request body tenant fields

## Enterprise Test Areas

## 1. CAPA Workflow

### Required Tests

- Tenant A cannot list Tenant B CAPA records.
- Tenant A cannot read Tenant B CAPA detail by ID.
- Tenant A cannot update Tenant B CAPA record.
- Tenant A cannot close Tenant B CAPA record.
- Tenant A cannot add notes to Tenant B CAPA record.
- Tenant A cannot export Tenant B CAPA evidence.

### Expected Result

Cross-tenant access returns:

- `403 Forbidden`

or:

- `404 Not Found`

The response must not reveal the existence of Tenant B records.

## 2. Audit Command Center

### Required Tests

- Tenant A cannot list Tenant B audit events.
- Tenant A cannot query Tenant B audit chain.
- Tenant A cannot verify Tenant B audit chain.
- Tenant A cannot export Tenant B audit logs.
- Tenant A cannot access Tenant B audit evidence.

### Expected Result

Unauthorized cross-tenant access is denied and should be audit logged.

## 3. Vendor Governance

### Required Tests

- Tenant A cannot list Tenant B vendor events.
- Tenant A cannot read Tenant B vendor issue details.
- Vendor User A cannot read Vendor User B assigned issues.
- Vendor User A cannot submit response to Vendor User B issue.
- Tenant A cannot export Tenant B vendor accountability report.

### Expected Result

Vendor and tenant scope must both be enforced.

## 4. Compliance Evidence Bundle

### Required Tests

- Tenant A cannot generate Tenant B evidence bundle.
- Tenant A cannot download Tenant B evidence bundle.
- Tenant A cannot verify Tenant B restricted evidence package unless explicitly authorized.
- Tenant A cannot access Tenant B manifest.
- Tenant A cannot infer Tenant B evidence object IDs.

### Expected Result

Evidence bundle actions require tenant authorization and role authorization.

## 5. Inspection and Quality Records

### Required Tests

- Tenant A cannot list Tenant B inspection records.
- Tenant A cannot read Tenant B inspection detail by ID.
- Tenant A cannot create quality event under Tenant B.
- Tenant A cannot update Tenant B quality finding.
- Tenant A cannot export Tenant B inspection history.

### Expected Result

All inspection and quality data must be tenant-scoped.

## 6. Dashboard Metrics

### Required Tests

- Tenant A dashboard cannot include Tenant B counts.
- Tenant A vendor metrics cannot include Tenant B vendor data.
- Tenant A CAPA metrics cannot include Tenant B CAPA records.
- Tenant A audit metrics cannot include Tenant B audit events.
- Tenant A evidence metrics cannot include Tenant B evidence records.

### Expected Result

Aggregates must be tenant-scoped and must not leak cross-tenant counts.

## 7. Public Endpoints

### Required Tests

Public endpoints must not expose tenant-specific data.

Public endpoint examples:

- `/api/public/module-status/vendor`
- `/api/public/module-status/capa`
- `/api/public/module-status/audit`
- `/api/public/module-status/evidence`
- `/api/public/module-status/all`

Expected public response:

- High-level module readiness only
- No tenant fields
- No object IDs
- No customer data
- No CAPA data
- No audit event contents
- No evidence records

## 8. Header Tampering

### Required Tests

A user must not gain access by changing:

- `X-Tenant-Id`
- `X-Tenant-Name`
- `X-LumenAI-Role`
- `X-LumenAI-Actor`

### Expected Result

In production, backend authorization must be based on authenticated claims, not trusted frontend headers.

## 9. Object ID Enumeration

### Required Tests

- Request valid Tenant B object ID from Tenant A context.
- Request sequential object IDs.
- Request random UUIDs.
- Request known evidence bundle ID from wrong tenant.
- Request known CAPA ID from wrong tenant.

### Expected Result

No unauthorized object should be returned.

## 10. Audit Logging of Denials

### Required Tests

Cross-tenant denial should create or prepare for audit records showing:

- attempted actor
- attempted tenant
- target resource
- denial reason
- timestamp
- request ID

### Expected Result

Denied access attempts are traceable without exposing restricted data to the caller.

## Recommended Test Naming

- `test_capa_cross_tenant_read_denied`
- `test_capa_cross_tenant_update_denied`
- `test_audit_cross_tenant_export_denied`
- `test_vendor_cross_vendor_access_denied`
- `test_evidence_cross_tenant_download_denied`
- `test_inspection_cross_tenant_read_denied`
- `test_dashboard_metrics_are_tenant_scoped`
- `test_public_module_status_has_no_tenant_data`
- `test_tenant_header_tampering_does_not_grant_access`
- `test_cross_tenant_denial_is_audit_logged`

## Acceptance Criteria

Tenant isolation is enterprise-ready when:

- All cross-tenant read tests pass.
- All cross-tenant write tests pass.
- All cross-tenant export tests pass.
- Public endpoints expose no tenant data.
- Tenant context is server-validated.
- Role headers are not trusted in production.
- Cross-tenant attempts are denied.
- Denials are audit-loggable.

## Final Statement

This test matrix defines the engineering path to prove tenant isolation across LumenAI’s CAPA, audit, vendor governance, evidence bundle, inspection, dashboard, and public module status workflows.
