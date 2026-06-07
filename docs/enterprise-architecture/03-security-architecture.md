# LumenAI Security Architecture

## Current Security State

Current MVP workflows use dev-token and header-based role/actor values. These are acceptable for demos but not enterprise production.

## Target Authentication

- OIDC / OAuth provider
- JWT validation
- Issuer validation
- Audience validation
- Token expiry validation
- User identity claims

## Target Authorization

Centralized RBAC / ABAC enforcement.

Roles:
- enterprise_admin
- hospital_admin
- spd_manager
- infection_prevention
- vendor_user
- viewer
- auditor

## Tenant Isolation

Every tenant-owned record should include tenant_id. Tenant enforcement should occur in middleware, repositories, services, and automated tests.

## Audit Logging

Audit logs should capture actor, role, tenant, action, resource, request ID, timestamp, IP when available, compliance flags, and structured details.

## Evidence Packet Security

Governance PDF exports should include actor, role, filename, SHA-256 packet hash, tamper-evident flag, audit trail inclusion flag, and verification endpoint support.

## Required Hardening

- Replace demo token with real auth
- Add centralized authorization dependency
- Add tenant enforcement tests
- Add secrets scanning
- Add dependency vulnerability scanning
- Add rate limiting
- Add request IDs
- Add audit immutability controls
