# LumenAI Architecture Summary

## Core Architecture

LumenAI runs as a Dockerized FastAPI platform with PostgreSQL, Redis, background workers, and an executive dashboard.

## Services

- FastAPI API service
- PostgreSQL database
- Redis queue backend
- Worker service
- Nginx edge service

## Major Product Modules

1. Portfolio Tenants
2. Tenant Insights
3. Tenant Remediations
4. Executive Escalations
5. Governance Packets
6. Portfolio Briefing Exports
7. Executive KPI Snapshots
8. KPI Scheduler
9. Executive Decisions
10. Enterprise Audit
11. Enterprise RBAC
12. Production Readiness

## Executive Workflow

Tenant data flows through:

tenant record
→ insight engine
→ remediation actions
→ executive escalation
→ governance packet
→ decision log
→ KPI snapshot
→ audit and access governance

## Artifact Generation

LumenAI generates:

- DOCX executive packets
- PPTX board packets
- PDF governance packets

## Governance Controls

- RBAC policy decisions
- audit event capture
- access decision logging
- production-readiness validation
- enterprise smoke test
