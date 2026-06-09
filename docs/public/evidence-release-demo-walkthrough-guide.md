# LumenAI Evidence Release Demo Walkthrough Guide

## Walkthrough Status

Status: Ready for public portfolio, customer review, investor demo, and enterprise leadership presentation.

This guide explains how to present the LumenAI Compliance Evidence v1.0 workflow from demo setup through evidence generation, verification, and customer-facing summary review.

## Release Name

LumenAI Compliance Evidence v1.0

## Release Tag

compliance-evidence-v1.0

## Demo Purpose

The demo shows how LumenAI converts healthcare operations audit activity into tamper-evident compliance evidence.

The walkthrough demonstrates:

- Enterprise audit event creation
- Compliance evidence bundle generation
- Audit export hash display
- Manifest hash display
- Bundle hash display
- Bundle verification
- Public verification summary
- Downloadable JSON evidence artifact
- Public evidence documentation

## Intended Audience

This walkthrough can be used with:

- Hospital executives
- Sterile processing directors
- Quality and safety leaders
- Compliance reviewers
- Vendor governance stakeholders
- Enterprise healthcare buyers
- Strategic partners
- Investors
- Public portfolio reviewers

## Demo Prerequisites

Backend should be running locally:

cd backend
source /home/ohna/lumen-ai/lumen-AI/.venv-backend/bin/activate
export DATABASE_URL="sqlite:///./lumenai.db"
export PYTHONPATH=.
export AUTH_MODE=dev
export DEV_AUTH_TOKEN=dev-token
uvicorn app.main:app --reload --port 8000

Frontend can be run separately if showing the UI:

cd frontend
nvm use 20.19.0
npm run dev

## Demo Script Command

Run the demo script from the repository root:

BASE_URL="http://127.0.0.1:8000" ./scripts/demo_compliance_evidence_bundle.sh

Optional custom output directory:

OUTPUT_DIR="/tmp/my-lumenai-demo" BASE_URL="http://127.0.0.1:8000" ./scripts/demo_compliance_evidence_bundle.sh

## Demo Output Location

Default output directory:

/tmp/lumenai-compliance-evidence-demo

Expected artifacts:

- audit_event.json
- bundle_response.json
- bundle_verify.json
- bundle_summary.json
- lumenai-compliance-evidence-bundle.json
- bundle_download_headers.txt
- demo_summary.txt

## Walkthrough Steps

### Step 1 — Explain the Problem

Healthcare operations evidence is often spread across spreadsheets, emails, screenshots, and informal logs.

This makes it difficult to prove what happened, when it happened, who generated evidence, whether an export changed, and whether a customer-facing verification summary can be safely shared.

### Step 2 — Introduce the LumenAI Evidence Workflow

Explain that LumenAI creates a tamper-evident evidence chain:

1. Audit event is recorded.
2. Audit evidence is exported.
3. Export receives SHA-256 hash.
4. Manifest binds export hash to metadata.
5. Manifest receives SHA-256 hash.
6. Evidence bundle binds export hash, manifest hash, controls, and verification URLs.
7. Bundle receives SHA-256 hash.
8. Verification endpoints confirm recorded evidence.
9. Public verification summary provides safe proof.

### Step 3 — Run the Demo Script

Run:

BASE_URL="http://127.0.0.1:8000" ./scripts/demo_compliance_evidence_bundle.sh

Point out the script sections:

- Preflight backend check
- Creating demo audit event
- Generating compliance evidence bundle
- Verifying bundle hash
- Loading public verification summary
- Downloading evidence bundle JSON artifact
- Writing demo summary

### Step 4 — Show the Bundle Hash

Open or display:

/tmp/lumenai-compliance-evidence-demo/demo_summary.txt

Highlight:

- Bundle hash
- Bundle event ID
- Audit export hash
- Manifest hash
- Verified status
- Tamper-evident status
- Export count

### Step 5 — Show the Downloaded JSON Artifact

Open:

/tmp/lumenai-compliance-evidence-demo/lumenai-compliance-evidence-bundle.json

Explain that this artifact is the downloadable compliance evidence bundle.

It contains structured evidence metadata, audit export hash, manifest hash, verification URLs, compliance controls, and audit linkage.

### Step 6 — Show Verification Output

Open:

/tmp/lumenai-compliance-evidence-demo/bundle_verify.json

Explain that this confirms the bundle hash exists in the recorded audit trail.

### Step 7 — Show Public Verification Summary

Open:

/tmp/lumenai-compliance-evidence-demo/bundle_summary.json

Explain that this is the safe customer-facing proof summary. It does not expose full audit details but confirms verification status, hashes, generated timestamp, tamper-evident status, and compliance controls.

### Step 8 — Show Frontend Evidence UI

In the frontend, show:

- Compliance Evidence Bundle card
- Generate Evidence Bundle button
- Download Bundle JSON button
- View Verification Summary button
- Evidence Bundle Verification panel
- Paste bundle hash verification workflow

### Step 9 — Show Public Documentation

Open:

- docs/public/evidence-index.md
- docs/public/compliance-evidence.md
- docs/public/evidence-release-customer-review-packet.md
- docs/public/evidence-release-investor-brief.md
- docs/public/evidence-release-sales-one-pager.md
- docs/public/evidence-release-market-positioning-brief.md

Explain that the repo contains public-facing proof, customer review materials, investor positioning, sales enablement, and release documentation.

## Demo Talk Track

Use this concise talk track:

LumenAI converts healthcare operations audit activity into tamper-evident compliance evidence. In this demo, we create an audit event, generate a compliance evidence bundle, compute SHA-256 hashes for the export, manifest, and bundle, verify the bundle hash, and produce a safe customer-facing verification summary. This demonstrates auditability, evidence traceability, vendor governance readiness, and enterprise trust.

## Key Proof Points to Highlight

- SHA-256 audit export hash
- SHA-256 manifest hash
- SHA-256 bundle hash
- Recorded audit event linkage
- Verification endpoint response
- Public verification summary
- Downloadable JSON evidence artifact
- Frontend verification panel
- Public evidence index and documentation

## Customer Questions This Demo Answers

- What evidence was generated?
- Who generated it?
- When was it generated?
- What was included?
- Was the export hashed?
- Was a manifest generated?
- Was the bundle hashed?
- Can the bundle be verified?
- Can a safe summary be shared?

## Final Demo Statement

LumenAI Compliance Evidence v1.0 demonstrates a complete evidence workflow from audit event to verified customer-facing proof summary.

Demo Walkthrough Guide: Complete.
