# LumenAI Production Auth Readiness Plan

## Purpose

This document defines the migration path from LumenAI's current MVP/demo authentication model to a production-ready enterprise authentication and authorization architecture.

The current implementation uses:

- Authorization: Bearer dev-token
- X-LumenAI-Role
- X-LumenAI-Actor
- X-LumenAI-Tenant-ID

This is acceptable for local demos and controlled MVP testing, but it is not production-grade because client-provided headers can be spoofed.

The production target is OIDC/JWT-based authentication with role, tenant, and permission claims validated server-side.

## Current State

LumenAI currently centralizes MVP enterprise authorization in:

backend/app/enterprise_auth.py

Current helpers support:

- Development token validation
- Actor extraction
- Role extraction
- Hospital admin / enterprise admin enforcement
- Vendor role enforcement

## Production Target

Production authentication should use OpenID Connect and JWT validation.

Recommended providers:

- Azure Entra ID
- Okta
- Auth0
- AWS Cognito
- Google Workspace Identity
- Hospital enterprise SSO through OIDC/SAML bridge

## Required JWT Claims

| Claim | Purpose |
|---|---|
| sub | Stable user identity |
| email | User email / actor identity |
| iss | Token issuer |
| aud | Token audience |
| exp | Expiration |
| iat | Issued-at time |
| roles or groups | Role mapping |
| tenant_id | Tenant boundary enforcement |

## Migration Plan

| Milestone | Description |
|---|---|
| 53 | Add Auth Context Object |
| 54 | Add Dev/OIDC Auth Mode Switch |
| 55 | Add JWT Validation Service |
| 56 | Add Permission-Based Authorization |
| 57 | Add Tenant Claim and Membership Enforcement |
| 58 | Add OIDC/JWT Regression Tests |
| 59 | Add Production Auth Deployment Guide |

## Security Requirements

Production JWT validation must check:

- Signature
- Expiration
- Issuer
- Audience
- Algorithm allowlist
- Required claims
- JWKS key rotation

Production must not accept:

- Unsigned JWTs
- alg=none
- Client-provided role headers
- Client-provided tenant overrides
- Expired tokens
- Wrong issuer or audience

## Enterprise Positioning

This migration gives LumenAI a clear enterprise security roadmap:

- MVP access control is centralized and tested.
- Production roadmap moves to OIDC/JWT.
- Tenant isolation is tested.
- Governance evidence is access-controlled.
- Audit actions are centralized and tamper-evident.
- Compliance evidence is mapped in the control matrix.
