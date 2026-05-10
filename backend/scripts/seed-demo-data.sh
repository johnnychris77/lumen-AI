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

create_tenant() {
  local payload="$1"

  curl -fsS -X POST "${BASE_URL}/api/portfolio-tenants" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: operator" \
    -H "Content-Type: application/json" \
    -d "$payload" | json_field id
}

create_remediations_from_tenant() {
  local tenant_id="$1"

  curl -fsS -X POST "${BASE_URL}/api/tenant-remediations/from-insight/${tenant_id}" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: operator" \
  | python -c 'import sys,json; data=json.load(sys.stdin); print(",".join(str(item["id"]) for item in data))'
}

wait_for_api

log "Seeding executive demo tenants"

TENANT_CRITICAL=$(
  create_tenant '{
    "tenant_name":"Northstar Surgical Network",
    "industry":"healthcare",
    "go_live_status":"implementation",
    "health_status":"critical",
    "health_score":15,
    "renewal_risk":true,
    "implementation_risk":true,
    "governance_exception_count":3,
    "last_qbr_date":"2026-01-15",
    "next_qbr_date":"2026-03-10",
    "executive_owner":"Chief Customer Officer",
    "customer_success_owner":"CSM Bravo",
    "notes":"Critical tenant with renewal risk, implementation risk, overdue QBR, and governance exceptions."
  }'
)

TENANT_AT_RISK=$(
  create_tenant '{
    "tenant_name":"MetroCare System",
    "industry":"healthcare",
    "go_live_status":"implementation",
    "health_status":"at_risk",
    "health_score":55,
    "renewal_risk":false,
    "implementation_risk":true,
    "governance_exception_count":2,
    "last_qbr_date":"2026-02-10",
    "next_qbr_date":"2026-04-01",
    "executive_owner":"VP Customer Operations",
    "customer_success_owner":"CSM Charlie",
    "notes":"Implementation risk and governance exceptions require executive visibility."
  }'
)

TENANT_WATCH=$(
  create_tenant '{
    "tenant_name":"Riverside Health",
    "industry":"healthcare",
    "go_live_status":"live",
    "health_status":"watch",
    "health_score":72,
    "renewal_risk":false,
    "implementation_risk":false,
    "governance_exception_count":1,
    "last_qbr_date":"2026-04-15",
    "next_qbr_date":"2026-06-15",
    "executive_owner":"Regional Executive Sponsor",
    "customer_success_owner":"CSM Alpha",
    "notes":"Stable tenant with one governance exception under monitoring."
  }'
)

TENANT_HEALTHY=$(
  create_tenant '{
    "tenant_name":"Summit Specialty Partners",
    "industry":"healthcare",
    "go_live_status":"live",
    "health_status":"healthy",
    "health_score":92,
    "renewal_risk":false,
    "implementation_risk":false,
    "governance_exception_count":0,
    "last_qbr_date":"2026-04-22",
    "next_qbr_date":"2026-07-22",
    "executive_owner":"Account Executive",
    "customer_success_owner":"CSM Delta",
    "notes":"Healthy tenant used as positive benchmark."
  }'
)

TENANT_BOARD=$(
  create_tenant '{
    "tenant_name":"Atlantic Care Alliance",
    "industry":"healthcare",
    "go_live_status":"at_risk",
    "health_status":"critical",
    "health_score":25,
    "renewal_risk":true,
    "implementation_risk":true,
    "governance_exception_count":5,
    "last_qbr_date":"2026-01-05",
    "next_qbr_date":"2026-02-20",
    "executive_owner":"Chief Growth Officer",
    "customer_success_owner":"CSM Echo",
    "notes":"Board-attention tenant with multiple unresolved governance issues."
  }'
)

echo "Created tenants:"
echo "  TENANT_CRITICAL=${TENANT_CRITICAL}"
echo "  TENANT_AT_RISK=${TENANT_AT_RISK}"
echo "  TENANT_WATCH=${TENANT_WATCH}"
echo "  TENANT_HEALTHY=${TENANT_HEALTHY}"
echo "  TENANT_BOARD=${TENANT_BOARD}"

log "Creating remediation actions from tenant insights"

REMS_CRITICAL="$(create_remediations_from_tenant "$TENANT_CRITICAL")"
REMS_AT_RISK="$(create_remediations_from_tenant "$TENANT_AT_RISK")"
REMS_BOARD="$(create_remediations_from_tenant "$TENANT_BOARD")"

echo "Critical tenant remediations: ${REMS_CRITICAL}"
echo "At-risk tenant remediations: ${REMS_AT_RISK}"
echo "Board tenant remediations: ${REMS_BOARD}"

FIRST_CRITICAL_REM="$(echo "$REMS_CRITICAL" | cut -d',' -f1)"
FIRST_BOARD_REM="$(echo "$REMS_BOARD" | cut -d',' -f1)"

log "Escalating selected remediation actions"

if [[ -n "${FIRST_CRITICAL_REM}" ]]; then
  curl -fsS -X PATCH "${BASE_URL}/api/tenant-remediations/${FIRST_CRITICAL_REM}" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: operator" \
    -H "Content-Type: application/json" \
    -d '{"status":"escalated"}' >/dev/null
