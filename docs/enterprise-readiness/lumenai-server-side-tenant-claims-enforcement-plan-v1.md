# LumenAI Server-Side Tenant Claims Enforcement Plan v1

## Status

Ready for engineering implementation.

## Purpose

This document defines the server-side tenant claims enforcement plan for LumenAI.

The goal is to ensure tenant identity is trusted only when it comes from verified authentication claims, not from frontend headers, query parameters, or user-controlled request fields.

## Security Objective

Production LumenAI must enforce tenant boundaries using server-side tenant context derived from verified JWT claims.

Protected enterprise data must never be authorized only by:

- frontend-provided tenant headers
- request body tenant IDs
- query string tenant IDs
- route tenant IDs without ownership validation
- simulated development identity in production

## Core Rule

The authenticated tenant claim is the source of truth.

All protected resource access must verify:

- authenticated principal exists
- principal has a tenant ID
- requested resource belongs to principal tenant
- role permits the requested action
- cross-tenant access is denied or hidden with safe error handling

## Required Tenant Claim

JWT must include:

- `tenant_id`

Optional future claims:

- `tenant_name`
- `tenant_type`
- `tenant_scope`
- `vendor_id`
- `facility_ids`
- `market_ids`

## Protected Tenant-Scoped Resources

Tenant enforcement must apply to:

- CAPA records
- audit events
- evidence bundles
- vendor governance records
- inspection records
- dashboard analytics
- quality events
- users and roles
- facility data
- market data

## Public Exceptions

Public-safe endpoints may remain tenantless:

- `/api/health`
- `/api/public/module-status/vendor`
- `/api/public/module-status/capa`
- `/api/public/module-status/audit`
- `/api/public/module-status/evidence`
- `/api/public/module-status/all`

## Required Backend Controls

## 1. Principal Tenant Validation

Every authenticated principal must include a tenant ID.

If tenant ID is missing:

- return `401` or `403`
- do not expose internal details
- log the event server-side

## 2. Resource Tenant Ownership Check

Before returning protected data, verify:

- resource exists
- resource tenant ID matches principal tenant ID
- user role allows access

## 3. Cross-Tenant Safe Failure

For cross-tenant access:

- prefer `404` where revealing object existence is sensitive
- use `403` where access denial is safe to reveal
- never return tenant details from another tenant

## 4. Tenant Context Dependency

Add reusable backend helpers:

- `require_tenant_context`
- `assert_same_tenant`
- `tenant_filter`
- `get_principal_tenant_id`

## 5. Query Filtering

Database queries should filter by server-side tenant ID.

Example rule:

```text
WHERE tenant_id = principal.tenant_id
