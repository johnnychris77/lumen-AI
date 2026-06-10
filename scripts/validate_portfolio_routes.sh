#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:5173}"

routes=(
  "/"
  "/dashboard"
  "/portfolio"
  "/portfolio/governance-hub"
  "/portfolio/governance-summary"
  "/portfolio/vendor-governance"
  "/portfolio/audit-command-center"
  "/portfolio/capa-workflow"
  "/portfolio/live-dashboard"
  "/portfolio/erp-style-governance"
  "/portfolio/customer-demo"
  "/portfolio/investor-review"
  "/portfolio/sales-readiness"
  "/portfolio/compliance-evidence"
  "/portfolio/vendor-accountability"
  "/portfolio/capa-governance"
  "/portfolio/audit-readiness"
)

echo "Validating LumenAI portfolio routes against: ${BASE_URL}"
echo

for route in "${routes[@]}"; do
  status="$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}${route}")"

  if [[ "$status" == "200" ]]; then
    echo "PASS ${status} ${route}"
  else
    echo "FAIL ${status} ${route}"
    exit 1
  fi
done

echo
echo "All portfolio routes passed."
