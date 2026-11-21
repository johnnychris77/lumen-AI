# P472-03 — Day 3: Adversarial Security Remediation Report (v1)

**Program:** P472-03 Enterprise Tenant Isolation
**PR:** #181 (branch `engineering/render-local-inference-p47`) — **DRAFT**
**Author:** AI-assisted engineering & verification agent (not an independent human security reviewer)
**Scope of authority:** Implement narrowly-scoped secure fixes and reproducible verification only. **No** merge, deploy, production/real-data access, governance sign-off, finding closure, or xfail-marker alteration.

> This report records technical remediation. It does **not** close any finding, grant any
> release authorization, or change the program disposition. Every finding below remains
> **OPEN** pending independent human security review.

---

## 1. Disposition (unchanged by this work)

| Item | State |
|------|-------|
| PR #181 | **DRAFT** (not merged) |
| P472-03 program | **OPEN** |
| Enterprise release | **HOLD / NO-GO** |
| Independent human security review | **PENDING** |

Technical remediation alone does not authorize changing any of the above.

---

## 2. Findings addressed (reproduce → analyze → remediate → verify)

All five reproduced defects were fixed in narrowly-scoped commits; one architecture-blocked
finding was analyzed and documented without code change. Each exploit was reproduced against a
**disposable, synthetic-tenant** database (no production or real data) before and after the fix.

| Finding | Class | Status after Day 3 | Commit |
|---------|-------|--------------------|--------|
| **AW-08b** vendor analytics aggregates every tenant's inspections behind a global role | BOLA / unscoped query | Code remediated; finding **OPEN** | `137e9b1` |
| **AW-08a** `GET /api/accreditation/programs` lists every tenant's programs | BOLA / unscoped query | Code remediated; finding **OPEN** | `fbd2581` |
| **AW-04** accreditation `?tenant_id=` selects another tenant's programs | tenant claim as selector | Code remediated (query field inert); finding **OPEN** | `fbd2581` |
| **PA-1** platform-admin/dev header-selected tenant leaves no access record | privileged cross-tenant | **Partial** (logging added; access decision governance-owned); finding **OPEN** | `b7b2295` |
| **AW-08c** GuardianX replay service loads inspection by id with no tenant predicate | unscoped service (defence-in-depth) | Code remediated; finding **OPEN** | `ae54f5e` |
| **AW-07** manufacturer identity trusted from `X-Manufacturer-ID` header | BFLA / no identity binding | **BLOCKED — architecture dependency** (no code change); finding **OPEN** | — (see §4) |
| **GD-3 oracle** sweep `WHERE`-detector missed `\nWHERE` | detector accuracy (false positive) | Tooling corrected + negative controls | `51c2133` |

### 2.1 AW-08b — vendor analytics (commit `137e9b1`)
- **Reproduce:** tenant-A viewer `GET /api/analytics/vendors` → tenant-B vendor marker present (leak).
- **Root cause:** all seven vendor-analytics routes ran `db.query(Inspection).all()` behind a global role.
- **Remediate:** added `Depends(resolve_tenant)` to every route and a single `_tenant_inspections(db, tenant_id)` helper filtered by the verified tenant, so the tenant predicate cannot diverge between endpoints.
- **Verify:** post-fix probe — tenant-A viewer sees only A's vendor; B absent. Routes now in the verified-resolver census.

### 2.2 AW-08a / AW-04 — accreditation programs (commit `fbd2581`)
- **Reproduce:** tenant-A admin `GET /api/accreditation/programs` (no `tenant_id`) → every tenant's programs; `?tenant_id=B` → tenant-B's programs.
- **Root cause:** `list_programs` applied an **optional** `tenant_id` filter (omitted ⇒ list-all; supplied ⇒ foreign select); `update_program_status` loaded the program by id with no tenant check (cross-tenant write + audit mis-attribution).
- **Remediate:** both handlers resolve the verified tenant via `Depends(resolve_tenant)`. `list_programs` always filters by it; the `tenant_id` query parameter is **inert** (cannot widen scope or select a foreign tenant — consistent with the app-wide resolver contract, which treats a query/body tenant as a non-selector rather than a 403 trigger when the verified `X-Tenant-Id` header selects the tenant). `update_program_status` enforces object ownership and returns a non-disclosing **404** for a foreign program.
- **Verify:** post-fix probe — A lists only A; `?tenant_id=B` → 403/own-scope, B absent. The two routes passed every adversarial parametrization in `test_p472_03_batch2_remediation.py` (owner-served and refusal).

