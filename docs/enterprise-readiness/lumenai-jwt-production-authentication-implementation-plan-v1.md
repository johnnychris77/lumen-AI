# LumenAI JWT Production Authentication Implementation Plan v1

## Status

Ready for engineering implementation.

## Purpose

This document defines the JWT production authentication implementation plan for LumenAI.

The goal is to move LumenAI from development authentication toward production-grade enterprise authentication based on verified identity, signed tokens, role claims, tenant claims, and server-side authorization enforcement.

## Security Objective

Production LumenAI must authenticate users through signed JWTs and must not rely on:

- development credentials
- simulated role headers
- simulated actor headers
- frontend-provided tenant identity
- unauthenticated access to protected enterprise workflows

## Authentication Standard

Production authentication should use:

- signed JWT access tokens
- server-side token verification
- issuer validation
- audience validation
- expiration validation
- role claim extraction
- tenant claim extraction
- subject/user ID claim extraction
- request-scoped authenticated principal

## Required JWT Claims

Minimum recommended claims:

- `sub`: authenticated user ID
- `email`: user email where available
- `tenant_id`: tenant identifier
- `roles`: user roles
- `iss`: token issuer
- `aud`: intended audience
- `exp`: expiration timestamp
- `iat`: issued-at timestamp

## Supported Roles

Initial role claims should align with the RBAC matrix:

- `system_admin`
- `customer_admin`
- `quality_manager`
- `auditor`
- `vendor_user`
- `demo_reviewer`
- `public_viewer`

## Protected Workflows

JWT authentication must protect:

- CAPA records
- audit event contents
- evidence bundle generation
- evidence bundle download
- vendor governance records
- inspection records
- tenant dashboard data
- user and role management
- enterprise configuration

## Public Exceptions

The following may remain unauthenticated because they expose only public-safe metadata:

- `/api/health`
- `/api/public/module-status/vendor`
- `/api/public/module-status/capa`
- `/api/public/module-status/audit`
- `/api/public/module-status/evidence`
- `/api/public/module-status/all`

## Implementation Phases

## Phase 1: Auth Configuration

Add production authentication configuration:

- `AUTH_MODE=production`
- `JWT_ISSUER`
- `JWT_AUDIENCE`
- `JWT_ALGORITHM`
- `JWT_PUBLIC_KEY` or `JWT_SECRET`
- `ENABLE_DEV_AUTH=false`

Development mode may continue using development authentication for local testing only.

## Phase 2: JWT Verification Helper

Create backend helper to:

- read `Authorization: Bearer <token>`
- reject missing token
- verify signature
- validate issuer
- validate audience
- validate expiration
- parse claims
- normalize authenticated principal

## Phase 3: Authenticated Principal Model

Create a request-scoped principal with:

- user ID
- email
- tenant ID
- roles
- auth mode
- raw claims where safe
- request ID

## Phase 4: Dependency Injection

Add FastAPI dependencies:

- `get_current_principal`
- `require_authenticated_user`
- `require_role`
- `require_any_role`
- `require_tenant_context`

## Phase 5: Protected Endpoint Enforcement

Apply authentication dependencies to protected enterprise routers.

Priority order:

1. Evidence bundle endpoints
2. Audit command center endpoints
3. CAPA endpoints
4. Vendor governance endpoints
5. Inspection endpoints
6. Tenant dashboard endpoints
7. User and role management endpoints

## Phase 6: Tests

Add tests for:

- missing JWT rejected
- malformed JWT rejected
- expired JWT rejected
- wrong issuer rejected
- wrong audience rejected
- valid JWT accepted
- role claim extracted
- tenant claim extracted
- protected endpoint requires JWT
- public endpoint remains public

## Acceptance Criteria

JWT production authentication is ready when:

- Production mode rejects development credentials.
- Protected enterprise routes require JWT authentication.
- Missing tokens return safe `401` responses.
- Invalid tokens return safe `401` responses.
- Valid JWT creates a trusted server-side principal.
- Tenant ID is extracted from verified claims.
- Roles are extracted from verified claims.
- Public-safe endpoints remain public.
- Tests validate all major authentication cases.

## Security Notes

JWT authentication alone is not sufficient for enterprise readiness.

It must be followed by:

- server-side tenant claims enforcement
- object-level authorization
- role-based authorization
- evidence bundle authorization enforcement
- audit logging for sensitive access
- production secret management

## Final Statement

JWT Production Authentication Implementation Plan v1 establishes the next engineering step for moving LumenAI from public-demo readiness toward enterprise-production readiness.
