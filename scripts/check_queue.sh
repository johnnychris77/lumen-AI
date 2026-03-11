#!/usr/bin/env bash
set -euo pipefail

echo "======================================"
echo "LumenAI Queue Diagnostics"
echo "======================================"

echo
echo "[1/4] Queue depth"
docker exec -i lumen-ai-redis-1 sh -lc 'redis-cli -n 0 LLEN rq:queue:lumenai'

echo
echo "[2/4] Queue items"
docker exec -i lumen-ai-redis-1 sh -lc 'redis-cli -n 0 LRANGE rq:queue:lumenai 0 10'

echo
echo "[3/4] Worker logs"
docker logs --tail=60 lumen-ai-worker-1 || true

echo
echo "[4/4] API logs"
docker logs --tail=40 lumen-ai-api-1 || true
