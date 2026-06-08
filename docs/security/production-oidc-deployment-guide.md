# LumenAI Production OIDC/JWT Deployment Guide

## Purpose

This guide describes how to deploy LumenAI with production-grade OIDC/JWT authentication.

LumenAI supports:

- AUTH_MODE=dev for local demos and MVP testing
- AUTH_MODE=oidc for production-style JWT claim validation

Production identity should use signed JWTs from an enterprise identity provider and map verified claims into the LumenAI AuthContext.

## Supported Identity Providers

- Azure Entra ID
- Okta
- Auth0
- AWS Cognito
- Google Workspace Identity
- Hospital enterprise SSO through OIDC/SAML bridge

## Required Environment Variables

Production:

AUTH_MODE=oidc
OIDC_ISSUER_URL=https://issuer.example.com/
OIDC_AUDIENCE=lumenai-api
OIDC_JWKS_URL=https://issuer.example.com/.well-known/jwks.json
OIDC_ALGORITHMS=RS256
AUTH_REQUIRE_HTTPS=true

Development:

AUTH_MODE=dev
DEV_AUTH_TOKEN=dev-token

Production systems must not run with AUTH_MODE=dev.

## Required JWT Claims

| Claim | Purpose |
|---|---|
| sub | Stable user identity |
| email | Actor identity for audit and display |
| iss | Issuer validation |
| aud | API audience validation |
| exp | Expiration validation |
| iat | Issued-at validation |
| roles or groups | Role mapping |
| tenant_id or lumenai_tenant_id | Tenant boundary enforcement |

## Auth Context Mapping

After token validation, LumenAI normalizes identity into:

- actor
- subject
- role
- tenant_id
- tenant_name
- permissions
- auth_provider
- issuer

Routes should use normalized AuthContext instead of raw client headers.

## Security Requirements

Production OIDC/JWT validation must check:

- Token signature
- Issuer
- Audience
- Expiration
- Issued-at time
- Algorithm allowlist
- Required claims
- JWKS key rotation
- HTTPS-only token transport

Production must reject:

- Unsigned JWTs
- alg=none
- Expired tokens
- Wrong issuer
- Wrong audience
- Missing required claims
- Client-provided role overrides
- Client-provided tenant overrides

## Tenant Enforcement

Tenant identity must come from verified claims or server-side membership lookup.

Rules:

1. Client headers cannot override verified tenant claims.
2. User must have an enabled tenant membership.
3. Cross-tenant access must be denied.
4. Disabled memberships must be denied.
5. Tenant ID must be written to audit events.

## Deployment Checklist

- [ ] AUTH_MODE=oidc
- [ ] DEV_AUTH_TOKEN not used in production
- [ ] JWT signature validation enabled
- [ ] JWKS URL configured
- [ ] Issuer configured
- [ ] Audience configured
- [ ] Algorithm allowlist configured
- [ ] Role/group mapping verified
- [ ] Tenant claim verified
- [ ] Tenant membership enforcement enabled
- [ ] Protected route regression tests passing
- [ ] CI security checks passing
- [ ] Audit chain verification passing
- [ ] TLS/HTTPS enforced

## Current Gap Before Production

Current OIDC mode validates decoded claims but does not yet verify JWT signatures against JWKS.

The next security hardening milestone should add JWKS-backed signature validation.
