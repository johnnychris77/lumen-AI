# LumenAI Object-Level Authorization Enforcement Plan v1

## Status

Ready for engineering implementation.

## Purpose

This document defines the object-level authorization enforcement plan for LumenAI.

The goal is to ensure that authenticated users can only access specific records they are authorized to access, even when they are authenticated and belong to the correct tenant.

## Security Objective

LumenAI must enforce authorization at the individual object level for protected enterprise resources.

Authentication alone is not enough.

Tenant match alone is not enough.

Every protected object access must validate:

- authenticated principal
- tenant ownership
- role permission
- workflow permission
- resource ownership or assignment where applicable

## Protected Objects

Object-level authorization must apply to:

- CAPA records
- audit events
- evidence bundles
- evidence manifests
- vendor issue records
- inspection records
- quality events
- instrument baseline records
- facility records
- market records
- user-role records

## Core Authorization Rule

A protected object may only be returned when:

1. The user is authenticated.
2. The user has a verified tenant claim.
3. The object belongs to the user’s tenant.
4. The user role permits the requested action.
5. The user is assigned to or permitted for the workflow scope when applicable.

## Role-Based Object Rules

## System Admin

Allowed:

- platform support access where explicitly permitted
- system-level administration

Requires:

- audit logging
- no silent cross-tenant access

## Customer Admin

Allowed:

- tenant-wide access to authorized customer records
- CAPA, audit, vendor, inspection, and evidence records within own tenant

Denied:

- other tenants
- system-level data without explicit authorization

## Quality Manager

Allowed:

- quality records within assigned tenant or facility scope
- CAPA and inspection records where assigned or permitted

Denied:

- unrelated tenant records
- unrestricted user administration
- system-level configuration

## Auditor

Allowed:

- read-only access to approved audit and evidence records

Denied:

- object modification
- deletion
- unrestricted tenant administration

## Vendor User

Allowed:

- vendor-specific records explicitly assigned to that vendor

Denied:

- other vendor records
- internal audit records
- tenant-wide evidence bundles
- unassigned CAPA records

## Required Backend Helpers

Recommended helper functions:

- `assert_same_tenant(resource_tenant_id, principal)`
- `require_object_permission(principal, resource, action)`
- `require_vendor_assignment(principal, resource_vendor_id)`
- `require_read_only_role(principal)`
- `hide_cross_tenant_resource()`

## Safe Failure Rules

Use safe responses:

- `404 Not Found` when revealing object existence is sensitive
- `403 Access Denied` when the user may safely know the object exists but lacks permission
- never return object details on failed authorization

## Required Tests

Add tests for:

- Tenant A cannot access Tenant B object
- Customer Admin can access own tenant object
- Quality Manager cannot access unassigned object
- Auditor cannot modify object
- Vendor User cannot access other vendor object
- missing tenant object returns safe 404
- cross-tenant object ID enumeration does not leak data
- authorized object access succeeds

## Acceptance Criteria

Object-level authorization is ready when:

- Protected object helpers exist.
- Cross-tenant object access is blocked.
- Role-based object actions are enforced.
- Vendor users are restricted to assigned records.
- Auditors are read-only.
- Failed access does not expose protected object details.
- Tests prove object-level authorization behavior.

## Final Statement

Object-Level Authorization Enforcement Plan v1 defines the next enterprise-readiness control after JWT authentication and server-side tenant claim enforcement.
