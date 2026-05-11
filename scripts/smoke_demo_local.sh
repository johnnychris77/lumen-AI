#!/usr/bin/env bash
set -euo pipefail

DEMO_URL="${DEMO_URL:-http://127.0.0.1:9092}"
API_URL="${API_URL:-http://127.0.0.1:18011}"
AUTH_HEADER="${AUTH_HEADER:-Authorization: Bearer dev-token}"

echo "========================================"
echo "LumenAI Local Demo Smoke Test"
echo "========================================"
echo "Demo URL: $DEMO_URL"
echo "API URL:  $API_URL"
echo

echo "Checking public demo page..."
curl -fsS "$DEMO_URL" >/dev/null
echo "✅ Demo page reachable"

echo "Checking API health..."
curl -fsS "$API_URL/api/health" >/dev/null
echo "✅ API health reachable"

echo "Checking OpenAPI..."
curl -fsS "$API_URL/openapi.json" >/dev/null
echo "✅ OpenAPI reachable"

echo "Checking production readiness config..."
curl -fsS -H "$AUTH_HEADER" "$API_URL/api/production-readiness/config" >/dev/null
echo "✅ Production readiness config reachable"

echo "Checking executive briefing dashboard..."
curl -fsS -H "$AUTH_HEADER" "$API_URL/api/executive-briefing-dashboard/view" >/dev/null
echo "✅ Executive briefing dashboard reachable"

echo
echo "========================================"
echo "✅ LumenAI local demo smoke test PASSED"
echo "========================================"
