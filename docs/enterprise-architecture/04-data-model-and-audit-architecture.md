# LumenAI Data Model and Audit Architecture

## Core Domains

- Enterprise findings
- Enterprise evidence
- Vendor baseline subscriptions
- Vendor baseline audit events
- Governance packet exports
- Packet hash records
- Enterprise audit log
- CAPA records

## Vendor Baseline Audit Chain

baseline_submitted -> baseline_approved -> baseline_used_in_scoring

Future events:
- baseline_rejected
- baseline_revision_requested
- baseline_superseded
- baseline_expired
- baseline_reapproved

## Governance Packet Chain

PDF generated -> export event recorded -> SHA-256 hash generated -> hash stored in export history -> verification endpoint confirms authenticity.

## Audit Principles

1. Events should be persistent.
2. Current state and historical state should be separate.
3. Exports must be traceable.
4. Hashes must be verifiable.
5. Audit logs should become immutable.
6. Compliance events should be append-only.

## Recommended Database Improvements

- Move production to PostgreSQL
- Use Alembic migrations
- Add indexes for tenant_id, finding_id, baseline_id, and created_at
- Add append-only audit tables
- Add retention policy fields
- Add backup and restore validation
