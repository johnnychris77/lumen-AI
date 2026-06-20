# LumenAI Evidence Index

## Purpose

This index provides a single navigation point for LumenAI’s enterprise compliance evidence, public portfolio artifacts, demo workflow, release lock, and validation coverage.

LumenAI now includes a tamper-evident compliance evidence workflow designed for enterprise healthcare operations, sterile processing governance, vendor accountability, and audit readiness.

## Public Portfolio Evidence

### Compliance Evidence Summary

Path:

docs/public/compliance-evidence.md

Purpose:

Explains the LumenAI compliance evidence workflow in customer-facing language, including audit exports, SHA-256 hashes, manifests, bundle verification, and public verification summaries.

### Compliance Evidence Badge

Path:

docs/public/lumenai-compliance-evidence-badge.md

Purpose:

Provides concise public badge language confirming that LumenAI includes tamper-evident compliance evidence capabilities.

### Final Launch Summary

Path:

docs/public/final-launch-summary.md

Purpose:

Summarizes the enterprise compliance evidence launch, including audit logging, export hashing, manifests, evidence bundles, verification endpoints, downloadable bundle JSON, and frontend UI.

### Release Lock

Path:

docs/public/compliance-evidence-release-lock.md

Purpose:

Confirms that the compliance evidence workflow is release-locked for public portfolio and enterprise customer review.

## Demo Evidence

### Compliance Evidence Bundle Demo README

Path:

docs/compliance/evidence-bundle-demo.md

Purpose:

Documents the evidence bundle demo workflow, key endpoints, tamper-evidence chain, and demo authorization headers.

### Compliance Evidence Bundle Demo Script

Path:

scripts/demo_compliance_evidence_bundle.sh

Purpose:

Runs a repeatable local demo that creates a demo audit event, generates a compliance evidence bundle, verifies the bundle hash, loads the verification summary, and downloads the bundle JSON artifact.

## Backend Evidence Services

### Audit Export Service

Path:

backend/app/services/audit_export_service.py

Purpose:

Generates filtered audit CSV exports, computes SHA-256 export hashes, creates manifests, and records audit export events.

### Audit Export Verification Service

Path:

backend/app/services/audit_export_verification_service.py

Purpose:

Verifies audit export hashes and manifest hashes against recorded audit events.

### Compliance Evidence Bundle Service

Path:

backend/app/services/compliance_evidence_bundle_service.py

Purpose:

Builds the JSON compliance evidence bundle, computes the bundle hash, and records bundle-generation audit events.

### Compliance Evidence Bundle Verification Service

Path:

backend/app/services/compliance_evidence_bundle_verification_service.py

Purpose:

Verifies evidence bundle hashes against recorded audit events.

### Compliance Evidence Summary Service

Path:

backend/app/services/compliance_evidence_summary_service.py

Purpose:

Builds safe customer-facing verification summaries without exposing full audit details.

## Protected Enterprise Endpoints

### Audit CSV Export

GET /api/enterprise/audit/events/export.csv

### Audit Export Hash Verification

GET /api/enterprise/audit/events/export/verify?audit_export_hash=<HASH>

### Audit Manifest Hash Verification

GET /api/enterprise/audit/events/export/manifest/verify?manifest_hash=<HASH>

### Compliance Evidence Bundle Generation

GET /api/enterprise/audit/evidence-bundle

### Compliance Evidence Bundle Download

GET /api/enterprise/audit/evidence-bundle/download.json

### Compliance Evidence Bundle Verification

GET /api/enterprise/audit/evidence-bundle/verify?bundle_hash=<HASH>

### Public Verification Summary

GET /api/enterprise/audit/evidence-bundle/verification-summary?bundle_hash=<HASH>

## Frontend Evidence UI

### Vendor Baseline Subscription Portal

Path:

frontend/src/components/VendorBaselineSubscriptionPortal.tsx

Purpose:

Includes the compliance evidence bundle card and evidence bundle verification panel.

Frontend capabilities:

- Generate evidence bundle
- Display bundle hash
- Display audit export hash
- Display manifest hash
- Download bundle JSON
- View verification summary
- Verify pasted bundle hash

## Test Evidence

### Audit Export and Hash Tests

- backend/tests/test_audit_csv_export.py
- backend/tests/test_audit_export_hash.py
- backend/tests/test_audit_export_verification.py
- backend/tests/test_audit_export_manifest.py
- backend/tests/test_audit_export_manifest_verification.py

### Compliance Evidence Bundle Tests

