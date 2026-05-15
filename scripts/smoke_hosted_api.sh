#!/usr/bin/env bash
set -euo pipefail

HOSTED_BASE_URL="${HOSTED_BASE_URL:-}"

if [[ -z "$HOSTED_BASE_URL" ]]; then
  echo "ERROR: HOSTED_BASE_URL is required."
  echo "Example:"
  echo "HOSTED_BASE_URL=https://lumen-ai-53u4.onrender.com ./scripts/smoke_hosted_api.sh"
  exit 1
fi

echo "========================================"
echo "LumenAI Hosted API Smoke Test"
echo "========================================"
echo "Hosted API: $HOSTED_BASE_URL"
echo

echo "Checking API health..."
curl -fsS "$HOSTED_BASE_URL/api/health" >/dev/null
echo "✅ API health reachable"

echo "Checking OpenAPI..."
curl -fsS "$HOSTED_BASE_URL/openapi.json" >/dev/null
echo "✅ OpenAPI reachable"

echo "Checking docs..."
curl -fsS "$HOSTED_BASE_URL/docs" >/dev/null
echo "✅ Docs reachable"

echo "Checking reviews queue..."
curl -fsS "$HOSTED_BASE_URL/api/reviews/queue" >/dev/null
echo "✅ Reviews queue reachable"

echo "Checking authenticated executive digest..."
curl -fsS \
  -H "Authorization: Bearer dev-token" \
  "$HOSTED_BASE_URL/api/executive-digest/weekly" >/dev/null
echo "✅ Executive digest reachable"

echo
echo "✅ Hosted API smoke test passed"
