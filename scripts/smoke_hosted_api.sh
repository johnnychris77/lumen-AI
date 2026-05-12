#!/usr/bin/env bash
set -euo pipefail

HOSTED_BASE_URL="${HOSTED_BASE_URL:-}"

if [[ -z "$HOSTED_BASE_URL" ]]; then
  echo "ERROR: HOSTED_BASE_URL is required."
  echo "Example:"
  echo "HOSTED_BASE_URL=https://lumen-ai-api.onrender.com ./scripts/smoke_hosted_api.sh"
  exit 1
fi

HOSTED_BASE_URL="${HOSTED_BASE_URL%/}"

echo "========================================"
echo "LumenAI Hosted API Smoke Test"
echo "========================================"
echo "Hosted API: $HOSTED_BASE_URL"
echo

echo "Checking API root..."
curl -fsS "$HOSTED_BASE_URL/" >/dev/null
echo "✅ API root reachable"

echo "Checking API health..."
curl -fsS "$HOSTED_BASE_URL/api/health" >/dev/null
echo "✅ API health reachable"

echo "Checking OpenAPI..."
curl -fsS "$HOSTED_BASE_URL/openapi.json" >/dev/null
echo "✅ OpenAPI reachable"

echo "Checking executive briefing dashboard..."
curl -fsS "$HOSTED_BASE_URL/api/executive-briefing-dashboard/view" >/dev/null
echo "✅ Executive briefing dashboard reachable"

echo
echo "========================================"
echo "✅ LumenAI hosted API smoke test PASSED"
echo "========================================"
