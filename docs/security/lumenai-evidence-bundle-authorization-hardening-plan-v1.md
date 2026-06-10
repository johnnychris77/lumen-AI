# LumenAI Evidence Bundle Authorization Hardening Plan v1

## Status

Ready for engineering implementation.

## Purpose

This document defines the authorization hardening plan for LumenAI evidence bundle workflows.

Evidence bundles are one of the most important enterprise trust features in LumenAI. They must be protected by authentication, role-based authorization, tenant isolation, audit logging, and tamper-evident verification controls.

## Security Objective

Only authorized users should be able to generate, view, verify, or download evidence bundles for their own tenant and permitted workflow scope.

No public user, demo reviewer, unauthorized vendor, or cross-tenant user should be able to access evidence bundle contents.

## Protected Evidence Assets

Evidence bundle authorization must apply to:

- Evidence bundle generation
- Evidence bundle download
- Evidence bundle verification
- Evidence bundle manifest
- Evidence export hash
- Audit chain verification
- CAPA evidence exports
- Vendor governance evidence exports
- Audit command center evidence exports
- Inspection and quality evidence exports

## Risk Summary

Evidence bundle risks include:

- Unauthorized evidence downloads
- Cross-tenant evidence access
- Vendor access to internal evidence
- Public endpoint exposure
- Evidence tampering
- Manifest manipulation
- Audit chain bypass
- Download activity not logged
- Insecure direct object reference by bundle ID
- Overexposure of verification summaries

## Core Authorization Rule

Evidence bundle access must be based on:

- authenticated identity
- server-side tenant context
- server-side role validation
- object-level tenant ownership
- evidence workflow permission
- audit logging of sensitive actions

Frontend headers alone must not authorize evidence access in production.

## Role-Based Evidence Access

## Public Viewer

Allowed:

- View public portfolio pages
- View public-safe module status

Denied:

- Generate evidence bundles
- Download evidence bundles
- View tenant evidence
- View audit chain details
- View CAPA evidence
- View vendor evidence

## Demo Reviewer

Allowed:

- View public demo pages
- View sample-only evidence narrative where no tenant data exists

Denied:

- Download real evidence bundles
- Generate tenant evidence bundles
- View real audit logs
- View CAPA records
- View vendor issue records

## Customer Admin

Allowed:

- Generate tenant evidence bundles
- View tenant verification summaries
- Download authorized tenant evidence bundles
- Request evidence exports for CAPA, vendor, audit, and inspection workflows

Denied:

- Cross-tenant evidence
- Platform-wide evidence unless specifically authorized
- Silent evidence modification

## Quality Manager

Allowed:

- Request evidence for assigned quality workflows
- View evidence summaries for tenant quality records
- View CAPA-related evidence where permitted

Denied:

- Cross-tenant evidence
- System-level evidence
- Unauthorized evidence downloads

## Auditor

Allowed:

- Read-only access to approved evidence bundles
- View verification summaries
- View audit readiness evidence

Denied:

- Modify evidence
- Generate unrestricted evidence
- Delete evidence
- Access other tenants

## Vendor User

Allowed:

- View vendor-specific shared evidence only when explicitly authorized

Denied:

- Internal audit evidence
- Other vendor evidence
- Tenant-wide evidence bundles
- CAPA evidence not assigned to vendor workflow
- Cross-tenant evidence

## System Admin

Allowed:

- Support evidence workflow administration
- Review system evidence generation health
- Assist tenant support under controlled audit logging

Denied:

- Unlogged evidence access
- Silent evidence modification
- Bypassing tenant controls
- Bypassing audit logging

## Required Backend Controls

## 1. Authentication

Every enterprise evidence endpoint must require authenticated identity.

Public evidence endpoints must not expose real evidence data.

## 2. Tenant Validation

Every evidence bundle must be tenant-scoped.

The backend must verify:

- authenticated tenant context
- evidence bundle tenant ID
- requested resource tenant ID
- export tenant ID

## 3. Role Validation

Evidence actions must check role permissions.

Examples:

- Customer Admin: generate and download tenant evidence
- Auditor: read-only access
- Vendor User: only explicitly shared vendor evidence
- Public Viewer: denied

## 4. Object-Level Authorization

Evidence bundle IDs must not be enough to grant access.

Before returning an evidence bundle, the backend must verify:

- bundle exists
- bundle belongs to authenticated tenant
- user role permits access
- user is permitted for the workflow type
- bundle has not been revoked or restricted

