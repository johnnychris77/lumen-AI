#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-https://lumen-ai-53u4.onrender.com}"

echo "========================================"
echo "LumenAI Enterprise Investor Demo Seed"
echo "========================================"
echo "API URL: $API_URL"
echo

echo "Creating enterprise intake..."
INTAKE_RESPONSE=$(curl -sS -X POST "$API_URL/api/enterprise/intake" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-token" \
  -H "X-LumenAI-Role: operator" \
  -H "X-LumenAI-Actor: investor-demo-seed" \
  -H "X-Tenant-Id: bonsecours" \
  -H "X-Tenant-Name: Bon Secours" \
  -d '{
    "facility_name": "St. Mary’s Hospital",
    "department_name": "Sterile Processing",
    "vendor_name": "Medtronic",
    "instrument_name": "Frazier suction",
    "instrument_category": "lumened instrument",
    "finding_category": "bioburden / retained debris",
    "finding_description": "Suspected retained debris identified during borescope inspection. Finding represents potential patient-safety, infection-prevention, vendor-quality, and survey-readiness risk.",
    "severity": "critical",
    "confidence_score": 0.91,
    "recommended_action": "Quarantine + reclean + second inspection + IP review"
  }')

echo "$INTAKE_RESPONSE" | python -m json.tool

FINDING_ID=$(python - <<PY
import json
data = json.loads("""$INTAKE_RESPONSE""")
print(data.get("finding_id", ""))
PY
)

if [ -z "$FINDING_ID" ]; then
  echo "Could not determine finding_id"
  exit 1
fi

echo
echo "Finding ID: $FINDING_ID"

echo
echo "Completing human review..."
curl -sS -X POST "$API_URL/api/enterprise/intake/$FINDING_ID/review" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-token" \
  -H "X-LumenAI-Role: operator" \
  -H "X-LumenAI-Actor: investor-demo-seed" \
  -d '{
    "reviewer_name": "Quality Reviewer",
    "reviewer_role": "quality_reviewer",
    "decision": "escalate_to_ip",
    "review_notes": "Finding confirmed. Escalate to Infection Prevention and vendor-quality review due to retained debris risk.",
    "human_confirmed": true
  }' | python -m json.tool

echo
echo "Generating governance packet JSON..."
curl -sS "$API_URL/api/enterprise/intake/$FINDING_ID/governance-packet" \
  -H "Authorization: Bearer dev-token" \
  -H "X-LumenAI-Role: viewer" \
  -H "X-LumenAI-Actor: investor-demo-seed" \
  | python -m json.tool >/tmp/lumenai-investor-demo-packet.json

echo "Saved JSON packet preview to /tmp/lumenai-investor-demo-packet.json"

echo
echo "Opening CAPA..."
CAPA_RESPONSE=$(curl -sS -X POST "$API_URL/api/enterprise/intake/$FINDING_ID/capa" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-token" \
  -H "X-LumenAI-Role: operator" \
  -H "X-LumenAI-Actor: investor-demo-seed" \
  -d '{
    "title": "CAPA - Frazier suction retained debris concern",
    "description": "CAPA opened due to confirmed high-risk retained debris finding during borescope inspection. Corrective action includes quarantine, recleaning, second inspection, IP review, vendor-quality review, and trend monitoring.",
    "owner_id": null,
    "due_date": "2026-06-30",
    "status": "open"
  }')

echo "$CAPA_RESPONSE" | python -m json.tool

CAPA_ID=$(python - <<PY
import json
data = json.loads("""$CAPA_RESPONSE""")
print(data.get("capa_id", ""))
PY
)

if [ -n "$CAPA_ID" ]; then
  echo
  echo "Moving CAPA to in_progress..."
  curl -sS -X PATCH "$API_URL/api/enterprise/capas/$CAPA_ID/status" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer dev-token" \
    -H "X-LumenAI-Role: operator" \
    -H "X-LumenAI-Actor: investor-demo-seed" \
    -d '{
      "status": "in_progress",
      "note": "CAPA owner review started. Corrective action workflow is active."
    }' | python -m json.tool
fi

echo
echo "CAPA summary:"
curl -sS "$API_URL/api/enterprise/capas/summary" \
  -H "Authorization: Bearer dev-token" \
  -H "X-LumenAI-Role: viewer" \
  -H "X-LumenAI-Actor: investor-demo-seed" \
  | python -m json.tool

echo
echo "Audit trail:"
curl -sS "$API_URL/api/enterprise/audit-trail?limit=10" \
  -H "Authorization: Bearer dev-token" \
  -H "X-LumenAI-Role: auditor" \
  -H "X-LumenAI-Actor: investor-demo-seed" \
  | python -m json.tool

echo
echo "========================================"
echo "✅ LumenAI enterprise investor demo seeded"
echo "========================================"
echo "Open frontend:"
echo "https://lumen-ai-1.onrender.com"
