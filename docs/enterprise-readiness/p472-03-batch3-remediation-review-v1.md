# P472-03 — Batch 3 Remediation Review (v1)

**Program:** P472-03 Enterprise Tenant Isolation · **PR #181 (DRAFT)** ·
Branch `engineering/render-local-inference-p47`
**Author:** AI-assisted engineering & verification agent (not an independent human security reviewer)
**Disposition:** Enterprise release **HOLD / NO-GO** — unchanged by this batch.

> Batch 3 records technical remediation and an evidence-grade analysis of the residual
> tenant-isolation findings. It does **not** merge, deploy, touch production data/databases,
> close any finding in the release gate, sign any governance decision, or weaken any strict-xfail
> assertion. Every finding below remains **OPEN** pending independent human review.

---

## 1. Baseline (Phase A)

| Item | Value |
|------|-------|
| Starting HEAD | `d653b1f` (Day 3 evidence) |
| Worktree | clean, synced with origin |
| CI on `d653b1f` | 11/13 green; the 2 red are **Backend tests (SQLite)** and **(PostgreSQL 16)**, each failing on the same 5 Day-3 remediation tripwires (4 XPASS finding tests + `test_registered_findings_still_reproduce`), not regressions |
| Strict-xfail inventory | `test_p472_03_application_wide_findings.py` (14 `_finding` markers), `test_p472_03_application_wide_isolation.py` (5 class tripwires), `test_p472_03_batch2_remediation.py` (1) |
| Findings register | `tests/p472_03_findings_register.json`: **186 routes** — AW-03 (118), AW-06M (122), AW-06N (28), AW-04 (38) (a route may carry several classes) |

### Genuine vulnerabilities vs test-oracle artifacts (Phase A §4)
- `require_tenant_roles` (`app/tenant_authz.py`) **already** enforces membership: it reads the tenant
  header (or `default-tenant`) and then calls `assert_tenant_membership`, which refuses (403) any
  tenant the caller is not an enabled member of. Routes behind it are therefore **not** the source of
  the residual header-trust leaks.
- The 186 register findings are on routes using **other** tenant-resolution patterns (handler-local
  header reads, `current_user.tenant_id or <header> or "default-tenant"`), spread across ~18 modules
  (`/api/network`, `/api/mobile`, `/api/integrations`, `/api/intelligence`, …). There is **no single
  shared resolver** left to fix — Batch 2 already converted the `resolve_tenant` / `principal_tenant`
  routes (455 of them).
- **AW-06M (122 routes)** is, by the sweep's own definition, a **pooling** issue ("verified members
  without a tenant header are pooled in `default-tenant`" — *"who: every client that sends no tenant
  header, with no attack"*). It is a correctness/pooling defect, **not** a cross-tenant exfiltration.
- **AW-03 (118)**, **AW-04 (38)**, **AW-06N (28)** are the exfiltration-relevant residuals (foreign
  `X-LumenAI-Tenant-Id` header, foreign tenant parameter, and no-membership principals served in
  `default-tenant`, respectively) on those non-resolver routes.

---

## 2. Remediated in Batch 3

### AW-07 — manufacturer identity bound to a verified membership ✅ (commit `e615afd`)
- **Root cause:** `require_manufacturer_auth` returned the client `X-Manufacturer-ID` header with no
  principal↔manufacturer binding; any authenticated hospital user could assume any manufacturer /
  repair-partner identity (BFLA).
- **Fix:** new `ManufacturerMembership` model + Alembic migration `e7c2a9f04b18` (mirrors
  `TenantMembership`). `require_manufacturer_auth` now resolves the manufacturer identity from an
  **enabled** membership: a header is honoured only for a verified member; no header → sole
  membership; no/ambiguous/disabled membership → 403 (fail closed).
- **No platform-wide bypass** was introduced. Manufacturer-managed GD-3 baselines remain **disabled**
  pending their separate governance/authorization.
- **Verification:** 7 adversarial tests (`test_p472_03_aw07_manufacturer_identity.py`: impersonation,
  cross-manufacturer, sole-membership, multi-membership selection, disabled membership,
  unauthenticated) + the existing AW-07 exploit test now passes with its assertion unchanged (marker
  removed; exploit no longer reproduces); 63 manufacturer/repair-partner/vendor portal tests pass on
  a fresh DB; migration up/down verified on **PostgreSQL 16** (disposable DB, dropped).
- **Status:** OPEN pending independent **IAM** review. The strict-xfail conversion records technical
  remediation only; it is not a finding closure in the release gate.

---

## 3. Analyzed, with a remediation roadmap — NOT yet remediated (honest status)

The residual tenant-isolation tail (AW-03 / AW-04 / AW-06M / AW-06N, 186 routes across ~18 modules)
was **not** remediated in Batch 3. A safe, independently-verifiable remediation requires a per-module
pass (each module resolves its tenant differently) and cannot be done as one sweeping change without
risking regressions that this automated agent could not fully verify. Rather than fabricate
completion, Batch 3 records the analysis and the roadmap:

| Class | Routes | Nature | Remediation approach |
|-------|--------|--------|----------------------|
| AW-04 | 38 | foreign tenant parameter selects another tenant | per route: resolve the verified tenant and treat the body/query/path `tenant_id` as a claim (refuse a foreign claim, or make it inert), as Batch 2 did for the `authorized_tenant` routes and Day 3 did for accreditation |
| AW-03 | 118 | foreign `X-LumenAI-Tenant-Id` binds data | per module: replace the handler-local header read with the verified resolver (`principal_tenant` / `verified_request_tenant`) |
| AW-06N | 28 | no-membership principal served in `default-tenant` | per module: route the handler through the verified resolver, which refuses a principal with no membership |
| AW-06M | 122 | verified member with no header pooled in `default-tenant` (no attack) | per module: resolve the member's own tenant from membership instead of defaulting; lower severity (pooling) |

**Recommended sequencing for a human-supervised Batch 3b:** one module per commit, highest-risk
modules first (those carrying AW-04/AW-03), each with before/after synthetic-tenant probes, converting
the corresponding register entries only after the sweep confirms the route no longer reproduces.

---

## 4. Strict-xfail / register reconciliation (Phase F §9)

- **AW-07** exploit test: converted to a passing test (assertion unchanged). Does **not** add a CI red
  (a strict-xfail that was failing-as-expected becomes a normal pass).
- **Day-3 tripwires** (AW-04 accreditation, AW-08a, AW-08b, AW-08c XPASS + `test_registered_findings_still_reproduce`):
  left intact — these remediations are genuine but their markers/register entries are reserved for the
  independent-review closure step. CI stays red on exactly these 5, by design.
- **Residual register findings** (AW-03/04/06M/06N): their strict-xfail class tripwires and register
  entries are **unchanged** because the routes are not yet remediated — the guards correctly still
  reproduce.

No assertion was changed and no coverage was removed to make any test pass.

---

## 5. Disposition

PR #181 **DRAFT** / P472-03 **OPEN** / Enterprise Release **HOLD / NO-GO** / Independent Human
Security Review **PENDING**. AW-07 is technically remediated and ready for independent IAM review; the
186-route tenant-isolation tail is analyzed with a roadmap and remains open; governance and clinical
approvals remain unsigned (see the governance register and clinical checklist).
