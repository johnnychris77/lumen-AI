# Audit Architecture

## Write path (pre-existing, single writer)

Every audit event is written through
`enterprise_audit_service.record_enterprise_audit_event` — the single
audit writer for the platform (`app.audit.log_audit_event` is a
delegating compatibility shim). Each event is **hash-chained** per
(resource_type, resource_id): the event hash covers the action, actor,
details, and the previous event's hash, so any mid-chain tampering is
detectable by `audit_chain_verification_service.verify_audit_chain`.

Audited actions span the Foundation Section 10 list: uploads (now
including governed-object registration), annotation lifecycle,
approvals, training, promotion, inference/decision events, policy
changes, rollbacks, exports, and — new this sprint — platform alerts,
governed-object access, and integrity failures.

## NEW this sprint: immutability enforced in the ORM

`app/models/audit_log.py` now registers SQLAlchemy guards that raise
`AuditImmutabilityError` on:

* any per-instance UPDATE of an `AuditLog` row (`before_update`),
* any per-instance DELETE (`before_delete`),
* any **bulk ORM** UPDATE/DELETE targeting `audit_logs`
  (`Session.do_orm_execute`).

Verified by `tests/test_gpae_foundation.py::TestAuditImmutability`
(all four paths).

## Honest boundary

Raw SQL issued outside the ORM (e.g. `psql` with a superuser role) is
not — and cannot be — intercepted by application code. In a managed
deployment that boundary is closed operationally: the application's
database role receives `INSERT`/`SELECT` but not `UPDATE`/`DELETE` on
`audit_logs`. Until such a deployment exists, the protections that
actually run are the ORM guards plus the hash chain (which makes
out-of-band tampering *detectable* even where it is not *preventable*).

## Recovery

Audit rows are ordinary database rows and were part of the executed
backup → destroy → restore round-trip: all audit rows survived intact
(`evidence/DR_EXERCISE_EVIDENCE.json`, `audit_rows` before == after).
