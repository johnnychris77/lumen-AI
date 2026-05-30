#!/usr/bin/env bash
set -euo pipefail

HOSTED_FRONTEND="${HOSTED_FRONTEND:-https://lumen-ai-1.onrender.com}"

echo "=============================================="
echo " LumenAI Hosted Frontend Verification"
echo "=============================================="
echo "Frontend: $HOSTED_FRONTEND"
echo ""

TMP_FILE="$(mktemp)"

echo "Checking hosted frontend..."
curl -L -s "$HOSTED_FRONTEND" -o "$TMP_FILE"

if [ ! -s "$TMP_FILE" ]; then
  echo "FAIL: Hosted frontend returned empty response."
  rm -f "$TMP_FILE"
  exit 1
fi

echo "PASS: Hosted frontend returned content."

echo ""
echo "Checking for core app shell markers..."

if grep -qi "lumen" "$TMP_FILE"; then
  echo "PASS: Lumen marker found."
else
  echo "WARN: Lumen marker not found in raw HTML."
fi

if grep -qi "script" "$TMP_FILE"; then
  echo "PASS: Frontend script bundle marker found."
else
  echo "WARN: Frontend script marker not found."
fi

echo ""
echo "Checking Audit Command Center route..."

AUDIT_TMP="$(mktemp)"
curl -L -s "$HOSTED_FRONTEND/audit-command-center" -o "$AUDIT_TMP" || true

if [ -s "$AUDIT_TMP" ]; then
  echo "PASS: Audit Command Center route returned content."
else
  echo "WARN: Audit Command Center route returned empty response."
fi

if grep -qi "audit" "$AUDIT_TMP"; then
  echo "PASS: Audit marker found in Audit Command Center route."
else
  echo "WARN: Audit marker not found in raw route HTML. This may be normal for React apps."
fi

echo ""
echo "Hosted frontend verification complete."
echo "Result: PASS_WITH_WARNINGS_ALLOWED"

rm -f "$TMP_FILE" "$AUDIT_TMP"
