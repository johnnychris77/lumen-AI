# LumenAI Current-State Architecture

## Purpose

LumenAI is an evidence governance platform for sterile processing, vendor baseline accountability, quality events, CAPA workflows, governance packets, audit trails, and survey-readiness documentation.

## Current Validated Capabilities

- Vendor baseline submission
- Hospital baseline approval
- Persistent vendor baseline audit events
- Vendor baseline audit UI
- Governance PDF packet export
- Export history tracking
- SHA-256 packet hashing
- Packet hash verification
- Frontend packet verification panel
- Immutable export certificate UI

## Current Components

### Frontend
React and TypeScript frontend with vendor baseline portal, audit panel, export history panel, packet verification panel, and immutable certificate card.

### Backend
FastAPI backend with enterprise intake, vendor baseline workflows, audit trail, governance packet export, PDF generation, packet hashing, and hash verification.

### Database
Current development uses SQLite. Production should mature toward PostgreSQL with Alembic migrations and stronger tenant isolation.

## Current Strengths

- Strong SPD / OR / IP / vendor governance use case
- Persistent audit trail
- Tamper-evident governance PDF exports
- Investor-friendly compliance narrative
- Validated frontend and backend workflows

## Current Gaps

- Demo authentication still uses dev-token patterns
- Header-based role and actor values are spoofable
- Tenant isolation needs hardening
- Large backend route file should be split into domains
- Automated tests and CI quality gates need expansion
- Security scanning and secrets scanning need to be formalized

## Current Maturity

LumenAI is an enterprise-grade MVP / early platform prototype. It has strong domain differentiation and validated compliance workflows, but needs architecture, security, and testing hardening before enterprise production diligence.
