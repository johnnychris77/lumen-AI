# LumenAI Target Enterprise Architecture

## Target Goal

LumenAI should evolve into a secure, modular, testable, multi-tenant enterprise platform for healthcare quality evidence governance.

## Target Logical Architecture

Frontend:
- React / TypeScript
- Role-aware UI
- Audit panels
- Export panels
- Verification panels

API Layer:
- FastAPI
- Auth middleware
- Tenant middleware
- Request ID middleware
- Rate limiting
- RBAC / ABAC enforcement

Domain Services:
- Vendor Baseline Service
- Audit Trail Service
- Governance Packet Service
- Export History Service
- Packet Hash Verification Service
- CAPA Service
- Tenant Service

Data Layer:
- PostgreSQL
- Alembic migrations
- Row-level tenant isolation
- Immutable audit tables
- Object storage metadata

Security Layer:
- OIDC / OAuth
- JWT validation
- Secrets manager
- TLS in transit
- Encryption at rest
- Structured security logs

Operations:
- CI/CD
- Automated tests
- Static analysis
- Dependency scanning
- Secrets scanning
- Monitoring
- Error tracking
- Backups

## Target Backend Structure

backend/app/domains/vendor_baseline/
backend/app/domains/audit_trail/
backend/app/domains/governance_packet/
backend/app/domains/export_history/
backend/app/domains/capa/
backend/app/domains/tenant/

Each domain should contain routes, services, repositories, schemas, and tests.

## Target Quality Gate

Every pull request should require unit tests, integration tests, type checks, linting, security scanning, dependency scanning, secrets scanning, build validation, and migration validation.
