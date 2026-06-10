# LumenAI Threat Model v1

## Status

Initial enterprise threat model documented.

## Purpose

This threat model identifies LumenAI’s primary assets, actors, trust boundaries, threats, controls, and mitigation roadmap. It supports enterprise-readiness, investor confidence, compliance review, and secure engineering execution.

## Platform Context

LumenAI is a healthcare operations intelligence platform with ERP-style governance for sterile processing, vendor accountability, CAPA workflow, audit readiness, compliance evidence, and executive operational visibility.

The platform includes:

- Public portfolio pages
- Public dashboard route
- Backend API
- Worker service
- Database
- Redis
- Audit logging
- CAPA workflow
- Vendor governance
- Evidence bundle and verification workflows
- Role-based access concepts
- Tenant-aware enterprise workflows

## Primary Assets

- Audit logs
- Audit chain hashes
- Evidence bundles
- Evidence bundle manifests
- Evidence export hashes
- CAPA records
- Vendor governance events
- Inspection and quality records
- Tenant data
- User identity and roles
- Dashboard metrics
- API tokens and secrets
- Deployment configuration
- Public portfolio and demo assets

## Primary Actors

### Public Visitor

Can access:

- Public landing page
- Portfolio index
- Public portfolio pages
- Static public dashboard route

Must not access:

- Tenant data
- CAPA records
- Audit event contents
- Evidence bundle downloads
- Protected enterprise APIs

### Demo Reviewer

Can access:

- Public-safe demo status
- Portfolio review pages
- Demo dashboard indicators

Must not access:

- Real customer data
- Tenant-specific evidence
- Administrative workflows

### Customer Admin

Can access:

- Tenant dashboard
- CAPA workflow
- Vendor governance workflow
- Evidence review workflow
- Tenant-specific reports

### Auditor

Can access:

- Read-only evidence records
- Verification summaries
- Audit readiness documentation

Must not perform:

- Destructive actions
- Administrative configuration changes

### Vendor User

Can access:

- Vendor-specific assigned items
- Vendor response workflows

Must not access:

- Other vendors' records
- Internal-only audit data
- Cross-tenant data

### System Admin

Can access:

- Platform configuration
- Tenant administration
- Security and operational monitoring

## Trust Boundaries

## 1. Public Browser to Static Frontend

Risk:

- Public users can inspect all frontend files.

Control:

- No secrets in frontend
- No dev tokens in public dashboard
- No protected data embedded in static pages

## 2. Public Frontend to Backend API

Risk:

- Public pages may call protected endpoints or reveal implementation details.

Control:

- Public pages should call only public-safe endpoints
- Protected endpoints require real authentication
- Public endpoint responses must not expose sensitive data

## 3. Authenticated User to Enterprise API

Risk:

- Broken access control
- Role escalation
- Unauthorized tenant access

Control:

- JWT-based identity
- Server-side RBAC
- Server-side tenant validation
- Object-level authorization

## 4. API to Database

Risk:

- Unauthorized data access
- Cross-tenant data leakage
- SQL injection

Control:

- Parameterized database access
- Tenant-scoped queries
- Authorization checks before database reads and writes

## 5. API to Evidence Bundle Export

Risk:

- Unauthorized evidence downloads
- Evidence tampering
- Incomplete audit trace

Control:

- Authorized export generation
- Hash-backed manifests
- Audit log record of export generation
- Tenant-scoped evidence bundles

## 6. Deployment Configuration to Production Services

Risk:

- Render configuration drift
- Manual changes not reflected in Git
- Incorrect CORS or environment variable settings

Control:

- Infrastructure-as-code through `render.yaml`
- Deployment verification checklist
- Documented production environment variables

## Threat Categories

## 1. Broken Access Control

Threat:

A user accesses another tenant's data or performs actions outside their role.

Mitigation:

- Server-side RBAC
- Server-side tenant validation
- Object-level authorization checks
- Cross-tenant denial tests

## 2. Dev Token Misuse

Threat:

