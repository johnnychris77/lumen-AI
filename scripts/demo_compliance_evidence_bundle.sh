#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
TOKEN="${TOKEN:-dev-token}"
ROLE="${ROLE:-enterprise_admin}"
ACTOR="${ACTOR:-demo-compliance-admin}"
TENANT_ID="${TENANT_ID:-demo-compliance-tenant}"
ACTION_TYPE="${ACTION_TYPE:-compliance_evidence_bundle_demo}"
RESOURCE_TYPE="${RESOURCE_TYPE:-demo_compliance_resource}"
RESOURCE_ID="${RESOURCE_ID:-demo-resource-001}"
OUTPUT_DIR="${OUTPUT_DIR:-/tmp/lumenai-compliance-evidence-demo}"

mkdir -p "${OUTPUT_DIR}"

AUDIT_EVENT_FILE="${OUTPUT_DIR}/audit_event.json"
BUNDLE_RESPONSE_FILE="${OUTPUT_DIR}/bundle_response.json"
BUNDLE_VERIFY_FILE="${OUTPUT_DIR}/bundle_verify.json"
BUNDLE_SUMMARY_FILE="${OUTPUT_DIR}/bundle_summary.json"
BUNDLE_DOWNLOAD_FILE="${OUTPUT_DIR}/lumenai-compliance-evidence-bundle.json"
BUNDLE_DOWNLOAD_HEADERS_FILE="${OUTPUT_DIR}/bundle_download_headers.txt"
DEMO_SUMMARY_FILE="${OUTPUT_DIR}/demo_summary.txt"
BUNDLE_HASH_FILE="${OUTPUT_DIR}/bundle_hash.txt"

AUTH_HEADERS=(
  -H "Authorization: Bearer ${TOKEN}"
  -H "X-LumenAI-Role: ${ROLE}"
  -H "X-LumenAI-Actor: ${ACTOR}"
  -H "X-LumenAI-Tenant-ID: ${TENANT_ID}"
  -H "X-Request-ID: demo-request-001"
  -H "X-Correlation-ID: demo-correlation-001"
)

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: Required command not found: $1"
    exit 1
  fi
}

print_step() {
  echo
  echo "== $1 =="
}

print_kv() {
  printf "   %-24s %s\n" "$1:" "$2"
}

require_command curl
require_command python

print_step "LumenAI Compliance Evidence Bundle Demo"
print_kv "Base URL" "${BASE_URL}"
print_kv "Tenant" "${TENANT_ID}"
print_kv "Actor" "${ACTOR}"
print_kv "Role" "${ROLE}"
print_kv "Output directory" "${OUTPUT_DIR}"

print_step "Preflight backend check"
if curl -sS "${BASE_URL}/openapi.json" >/dev/null 2>&1; then
  echo "   Backend reachable."
else
  echo "   WARNING: Backend health check failed at ${BASE_URL}/openapi.json"
  echo "   Make sure the backend is running before continuing."
fi

print_step "1. Creating demo audit event"
curl -sS -X POST "${BASE_URL}/api/enterprise/audit/events"   "${AUTH_HEADERS[@]}"   -H "Content-Type: application/json"   -d "{
    \"action_type\": \"${ACTION_TYPE}\",
    \"resource_type\": \"${RESOURCE_TYPE}\",
    \"resource_id\": \"${RESOURCE_ID}\",
    \"details\": {
      \"workflow\": \"compliance-evidence-bundle-demo\",
      \"demo\": true,
      \"source\": \"public-demo-script\"
    }
  }"   -o "${AUDIT_EVENT_FILE}" || true

print_kv "Audit event file" "${AUDIT_EVENT_FILE}"

print_step "2. Generating compliance evidence bundle"
curl -sS -G "${BASE_URL}/api/enterprise/audit/evidence-bundle"   "${AUTH_HEADERS[@]}"   --data-urlencode "tenant_id=${TENANT_ID}"   --data-urlencode "action_type=${ACTION_TYPE}"   --data-urlencode "limit=200"   -o "${BUNDLE_RESPONSE_FILE}"

python - <<PYTHON
import json
from pathlib import Path

payload = json.loads(Path("${BUNDLE_RESPONSE_FILE}").read_text())

bundle_hash = payload.get("bundle_hash", "")
bundle = payload.get("bundle", {})
audit_export = bundle.get("audit_export", {})
manifest = bundle.get("manifest", {})

Path("${BUNDLE_HASH_FILE}").write_text(bundle_hash)

print(f"   Bundle hash:          {bundle_hash}")
print(f"   Bundle algorithm:     {payload.get('bundle_hash_algorithm', '')}")
print(f"   Bundle event ID:      {payload.get('bundle_event_id', '')}")
print(f"   Audit export hash:    {audit_export.get('audit_export_hash', '')}")
print(f"   Manifest hash:        {manifest.get('manifest_hash', '')}")
print(f"   Export count:         {audit_export.get('count', '')}")
PYTHON

