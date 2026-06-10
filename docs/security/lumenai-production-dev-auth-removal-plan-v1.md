# LumenAI Production Dev Auth Removal Plan v1

## Status

Ready for engineering implementation.

## Purpose

This document defines the plan to remove development authentication dependency from production-facing LumenAI workflows.

The goal is to ensure production access is based on real authentication, server-side authorization, tenant isolation, and audit logging — not development tokens, simulated role headers, or frontend-provided identity.

## Security Objective

Production LumenAI must not rely on:

- `dev-token`
- frontend-provided enterprise admin role headers
- frontend-provided actor identity
- manually trusted tenant headers
- development-only authentication bypasses

## Current Risk

Development authentication is useful for local testing and demo workflows, but it must not be treated as production-grade identity.

Risk areas include:

- public dashboard using dev-token
- demo routes using enterprise admin headers
- backend accepting simulated role headers in production
- tenant headers being trusted without authenticated claims
- evidence, audit, CAPA, and vendor workflows being callable with development credentials

## Production Authentication Standard

Production enterprise access should use:

- JWT authentication
- server-side identity validation
- server-side role validation
- server-side tenant validation
- object-level authorization
- audit logging for protected actions

## Environment Rules

## Development

Allowed:

- `AUTH_MODE=dev`
- `DEV_AUTH_TOKEN=dev-token`
- local Vite frontend
- local test clients
- simulated actors for tests

## Production

Required:

- `AUTH_MODE=production` or equivalent
- `ENABLE_DEV_AUTH=false`
- no `dev-token` access
- no frontend-trusted role headers
- no frontend-trusted actor headers
- no frontend-trusted tenant headers as final authority

## Public Pages

Public pages may access:

- static HTML
- public portfolio pages
- public-safe module status endpoints

Public pages must not use:

- dev-token
- enterprise admin headers
- protected CAPA endpoints
- protected audit endpoints
- protected evidence endpoints
- tenant records

## Protected Enterprise Workflows

The following workflows must require production-grade auth:

- CAPA records
- audit event contents
- evidence bundle generation
- evidence bundle download
- vendor governance records
- inspection records
- tenant dashboard data
- user-role management

## Required Engineering Actions

1. Keep dev auth available only for local development and tests.
2. Confirm production sets `ENABLE_DEV_AUTH=false`.
3. Confirm public dashboard uses `/api/public/module-status/all`.
4. Remove `dev-token` from public frontend code.
5. Remove enterprise admin headers from public frontend code.
6. Add tests to ensure public dashboard does not contain `dev-token`.
7. Add tests to ensure protected endpoints reject unauthenticated access.
8. Document real production auth path.

## Acceptance Criteria

This control is complete when:

- Public dashboard contains no `dev-token`.
- Public dashboard contains no `X-LumenAI-Role`.
- Public dashboard contains no `X-LumenAI-Actor`.
- Public pages call only public-safe endpoints.
- Production env disables dev auth.
- Protected enterprise endpoints require authentication.
- Tests prevent accidental dev-token reintroduction.

## Final Statement

Removing production dependency on development authentication is required for LumenAI to move from public portfolio readiness toward enterprise-production readiness.
