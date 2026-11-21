# P472-03 — Release Gate Evidence Index (v2 — Batch 3 update)

**Program:** P472-03 · **PR #181 (DRAFT)** · supersedes `p472-03-release-gate-evidence-index-v1.md`
(preserved). Status legend: **PASS** / **PENDING** (awaiting independent human action) / **BLOCKED**
(dependency) / **FAIL** / **NOT-ASSESSED**. Overall gate: **NO-GO**.

| Gate | Criterion | Evidence | Status |
|------|-----------|----------|--------|
| G1 | Tenant isolation — resolver routes (Batch 1/2) | 455 routes via `resolve_tenant`/`principal_tenant`; batch2 suite | **PENDING** (independent security review) |
| G2 | Tenant isolation — residual tail (AW-03/04/06M/06N, 186 routes) | Batch 3 review §3 roadmap; **not remediated** | **FAIL / OPEN** (release blocker) |
| G3 | Manufacturer identity (AW-07) | `require_manufacturer_auth` + `ManufacturerMembership` + migration `e7c2a9f04b18`; adversarial tests; PG16 up/down | **PENDING** (IAM review) — technically remediated |
| G4 | Accreditation AW-04 reads | Batch 3 (evidence/readiness/trend/survey/certifications) + Day-3 programs | **PENDING** (independent review) |
| G5 | GD-3 tenant-private floor + migration | GD-3 assessment; PG16 NULL-quarantine (Day-3 §5) | **PENDING** (security + DB review) |
| G6 | PA-1 platform-admin cross-tenant | Access unchanged; logged (Day 3) | **PENDING** (governance decision) |
| G7 | GD-1…GD-4 governance sign-off | `gd1-gd4-governance-decision-register-v2.md` | **PENDING** (owners) |
| G8 | Clinical workflow / legacy attribution | `gd3-clinical-workflow-approval-checklist-v2.md` | **PENDING** (clinical owner) |
| G9 | Day-3 open-finding closure (AW-04/08a/08b/08c) | Day-3 tripwires red by design | **PENDING** (independent-review closure) |
| G10 | CI — security/lint/compliance/quality gates | 11/13 green on `d653b1f`; Batch 3 re-run pending | **PENDING** (re-run on Batch 3 head) |
| G11 | CI — Backend tests (SQLite) & (PostgreSQL 16) | Red on the remediation tripwires; Batch 3 full run pending | **PENDING** (see Batch 3 regression evidence) |
| G12 | Historical access investigation | Plan only; not executed (no production access) | **BLOCKED** (needs authorization) |
| G13 | Independent human security review | Not performed | **PENDING** |
| G14 | Authorized release decision | Not recorded | **PENDING** |

## Determination
At least one gate (G2) is **FAIL/OPEN** and the rest are PENDING/BLOCKED. **No release criterion is
independently satisfied and no authorized release decision is recorded.** Final disposition:
**HOLD / NO-GO** — PR #181 DRAFT, P472-03 OPEN, Independent Human Security Review PENDING.
