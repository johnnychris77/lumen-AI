#!/usr/bin/env bash
set -euo pipefail

echo "==> LumenAI Render Deployment Readiness Check"

FAILURES=0

check_file() {
  local file="$1"
  if [[ -f "$file" ]]; then
    echo "OK: $file"
  else
    echo "MISSING: $file"
    FAILURES=$((FAILURES + 1))
  fi
}

check_contains() {
  local file="$1"
  local text="$2"
  if grep -q "$text" "$file"; then
    echo "OK: $file contains $text"
  else
    echo "MISSING: $file does not contain $text"
    FAILURES=$((FAILURES + 1))
  fi
}

echo
echo "==> Required deployment files"
check_file "render.yaml"
check_file "docs/deployment/HOSTED_BACKEND_QUICKSTART.md"
check_file "docs/deployment/HOSTED_DEMO_VALIDATION.md"
check_file "scripts/check-hosted-demo.sh"
check_file "scripts/seed-hosted-demo.sh"
check_file "scripts/update-public-demo-links.sh"
check_file "scripts/public-demo-go-live.sh"

echo
echo "==> Render blueprint content"
if [[ -f render.yaml ]]; then
  check_contains "render.yaml" "lumen-ai-api"
  check_contains "render.yaml" "DATABASE_URL"
  check_contains "render.yaml" "REDIS_URL"
  check_contains "render.yaml" "PUBLIC_BASE_URL"
  check_contains "render.yaml" "/api/health"
fi

echo
echo "==> Local API health"
if curl -fsS http://127.0.0.1:18011/api/health >/tmp/lumenai_render_readiness_health.json 2>/dev/null; then
  echo "OK: local API health endpoint is reachable"
  cat /tmp/lumenai_render_readiness_health.json
  echo
else
  echo "WARN: local API health endpoint is not reachable"
  echo "Run: scripts/demo-start.sh"
fi

echo
echo "==> Local production readiness"
if curl -fsS http://127.0.0.1:18011/api/production-readiness/config \
  -H "Authorization: Bearer dev-token" \
  -H "X-LumenAI-Role: admin" >/tmp/lumenai_render_readiness_config.json 2>/dev/null; then
  echo "OK: production readiness endpoint is reachable"
  python -m json.tool /tmp/lumenai_render_readiness_config.json >/dev/null
else
  echo "WARN: production readiness endpoint is not reachable"
fi

echo
echo "==> Git status"
git status --short

echo
if [[ "$FAILURES" -gt 0 ]]; then
  echo "RENDER READINESS CHECK FAILED with $FAILURES missing requirement(s)."
  exit 1
fi

echo "RENDER READINESS CHECK PASSED"
