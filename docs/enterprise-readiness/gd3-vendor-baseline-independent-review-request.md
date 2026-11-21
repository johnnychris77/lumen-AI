# GD-3 — Request for independent review (design + tenant-private floor)

| | |
|---|---|
| Repository / PR | `johnnychris77/lumen-AI`, PR #181 (draft) |
| Scope | The GD-3 vendor/manufacturer baseline **ownership design** (`gd3-vendor-baseline-architecture-decision.md`) **and** the already-landed **tenant-private default floor** (commits `78426ce`, `38d1222`) |
| What this document is | A **request** for independent, non-author review and for governance approval of the ownership/sharing policy. It is **not** a sign-off and records no reviewer decision. |
| Release disposition | **HOLD / NO-GO.** P472-03 open. PR #181 draft. |

> Passing CI, the adversarial sweep and `ruff` is **not** security approval and
> **not** authorization to implement the sharing model or to release. The
> ownership and sharing policy is **undecided**; this prompt does not approve it.

## 0. Package contents for the reviewer

| Artifact | File / location |
|---|---|
| Architecture decision record (ownership model, schema, access-grant table, manufacturer identity, revocation, migration contract, authorization policy, downstream isolation) | `gd3-vendor-baseline-architecture-decision.md` |
| Migration | `backend/alembic/versions/d8f3a6b914c7_add_vendor_baseline_tenant_id.py` |
| Migration validation vs. representative legacy records (PG16: preserved + quarantined, reversible) | `gd3-quarantine-impact-and-attribution-proposal.md` §1 |
| Authorization changes (the enforced floor) | `backend/app/routes/enterprise_intake.py`, `app/services/baseline_comparison_scoring_service.py`, `app/services/veritas_baseline_resolution_service.py`, `app/services/vendor_baseline_audit_service.py`, `app/models/{enterprise_quality,vendor_baseline_audit}.py` |
| Test evidence | `tests/test_p472_03_governance_policies.py::TestGd3VendorBaselinesAreTenantPrivate` (5 tests) + the cross-tenant adversarial suite |
| Clinical-workflow impact of quarantine | `gd3-quarantine-impact-and-attribution-proposal.md` §2 |
| Attribution procedure proposal (no production attribution performed) | `gd3-quarantine-impact-and-attribution-proposal.md` §3 |
| Residual risks / open findings | §2 below, plus AW-07 and the governance register |

## 1. Two things are submitted, at two different maturities

1. **Design (not implemented):** the ownership model (tenant-private /
   manufacturer-managed / platform-governed shared), the schema and the separate
   access-grant table, the migration contract, the legacy reconciliation and
   quarantine rule, the centralized authorization policy, and downstream-inference
   isolation. All in the architecture decision record. **Nothing in this group is
   built.** Per the brief's execution control, implementation stops here pending
   approval.
2. **Tenant-private floor (implemented, pending this review):** a nullable
   owning-tenant `tenant_id` on both baseline tables, fail-closed quarantine of
   untagged rows, and tenant-scoping of every list/approve/match/audit/scoring/
   packet/count path. A strict expected-failure test was converted to a passing
   `TestGd3VendorBaselinesAreTenantPrivate` suite. This is a pure access
   *reduction* with no sharing surface; it can be reverted if the reviewers
   prefer the whole change to wait.

## 2. What the reviewer is asked to assess

The reviewer must be a non-author. Beyond the Batch 2 questions
(`p472-03-batch2-independent-review-request.md`), GD-3 adds:

1. **Can cross-tenant sharing bypass verified membership?** In the design, a
   tenant reaches another tenant's baseline only through an active access-grant
   row; confirm no path (grant, manufacturer, platform-shared) lets a caller
   reach a baseline without either verified ownership or an active grant.
2. **Can manufacturer identity be forged?** `require_manufacturer_auth` trusts
   `X-Manufacturer-ID` unverified (open finding **AW-07**). Confirm that the
   manufacturer-managed category is **blocked** until AW-07 is fixed, and assess
   the proposed verification against the manufacturer registry.
3. **Is the ownership model right?** Are the three categories, and
   "vendor/manufacturer-supplied is private by default, not public," the correct
   defaults?
4. **Is the access-grant table sufficient?** Does {baseline, grantee tenant,
   permitted operations, authorizing actor, approval evidence, effective/expiry,
   revocation} capture what a grant must record, and is a separate table (not a
   CSV field) the right shape?
5. **Legacy reconciliation:** is "never guess an owner; quarantine the ambiguous;
   release only on documented verification" acceptable, and is the clinical-
   workflow impact (baselines unreachable until attributed) acceptable as a
   deployment precondition?
6. **Revocation:** does the design prevent a revoked baseline from remaining
   reachable through caches, queued jobs or stored client references while
   preserving historical evidence?
7. **The floor itself:** should the tenant-private floor remain on the branch now,
   or wait with the rest of the design?

## 3. Evidence for the floor (what the reviewer can reproduce)

From `backend/`:

```bash
ruff check app tests scripts/tenant_isolation_matrix.py
python -m pytest tests/test_p472_03_governance_policies.py \
    tests/test_vendor_baseline_access_control.py \
    tests/test_vendor_baseline_audit_access_control.py \
    tests/test_vendor_baseline_persistent_workflow.py \
    tests/test_baseline_comparison_scoring.py \
    tests/test_inspection_30_baseline_resolution.py \
    tests/test_veritas_evidence.py -q
python -m pytest tests/ -q                      # full suite; 8505 passed, 3 skipped, 15 xfailed
python scripts/tenant_isolation_matrix.py --sweep sqlite --out /tmp/sweep.json
```

Reproducing these confirms the author's claims; it is **not** independent review.

**Adversarial evidence for the floor.** Every A→B probe that names another tenant
through the primary header is refused (403) on all six vendor-baseline routes;
foreign writes to both baseline tables are zero. The sweep still lists
`enterprise_vendor_baseline_subscriptions` / `vendor_baseline_audit_events` as
"unscoped SQL leads" on the create/match/kpi routes — this is the known **AW-08
oracle artifact**: those queries do filter on `tenant_id`, but SQLAlchemy renders
the predicate after a newline so the sweep's spaced `" WHERE "` match misses it,
and create's residual flag is `db.refresh()`'s primary-key read of the caller's
own just-created row. The reviewer is asked to confirm this reading against the
route code rather than take it on trust.

## 4. What the reviewer must not conclude

- That the sharing model, manufacturer-managed category or revocation machinery
  exist — they are design only.
- That the floor's green tests, sweep or CI amount to approval or authorization.
- That GD-3 may be closed or the HOLD lifted. Only the completed independent
  review, the governance approval of the ownership/sharing policy, the AW-07 fix
  (for category B) and the agreed legacy-attribution procedure can support that —
  and those decisions are the reviewers' and owners', not the author's.

## 5. Outcome (to be completed by the reviewers — unsigned)

| Role | Name | Decision | Date |
|---|---|---|---|
| Independent security reviewer | _unassigned_ | _pending_ | — |
| Product owner (ownership model) | _unassigned_ | _pending_ | — |
| Clinical quality lead (scoring impact) | _unassigned_ | _pending_ | — |
| Data-governance owner (sharing/licensing) | _unassigned_ | _pending_ | — |

Until signed by non-authors, GD-3 stays open, the floor stays submitted-for-review,
no sharing is built, and the release stays **HOLD / NO-GO**.
