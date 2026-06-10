# LumenAI RBAC Matrix v1

## Status

Initial enterprise RBAC matrix documented.

## Purpose

This document defines the LumenAI role-based access control model for public, demo, customer, auditor, vendor, and system administration workflows.

The goal is to reduce authorization risk, improve tenant isolation, strengthen investor confidence, and establish a clear enterprise security foundation.

## Core Security Principle

Frontend headers must not be trusted for production authorization.

Production authorization should be based on:

- Authenticated identity
- JWT claims
- Server-side role validation
- Server-side tenant validation
- Object-level authorization checks
- Audit logging of protected actions

## Roles

## 1. Public Viewer

Purpose:

Unauthenticated public visitor reviewing LumenAI public pages.

Allowed:

- View public landing page
- View portfolio index
- View public portfolio pages
- View static dashboard fallback
- View public-safe module status

Denied:

- CAPA records
- Audit event contents
- Evidence bundle downloads
- Vendor records
- Tenant records
- Administrative workflows

## 2. Demo Reviewer

Purpose:

Reviewer accessing a safe demo experience.

Allowed:

- View demo dashboard
- View public-safe module readiness
- View sample-only demo narratives
- View portfolio pages

Denied:

- Real tenant data
- Evidence bundle downloads
- Audit event contents
- CAPA editing
- Vendor record editing
- Admin configuration

## 3. Customer Admin

Purpose:

Customer-side enterprise administrator for a specific tenant.

Allowed:

- View tenant dashboard
- View tenant CAPA records
- Create and update CAPA records
- View vendor governance records
- View tenant evidence summaries
- Request evidence bundle generation
- Manage tenant-level users where enabled

Denied:

- Cross-tenant access
- Platform-wide administration
- Other customer records
- System secrets

## 4. Quality Manager

Purpose:

Operational quality leader managing quality and corrective action workflows.

Allowed:

- View tenant quality dashboard
- Create CAPA records
- Update assigned CAPA records
- Review vendor-related quality events
- Add governance notes
- View evidence summaries

Denied:

- Cross-tenant records
- System administration
- Evidence deletion
- User role escalation

## 5. Auditor

Purpose:

Read-only reviewer of compliance evidence and audit readiness.

Allowed:

- View audit readiness summaries
- View verification summaries
- View approved evidence packages
- View read-only CAPA and governance history

Denied:

- Create or modify CAPA records
- Modify vendor records
- Delete evidence
- Change user roles
- Access other tenants

## 6. Vendor User

Purpose:

External vendor participant for assigned vendor accountability workflows.

Allowed:

- View vendor-specific assigned issues
- Submit vendor responses
- Upload or provide response documentation where enabled
- View status of vendor-specific corrective actions

Denied:

- Internal audit logs
- Other vendor records
- Tenant-wide CAPA records
- Evidence bundle downloads unless explicitly shared
- Administrative workflows

## 7. System Admin

Purpose:

Platform administrator responsible for system configuration and enterprise support.

Allowed:

- Manage platform configuration
- Manage tenant setup
- Review system health
- Review security logs
- Support deployment operations
- Manage user roles where authorized

Denied:

- Unlogged access to customer records
- Silent evidence modification
- Bypassing tenant audit controls
- Bypassing security logging

## Permission Matrix

| Workflow / Resource | Public Viewer | Demo Reviewer | Customer Admin | Quality Manager | Auditor | Vendor User | System Admin |
|---|---:|---:|---:|---:|---:|---:|---:|
| Public landing page | Allow | Allow | Allow | Allow | Allow | Allow | Allow |
| Portfolio pages | Allow | Allow | Allow | Allow | Allow | Allow | Allow |
| Public dashboard fallback | Allow | Allow | Allow | Allow | Allow | Allow | Allow |
| Public module status | Allow | Allow | Allow | Allow | Allow | Allow | Allow |
| Tenant dashboard | Deny | Deny | Allow | Allow | Read | Deny | Support |
| CAPA records | Deny | Deny | Manage | Manage | Read | Assigned Only | Support |
| Vendor governance records | Deny | Deny | Manage | Review | Read | Assigned Only | Support |
| Audit event contents | Deny | Deny | Read | Read | Read | Deny | Support |
| Evidence verification summary | Deny | Demo Only | Read | Read | Read | Shared Only | Support |
| Evidence bundle download | Deny | Deny | Allow | Request/Read | Read | Shared Only | Support |
| User role management | Deny | Deny | Tenant Limited | Deny | Deny | Deny | Allow |
| System configuration | Deny | Deny | Deny | Deny | Deny | Deny | Allow |
| Cross-tenant access | Deny | Deny | Deny | Deny | Deny | Deny | Controlled Support Only |

## Protected Endpoint Rules

All enterprise endpoints must enforce:

- Authentication
- Role check
- Tenant check
- Object ownership or object tenant validation
- Audit logging for sensitive actions

## Public Endpoint Rules

Public endpoints must:

- Return only safe high-level status
- Expose no PHI
- Expose no tenant records
- Expose no CAPA details
- Expose no audit event contents
- Expose no secrets
- Expose no stack traces

## Public Status Endpoint Policy

Public module status endpoints may return:

- module name
- availability status
- public status
- safe description

Public module status endpoints must not return:

- object IDs
- tenant names
- user names
- audit contents
- CAPA details
- evidence package contents
- secrets
- raw backend validation errors

## Tenant Isolation Rules

Tenant isolation must be enforced server-side.

The platform must not rely on frontend headers alone for tenant access.

Required rules:

- Tenant context must be derived from authenticated claims or trusted server-side mapping
- Object tenant ID must match authenticated tenant context
- Cross-tenant access attempts must be denied
- Denied cross-tenant attempts should be audit logged

## Audit Logging Rules

Audit logs should be created for:

- CAPA creation
- CAPA update
- Vendor response
- Evidence bundle generation
- Evidence bundle download
- Audit verification
- Role changes
- Denied cross-tenant attempts
- Failed authorization attempts

## Acceptance Criteria

This RBAC model is ready for engineering implementation when:

- Roles are documented
- Permissions are documented
- Public and enterprise access boundaries are defined
- Tenant isolation requirements are documented
- Evidence bundle authorization requirements are documented
- Audit logging requirements are documented
- Tests can be written from this matrix

## Final Statement

The LumenAI RBAC Matrix v1 establishes the access-control foundation required to move LumenAI from public portfolio readiness toward enterprise-production readiness.
