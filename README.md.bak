# LumenAI

Enterprise Executive Intelligence Platform for Regulated Operations.

LumenAI converts operational risk into executive insight, remediation actions, escalation cadence, KPI trends, governance packets, audit trails, and role-based access control.

## Executive Workflow

tenant risk
→ executive insight
→ remediation action
→ escalation
→ governance packet
→ executive decision
→ KPI trend
→ audit trail
→ RBAC policy guardrails

## Key Capabilities

- Tenant portfolio management
- Tenant risk insights
- Executive narrative generation
- Remediation workflow
- Executive escalation cadence
- Governance packet generation
- DOCX / PPTX / PDF exports
- Executive KPI snapshots
- Automated KPI scheduler
- Board trend narrative
- Executive decision log
- Enterprise audit trail
- Enterprise RBAC policy guardrails
- Production readiness endpoint
- Enterprise smoke test and quality gate

## Architecture

LumenAI runs as a Dockerized FastAPI platform with PostgreSQL, Redis, background workers, Nginx, and generated artifact storage.

## Quick Start

Start the stack:

    docker compose -f docker-compose.prod.yml up -d --build

Health check:

    curl -sS http://127.0.0.1:18011/api/health

Production readiness:

    curl -sS http://127.0.0.1:18011/api/production-readiness/config \
      -H "Authorization: Bearer dev-token" \
      -H "X-LumenAI-Role: admin" | python -m json.tool

Dashboard:

    http://127.0.0.1:18011/api/executive-briefing-dashboard/view

## Enterprise Quality Gate

Run:

    backend/scripts/local-quality-gate.sh

Expected:

    ENTERPRISE SMOKE TEST PASSED
    ==> Quality gate passed

## Portfolio Value

This project demonstrates enterprise workflow automation, healthcare operations intelligence, API design, Docker deployment, PostgreSQL-backed workflow state, AI-ready narrative generation, board packet automation, audit governance, RBAC, and regression validation.

---

## Visual Proof

### Executive Demo Scenario

![LumenAI Executive Story Panel](docs/assets/screenshots/lumenai-executive-story-panel.png)

### Hosted Dashboard Overview

![LumenAI Dashboard Overview](docs/assets/screenshots/lumenai-dashboard-overview.png)

### Alert Control Center

![LumenAI Alert Control Center](docs/assets/screenshots/lumenai-alert-control-center.png)

### Vendor Intelligence and Model Performance

![LumenAI Vendor Intelligence and Model Performance](docs/assets/screenshots/lumenai-vendor-model-performance.png)