- backend/tests/test_compliance_evidence_bundle.py
- backend/tests/test_compliance_evidence_bundle_verification.py
- backend/tests/test_compliance_evidence_bundle_download.py
- backend/tests/test_compliance_evidence_summary.py

### Documentation and Release Tests

- backend/tests/test_compliance_evidence_demo_docs.py
- backend/tests/test_public_compliance_evidence_docs.py
- backend/tests/test_public_compliance_launch_docs.py
- backend/tests/test_compliance_evidence_release_lock.py

## Validation Commands

Backend validation:

ruff check app tests

python -m pytest tests/test_audit_csv_export.py -q
python -m pytest tests/test_audit_export_hash.py -q
python -m pytest tests/test_audit_export_verification.py -q
python -m pytest tests/test_audit_export_manifest.py -q
python -m pytest tests/test_audit_export_manifest_verification.py -q
python -m pytest tests/test_compliance_evidence_bundle.py -q
python -m pytest tests/test_compliance_evidence_bundle_verification.py -q
python -m pytest tests/test_compliance_evidence_bundle_download.py -q
python -m pytest tests/test_compliance_evidence_summary.py -q
python -m pytest tests/test_compliance_evidence_demo_docs.py -q
python -m pytest tests/test_public_compliance_evidence_docs.py -q
python -m pytest tests/test_public_compliance_launch_docs.py -q
python -m pytest tests/test_compliance_evidence_release_lock.py -q

Frontend validation:

npm run build

## CI Workflow

Path:

.github/workflows/backend-compliance-tests.yml

Purpose:

Runs compliance and evidence workflow tests as part of backend compliance validation.

## Final Evidence Status

Status: Evidence index complete.

The LumenAI repository now contains backend implementation, frontend evidence UI, verification endpoints, public portfolio documentation, demo workflow, release lock, and validation coverage for the enterprise compliance evidence workflow.


## Final Public Navigation

Use this section as the fastest public-review path through the LumenAI Compliance Evidence v1.0 release.

### Executive Review Path

- [Executive Summary](evidence-release-executive-summary.md)
- [Customer Review Packet](evidence-release-customer-review-packet.md)
- [Sales One-Pager](evidence-release-sales-one-pager.md)
- [Market Positioning Brief](evidence-release-market-positioning-brief.md)

### Technical Evidence Path

- [Compliance Evidence Summary](compliance-evidence.md)
- [Evidence Bundle Demo](../compliance/evidence-bundle-demo.md)
- [Demo Walkthrough Guide](evidence-release-demo-walkthrough-guide.md)
- [Release Lock](compliance-evidence-release-lock.md)

### Release Closure Path

- [Final Launch Summary](final-launch-summary.md)
- [Evidence Release Tag](evidence-release-tag.md)
- [Final Repository Closure Summary](final-repository-closure-summary.md)
- [Archive Note](evidence-release-archive-note.md)
- [Completion Badge](evidence-release-completion-badge.md)
- [Completion Summary](evidence-release-completion-summary.md)
- [Repository Seal](evidence-release-repository-seal.md)

### Demo and Proof Path

- [Evidence Bundle Demo README](../compliance/evidence-bundle-demo.md)
- [Demo Walkthrough Guide](evidence-release-demo-walkthrough-guide.md)
- Demo Script: scripts/demo_compliance_evidence_bundle.sh
- Frontend UI: frontend/src/components/VendorBaselineSubscriptionPortal.tsx

### Buyer-Facing Short Links

- [Compliance Evidence Badge](lumenai-compliance-evidence-badge.md)
- [Customer Review Packet](evidence-release-customer-review-packet.md)
- [Investor Brief](evidence-release-investor-brief.md)
- [Sales One-Pager](evidence-release-sales-one-pager.md)
- [Market Positioning Brief](evidence-release-market-positioning-brief.md)

## Final Navigation Status

Status: Public navigation index polished.

The LumenAI evidence index now supports executive review, customer review, technical review, demo review, sales review, investor review, and final release closure review from a single document.
### Baseline Ranking Audit Evidence

Path:

docs/pilot-readiness/baseline-ranking-audit-evidence.md

Purpose:

Documents the backend baseline ranking audit/evidence helper added after the baseline-aware inspection ingestion work. It describes captured evidence fields, approved, pending, manual-review, malformed-input, and unsafe-override outcomes, and fail-closed handling for malformed or unsafe baseline-aware payloads without claiming external persistence or production validation.
