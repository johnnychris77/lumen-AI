# P472-03 Batch 7 (B7.4) — Clinical and Data-Governance Packet: Quarantined Historical Evidence (CLIN-1) and the Historical-Access Investigation (v1)

**Issue #189 · PR #181 (DRAFT) · baseline `c6ba66c`.** Author-prepared for clinical, privacy/security and
data-governance owners. **No production system, database, log or deployment record was accessed.** No row
has been attributed, released, deleted or migrated. Nothing here is a finding about production. Current
sweeps and tests describe the **code**; they say nothing about whether the earlier exposures were used.

## 1. What is quarantined or unprovenanced in the code today

| Class | Mechanism (code) | Since | Who can read it now | Provenance available | Decision |
|---|---|---|---|---|---|
| **Legacy vendor baselines** (rows from before GD-3) | `tenant_id IS NULL` after migration `d8f3a6b914c7`; every tenant-scoped read and `resolve_baseline` misses them; governed resolver returns `SUPERVISOR_REVIEW_REQUIRED` | GD-3 floor | **no tenant** | audit events on the same NULL tenant; catalog/category/approval metadata; no owner field | GD-3 + CLIN-1 |
| **Ownerless CAPAs** | quarantined by GD-4 (no owner tenant → visible to none) | Batch 1 | no tenant | creation audit events where present | GD-4 + CLIN-1 |
| **GuardianX evidence-ledger entries with no provable owner** | B6.2 read gate: readable only by the single real tenant on the entry's hash-chained audit trail; entries with no audit event, `default-tenant` only, or several tenants → no tenant | B6.2 `3f479d9` | no tenant | audit trail (if any); sealed content digest only for entries written after B5.4 (`3c8d347`) | GD-7 + CLIN-1 |
| **Legacy ledger entries without a sealed digest** (pre-B5.4) | `verify` reports `legacy_unsealed_evidence`, `verified: false` | B5.4 | owner (if attributable) sees them as unverifiable | chain only; content cannot be proven unaltered | GD-7 (chain-only attribution?) |
| **Genesis content published under the open model** (before B6.1 any tenant's leadership could publish/reject any update) | not quarantined; published content stays network-visible | — | everyone (published) | `reviewed_by` / status history if recorded; audit events only from B6.1 onwards | GD-6 + CLIN-1 |
| **Manufacturer memberships created before Batch 5** | **not quarantined** — still active; NULL `granted_by`/`grant_reference` | B5.2 | — (they grant portal access) | none | GD-9 re-certification |
| **Users with `users.role` set** | becomes effective on deploy (AUTH-2) | B5.5 | — | none | AUTH-2 inventory |

## 2. Clinical-safety impact (for the clinical owner)

| Class | Impact while quarantined | Impact if released wrongly |
|---|---|---|
| Legacy baselines | Inspections that relied on a legacy baseline get **no baseline match** → `SUPERVISOR_REVIEW_REQUIRED` (more human review; no silent pass). Throughput effect, not a false-safe result. | One hospital's baseline scores another hospital's instruments: wrong comparison reference → possible incorrect inspection outcome. **Higher clinical risk than quarantine.** |
| Ownerless CAPAs | Corrective actions not visible to the tenant that should act on them → an open CAPA may be missed. **Needs an operational check** (owner should confirm none is clinically urgent). | CAPA details (often naming instruments, events) disclosed to another hospital. |
| GuardianX legacy entries | Audit/accreditation evidence unavailable through tenant APIs → accreditation evidence gaps; no effect on live inspection outcomes. | Another tenant's evidence (and reviewer identity) disclosed; contaminated sources mixed into a tenant's record (RB-T28 write-side gap). |
| Genesis open-model content | Already visible; content may not have been reviewed by anyone outside the submitting tenant. | — (already public) — but clinical accuracy of self-published guidance is unreviewed. |

No patient data is expected in these tables by design (instrument/process data; "no PHI in demo data or image
metadata"). **Whether production rows contain PHI or free text with patient identifiers is unknown** and must
be checked by an authorized operator before any release or export.

## 3. Confidentiality

Release to the wrong tenant is a cross-tenant disclosure. Hospital identities in cross-hospital intelligence
must be anonymised; reviewer emails in ledger entries and Genesis records are personal data. Any re-attribution
work happens in production by authorized operators, with working data kept in an access-controlled location —
**not** in GitHub, a PR, an issue, chat or a shared drive (same rule as the investigation plan).

## 4. Re-attribution options (per class; for decision)

| Option | Method | Evidence standard | Risk |
|---|---|---|---|
| R1 — leave quarantined | none | — | availability / operational burden; no disclosure risk |
| R2 — audit-chain attribution | attribute only rows whose hash-chained audit trail names exactly one real tenant and verifies (ledger dry run `classify_entries` already implements the classification read-only; GD-3 has the equivalent proposal) | chain verified + single tenant | low if the chain is intact; chain-only legacy ledger rows cannot prove content |
| R3 — owner attestation | the candidate tenant's authorized representative attests ownership, row by row, with a second-person check by the data-governance owner | attestation + corroborating metadata | moderate; must be logged as an audit event per row |
| R4 — retire | archive read-only for the platform-security role (PA-1 governed) and stop using | retention policy | loses availability; needs the GD-7 retention decision |

**Never** acceptable: inferring an owner from naming, timing or "most likely" heuristics; writing a guessed
owner; rewriting audit rows or hashes.

## 5. Disposition criteria (proposed, for CLIN-1 sign-off)

A quarantined row may be released only when **all** hold:
1. the class decision (GD-3 / GD-4 / GD-7) is signed and names the permitted option (R2/R3/R4);
2. the row meets that option's evidence standard;
3. a clinical owner confirms the release does not change a past or pending inspection outcome without review
   (or the affected inspections are re-reviewed);
4. a data-governance owner confirms no PHI and the correct tenant;
5. the release writes an audit event (row id, tenant, option, approver, ticket);
6. counts before and after are reconciled and filed with the incident/governance record.

## 6. Historical-access investigation (HIST) — authorization plan

The full read-only plan is `p472-03-historical-access-investigation-plan.md` (prepared at `48ef45f`). Batches
3–6 widened the scope; the additions below must be included when the plan is authorized.

| Scope addition | Exposure window (code) | What an investigator would look for (production, authorized only) |
|---|---|---|
| Genesis drafts and cross-tenant review | until B6.1 `38251e6` | reads of `/api/genesis-ai/manufacturer-updates/{id}`, version chains and status filters by tenants other than the submitter; publish/reject by non-owners |
| GuardianX ledger reads/verify/list | until B6.2 `3f479d9` | ledger reads where the caller's tenant ≠ entry's audit tenant |
| Audit replay by id (workflow executions, rules) | until B6.2b `00aec32` | replay requests for ids owned by another tenant |
| AW-01…AW-13 routes (batches 1–4) | per the plan | per the plan |
| PA-1 privileged cross-tenant access | ongoing | `lumenai.security.tenant` WARNING lines (exist only since the PA-1 logging change) and earlier access logs |
| Manufacturer portal before AW-07 | until `e615afd` | portal reads by identities without a membership |

**Required before starting** (unchanged from the plan, restated): written authorization naming people and time
window (security lead + system owner); legal/privacy confirmation of notification clocks; named incident-response
owner; read-only credentials; an agreed access-controlled working location. **Do not start on verbal
instruction.**

**What current evidence cannot show:** zero sweep findings and passing tripwires show the code now refuses
these requests. They do not show that nobody made such requests before the fixes. Application-level audit
trails did not record most of these reads, so the answer depends on retained access/edge logs whose retention
is not stated in the repository; the earliest windows may already be beyond retention.

## 7. Sign-offs required (none recorded)

| Role | Decision | Name | Date | Reference |
|---|---|---|---|---|
| Clinical owner (CLIN-1) | release criteria §5; clinical urgency check for ownerless CAPAs | — | — | **UNSIGNED** |
| Privacy / security owner | confidentiality controls §3; HIST authorization | — | — | **UNSIGNED** |
| Data-governance owner | re-attribution option per class §4 | — | — | **UNSIGNED** |
| Incident-response owner | suspected-exposure record; HIST execution | — | — | **UNSIGNED** |

**No historical data migration or exposure may proceed without these. Release HOLD / NO-GO.**
