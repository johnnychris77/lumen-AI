#!/usr/bin/env bash
set -euo pipefail

OUT_FILE="docs/portfolio-evidence/EVIDENCE_SUMMARY.md"
SCREENSHOT_DIR="docs/portfolio-evidence/screenshots"
PROOF_DIR="docs/portfolio-evidence/terminal-proof"

mkdir -p "$SCREENSHOT_DIR"
mkdir -p "$PROOF_DIR"

cat > "$OUT_FILE" <<'SUMMARY'
# LumenAI Portfolio Evidence Summary

## Project

LumenAI — Enterprise Executive Intelligence Platform

## Product Proof

LumenAI demonstrates:

- public demo landing page
- executive dashboard
- tenant intelligence
- remediation workflow
- executive escalation cadence
- governance packet export
- KPI trend engine
- executive decision log
- enterprise audit trail
- RBAC policy guardrails
- production readiness
- hosted demo validation
- quality gate discipline

## Screenshot Evidence

SUMMARY

if find "$SCREENSHOT_DIR" -type f | grep -q .; then
  find "$SCREENSHOT_DIR" -type f | sort | while read -r file; do
    echo "- ${file}" >> "$OUT_FILE"
  done
else
  echo "- No screenshots added yet." >> "$OUT_FILE"
fi

cat >> "$OUT_FILE" <<'SUMMARY'

## Terminal Proof Evidence

SUMMARY

if find "$PROOF_DIR" -type f | grep -q .; then
  find "$PROOF_DIR" -type f | sort | while read -r file; do
    echo "- ${file}" >> "$OUT_FILE"
  done
else
  echo "- No terminal proof files added yet." >> "$OUT_FILE"
fi

cat >> "$OUT_FILE" <<'SUMMARY'

## Interview Talking Point

LumenAI shows how operational risk can be converted into an executive operating workflow:

risk detection
→ insight generation
→ remediation ownership
→ escalation cadence
→ governance packet
→ executive decision
→ KPI trend
→ audit and RBAC governance
SUMMARY

echo "Generated ${OUT_FILE}"
