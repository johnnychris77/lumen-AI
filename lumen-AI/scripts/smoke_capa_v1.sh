#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://172.27.41.109:18121}"
FRONTEND_URL="${FRONTEND_URL:-http://172.27.41.109:5173}"

echo "========================================"
echo " LumenAI CAPA Intelligence v1 Smoke Test"
echo "========================================"
echo "Backend:  $BACKEND_URL"
echo "Frontend: $FRONTEND_URL"
echo ""

echo "1) Checking frontend..."
curl -fsSI "$FRONTEND_URL/" >/dev/null
echo "✅ Frontend reachable"

echo ""
echo "2) Checking backend CAPA summary..."
curl -fsS "$BACKEND_URL/api/capa/dashboard/summary" | python -m json.tool >/tmp/lumenai_capa_summary.json
cat /tmp/lumenai_capa_summary.json
echo "✅ CAPA dashboard summary reachable"

echo ""
echo "3) Checking CAPA analytics..."
curl -fsS "$BACKEND_URL/api/capa/analytics/trends" | python -m json.tool >/tmp/lumenai_capa_analytics.json
cat /tmp/lumenai_capa_analytics.json
echo "✅ CAPA analytics reachable"

echo ""
echo "4) Checking CAPA list..."
curl -fsS "$BACKEND_URL/api/capa/" | python -m json.tool >/tmp/lumenai_capa_list.json
cat /tmp/lumenai_capa_list.json
echo "✅ CAPA list reachable"

CAPA_ID=$(python - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/lumenai_capa_list.json").read_text())
items = data.get("items", [])
print(items[0]["capa_id"] if items else "")
PY
)

if [ -z "$CAPA_ID" ]; then
  echo ""
  echo "⚠️ No CAPA records found. Run seed endpoint first:"
  echo "curl -sS -X POST \"$BACKEND_URL/api/capa/seed/demo-analytics\" | python -m json.tool"
  exit 0
fi

echo ""
echo "5) Checking CAPA detail for $CAPA_ID..."
curl -fsS "$BACKEND_URL/api/capa/$CAPA_ID" | python -m json.tool >/tmp/lumenai_capa_detail.json
cat /tmp/lumenai_capa_detail.json
echo "✅ CAPA detail reachable"

echo ""
echo "6) Checking CAPA report for $CAPA_ID..."
curl -fsS "$BACKEND_URL/api/capa/$CAPA_ID/report" | python -m json.tool >/tmp/lumenai_capa_report.json
cat /tmp/lumenai_capa_report.json
echo "✅ CAPA report reachable"

echo ""
echo "========================================"
echo "✅ LumenAI CAPA Intelligence v1 smoke test PASSED"
echo "========================================"
