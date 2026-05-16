#!/usr/bin/env bash
set -euo pipefail

HOSTED_API="${HOSTED_API:-https://lumen-ai-53u4.onrender.com}"
LOCAL_FRONTEND="${LOCAL_FRONTEND:-http://localhost:5173}"

AUTH_HEADER="Authorization: Bearer ${VITE_AUTH_TOKEN:-dev-token}"

echo "========================================"
echo "LumenAI Hosted Demo Verification"
echo "========================================"
echo "Hosted API:      $HOSTED_API"
echo "Local Frontend:  $LOCAL_FRONTEND"
echo

echo "Checking hosted API health..."
curl -fsS "$HOSTED_API/api/health" >/dev/null
echo "✅ Hosted API health reachable"

echo "Checking hosted OpenAPI..."
curl -fsS "$HOSTED_API/openapi.json" >/dev/null
echo "✅ Hosted OpenAPI reachable"

echo "Checking hosted history summary..."
curl -fsS \
  -H "$AUTH_HEADER" \
  -H "X-Tenant-Id: bonsecours" \
  -H "X-Tenant-Name: Bon Secours" \
  "$HOSTED_API/api/history/summary" >/dev/null
echo "✅ Hosted history summary reachable"

echo "Checking hosted history list..."
curl -fsS \
  -H "$AUTH_HEADER" \
  -H "X-Tenant-Id: bonsecours" \
  -H "X-Tenant-Name: Bon Secours" \
  "$HOSTED_API/api/history?limit=8" >/dev/null
echo "✅ Hosted history list reachable"

echo "Checking hosted alert history..."
curl -fsS \
  -H "$AUTH_HEADER" \
  -H "X-Tenant-Id: bonsecours" \
  -H "X-Tenant-Name: Bon Secours" \
  "$HOSTED_API/api/alerts/history?limit=12" >/dev/null
echo "✅ Hosted alert history reachable"

echo "Checking hosted model performance..."
curl -fsS \
  -H "$AUTH_HEADER" \
  -H "X-Tenant-Id: bonsecours" \
  -H "X-Tenant-Name: Bon Secours" \
  "$HOSTED_API/api/model-performance/summary" >/dev/null
echo "✅ Hosted model performance reachable"

echo
echo "========================================"
echo "✅ LumenAI hosted demo verification PASSED"
echo "========================================"
echo
echo "Open local frontend:"
echo "$LOCAL_FRONTEND"