Public dashboard or demo pages depend on development tokens.

Mitigation:

- Remove `dev-token` from public frontend
- Add public-safe module status endpoints
- Disable dev auth in production
- Verify no public frontend files contain development secrets

## 3. Public Endpoint Information Leakage

Threat:

Public pages reveal protected endpoint names, validation behavior, or internal status codes.

Mitigation:

- Use public facade endpoints
- Return safe module status
- Hide internal route implementation
- Standardize public error responses

## 4. CORS Misconfiguration

Threat:

Untrusted domains call LumenAI APIs from browsers.

Mitigation:

- Restrict production CORS to `https://lumen-ai-1.onrender.com`
- Permit localhost only in development
- Add CORS tests

## 5. Evidence Tampering

Threat:

An attacker modifies evidence exports or audit records.

Mitigation:

- Hash-backed evidence manifests
- Audit chain verification
- Immutable audit event references
- Export verification workflow

## 6. Unauthorized Evidence Access

Threat:

A user downloads evidence bundles without proper authorization.

Mitigation:

- Evidence bundle authorization checks
- Tenant-scoped evidence exports
- Download audit logs
- Auditor read-only role

## 7. Cross-Tenant Data Exposure

Threat:

A user changes tenant headers or object IDs to access another tenant's records.

Mitigation:

- Tenant comes from authenticated claims, not frontend trust
- Object-level tenant validation
- Deny cross-tenant object access
- Log denied cross-tenant attempts

## 8. Deployment Route Failure

Threat:

Public routes fail after deployment.

Mitigation:

- Static dashboard fallback
- Route validation script
- Public deployment verification
- Infrastructure-as-code for routing when possible

## 9. Production Error Leakage

Threat:

Backend returns stack traces, database errors, or internal implementation details.

Mitigation:

- Standardized error response format
- Production-safe messages
- Internal logging with request IDs
- No stack traces in public responses

## 10. Portfolio Maintenance Drift

Threat:

Duplicated static HTML pages become inconsistent or outdated.

Mitigation:

- Portfolio generator
- Shared template
- Content validation
- Centralized page metadata

## Existing Controls

- Public portfolio directory
- Static dashboard fallback page
- Portfolio route validation script
- Compliance evidence documentation
- Audit command center documentation
- CAPA workflow documentation
- Vendor governance documentation
- Release locks and repository seals
- Security hardening checklist
- Vulnerability reduction plan

## Required New Controls

- Public module status API facade
- Removal of dev-token from public dashboard
- Production CORS lock
- Formal RBAC matrix
- Tenant isolation test suite
- Evidence bundle authorization tests
- Standardized error response policy
- Deployment blueprint cleanup
- Portfolio content validation
- CI security validation workflow

## Residual Risks

Until the hardening roadmap is completed, LumenAI should be described as:

- Public portfolio-ready
- Demo-ready
- Investor-review ready
- Security-hardening roadmap documented

It should not yet be described as fully enterprise-production ready.

## Security Roadmap

## Phase 1: Public Safety

- Remove dev-token from public dashboard
- Add public-safe module status endpoints
- Standardize public module status responses
- Lock CORS to production frontend domain

## Phase 2: Enterprise Access Control

- Define RBAC matrix
- Enforce JWT claims
- Remove trust in frontend role headers
- Add tenant isolation tests

## Phase 3: Evidence Security

- Harden evidence bundle authorization
- Add evidence download audit logs
- Verify manifest hash behavior
- Add audit chain verification tests

## Phase 4: Deployment Assurance

- Clean Render blueprint
- Validate production routes
- Add content checks to validation script
- Document deployment rollback plan

## Threat Model Statement

LumenAI’s key security objective is to separate public review assets from enterprise data workflows while protecting tenant data, audit logs, evidence bundles, CAPA records, and vendor governance records through authentication, authorization, tenant isolation, tamper-evident evidence controls, and deployment reliability.

## Final Statement

This threat model establishes the security foundation for moving LumenAI from public portfolio readiness toward enterprise-production readiness.