### 2.3 PA-1 — privileged cross-tenant resolution (commit `b7b2295`, **partial**)
- **Reproduce:** a platform-admin principal (role `admin`, no membership) naming tenant B via `X-Tenant-Id` resolves to tenant B with no record.
- **Decision boundary:** the admin/dev cross-tenant rule is a **pre-existing, documented, governance-owned** decision, pinned by `test_the_platform_administrator_rule_is_unchanged_and_explicit`. Whether this access *should exist* is **not** an AI decision (Stop condition — governance).
- **Remediate (technical half only):** `principal_tenant` now emits a structured security log (`lumenai.security.tenant`) whenever an admin/dev principal is resolved to a tenant it is **not** a verified member of. The access decision and return value are unchanged; a member acting in their own tenant is not logged.
- **Residual (governance):** the access decision itself, and a durable tamper-evident audit sink (the resolver is a pure function with no DB handle), remain for governance review. See the Governance Dependency Register.

### 2.4 AW-08c — GuardianX replay service (commit `ae54f5e`, defence-in-depth)
- **Reproduce:** the finding test `test_aw08_guardianx_replay_does_not_serve_another_tenants_inspection` drives the path where the route guard passes (caller is a verified member of the tenant it names) but requests a **foreign** inspection id; the unscoped service returned the other tenant's inspection.
- **Remediate:** `replay_inspection(db, inspection_id, tenant_id=None)` filters the lookup by tenant when supplied; the route passes the membership-verified `current_user["tenant_id"]`. A foreign/missing inspection is an indistinguishable 404. (Defence in depth: the `require_tenant_roles` guard already blocks the common cross-tenant path.)
- **Verify:** finding test now secure (see §3 on markers); replay smoke test seeds the inspection in the caller's own tenant and passes.

### 2.5 GD-3 oracle — WHERE-clause detector (commit `51c2133`)
- **Issue:** the sweep's unscoped-table detector split on literal `" WHERE "`; SQLAlchemy renders the clause as `...\nWHERE foo.tenant_id = ?`, so a genuinely scoped statement was reported as a review lead — a **false positive** (noise), never a missed leak, but it erodes trust in the oracle that underwrites GD-3 and the app-wide isolation assertions.
- **Fix:** split on `\sWHERE\s` (space/newline/tab). A statement with no WHERE, or a tenant-less WHERE, is still reported exactly as before — detection is **not** weakened. Negative-control tests cover both directions.

---

## 3. Open-finding tripwires: markers left intact (findings remain OPEN)

The repository encodes each open finding as a `xfail(strict=True)` test asserting the **secure**
behaviour; by design the suite turns red the moment the route is fixed *without the marker being
removed*. The normal codebase convention removes the marker on remediation. **Day 3 does not do
this** — removing the marker is the finding-closure step reserved for independent human review,
which this agent is explicitly forbidden to perform.

Consequently, the following tests now go RED in CI as the honest signal — "code remediated, closure
pending" — not a defect to suppress. The full backend suite (SQLite, both locally and in CI on
`51c2133`) is **5 failed, 8526 passed, 3 skipped, 11 xfailed** — and all 5 "failures" are these
remediation tripwires; there is **no genuine regression**:

