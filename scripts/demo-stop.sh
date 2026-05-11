#!/usr/bin/env bash
set -euo pipefail

LANDING_PORT="${LANDING_PORT:-9092}"

echo "==> Stopping landing page server if tracked"

if [[ -f /tmp/lumenai-public-demo.pid ]]; then
  PID="$(cat /tmp/lumenai-public-demo.pid || true)"
  if [[ -n "$PID" ]] && kill -0 "$PID" >/dev/null 2>&1; then
    kill "$PID" || true
    echo "Stopped landing page server PID ${PID}"
  fi
  rm -f /tmp/lumenai-public-demo.pid
fi

echo
echo "==> Checking for remaining process on port ${LANDING_PORT}"
if lsof -ti ":${LANDING_PORT}" >/dev/null 2>&1; then
  echo "Port ${LANDING_PORT} is still in use."
  echo "To force stop:"
  echo "kill \$(lsof -ti :${LANDING_PORT})"
else
  echo "Port ${LANDING_PORT} is free."
fi

echo
echo "==> Stopping Docker stack"
docker compose -f docker-compose.prod.yml down --remove-orphans

echo
echo "Demo stopped."
