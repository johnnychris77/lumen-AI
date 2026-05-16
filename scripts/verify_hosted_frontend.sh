#!/usr/bin/env bash
set -euo pipefail

HOSTED_FRONTEND="${HOSTED_FRONTEND:-}"
HOSTED_API="${HOSTED_API:-https://lumen-ai-53u4.onrender.com}"

if [[ -z "$HOSTED_FRONTEND" ]]; then
  echo "ERROR: HOSTED_FRONTEND is required."
  echo "Example:"
  echo "HOSTED_FRONTEND=https://lumen-ai-frontend.onrender.com ./scripts/verify_hosted_frontend.sh"
  exit 1
fi

HOSTED_FRONTEND="${HOSTED_FRONTEND%/}"
HOSTED_API="${HOSTED_API%/}"

echo "========================================"
echo "LumenAI Hosted Frontend Verification"
echo "========================================"
echo "Hosted Frontend: $HOSTED_FRONTEND"
echo "Hosted API:      $HOSTED_API"
echo

echo "Checking hosted frontend..."
curl -fsS "$HOSTED_FRONTEND" >/dev/null
echo "✅ Hosted frontend reachable"

echo "Checking hosted API health..."
curl -fsS "$HOSTED_API/api/health" >/dev/null
echo "✅ Hosted API health reachable"

echo "Checking authenticated API route..."
curl -fsS \
  -H "Authorization: Bearer dev-token" \
  -H "X-Tenant-Id: bonsecours" \
  -H "X-Tenant-Name: Bon Secours" \
  "$HOSTED_API/api/history/summary" >/dev/null
echo "✅ Authenticated API route reachable"

echo
echo "========================================"
echo "✅ LumenAI hosted frontend verification PASSED"
echo "========================================"
