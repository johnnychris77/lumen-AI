# P472-03 — Request for independent review of Remediation Batch 2

| | |
|---|---|
| Repository / PR | `johnnychris77/lumen-AI`, PR #181 (draft) |
| Branch | `engineering/render-local-inference-p47` |
| Scope of this request | Remediation Batch 2 (verified tenant membership: AW-01, AW-02, AW-05; GD-1; GD-2; AW-12; AW-13) as submitted in commits `cf0eda2` → `63bc840` and documented in `p472-03-batch2-remediation-review.md` |
| What this document is | A **request** for an independent review and contract sign-off. It is **not** a sign-off, an approval, or a statement that the work is correct. |
| Release status | **HOLD / NO-GO.** Unchanged by this request. |
| P472-03 status | **Open.** This request does not close it. |

> This is a request addressed to people who did **not** write the Batch 2
> fixes. It asks them to review the submitted work and decide. It records no
> decision of their own. Nothing here should be read as their agreement.

---

## 1. Why this request exists

Batch 2 was implemented and tested by one author. Every test in the package was
written by that author. Automated checks — CI, the adversarial sweep, `ruff`,
the dedicated per-route tests — all currently pass on the head of the branch.

**Passing automated checks is not security approval.** CI green means the code
the author wrote agrees with the tests the author wrote. It does not establish
that the rule is the right rule, that the tests cover the real threat, that the
contract changes are acceptable to the people who own those contracts, or that
anything has been exercised against a deployed system (nothing has). Those
judgements require a reviewer who did not write the code. This document asks for
that reviewer, and for the contract owners, to be assigned.

Until an independent review and the contract sign-offs below are complete, the
batch closes no finding and the release stays HOLD / NO-GO.

## 2. Who this is routed to

| Role | What they are asked to decide | Must not be the author of the fixes |
|---|---|---|
| Independent security reviewer (application security / tenant isolation) | Whether the rule and its tests are sound, and whether the remaining-findings register is honest about what is still open | **Required** |
| Multi-tenant data-isolation / platform-security owner | Whether PA-1 (the platform administrator reaching any tenant by header, unchanged) is acceptable to leave open while this ships behind HOLD | Required |
| API contract owner(s) | Whether the contract changes in §4.1 of the review document (e.g. a signed-in user with no tenant membership now gets 403 on 502 routes; two disagreeing tenant headers now 403) are acceptable, and whether the deployment precondition (every production account needs a tenant membership) can be met | Required |
| Governance decision owners (GD-1, GD-2, and GD-3 once its separate commit lands) | Whether to confirm or change each policy; none is signed off | Required |
| Incident-response owner | Whether to carry out, or commission, the historical access investigation (`p472-03-historical-access-investigation-plan.md`) | Required |

Assigning these reviewers is the responsibility of the workstream owner, not of
the author. This document does not name individuals.

## 3. What is submitted for review

- **Code.** Commits `cf0eda2` → `63bc840`. Start with
  `backend/app/auth/tenant_scope.py` (the rule, ~60 lines) and
  `backend/app/tenant.py`.
- **Evidence package.** `p472-03-batch2-remediation-review.md` — the
  contract-impact assessment, adversarial before/after, authorization matrix,
  the tests, the mutation checks, and the full remaining-findings register.
- **Governance context.** `p472-03-security-governance-decisions.md`
  (GD-1 … GD-4) and `p472-03-historical-access-investigation-plan.md`.
- **Related, not part of Batch 2.** GD-3 (vendor baselines tenant-private) is a
  separate commit on this branch. It is noted here only so the reviewer sees the
  whole branch; it has its own enforcement and its own deployment precondition
  and is equally unreviewed.

## 4. How to reproduce the author's checks

From `backend/`:

```bash
ruff check app tests scripts/tenant_isolation_matrix.py
python -m pytest tests/test_p472_03_batch2_remediation.py \
    tests/test_p472_03_governance_policies.py \
    tests/test_p472_03_application_wide_findings.py -q
python -m pytest tests/ -q                      # full suite; runs the sweep as well
python scripts/tenant_isolation_matrix.py --sweep sqlite --out /tmp/sweep.json
```

Each fix can be reverted on its own (`git revert <sha>`) to watch its tests
fail; that is how the mutation checks were produced. **Reproducing these checks
confirms the author's claims; it does not constitute independent review** — the
tests are the author's own.

## 5. Questions the reviewer is asked to answer

These are carried from §10 of the review document, restated as the questions a
non-author must settle:

1. **Is the rule right?** In particular, refusing a named foreign tenant rather
   than ignoring it, and refusing a user with several memberships who names none.
2. **Are the two unchanged caller classes acceptable** until PA-1 is decided?
   The platform administrator can still read and write any tenant by header; the
   development tokens are unchanged (not accepted in production).
3. **Did any caller rely on `resolve_tenant` not authenticating?** It now
   authenticates the caller itself. None was found among the 181 routes — confirm.
4. **Are the patterns this batch did not remove correctly left open?**
   `get_request_tenant_id(request)` (AW-03), `or "default-tenant"` (AW-06N), and
   any handler that calls a function operating on all tenants (the AW-12 pattern).
5. **AW-13:** are counts of participating organisations acceptable to return,
   given the network's minimum group size?
6. **Governance:** confirm or change GD-1 and GD-2 (and GD-3 on its own commit)
   with their owners.
7. **Historical access:** carry out, or commission, the investigation.

## 6. What the reviewer is asked **not** to conclude

- That the 186 routes still carrying a sweep finding are the only ones with a
  finding. 731 routes are only partly exercised; production was not examined.
- That the dedicated per-route tests are independent evidence. They are the
  author's.
- That passing CI, the sweep, `ruff`, or any automated check amounts to security
  approval or to authorization to release.
- That anything here has been exercised against a deployed system. Nothing was
  deployed.
- That P472-03 may be closed, or the HOLD lifted, on the strength of this
  package. It may not — only the completed independent review and the contract
  sign-offs can support that, and that decision is the reviewers' and owners' to
  make, not the author's.

## 7. Outcome of this request (to be completed by the reviewers — unsigned)

This section is deliberately empty of decisions. It is filled in by the assigned
reviewers, not by the author, and only then does it carry weight.

| Reviewer role | Name | Decision (accept / change / reject) | Date | Notes |
|---|---|---|---|---|
| Independent security reviewer | _unassigned_ | _pending_ | — | — |
| Data-isolation / platform-security owner | _unassigned_ | _pending_ | — | — |
| API contract owner(s) | _unassigned_ | _pending_ | — | — |
| GD-1 owner | _unassigned_ | _pending_ | — | — |
| GD-2 owner | _unassigned_ | _pending_ | — | — |
| Incident-response owner | _unassigned_ | _pending_ | — | — |

Until every row above is signed by a non-author, Batch 2 remains submitted-for-
review only, P472-03 stays open, and the release stays **HOLD / NO-GO**.