fi

if [[ -n "${FIRST_BOARD_REM}" ]]; then
  curl -fsS -X PATCH "${BASE_URL}/api/tenant-remediations/${FIRST_BOARD_REM}" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: operator" \
    -H "Content-Type: application/json" \
    -d '{"status":"blocked"}' >/dev/null
fi

log "Running executive escalation scan"

curl -fsS -X POST "${BASE_URL}/api/executive-escalations/run" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: executive" | python -m json.tool >/tmp/lumenai_demo_escalation_scan.json

cat /tmp/lumenai_demo_escalation_scan.json

log "Creating executive decision from top open escalation"

ESCALATION_ID="$(
  curl -fsS "${BASE_URL}/api/executive-escalations/open" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: executive" \
  | python -c 'import sys,json; data=json.load(sys.stdin); print(data[0]["id"] if data else "")'
)"

if [[ -n "$ESCALATION_ID" ]]; then
  DECISION_ID="$(
    curl -fsS -X POST "${BASE_URL}/api/executive-decisions/from-escalation/${ESCALATION_ID}" \
      -H "$AUTH_HEADER" \
      -H "X-LumenAI-Role: executive" \
    | json_field id
  )"

  echo "Created executive decision: ${DECISION_ID}"

  curl -fsS -X POST "${BASE_URL}/api/executive-decisions/${DECISION_ID}/approve" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: executive" >/dev/null

  echo "Approved executive decision: ${DECISION_ID}"
else
  echo "No open escalation found; skipping decision creation"
fi

log "Capturing KPI snapshots"

curl -fsS -X POST "${BASE_URL}/api/executive-kpi-snapshots/capture" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: executive" \
  -H "Content-Type: application/json" \
  -d '{"snapshot_label":"Demo Baseline Executive KPI Snapshot"}' | python -m json.tool >/tmp/lumenai_demo_kpi_1.json

curl -fsS -X POST "${BASE_URL}/api/executive-kpi-snapshots/capture" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: executive" \
  -H "Content-Type: application/json" \
  -d '{"snapshot_label":"Demo Follow-up Executive KPI Snapshot"}' | python -m json.tool >/tmp/lumenai_demo_kpi_2.json

echo "Captured KPI snapshots"

log "Generating governance packet and exports"

PACKET_ID="$(
  curl -fsS -X POST "${BASE_URL}/api/governance-packets" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: executive" \
    -H "Content-Type: application/json" \
    -d '{"packet_title":"Demo Executive Governance Packet"}' \
  | json_field id
)"

PACKET_EXPORT_ID="$(
  curl -fsS -X POST "${BASE_URL}/api/governance-packets/${PACKET_ID}/exports" \
    -H "$AUTH_HEADER" \
    -H "X-LumenAI-Role: executive" \
  | json_field id
)"

curl -fsS -X POST "${BASE_URL}/api/governance-packets/${PACKET_ID}/deliver" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: executive" \
  -H "Content-Type: application/json" \
  -d "{\"export_id\":${PACKET_EXPORT_ID},\"delivery_channel\":\"internal\",\"delivery_target\":\"executive-governance-council\",\"message\":\"Demo governance packet ready for executive review.\"}" \
  | python -m json.tool >/tmp/lumenai_demo_packet_delivery.json

echo "PACKET_ID=${PACKET_ID}"
echo "PACKET_EXPORT_ID=${PACKET_EXPORT_ID}"

log "Generating RBAC proof activity"

curl -sS -o /tmp/lumenai_demo_rbac_deny.json -w "Viewer write deny HTTP status: %{http_code}\n" \
  -X POST "${BASE_URL}/api/portfolio-tenants" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: viewer" \
  -H "Content-Type: application/json" \
  -d '{"tenant_name":"Demo Viewer Deny Proof"}'

curl -fsS "${BASE_URL}/api/enterprise-access-control/rollup" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: admin" | python -m json.tool >/tmp/lumenai_demo_access_rollup.json

curl -fsS "${BASE_URL}/api/enterprise-audit-events/rollup" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: admin" | python -m json.tool >/tmp/lumenai_demo_audit_rollup.json

log "Demo data seed summary"

curl -fsS "${BASE_URL}/api/executive-briefing-dashboard/summary" \
  -H "$AUTH_HEADER" \
  -H "X-LumenAI-Role: executive" | python -m json.tool >/tmp/lumenai_demo_dashboard_summary.json

python - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/lumenai_demo_dashboard_summary.json").read_text())

print("Demo Summary:")
for key in [
    "portfolio_intelligence",
    "tenant_remediations",
    "executive_escalations",
    "executive_decisions",
    "executive_kpi_trends",
    "governance_packets",
    "enterprise_audit",
    "enterprise_access",
]:
    if key in data:
        print(f"- {key}: {data[key]}")
PY

echo
echo "DEMO DATA SEED COMPLETE"
echo "Open dashboard:"
echo "${BASE_URL}/api/executive-briefing-dashboard/view"
