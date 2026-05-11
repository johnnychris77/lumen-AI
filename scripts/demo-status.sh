#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:18011}"
LANDING_PORT="${LANDING_PORT:-9092}"
TOKEN="${TOKEN:-dev-token}"

AUTH_HEADER="Authorization: Bearer ${TOKEN}"

echo "==> Docker containers"
docker compose -f docker-compose.prod.yml ps

echo
echo "==> API health"
curl -sS "${BASE_URL}/api/health" || true
echo

echo
echo "==> Production readiness"
curl -sS "${BASE_URL}/api/production-readiness/config" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: admin" | python -m json.tool || true

echo
echo "==> Dashboard summary key counts"
SUMMARY_FILE="/tmp/lumenai_demo_dashboard_summary.json"

if curl -fsS "${BASE_URL}/api/executive-briefing-dashboard/summary" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: executive" > "$SUMMARY_FILE"; then
  python - "$SUMMARY_FILE" <<'PY' || true
import json
import sys
from pathlib import Path

try:
    data = json.loads(Path(sys.argv[1]).read_text())
except Exception as exc:
    print(f"Unable to parse dashboard summary: {exc}")
    raise SystemExit(0)

keys = [
    "portfolio_tenants",
    "tenant_remediations",
    "executive_escalations",
    "governance_packets",
    "executive_decisions",
    "enterprise_audit",
    "enterprise_access",
]

for key in keys:
    print(f"{key}: {data.get(key)}")
PY
else
  echo "Unable to fetch dashboard summary."
fi

echo
echo "==> Landing page"
if lsof -i ":${LANDING_PORT}" >/dev/null 2>&1; then
  echo "Landing page port ${LANDING_PORT} is active."
  echo "http://127.0.0.1:${LANDING_PORT}"
else
  echo "Landing page port ${LANDING_PORT} is not active."
  echo "Run: LANDING_PORT=${LANDING_PORT} scripts/demo-start.sh"
fi

echo
echo "==> Useful links"
echo "Landing page: http://127.0.0.1:${LANDING_PORT}"
echo "Dashboard:    ${BASE_URL}/api/executive-briefing-dashboard/view"
echo "Health:       ${BASE_URL}/api/health"
