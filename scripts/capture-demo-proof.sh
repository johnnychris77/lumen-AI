#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:18011}"
TOKEN="${TOKEN:-dev-token}"
OUT_DIR="docs/portfolio-evidence/terminal-proof"
AUTH_HEADER="Authorization: Bearer ${TOKEN}"

mkdir -p "$OUT_DIR"

echo "==> Capturing health proof"
{
  echo "# Health Proof"
  echo
  curl -sS "${BASE_URL}/api/health"
  echo
} > "${OUT_DIR}/health.txt"

echo "==> Capturing production readiness proof"
{
  echo "# Production Readiness Proof"
  echo
  curl -sS "${BASE_URL}/api/production-readiness/config" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: admin" | python -m json.tool
} > "${OUT_DIR}/production-readiness-ready.txt"

echo "==> Capturing RBAC viewer denied proof"
{
  echo "# RBAC Viewer Denied Proof"
  echo
  curl -i -sS -X POST "${BASE_URL}/api/portfolio-tenants" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: viewer" \
    -H "Content-Type: application/json" \
    -d '{"tenant_name":"Portfolio Evidence Viewer Deny Test"}'
  echo
} > "${OUT_DIR}/rbac-viewer-denied.txt"

echo "==> Capturing RBAC operator allowed proof"
{
  echo "# RBAC Operator Allowed Proof"
  echo
  curl -sS -X POST "${BASE_URL}/api/portfolio-tenants" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: operator" \
    -H "Content-Type: application/json" \
    -d '{"tenant_name":"Portfolio Evidence Operator Allow Test","industry":"healthcare"}' | python -m json.tool
} > "${OUT_DIR}/rbac-operator-allowed.txt"

echo "==> Capturing dashboard summary proof"
{
  echo "# Dashboard Summary Proof"
  echo
  curl -sS "${BASE_URL}/api/executive-briefing-dashboard/summary" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: executive" | python -m json.tool
} > "${OUT_DIR}/dashboard-summary.txt"

echo "==> Capturing access governance proof"
{
  echo "# Access Governance Proof"
  echo
  curl -sS "${BASE_URL}/api/enterprise-access-control/rollup" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: admin" | python -m json.tool
} > "${OUT_DIR}/enterprise-access-rollup.txt"

echo "==> Capturing audit governance proof"
{
  echo "# Audit Governance Proof"
  echo
  curl -sS "${BASE_URL}/api/enterprise-audit-events/rollup" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: admin" | python -m json.tool
} > "${OUT_DIR}/enterprise-audit-rollup.txt"

echo
echo "DEMO PROOF CAPTURE COMPLETE"
find "$OUT_DIR" -type f | sort
