# LumenAI Compliance Evidence Bundle Demo

## Purpose

The Compliance Evidence Bundle provides a tamper-evident proof package for enterprise customers, hospital leadership, compliance reviewers, and vendor governance reviews.

It combines:

- Filtered enterprise audit export metadata
- SHA-256 audit CSV export hash
- Audit export manifest
- Manifest SHA-256 hash
- Bundle SHA-256 hash
- Verification URLs
- Compliance control metadata
- Recorded audit event evidence

## Key Endpoints

### Generate Evidence Bundle

GET /api/enterprise/audit/evidence-bundle

Optional filters:

- tenant_id
- actor
- actor_role
- request_id
- correlation_id
- action_type
- resource_type
- resource_id
- limit

### Download Evidence Bundle JSON

GET /api/enterprise/audit/evidence-bundle/download.json

Returns:

- application/json payload
- Content-Disposition attachment header
- X-LumenAI-Bundle-Hash
- X-LumenAI-Bundle-Hash-Algorithm
- X-LumenAI-Bundle-Event-ID

### Verify Evidence Bundle

GET /api/enterprise/audit/evidence-bundle/verify?bundle_hash=<HASH>

Returns the matching audit event and verification status.

### Public Verification Summary

GET /api/enterprise/audit/evidence-bundle/verification-summary?bundle_hash=<HASH>

Returns a safe customer-facing summary without exposing full audit details.

## Demo Authorization Headers

In dev mode, use:

Authorization: Bearer dev-token
X-LumenAI-Role: enterprise_admin
X-LumenAI-Actor: demo-admin

## Tamper-Evidence Chain

The evidence bundle supports the following trust chain:

1. Audit events are recorded with centralized audit logging.
2. Audit events include integrity hash metadata.
3. Filtered audit CSV exports receive a SHA-256 hash.
4. Audit export manifests bind the CSV hash to filters and metadata.
5. Evidence bundles bind the export hash, manifest hash, and compliance controls.
6. Verification endpoints prove whether a hash exists in the recorded audit trail.

## Compliance Controls Represented

- centralized_audit_logging
- audit_event_integrity_hash
- audit_chain_verification
- request_correlation_id
- filtered_audit_export
- audit_export_hash
- audit_export_manifest
- manifest_verification

## Demo Script

Run:

./scripts/demo_compliance_evidence_bundle.sh

The script will:

1. Create a demo audit event.
2. Generate a compliance evidence bundle.
3. Extract the bundle hash.
4. Verify the bundle.
5. Load the public verification summary.
6. Download the JSON bundle artifact.
