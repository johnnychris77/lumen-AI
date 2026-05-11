#!/usr/bin/env bash
set -euo pipefail

LANDING_PORT="${LANDING_PORT:-9092}"
BASE_URL="${BASE_URL:-http://127.0.0.1:18011}"

echo "==> Starting LumenAI Docker stack"
docker compose -f docker-compose.prod.yml up -d --build

echo
echo "==> Waiting for API health"
for i in {1..60}; do
  if curl -fsS "${BASE_URL}/api/health" >/dev/null 2>&1; then
    echo "API is healthy: ${BASE_URL}/api/health"
    break
  fi

  if [[ "$i" == "60" ]]; then
    echo "API did not become healthy."
    echo "Check logs:"
    echo "docker logs --tail=160 lumen-ai-api-1"
    exit 1
  fi

  echo "waiting for api..."
  sleep 2
done

echo
echo "==> Starting public landing page server"

if lsof -i ":${LANDING_PORT}" >/dev/null 2>&1; then
  echo "Port ${LANDING_PORT} is already in use. Landing page may already be running."
else
  nohup python -m http.server "${LANDING_PORT}" -d docs/public-demo >/tmp/lumenai-public-demo.log 2>&1 &
  echo $! > /tmp/lumenai-public-demo.pid
  echo "Landing page server started on port ${LANDING_PORT}"
fi

echo
echo "LumenAI demo is ready."
echo
echo "Landing page:"
echo "http://127.0.0.1:${LANDING_PORT}"
echo
echo "Executive dashboard:"
echo "${BASE_URL}/api/executive-briefing-dashboard/view"
echo
echo "Production readiness:"
echo "${BASE_URL}/api/production-readiness/config"
