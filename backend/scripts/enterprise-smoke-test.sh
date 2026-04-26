#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:18011}"
TOKEN="${TOKEN:-dev-token}"

AUTH_HEADER="Authorization: Bearer ${TOKEN}"

log() {
  echo
  echo "==> $*"
}

json_field() {
  python -c 'import sys,json; data=json.load(sys.stdin); print(data.get("'"$1"'", ""))'
}

assert_contains() {
  local haystack="$1"
  local needle="$2"
  if [[ "$haystack" != *"$needle"* ]]; then
    echo "Expected output to contain: $needle"
    echo "Actual output:"
    echo "$haystack"
    exit 1
  fi
}

wait_for_api() {
  log "Waiting for API at ${BASE_URL}"
  for i in {1..60}; do
    if curl -fsS "${BASE_URL}/api/health" >/dev/null 2>&1; then
      echo "API is healthy"
      return 0
    fi
    sleep 2
  done

  echo "API did not become healthy"
  exit 1
}

log "Enterprise smoke test starting"
wait_for_api

log "Health check"
curl -fsS "${BASE_URL}/api/health"
echo

log "Route table sanity check"
OPENAPI="$(curl -fsS "${BASE_URL}/openapi.json")"
assert_contains "$OPENAPI" "portfolio-tenants"
assert_contains "$OPENAPI" "tenant-insights"
assert_contains "$OPENAPI" "tenant-remediations"
assert_contains "$OPENAPI" "executive-escalations"
assert_contains "$OPENAPI" "executive-decisions"
assert_contains "$OPENAPI" "governance-packets"
assert_contains "$OPENAPI" "executive-kpi-snapshots"
assert_contains "$OPENAPI" "enterprise-audit-events"
assert_contains "$OPENAPI" "enterprise-access-control"
echo "Route table contains enterprise routes"

log "RBAC viewer read should pass"
curl -fsS "${BASE_URL}/api/portfolio-tenants" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: viewer" >/dev/null
echo "Viewer read passed"

log "RBAC viewer write should be denied"
DENY_STATUS="$(
  curl -sS -o /tmp/lumenai_rbac_deny.json -w "%{http_code}" \
    -X POST "${BASE_URL}/api/portfolio-tenants" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: viewer" \
    -H "Content-Type: application/json" \
    -d '{"tenant_name":"RBAC Smoke Deny Tenant"}'
)"
if [[ "$DENY_STATUS" != "403" ]]; then
  echo "Expected 403 for viewer write, got ${DENY_STATUS}"
  cat /tmp/lumenai_rbac_deny.json
  exit 1
fi
echo "Viewer write denied as expected"

log "Create portfolio tenant as operator"
TENANT_ID="$(
  curl -fsS -X POST "${BASE_URL}/api/portfolio-tenants" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: operator" \
    -H "Content-Type: application/json" \
    -d '{"tenant_name":"Smoke Test Health System","industry":"healthcare","go_live_status":"implementation","renewal_risk":true,"implementation_risk":true,"governance_exception_count":4,"last_qbr_date":"2026-02-01","next_qbr_date":"2026-03-01","executive_owner":"Chief Customer Officer","customer_success_owner":"Smoke CSM","notes":"Created by enterprise smoke test."}' \
  | json_field id
)"
echo "TENANT_ID=${TENANT_ID}"

log "Get tenant insight"
curl -fsS "${BASE_URL}/api/tenant-insights/${TENANT_ID}" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: operator" | python -m json.tool >/tmp/lumenai_tenant_insight.json
cat /tmp/lumenai_tenant_insight.json | grep -q "recommended_actions"
echo "Tenant insight passed"

log "Create remediations from tenant insight"
REMEDIATION_ID="$(
  curl -fsS -X POST "${BASE_URL}/api/tenant-remediations/from-insight/${TENANT_ID}" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: operator" \
  | python -c 'import sys,json; data=json.load(sys.stdin); print(data[0]["id"] if data else "")'
)"
if [[ -z "$REMEDIATION_ID" ]]; then
  echo "No remediation created"
  exit 1
fi
echo "REMEDIATION_ID=${REMEDIATION_ID}"

log "Escalate remediation"
curl -fsS -X PATCH "${BASE_URL}/api/tenant-remediations/${REMEDIATION_ID}" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: operator" \
  -H "Content-Type: application/json" \
  -d '{"status":"escalated"}' >/dev/null
echo "Remediation escalated"

