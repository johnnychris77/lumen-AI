# LumenAI Public Module Status API Design v1

## Status

Design ready for engineering implementation.

## Purpose

This document defines the public-safe module status API design for LumenAI.

The goal is to remove dev-token and protected enterprise endpoint dependency from the deployed public dashboard while preserving a user-friendly, investor-ready, and security-conscious public demo experience.

## Problem

The current public dashboard can show module reachability, but it may rely on demo headers or protected enterprise endpoints such as:

- CAPA workflow endpoints
- Audit command center endpoints
- Compliance evidence endpoints
- Vendor governance endpoints

This creates unnecessary risk because public pages should not call protected enterprise workflows directly.

## Engineering Goal

Create public-safe module status endpoints that return only high-level module readiness.

The public dashboard should call these public endpoints instead of protected enterprise endpoints.

## Target Public Endpoints

- `/api/public/module-status/vendor`
- `/api/public/module-status/capa`
- `/api/public/module-status/audit`
- `/api/public/module-status/evidence`
- `/api/public/module-status/all`

## Security Principle

Public status endpoints must be safe by design.

They must not expose:

- PHI
- tenant records
- CAPA records
- audit event contents
- evidence bundle contents
- vendor issue details
- internal stack traces
- secrets
- raw backend validation errors
- object IDs
- customer names
- user names

They may expose:

- module name
- module availability
- public status
- safe description
- whether enterprise authentication is required
- timestamp of public status response

## Recommended Response Shape

```json
{
  "module": "Compliance Evidence",
  "status": "available",
  "public_status": "protected",
  "requires_authentication": true,
  "description": "Compliance evidence workflows are available for authenticated enterprise users.",
  "checked_at": "2026-06-10T00:00:00Z"
}
