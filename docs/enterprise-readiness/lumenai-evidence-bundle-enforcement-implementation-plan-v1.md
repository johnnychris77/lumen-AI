# LumenAI Evidence Bundle Enforcement Implementation Plan v1

## Status

Ready for engineering implementation.

## Purpose

This document defines the implementation plan for enforcing evidence bundle authentication, tenant isolation, object-level authorization, audit logging, and tamper-aware verification in LumenAI.

This builds on:

- JWT production authentication
- Server-side tenant claims enforcement
- Object-level authorization enforcement
- Evidence bundle authorization hardening
- Production error response safety

## Security Objective

Evidence bundles must be treated as high-trust enterprise compliance assets.

Evidence bundle workflows must require:

- authenticated principal
- verified tenant claim
- object-level authorization
- role-based action permission
- audit logging
- tamper-aware manifest verification

## Protected Evidence Actions

This plan applies to:

- evidence bundle generation
- evidence bundle download
- evidence manifest retrieval
- evidence verification summary
- audit chain verification
- evidence export regeneration
- CAPA evidence export
- vendor evidence export
- audit readiness evidence export

## Required Authorization Rules

## Customer Admin

Allowed:

- generate own-tenant evidence bundles
- download own-tenant evidence bundles
- verify own-tenant evidence bundles

Denied:

- cross-tenant evidence
- system evidence unless explicitly permitted

## Quality Manager

Allowed:

- generate and view evidence for assigned quality workflows
- access CAPA, inspection, and quality evidence in own tenant

Denied:

- cross-tenant evidence
- unrelated vendor evidence
- system evidence

## Auditor

Allowed:

- read-only verification and approved evidence review

Denied:

- evidence generation unless explicitly granted
- evidence modification
- evidence deletion

## Vendor User

Allowed:

- view explicitly shared vendor evidence only

Denied:

- tenant-wide evidence bundles
- internal audit evidence
- other vendor evidence
- unassigned CAPA evidence

## System Admin

Allowed:

- support and system operations where explicitly permitted

Requires:

- audit logging
- no silent evidence access

## Enforcement Components

Recommended backend helpers:

- `EvidenceBundle`
- `EvidenceAction`
- `require_evidence_permission`
- `assert_evidence_tenant`
- `create_evidence_audit_event`
- `verify_evidence_manifest_hash`

## Evidence Audit Events

Evidence workflows should log:

- generation
- download
- verification
- failed authorization
- manifest validation failure
- evidence export regeneration

Minimum audit fields:

- actor user ID
- tenant ID
- role
- evidence bundle ID
- action
- workflow type
- authorization result
- timestamp
- request ID

## Tamper-Aware Controls

Evidence bundles should use:

- manifest hash
- export hash
- audit chain hash
- generated timestamp
- immutable event reference
- verification status

## Public-Safe Evidence Policy

Public pages may expose only:

- evidence module status
- public-safe security evidence narrative
- verification availability statement

Public pages must not expose:

- real evidence bundle contents
- tenant records
- CAPA details
- audit events
- vendor records
- patient data
- internal object IDs

## Required Tests

Add tests for:

- public user cannot generate evidence
- public user cannot download evidence
- Customer Admin can download own-tenant evidence
- Tenant A cannot download Tenant B evidence
- Auditor cannot modify evidence
- Vendor User cannot access other vendor evidence
- evidence download creates audit event
- evidence generation creates audit event
- evidence manifest detects tampering
- public verification summary does not leak tenant data

## Acceptance Criteria

Evidence bundle enforcement is ready when:

- evidence actions require authenticated principal
- evidence tenant ownership is enforced
- object-level evidence permission is enforced
- vendor evidence is assignment-scoped
- auditor evidence access is read-only
- evidence generation and download are audit logged
- manifest tampering is detected
- public pages expose no protected evidence contents

## Final Statement

Evidence Bundle Enforcement Implementation Plan v1 defines the next enterprise-production readiness step for securing LumenAI evidence workflows end-to-end.
