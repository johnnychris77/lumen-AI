#!/usr/bin/env bash
set -euo pipefail

DEMO_URL="${DEMO_URL:-http://127.0.0.1:9092}"
API_URL="${API_URL:-http://127.0.0.1:18011}"

echo "========================================"
echo "LumenAI Local Demo Launcher"
echo "========================================"
echo "Demo URL: $DEMO_URL"
echo "API URL:  $API_URL"
echo

echo "Checking demo readiness..."
DEMO_URL="$DEMO_URL" API_URL="$API_URL" ./scripts/smoke_demo_local.sh

echo
echo "========================================"
echo "Demo Links"
echo "========================================"
echo "Landing Page:              $DEMO_URL"
echo "Executive Dashboard:        $API_URL/api/executive-briefing-dashboard/view"
echo "Production Readiness:       $API_URL/api/production-readiness/config"
echo "API Health:                 $API_URL/api/health"
echo "OpenAPI:                    $API_URL/openapi.json"
echo

echo "========================================"
echo "Recommended Walkthrough"
echo "========================================"
echo "1. Open landing page"
echo "2. Show screenshot gallery"
echo "3. Open executive dashboard"
echo "4. Explain evidence-driven workflow"
echo "5. Explain AI-ready classification"
echo "6. Explain auto-routing"
echo "7. Explain CAPA/report/audit trail"
echo "8. Show quality gate smoke test"
echo

echo "✅ LumenAI local demo is ready."