log "Run executive escalation scan"
curl -fsS -X POST "${BASE_URL}/api/executive-escalations/run" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: executive" | python -m json.tool >/tmp/lumenai_escalation_scan.json
cat /tmp/lumenai_escalation_scan.json
echo "Escalation scan passed"

log "Get first open escalation"
ESCALATION_ID="$(
  curl -fsS "${BASE_URL}/api/executive-escalations/open" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: executive" \
  | python -c 'import sys,json; data=json.load(sys.stdin); print(data[0]["id"] if data else "")'
)"
if [[ -z "$ESCALATION_ID" ]]; then
  echo "No open escalation found"
  exit 1
fi
echo "ESCALATION_ID=${ESCALATION_ID}"

log "Create executive decision from escalation"
DECISION_ID="$(
  curl -fsS -X POST "${BASE_URL}/api/executive-decisions/from-escalation/${ESCALATION_ID}" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: executive" \
  | json_field id
)"
echo "DECISION_ID=${DECISION_ID}"

log "Approve and complete executive decision"
curl -fsS -X POST "${BASE_URL}/api/executive-decisions/${DECISION_ID}/approve" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: executive" >/dev/null

curl -fsS -X POST "${BASE_URL}/api/executive-decisions/${DECISION_ID}/complete" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: executive" >/dev/null
echo "Executive decision workflow passed"

log "Capture KPI snapshot"
SNAPSHOT_ID="$(
  curl -fsS -X POST "${BASE_URL}/api/executive-kpi-snapshots/capture" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: executive" \
    -H "Content-Type: application/json" \
    -d '{"snapshot_label":"Enterprise Smoke Test KPI Snapshot"}' \
  | json_field id
)"
echo "SNAPSHOT_ID=${SNAPSHOT_ID}"

log "Generate KPI narrative"
curl -fsS "${BASE_URL}/api/executive-kpi-scheduler/narrative" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: executive" | python -m json.tool >/tmp/lumenai_kpi_narrative.json
cat /tmp/lumenai_kpi_narrative.json | grep -q "executive_summary"
echo "KPI narrative passed"

log "Create governance packet"
PACKET_ID="$(
  curl -fsS -X POST "${BASE_URL}/api/governance-packets" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: executive" \
    -H "Content-Type: application/json" \
    -d '{"packet_title":"Enterprise Smoke Test Governance Packet"}' \
  | json_field id
)"
echo "PACKET_ID=${PACKET_ID}"

log "Export governance packet"
PACKET_EXPORT_ID="$(
  curl -fsS -X POST "${BASE_URL}/api/governance-packets/${PACKET_ID}/exports" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: executive" \
  | json_field id
)"
echo "PACKET_EXPORT_ID=${PACKET_EXPORT_ID}"

log "Deliver governance packet"
curl -fsS -X POST "${BASE_URL}/api/governance-packets/${PACKET_ID}/deliver" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: executive" \
  -H "Content-Type: application/json" \
  -d "{\"export_id\":${PACKET_EXPORT_ID},\"delivery_channel\":\"internal\",\"delivery_target\":\"executive-governance-council\",\"message\":\"Enterprise smoke test governance packet delivery.\"}" \
  | python -m json.tool >/tmp/lumenai_packet_delivery.json
cat /tmp/lumenai_packet_delivery.json | grep -q "sent"
echo "Governance packet export and delivery passed"

log "Validate dashboard summary"
curl -fsS "${BASE_URL}/api/executive-briefing-dashboard/summary" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: executive" | python -m json.tool >/tmp/lumenai_dashboard_summary.json
cat /tmp/lumenai_dashboard_summary.json | grep -q "enterprise_access"
cat /tmp/lumenai_dashboard_summary.json | grep -q "enterprise_audit"
cat /tmp/lumenai_dashboard_summary.json | grep -q "executive_decisions"
echo "Dashboard summary passed"

log "Validate audit and access logs"
curl -fsS "${BASE_URL}/api/enterprise-audit-events/rollup" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: admin" | python -m json.tool >/tmp/lumenai_audit_rollup.json
cat /tmp/lumenai_audit_rollup.json | grep -q "total"

curl -fsS "${BASE_URL}/api/enterprise-access-control/rollup" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: admin" | python -m json.tool >/tmp/lumenai_access_rollup.json
cat /tmp/lumenai_access_rollup.json | grep -q "denied"
echo "Audit and access logs passed"

log "Artifact verification"
find generated_governance_packets -type f | sort | tail -10 || true
find generated_portfolio_briefings -type f | sort | tail -10 || true

echo
echo "ENTERPRISE SMOKE TEST PASSED"
