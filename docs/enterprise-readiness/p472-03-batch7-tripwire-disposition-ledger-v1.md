# P472-03 — Tripwire Disposition Ledger (v1, Batch 7)

**Issue #189 · PR #181 (DRAFT).** The only place a tripwire disposition is recorded. Allowed dispositions:
**ACCEPT-CONVERSION** · **REJECT-CONVERSION** · **ACCEPT-RISK** (named risk owner) · **PENDING**.

Rules: a row is completed by a reviewer who did not author the change, in a commit or PR comment under the
reviewer's own GitHub identity (the evidence link must resolve to that), and never edited afterwards — a
change of disposition is a new row. The author must not fill any reviewer column. ACCEPT-RISK requires a
named risk owner with authority to accept it. Packets: `p472-03-batch7-tripwire-review-packets-v1.md`.

| ID | Finding | Converted in | Reviewer (name, affiliation) | Evidence link | Date | Disposition | Risk owner (ACCEPT-RISK) |
|---|---|---|---|---|---|---|---|
| RB-T01 | AW-04 Genesis publisher filter (register-driven) | `38251e6` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T02 | AW-03 intelligence-network opt-in | `5adde8d` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T03 | AW-04 create accreditation program | `76d7fc3` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T04 | AW-04 list accreditation programs | `76d7fc3` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T05 | AW-04 data-sharing consent | `76d7fc3` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T06 | AW-04 network registry entry | `76d7fc3` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T07 | AW-06M shared default tenant | `5adde8d` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T08 | AW-06N no-membership pooling | `cea6d7f` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T09 | AW-08a accreditation listing | `c826fcc` (fix `fbd2581`) | UNASSIGNED | — | — | **PENDING** | — |
| RB-T10 | AW-08b vendor scorecard | `c826fcc` (fix `137e9b1`) | UNASSIGNED | — | — | **PENDING** | — |
| RB-T11 | AW-08c GuardianX inspection replay | `c826fcc` (fix `ae54f5e`) | UNASSIGNED | — | — | **PENDING** | — |
| RB-T12 | AW-03 sweep class | `5adde8d` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T13 | AW-06M sweep class | `5adde8d` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T14 | AW-06N sweep class | `cea6d7f` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T15 | GD6-01 read pending by id | `38251e6` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T16 | GD6-02 feed lists drafts | `38251e6` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T17 | GD6-03 status-filter side channel | `38251e6` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T18 | GD6-04 publisher filter (**assertion amended**) | `38251e6` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T19 | GD6-05 version chain | `38251e6` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T20 | GD6-06 cross-tenant publish | `38251e6` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T21 | GD6-07 cross-tenant reject | `38251e6` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T22 | GD6-08 supersedes linkage | `38251e6` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T23 | GD6-09 identity disclosure | `38251e6` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T24 | GD7-01 ledger read by id | `3f479d9` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T25 | GD7-02 list by source | `3f479d9` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T26 | GD7-03 cross-tenant verify | `3f479d9` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T27 | GD7-04 reviewer email | `3f479d9` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T28 | GD7-05 source contamination (**read-side only; does not show write refusal**) | `3f479d9` (set-up `6a661bb`) | UNASSIGNED | — | — | **PENDING** | — |
| RB-T29 | GD7-06 ledger write under foreign/missing owned source | `6a661bb` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T30 | GD7-07 ledger write into ownerless key in use | `6a661bb` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T31 | GX-08 explanation under foreign owned source | `6a661bb` | UNASSIGNED | — | — | **PENDING** | — |
| RB-T32 | GX-09 explanations disclosed cross-tenant — **OPEN, failing** | not converted | UNASSIGNED | — | — | **OPEN** | — |
| RB-T33 | GX-10 digital-twin tenant claim | `6a661bb` | UNASSIGNED | — | — | **PENDING** | — |

**Totals: 32 PENDING + 1 OPEN (failing) · 0 ACCEPT-CONVERSION · 0 REJECT-CONVERSION · 0 ACCEPT-RISK. 33 release blockers.**