| Tripwire test | Finding | Mechanism |
|---|---|---|
| `test_p472_03_application_wide_findings.py::test_aw04_a_member_of_a_cannot_list_tenant_b_accreditation_programs` | AW-04 | XPASS(strict) |
| `test_p472_03_application_wide_findings.py::test_aw08_listing_accreditation_programs_does_not_return_other_tenants` | AW-08a | XPASS(strict) |
| `test_p472_03_application_wide_findings.py::test_aw08_vendor_scorecard_does_not_aggregate_another_tenants_inspections` | AW-08b | XPASS(strict) |
| `test_guardianx_assurance.py::test_aw08_guardianx_replay_does_not_serve_another_tenants_inspection` | AW-08c | XPASS(strict) |
| `test_p472_03_application_wide_isolation.py::test_registered_findings_still_reproduce` | AW-04 (sweep register) | finding `GET /api/accreditation/programs: [AW-04]` no longer reproduces |

The fifth is the sweep's "register must not go stale" guard: it fails because the fixed route no
longer exhibits AW-04 in the SQL oracle. Removing the register entry (and regenerating the
authorization matrix), like removing an xfail marker, **declares the finding closed** — a reserved
independent-review action. The register is therefore left intact; it honestly still lists AW-04 as
an OPEN finding whose code is remediated.

**Action for the independent reviewer:** confirm each remediation, then (and only then) remove the
corresponding xfail marker **and** the register entry to close the finding, and regenerate the
authorization matrix.

---

## 4. AW-07 — BLOCKED (architecture dependency, no code change)

`require_manufacturer_auth` authenticates the enterprise user, then returns
`request.headers.get("X-Manufacturer-ID")` with **no binding** between the authenticated principal
and the claimed manufacturer. Any authenticated hospital user can assert any manufacturer identity
(reproduced: a tenant-A hospital admin obtains `manufacturer_id="manufacturer-beta"`). Seven routes
in `app/routes/industry_collaboration.py` consume it.

There is **no user↔manufacturer membership model** in the schema. A correct fix requires a new
authorization primitive (a manufacturer-membership table and a verified-manufacturer resolver,
analogous to `TenantMembership`/`resolve_tenant`), which is an **architecture and governance
decision**, not a narrowly-scoped patch. Per the Day 3 stop conditions, AW-07 is left **BLOCKED**
and routed to governance/design. It is documented in the Governance Dependency Register with the
proposed design direction.

---

## 5. Migration security review (disposable PostgreSQL 16, no production data)

The GD-3 tenant migration `d8f3a6b914c7` (and the full Alembic chain) was reviewed on a **throwaway**
PG16 database, then dropped:

- `alembic upgrade head` applied the chain; `tenant_id` columns on
  `enterprise_vendor_baseline_subscriptions` and `vendor_baseline_audit_events` are **nullable with
  no server default** (fail-closed by design).
- **NULL-quarantine confirmed** with synthetic rows: a legacy NULL-tenant row, a tenant-A row and a
  tenant-B row; a tenant-A-scoped read returned **only** A's row — the NULL (legacy) row matched no
  tenant filter and B's row was invisible. No cross-tenant exposure is introduced; unattributed
  legacy baselines are unreachable (and therefore cannot drive clinical scoring) until a governance
  owner attributes them.
- `alembic downgrade -1` cleanly removed both columns (reversible).

This confirms the migration is fail-closed and reversible; it does **not** attribute or migrate any
real data (no production migration was run).

---

## 6. Constraints honored

- No merge, no deploy, no production or real-data access.
- No governance decision signed; no finding closed; no xfail marker altered.
- Every test-suite edit is accuracy-preserving maintenance (route-census counts that move only when
  routes are converted; legacy smoke tests updated to the secure contract; new negative-control and
  regression tests), documented in the Regression Evidence Index — never a weakening of a security
  assertion.
- All adversarial reproduction used synthetic tenants on disposable databases.

**The enterprise system is not declared secure because tests pass.** Residual risk, the OPEN
findings, AW-07's architecture dependency, and PA-1's governance-owned access decision are carried
forward for independent human security review.
