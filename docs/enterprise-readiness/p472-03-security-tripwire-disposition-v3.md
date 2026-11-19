# P472-03 — Security Tripwire Disposition Register (v3 — Batch 6)

**PR #181 (DRAFT) · Issue #188** · supersedes v2 (preserved). **Rule:** a failing security tripwire is not a
passing check; an author-converted tripwire is not a closed finding. Every item is a **release blocker**
until a non-author reviewer records a disposition. **No disposition is recorded; no reviewer is assigned.**

| ID | Test | State at Batch 6 code (`3f479d9`) | Converted by | Assertion | Disposition |
|---|---|---|---|---|---|
| RB-T01 | `test_no_route_exhibits[AW-04]` (register-driven) | **passes** — both sweeps 0 findings | B6.1 `38251e6` (register regenerated) | unchanged; depends on sweep oracle | **PENDING — BLOCKER** |
| RB-T02…T11 | findings-file exploit tests (AW-03/04/06M/06N/08) | pass | Batch 4 | unchanged (diff-verified) | **PENDING — BLOCKER** |
| RB-T12…T14 | `test_no_route_exhibits[AW-03/06M/06N]` | pass | Batch 4 | unchanged | **PENDING — BLOCKER** |
| RB-T15, T16, T17, T19…T23 | `test_p472_03_batch5_genesis_gd6.py::TestOpenFindings` (GD6-01/02/03/05…09) | pass | B6.1 `38251e6` | **unchanged** | **PENDING — BLOCKER** |
| RB-T18 | `…::test_publisher_filter_does_not_reveal_unpublished_content` (GD6-04) | pass | B6.1 `38251e6` | **AMENDED** — request now refused (403); accepts 200 or 403 and still requires the pending id and body to be absent | **PENDING — BLOCKER (reviewer must judge the amendment)** |
| RB-T24…T28 | `test_p472_03_batch5_guardianx_gd7.py::TestOpenOwnershipFindings` (GD7-01…05) | pass | B6.2 `3f479d9` | **unchanged** | **PENDING — BLOCKER** |

**Still-failing strict xfails at `3f479d9`: 0.** This does **not** mean the security gate passes: all 28 are
author conversions awaiting independent before/after reproduction (`p472-03-batch6-independent-review-packages-v2.md`),
and the Genesis/GuardianX fixes are fail-closed floors whose governance questions (GD-6, GD-7) remain open.

New test outside the register (not a tripwire): `TestB62ReplayEmbedding` — reproduced before the B6.2 fix
(replay embedded another tenant's evidence), passes after.

**28 release blockers. HOLD / NO-GO.**
