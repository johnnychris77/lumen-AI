#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:18011}"
LANDING_PORT="${LANDING_PORT:-9092}"

echo "WARNING: This will delete the local Postgres Docker volume and reset local demo data."
echo "Generated artifact folders are not deleted by this script."
echo
read -r -p "Type RESET to continue: " CONFIRM

if [[ "$CONFIRM" != "RESET" ]]; then
  echo "Reset cancelled."
  exit 0
fi

echo
echo "==> Stopping existing stack and deleting DB volume"
docker compose -f docker-compose.prod.yml down -v --remove-orphans

echo
echo "==> Rebuilding stack"
docker compose -f docker-compose.prod.yml up -d --build

echo
echo "==> Waiting for API health"
for i in {1..60}; do
  if curl -fsS "${BASE_URL}/api/health" >/dev/null 2>&1; then
    echo "API is healthy."
    break
  fi

  if [[ "$i" == "60" ]]; then
    echo "API did not become healthy."
    docker logs --tail=160 lumen-ai-api-1 || true
    exit 1
  fi

  echo "waiting for api..."
  sleep 2
done

echo
echo "==> Starting landing page if needed"
if lsof -i ":${LANDING_PORT}" >/dev/null 2>&1; then
  echo "Port ${LANDING_PORT} already in use."
else
  nohup python -m http.server "${LANDING_PORT}" -d docs/public-demo >/tmp/lumenai-public-demo.log 2>&1 &
  echo $! > /tmp/lumenai-public-demo.pid
fi

echo
echo "Reset complete."
echo "Run demo seed:"
echo "scripts/demo-seed.sh"
