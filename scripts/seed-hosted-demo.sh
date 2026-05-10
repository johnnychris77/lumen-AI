#!/usr/bin/env bash
set -euo pipefail

HOSTED_BASE_URL="${HOSTED_BASE_URL:-}"
TOKEN="${TOKEN:-dev-token}"

if [[ -z "$HOSTED_BASE_URL" ]]; then
  echo "HOSTED_BASE_URL is required."
  echo
  echo "Example:"
  echo "HOSTED_BASE_URL=https://your-lumenai-api.onrender.com TOKEN=your-token scripts/seed-hosted-demo.sh"
  exit 1
fi

HOSTED_BASE_URL="${HOSTED_BASE_URL%/}"

BASE_URL="$HOSTED_BASE_URL" TOKEN="$TOKEN" backend/scripts/seed-demo-data.sh

echo
echo "Hosted demo seeded."
echo "Dashboard:"
echo "${HOSTED_BASE_URL}/api/executive-briefing-dashboard/view"