## 5. Download Audit Logging

Every evidence bundle download should create an audit event.

Audit event should include:

- actor
- tenant
- role
- evidence bundle ID
- workflow type
- timestamp
- request ID
- download action
- authorization result

## 6. Generation Audit Logging

Every evidence bundle generation should create an audit event.

Audit event should include:

- actor
- tenant
- role
- source workflow
- evidence scope
- manifest hash
- generated timestamp
- request ID

## 7. Verification Audit Logging

Evidence verification should be logged when performed by authenticated enterprise users.

Public verification summaries must expose only safe metadata.

## 8. Tamper-Evident Controls

Evidence bundle integrity should use:

- manifest hash
- export hash
- audit chain hash
- deterministic or canonicalized export structure
- verification endpoint
- immutable audit event references

## 9. Safe Verification Summary

Public-safe verification summaries may include:

- bundle status
- verification status
- public-safe hash presence indicator
- generated timestamp
- no tenant records
- no CAPA details
- no audit event contents
- no patient or user information

## 10. Standard Error Handling

Unauthorized evidence access should return safe errors:

- `403 Forbidden`
- `404 Not Found` where record existence should not be revealed

Do not return:

- stack traces
- database errors
- internal file paths
- raw object IDs from other tenants
- validation internals

## Required Tests

## Evidence Authorization Tests

- Public user cannot generate evidence bundle.
- Public user cannot download evidence bundle.
- Demo reviewer cannot download real evidence bundle.
- Tenant A cannot download Tenant B evidence bundle.
- Tenant A cannot verify restricted Tenant B evidence bundle.
- Vendor User A cannot access Vendor User B evidence.
- Auditor has read-only access only.
- Customer Admin can access own-tenant authorized evidence.
- Evidence bundle ID enumeration does not expose data.
- Unauthorized evidence access returns safe error.
- Evidence download creates audit event.
- Evidence generation creates audit event.
- Evidence manifest hash changes when content changes.
- Evidence verification fails if manifest is altered.

## Recommended Test Names

- `test_public_user_cannot_download_evidence_bundle`
- `test_demo_reviewer_cannot_access_real_evidence_bundle`
- `test_cross_tenant_evidence_download_denied`
- `test_vendor_user_cannot_access_unassigned_evidence`
- `test_auditor_evidence_access_is_read_only`
- `test_customer_admin_can_download_own_tenant_evidence`
- `test_evidence_download_creates_audit_event`
- `test_evidence_generation_creates_audit_event`
- `test_evidence_manifest_hash_detects_tampering`
- `test_evidence_bundle_id_enumeration_denied`

## Implementation Plan

## Phase 1: Documentation and Policy

- Document authorization rules
- Document role permissions
- Document tenant isolation rules
- Document evidence audit logging requirements

## Phase 2: Backend Guardrails

- Add evidence authorization helper
- Add tenant ownership check
- Add role permission check
- Add standardized safe error responses
- Add evidence download audit logging

## Phase 3: Tests

- Add cross-tenant evidence tests
- Add role-based evidence tests
- Add evidence tamper-detection tests
- Add evidence audit logging tests

## Phase 4: Public Dashboard Safety

- Ensure public dashboard does not call enterprise evidence endpoints directly
- Use `/api/public/module-status/evidence`
- Show evidence module as protected, not broken

## Phase 5: Production Readiness

- Confirm production dev auth is disabled
- Confirm evidence endpoints require JWT
- Confirm CORS is locked
- Confirm logs capture evidence access attempts
- Confirm all evidence tests pass in CI

## Acceptance Criteria

Evidence bundle authorization is enterprise-ready when:

- All evidence endpoints require proper authentication.
- All evidence actions enforce role permissions.
- All evidence bundles are tenant-scoped.
- Cross-tenant evidence access is denied.
- Evidence downloads are audit logged.
- Evidence generation is audit logged.
- Evidence verification is tamper-aware.
- Public pages expose no evidence contents.
- Vendor users cannot access unassigned evidence.
- Auditors have read-only access only.
- Tests prove the above controls.

## Investor Confidence Statement

Evidence bundle authorization hardening strengthens LumenAI’s enterprise trust layer by protecting compliance evidence, enforcing tenant boundaries, preserving auditability, and reducing the risk of unauthorized evidence access.

## Final Statement

LumenAI evidence bundles must be treated as high-trust enterprise assets. This plan defines the engineering path to protect them with authentication, authorization, tenant isolation, audit logging, and tamper-evident verification controls.
