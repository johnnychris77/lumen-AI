# LPR-DIR-012 — Architecture Change Control (Post-Freeze)

After the Version 1.0 architecture freeze, all architecture-affecting change flows
through this process. This governs change control only; it authorizes no
deployment.

## Change request template (required fields)

Every architecture-change proposal must include:

* Change request ID
* Problem statement
* Evidence
* Alternatives considered
* Proposed design
* Components affected
* Interface changes
* Data changes
* Security impact
* Tenant impact
* Audit impact
* Migration plan
* Rollback plan
* Test plan
* Documentation plan
* Architecture approval
* Security approval
* Quality approval

## Change classes

### CLASS A — Non-architectural correction
Bug fix, documentation correction, test correction, logging improvement,
dependency cleanup, deprecated-shim removal (post-migration), performance
correction.
* **Approval:** Accountable Owner + Quality approver.
* **Freeze:** always permitted.

### CLASS B — Controlled architectural modification
Modifying an existing interface, changing module ownership, changing persistence
behavior, changing a trust boundary, enforcing an existing governance rule in code.
* **Approval:** Architecture + Security + Quality approvals (all three).
* **Freeze:** permitted with full change-request record and approvals.

### CLASS C — Architecture expansion
New engine, service, workflow, agent/AI specialist, externally exposed API, data
authority, event type, integration layer.
* **Approval:** Architecture + Security + Quality + Program approval.
* **Freeze:** **PROHIBITED during the Production Readiness Program** unless required
  to resolve a **release-blocking** defect and formally approved via full change
  request.

## Mapping to freeze declaration

The freeze (`ARCHITECTURE_FREEZE_DECLARATION.md`) prohibits new agents/modules/
engines/services/dashboards/APIs/workflows/data-domains/event-types/integration-
layers/AI-specialists — i.e., **all Class C**. It explicitly permits Class A and
(with approvals) Class B, including enforcement of existing boundaries.

## Preserved invariants (no change may weaken)

Fail-closed behavior, tenant isolation, authenticated-principal boundaries, human
authority over AI, audit-chain integrity, evidence lineage, immutable historical
records. Any change request touching these requires Security approval and a test
plan proving the invariant is preserved.

## Process flow

```
Proposal → classify (A/B/C) → change request (fields above) → approvals per class
→ implement on a branch → tests + validation → documentation update
→ merge (Class A/B) or Program gate (Class C) → record in ADR register if a decision
```

## Records

Every Class B/C change updates `ARCHITECTURAL_DECISION_REGISTER.md`. Class A changes
are tracked in normal PR history. The change-control log is auditable.
