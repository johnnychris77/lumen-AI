#!/usr/bin/env bash
set -euo pipefail

echo "==> Python compile gate"
python -m py_compile \
  backend/run_reset_app.py \
  backend/app/auth.py \
  backend/app/portfolio_tenants.py \
  backend/app/tenant_insights.py \
  backend/app/tenant_remediations.py \
  backend/app/executive_escalations.py \
  backend/app/governance_packet_exports.py \
  backend/app/executive_kpi_snapshots.py \
  backend/app/executive_kpi_scheduler.py \
  backend/app/executive_decisions.py \
  backend/app/enterprise_audit.py \
  backend/app/enterprise_access_control.py \
  backend/app/routes/portfolio_tenants.py \
  backend/app/routes/tenant_insights.py \
  backend/app/routes/tenant_remediations.py \
  backend/app/routes/executive_escalations.py \
  backend/app/routes/governance_packet_exports.py \
  backend/app/routes/executive_kpi_snapshots.py \
  backend/app/routes/executive_kpi_scheduler.py \
  backend/app/routes/executive_decisions.py \
  backend/app/routes/enterprise_audit.py \
  backend/app/routes/enterprise_access_control.py \
  backend/app/routes/executive_briefing_dashboard.py

echo "==> Docker rebuild"
docker compose -f docker-compose.prod.yml down --remove-orphans
docker compose -f docker-compose.prod.yml up -d --build

echo "==> Enterprise smoke test"
BASE_URL="${BASE_URL:-http://127.0.0.1:18011}" backend/scripts/enterprise-smoke-test.sh

echo "==> Quality gate passed"
