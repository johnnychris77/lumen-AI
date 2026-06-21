# LumenAI Staging Smoke Test Runbook

## Overview

Run this runbook after every staging deployment to verify all critical API endpoints are functioning before promoting to production.

**Prerequisites**:
```bash
export STAGING_URL=https://api.staging.lumenai.health
export TOKEN=""  # Set after step 3
```

---

## Smoke Test Steps

### Step 1: Health Check
```bash
curl -si "${STAGING_URL}/health"
```
**Expected**: HTTP 200
```json
{"status": "ok", "version": "P11", "environment": "staging"}
```
**Fail action**: Backend pod is down — check `kubectl get pods -n lumenai-staging`

---

### Step 2: Readiness Check
```bash
curl -si "${STAGING_URL}/ready"
```
**Expected**: HTTP 200
```json
{"status": "ready", "database": "ok"}
```
**Fail action**: Database unreachable — check DB connection string and RDS status

---

### Step 3: Authentication
```bash
LOGIN_RESPONSE=$(curl -si -X POST "${STAGING_URL}/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "smoketest@lumenai.health", "password": "<staging-password>"}')
echo "$LOGIN_RESPONSE"
export TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
```
**Expected**: HTTP 200 with `access_token`

**Dev-token alternative (if OIDC not configured in staging)**:
```bash
export AUTH_HEADER="X-LumenAI-Role: admin"
# Use -H "$AUTH_HEADER" instead of -H "Authorization: Bearer $TOKEN" below
```

---

### Step 4: Executive Dashboard
```bash
curl -si "${STAGING_URL}/api/executive-dashboard" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-LumenAI-Tenant-Id: smoke-test"
```
**Expected**: HTTP 200 with JSON containing dashboard data

---

### Step 5: Vendor Intelligence
```bash
curl -si "${STAGING_URL}/api/vendor-intelligence/vendors" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-LumenAI-Tenant-Id: smoke-test"
```
**Expected**: HTTP 200 with vendor list (may be empty array `[]`)

---

### Step 6: Baseline Upload
```bash
curl -si -X POST "${STAGING_URL}/api/baseline/upload" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-LumenAI-Tenant-Id: smoke-test" \
  -F "file=@/tmp/test-baseline.csv"
```
**Expected**: HTTP 200

*Create test file if needed*:
```bash
echo "device_id,status\nDEV001,active" > /tmp/test-baseline.csv
```

---

### Step 7: Inspection Ranking (CV Analysis)
```bash
curl -si -X POST "${STAGING_URL}/api/cv/analyze" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-LumenAI-Tenant-Id: smoke-test" \
  -H "Content-Type: application/json" \
  -d '{"device_type": "infusion_pump", "image_url": "https://example.com/test.jpg"}'
```
**Expected**: HTTP 200 with `ai_findings` field in response

---

### Step 8: Audit Evidence Export
```bash
curl -si -X POST "${STAGING_URL}/api/regulatory/audit-package" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-LumenAI-Tenant-Id: smoke-test" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "smoke-test", "period": "2026-Q1"}'
```
**Expected**: HTTP 200

---

### Step 9: PDF Export
```bash
curl -si -X POST "${STAGING_URL}/api/regulatory/audit-package/pdf" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-LumenAI-Tenant-Id: smoke-test" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "smoke-test"}' \
  -o /tmp/audit-package-smoke.pdf
```
**Expected**: HTTP 200 with `Content-Type: application/pdf`

Verify PDF is valid:
```bash
file /tmp/audit-package-smoke.pdf  # Should output: PDF document
```

---

### Step 10: Digital Twin State
```bash
curl -si "${STAGING_URL}/api/digital-twin/state" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-LumenAI-Tenant-Id: smoke-test"
```
**Expected**: HTTP 200 with `stations` field in response

---

### Step 11: Copilot Session
```bash
curl -si -X POST "${STAGING_URL}/api/copilot/sessions" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-LumenAI-Tenant-Id: smoke-test" \
  -H "Content-Type: application/json" \
  -d '{"context": "inspection_review"}'
```
**Expected**: HTTP 200 with `steps` field in response

---

### Step 12: Predictive Dashboard
```bash
curl -si "${STAGING_URL}/api/predictions/dashboard" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-LumenAI-Tenant-Id: smoke-test"
```
**Expected**: HTTP 200 with ROI metric in response

---

## Automated Smoke Test Script

Save as `scripts/smoke-test.sh`:
```bash
#!/bin/bash
set -euo pipefail

BASE_URL="${STAGING_URL:-https://api.staging.lumenai.health}"
PASS=0
FAIL=0

check() {
  local name="$1"
  local url="$2"
  local method="${3:-GET}"
  local expected_status="${4:-200}"

  status=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$url" \
    -H "Authorization: Bearer ${TOKEN:-}" \
    -H "X-LumenAI-Tenant-Id: smoke-test")

  if [ "$status" = "$expected_status" ]; then
    echo "  PASS: $name ($status)"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $name (expected $expected_status, got $status)"
    FAIL=$((FAIL + 1))
  fi
}

echo "Running smoke tests against $BASE_URL"
echo ""

check "Health"              "$BASE_URL/health"
check "Ready"               "$BASE_URL/ready"
check "Executive Dashboard" "$BASE_URL/api/executive-dashboard"
check "Vendor Intelligence" "$BASE_URL/api/vendor-intelligence/vendors"
check "Digital Twin State"  "$BASE_URL/api/digital-twin/state"
check "Predictions"         "$BASE_URL/api/predictions/dashboard"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && echo "SMOKE TEST PASSED" || { echo "SMOKE TEST FAILED"; exit 1; }
```

---

## Sign-Off Checklist

After all steps pass:
- [ ] Step 1 — /health → 200 ✓
- [ ] Step 2 — /ready → 200 ✓
- [ ] Step 3 — Auth token received ✓
- [ ] Step 4 — Executive dashboard loads ✓
- [ ] Step 5 — Vendor list accessible ✓
- [ ] Step 6 — Baseline upload accepted ✓
- [ ] Step 7 — CV analysis returns ai_findings ✓
- [ ] Step 8 — Audit package generated ✓
- [ ] Step 9 — PDF export valid ✓
- [ ] Step 10 — Digital twin returns stations ✓
- [ ] Step 11 — Copilot session has steps ✓
- [ ] Step 12 — Predictions dashboard has ROI metric ✓

**Approved by**: __________________ **Date**: __________

*Only after all steps pass should production deployment be approved.*
