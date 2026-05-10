#!/usr/bin/env bash
set -euo pipefail

HOSTED_BASE_URL="${HOSTED_BASE_URL:-}"
TOKEN="${TOKEN:-dev-token}"
ROLE="${ROLE:-admin}"

if [[ -z "$HOSTED_BASE_URL" ]]; then
  echo "HOSTED_BASE_URL is required."
  echo
  echo "Example:"
  echo "HOSTED_BASE_URL=https://your-lumenai-api.onrender.com TOKEN=your-token scripts/check-hosted-demo.sh"
  exit 1
fi

HOSTED_BASE_URL="${HOSTED_BASE_URL%/}"
AUTH_HEADER="Authorization: Bearer ${TOKEN}"

log() {
  echo
  echo "==> $*"
}

json_pretty() {
  python -m json.tool
}

log "Checking hosted API health"
curl -fsS "${HOSTED_BASE_URL}/api/health" | json_pretty

log "Checking production readiness"
curl -fsS "${HOSTED_BASE_URL}/api/production-readiness/config" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: ${ROLE}" | json_pretty

log "Checking dashboard summary"
curl -fsS "${HOSTED_BASE_URL}/api/executive-briefing-dashboard/summary" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: executive" | json_pretty > /tmp/lumenai_hosted_dashboard_summary.json

python - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/lumenai_hosted_dashboard_summary.json").read_text())

print("Hosted Dashboard Summary Check")
print("--------------------------------")
for key in [
    "portfolio_tenants",
    "tenant_remediations",
    "executive_escalations",
    "governance_packets",
    "executive_decisions",
    "enterprise_audit",
    "enterprise_access",
]:
    print(f"{key}: {data.get(key)}")
PY

log "Checking RBAC viewer write denial"
status="$(
  curl -sS -o /tmp/lumenai_hosted_rbac_deny.json -w "%{http_code}" \
    -X POST "${HOSTED_BASE_URL}/api/portfolio-tenants" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: viewer" \
    -H "Content-Type: application/json" \
    -d '{"tenant_name":"Hosted RBAC Deny Test"}'
)"

if [[ "$status" != "403" ]]; then
  echo "Expected 403 for viewer write, got ${status}"
  cat /tmp/lumenai_hosted_rbac_deny.json
  exit 1
fi

echo "RBAC viewer write denied as expected."

log "Checking public dashboard URL"
echo "${HOSTED_BASE_URL}/api/executive-briefing-dashboard/view"

echo
echo "HOSTED DEMO VALIDATION COMPLETE"
