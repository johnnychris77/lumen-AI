#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:18011}"
TOKEN="${TOKEN:-dev-token}"

echo "==> Checking API health before seeding"

if ! curl -fsS "${BASE_URL}/api/health" >/dev/null 2>&1; then
  echo "API is not healthy at ${BASE_URL}."
  echo "Run:"
  echo "scripts/demo-start.sh"
  exit 1
fi

echo "API is healthy."

echo
echo "==> Seeding demo data"
BASE_URL="$BASE_URL" TOKEN="$TOKEN" backend/scripts/seed-demo-data.sh

echo
echo "Demo data seed complete."
echo
echo "Open dashboard:"
echo "${BASE_URL}/api/executive-briefing-dashboard/view"
