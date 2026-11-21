# P472-03 — Security Tripwire Disposition Register (v1 — Batch 4)

**PR #181 (DRAFT)** · **Issue #186** · Code under review: `d62dddc`.
**Rule (program owner, Batch 4):** an expected security-tripwire failure is **not** a successful check, and
a tripwire converted by the author is **not** a closed finding. Every item below is a **release blocker**
until a non-author reviewer records its disposition (routing `p472-03-independent-review-routing-v2.md`).
No disposition below is recorded. This agent authored the fixes and cannot record one.

Disposition values a reviewer may record: **ACCEPT-CONVERSION** (fix verified; assertion unchanged) ·
**REJECT-CONVERSION** (restore the marker) · **ACCEPT-RISK** (named owner, open item). Until then: **PENDING**.

## A. Tripwire still failing (expected failure — release blocker)
| ID | Test | Finding | Why it still fails | Disposition |
|---|---|---|---|---|
| RB-T01 | `tests/test_p472_03_application_wide_isolation.py::test_no_route_exhibits[AW-04]` (strict `xfail`) | AW-04 | `GET /api/genesis-ai/manufacturer-updates?manufacturer_tenant_id=` — publisher filter over the network feed; depends on GD-6 | **PENDING — RELEASE BLOCKER** |

CI shows this as `1 xfailed` inside a job whose conclusion is *success*. That job conclusion is **not**
evidence that tenant isolation passes; it is evidence that the one known open finding still reproduces.

## B. Tripwires converted by the author in Batch 4 (marker removed; assertion unchanged) — release blockers pending review
| ID | Test (file `tests/test_p472_03_application_wide_findings.py` unless stated) | Finding | Fix commit(s) | Disposition |
|---|---|---|---|---|
| RB-T02 | `test_aw03_a_member_of_a_cannot_opt_tenant_b_into_the_intelligence_network` | AW-03 | `5adde8d` | **PENDING** |
| RB-T03 | `test_aw04_a_member_of_a_cannot_create_an_accreditation_program_in_tenant_b` | AW-04 | `76d7fc3` | **PENDING** |
| RB-T04 | `test_aw04_a_member_of_a_cannot_list_tenant_b_accreditation_programs` | AW-04 | `30638f0` (inert), `76d7fc3` (refused) | **PENDING** |
| RB-T05 | `test_aw04_a_member_of_a_cannot_grant_data_sharing_consent_for_tenant_b` | AW-04 | `76d7fc3` | **PENDING** |
| RB-T06 | `test_aw04_a_member_of_a_cannot_read_tenant_b_network_registry_entry` | AW-04 | `76d7fc3` | **PENDING** |
| RB-T07 | `test_aw06m_members_of_different_tenants_do_not_share_a_default_tenant` | AW-06M | `5adde8d`, `76d7fc3`, `24ec88d` | **PENDING** |
| RB-T08 | `test_aw06n_users_with_no_membership_are_still_pooled_where_the_default_is_a_literal` | AW-06N | `cea6d7f` | **PENDING** |
| RB-T09 | `test_aw08_listing_accreditation_programs_does_not_return_other_tenants` | AW-08 | `fbd2581` (Day 3), re-verified `c826fcc` | **PENDING** |
| RB-T10 | `test_aw08_vendor_scorecard_does_not_aggregate_another_tenants_inspections` | AW-08 | `137e9b1` (Day 3), re-verified `c826fcc` | **PENDING** |
| RB-T11 | `test_aw08_guardianx_replay_does_not_serve_another_tenants_inspection` | AW-08 | `ae54f5e` (Day 3), re-verified `c826fcc` | **PENDING** |
| RB-T12 | `test_p472_03_application_wide_isolation.py::test_no_route_exhibits[AW-03]` (register-driven strict xfail → pass) | AW-03 | `5adde8d` | **PENDING** |
| RB-T13 | `test_p472_03_application_wide_isolation.py::test_no_route_exhibits[AW-06M]` | AW-06M | `5adde8d`, `76d7fc3` | **PENDING** |
| RB-T14 | `test_p472_03_application_wide_isolation.py::test_no_route_exhibits[AW-06N]` | AW-06N | `cea6d7f` | **PENDING** |

Reviewer check for each: `git diff 4fdac4c d62dddc -- <test file>` must show only the marker removed (and
an explanatory comment) — no assertion, fixture or request changed; then confirm the test fails on
`4fdac4c` and passes on `d62dddc`. RB-T12…T14 are parametrised from the findings register: they flip
because the register (rebuilt from the SQLite and PostgreSQL 16 sweeps) no longer lists those classes, so
the reviewer must also check the sweep oracle and the register rebuild, not only the test.

## C. Tests that did not execute (not a pass)
| Test | Backend | Reason | Note |
|---|---|---|---|
| `test_p472_trusted_inference_provenance.py:788` (Alembic chain) | SQLite | PostgreSQL-only | Runs in the PostgreSQL 16 suite |
| `test_benchmarking.py:83` | both | `No hospitals returned` (data-dependent skip) | Assertions unexecuted — pre-existing |
| `test_p10_digital_twin.py:317` | both | `No open alerts` (data-dependent skip) | Assertions unexecuted — pre-existing |

## Determination
1 tripwire still fails (RB-T01); 13 author conversions await independent disposition (RB-T02…T14).
**All 14 are release blockers. Release: HOLD / NO-GO.**