BUNDLE_HASH="$(cat "${BUNDLE_HASH_FILE}")"

if [[ -z "${BUNDLE_HASH}" || "${BUNDLE_HASH}" == "None" ]]; then
  echo "ERROR: Bundle hash was not generated."
  cat "${BUNDLE_RESPONSE_FILE}"
  exit 1
fi

print_step "3. Verifying bundle hash"
curl -sS -G "${BASE_URL}/api/enterprise/audit/evidence-bundle/verify"   "${AUTH_HEADERS[@]}"   --data-urlencode "bundle_hash=${BUNDLE_HASH}"   -o "${BUNDLE_VERIFY_FILE}"

python - <<PYTHON
import json
from pathlib import Path

payload = json.loads(Path("${BUNDLE_VERIFY_FILE}").read_text())

print(f"   Verified:             {payload.get('verified')}")
print(f"   Message:              {payload.get('message')}")
print(f"   Event ID:             {payload.get('event_id')}")
print(f"   Audit export hash:    {payload.get('audit_export_hash')}")
print(f"   Manifest hash:        {payload.get('manifest_hash')}")
PYTHON

print_step "4. Loading public verification summary"
curl -sS -G "${BASE_URL}/api/enterprise/audit/evidence-bundle/verification-summary"   "${AUTH_HEADERS[@]}"   --data-urlencode "bundle_hash=${BUNDLE_HASH}"   -o "${BUNDLE_SUMMARY_FILE}"

python - <<PYTHON
import json
from pathlib import Path

payload = json.loads(Path("${BUNDLE_SUMMARY_FILE}").read_text())

print(f"   Summary type:         {payload.get('summary_type')}")
print(f"   Verified:             {payload.get('verified')}")
print(f"   Tamper evident:       {payload.get('tamper_evident')}")
print(f"   Generated by:         {payload.get('generated_by')}")
print(f"   Generated at:         {payload.get('generated_at')}")
print(f"   Controls:             {', '.join(payload.get('compliance_controls', []))}")
PYTHON

print_step "5. Downloading evidence bundle JSON artifact"
curl -sS -G "${BASE_URL}/api/enterprise/audit/evidence-bundle/download.json"   "${AUTH_HEADERS[@]}"   --data-urlencode "tenant_id=${TENANT_ID}"   --data-urlencode "action_type=${ACTION_TYPE}"   --data-urlencode "limit=200"   -D "${BUNDLE_DOWNLOAD_HEADERS_FILE}"   -o "${BUNDLE_DOWNLOAD_FILE}"

print_kv "Bundle JSON" "${BUNDLE_DOWNLOAD_FILE}"
print_kv "Bundle headers" "${BUNDLE_DOWNLOAD_HEADERS_FILE}"

print_step "6. Writing demo summary"
python - <<PYTHON
import json
from pathlib import Path

bundle_response = json.loads(Path("${BUNDLE_RESPONSE_FILE}").read_text())
verification = json.loads(Path("${BUNDLE_VERIFY_FILE}").read_text())
summary = json.loads(Path("${BUNDLE_SUMMARY_FILE}").read_text())

bundle = bundle_response.get("bundle", {})
audit_export = bundle.get("audit_export", {})
manifest = bundle.get("manifest", {})

lines = [
    "LumenAI Compliance Evidence Bundle Demo Summary",
    "",
    "Base URL: ${BASE_URL}",
    "Tenant ID: ${TENANT_ID}",
    "Actor: ${ACTOR}",
    f"Bundle hash: {bundle_response.get('bundle_hash', '')}",
    f"Bundle event ID: {bundle_response.get('bundle_event_id', '')}",
    f"Audit export hash: {audit_export.get('audit_export_hash', '')}",
    f"Manifest hash: {manifest.get('manifest_hash', '')}",
    f"Verified: {verification.get('verified')}",
    f"Tamper evident: {summary.get('tamper_evident')}",
    f"Export count: {audit_export.get('count', '')}",
    "",
    "Artifacts:",
    f"- Audit event: ${AUDIT_EVENT_FILE}",
    f"- Bundle response: ${BUNDLE_RESPONSE_FILE}",
    f"- Bundle verification: ${BUNDLE_VERIFY_FILE}",
    f"- Verification summary: ${BUNDLE_SUMMARY_FILE}",
    f"- Bundle JSON: ${BUNDLE_DOWNLOAD_FILE}",
    f"- Download headers: ${BUNDLE_DOWNLOAD_HEADERS_FILE}",
]

Path("${DEMO_SUMMARY_FILE}").write_text("\n".join(lines) + "\n")
print(Path("${DEMO_SUMMARY_FILE}").read_text())
PYTHON

print_step "Demo complete"
print_kv "Summary" "${DEMO_SUMMARY_FILE}"
print_kv "Output directory" "${OUTPUT_DIR}"
