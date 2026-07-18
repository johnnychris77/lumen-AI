# LPZ-DIR-002 — Progress Report (Increment 1)

**Directive:** LPZ-DIR-002 — Security & Engineering Gate
**Increment:** 1 of N (controlled, smallest-safe remediation)
**Branch:** `claude/sentinel-simulation-engine-hhh6o7`
**Gate status:** **IN PROGRESS / PARTIALLY PASSED — NOT COMPLETE.**

> Per directive execution rule: *"Do not mark Directive 002 complete after one
> pull request."* This increment delivers the highest-severity fix (cross-tenant
> history fail-open) plus the typed-principal and placeholder-isolation
> contracts. Several findings are explicitly deferred to later increments with
> concrete, named deliverables. The gate does **not** pass on this increment.

---

## 1. What this increment delivers (verified by code + tests)

| Finding | Severity | Status this increment |
|---|---|---|
| F3 — tenant query fails OPEN when tenant_id missing | **Critical** | **REMEDIATED** (history + all exports fail closed) |
| F2 — principal lacked tenant/identity fields | High | **REMEDIATED (contract)** — typed `AuthenticatedPrincipal` |
| F1 — header-selected tenant without membership check | High | **PARTIALLY REMEDIATED** — deps principal now membership-verified; per-route migration deferred |
| F8 — placeholder indistinguishable from validated model | High | **STRUCTURALLY REMEDIATED (contract)** — capability envelope + guard |
| F7 — unreproducible dependency manifests | Medium | **REMEDIATED under WS1**, re-verified here |
| F4 — write endpoints lacking auth | High | **DEFERRED** — endpoint inventory in progress |
| F5 — overlapping auth implementations | Medium | **CONFIRMED / DOCUMENTED** — consolidation deferred (architecturally significant) |
| F6 — audit actor `unknown` | Medium | **PARTIALLY REMEDIATED** — attribution contract specified; wiring deferred |

Full evidence per finding: `SECURITY_FINDINGS_REGISTER.md`.

## 2. Highest-risk root cause fixed

A tenant-scoped query that fell **open** (returned every tenant's rows) when
the identity principal carried no tenant — because the principal
(`SimpleNamespace(id=0, email, role)`) had no tenant field at all, so
`if tenant_id:` was always false for non-admins. Any authenticated non-admin
could read every hospital's inspection history and exports with a single GET.
The fix makes tenant scope explicit and fail-closed: cross-tenant access
requires a verified platform admin; every other principal is confined to a
membership-verified tenant, and a missing verified tenant returns **403** — never
unfiltered data.

## 3. Test evidence (actually executed)

**Directive 002 unit/integration tests:** 16 passed (12 tenant-context + 4
placeholder-isolation), ruff clean, `git diff --check` clean.

```
tests/test_directive_002_tenant_context.py ............  (12)
tests/test_directive_002_placeholder_isolation.py ....   (4)
16 passed
```

**Full backend suite with the Directive 002 increment (Python 3.11.15,
clean database):**

```
3699 passed, 2 skipped, 1368 warnings in 447.19s (0:07:27)
```

The suite is **fully green** with this increment applied — zero failures,
including the 16 new tests above.

**Test-environment note (important for anyone re-running):** the pytest
harness uses a **file-based** SQLite database (`sqlite:///./test.db`, see
`tests/conftest.py`) and calls `create_all` without dropping tables, so
`backend/test.db` **persists between separate pytest invocations**. Several
suites (e.g. `test_sentinel_orchestration.py`, the dataset/LCID suites) assert
on aggregate row counts and are therefore **order- and prior-state-dependent**:
if a previous run left rows behind — or was interrupted mid-run — a fresh
`pytest tests/` reports spurious failures that vanish once `test.db` is
removed. The authoritative result above was produced by deleting `test.db`
first:

```bash
cd backend && rm -f test.db && \
  ../.venv/bin/python -m pytest tests/ -q
# => 3699 passed, 2 skipped
```

This persistent-`test.db` fragility is a **pre-existing test-infrastructure
issue**, independent of Directive 002; it is recorded here for transparency
and is a candidate for a future hygiene fix (in-memory or per-session DB),
which is **out of scope** for this security increment.

## 4. Non-negotiable constraints honored

* Tenant-sensitive behavior fails **closed**; missing tenant context → 403,
  never unfiltered.
* A client header can *request* a tenant but never *grants* authority — authority
  comes from `TenantMembership` verified against authenticated identity.
* Dev auth is inert in production (`_DEV_AUTH_ACTIVE is False` when
  `APP_ENV=production`), pinned by test.
* Placeholder scorer is **not** represented as trained computer vision; its
  capability envelope declares `NOT_VALIDATED`, GT-ineligible, clinical-use
  prohibited.
* **No** claim of HIPAA, SOC 2, ISO 13485, IEC 62304, ISO 14971, FDA clearance,
  or 21 CFR Part 11 compliance is made anywhere in this increment.
* No new features, dashboards, or specialists; architecture remains frozen; no
  unrelated cleanup bundled in.

## 5. Deferred to later increments (named deliverables)

1. **F4** — complete `ENDPOINT_INVENTORY.md`: classify every mounted route;
   zero UNCLASSIFIED; remediate any confirmed unauthenticated writer.
2. **F1** — migrate the remaining header-fallback routes
   (`TENANT_MIGRATION_INVENTORY.md`) to `resolve_verified_tenant`.
3. **F6** — wire every audit call to attribute from the principal
   (`AUDIT_ACTOR_SPECIFICATION.md`), removing header-derived `unknown`.
4. **F8** — stamp every scoring result with its capability envelope and enforce
   `assert_not_placeholder_for_ground_truth` in the GT-approval and
   performance-reporting paths (`PLACEHOLDER_ISOLATION_POLICY.md`).
5. **F5** — consolidate the two load-bearing auth paths onto one typed principal
   (architecturally significant; its own PR).

## 6. Gate decision

**Directive 002 is NOT complete.** Increment 1 closes the critical
cross-tenant fail-open and establishes the identity, tenant, and
engine-capability contracts the remaining increments build on. The full backend
suite is green on a clean database with this increment applied. The gate remains
**IN PROGRESS** until F1, F4, F5, F6, and F8 wiring are closed with tests.

---

# Increment 2 — Endpoint governance, reproducible builds, engineering integrity

**Gate status: IN PROGRESS / PARTIALLY PASSED — NOT COMPLETE.**
**Directive completion estimate: ~55%.**

## Executive summary

Increment 2 establishes *complete, continuously-enforced* endpoint governance
and re-verifies build/dependency integrity, without securing endpoints blind or
touching the frozen product architecture. The centrepiece is a generator that
introspects the live FastAPI app and classifies **all 1912 endpoints from
evidence** (resolved dependency tree + in-body auth guards), plus a governance
regression test that forbids any *new* unauthenticated write.

## Repository baseline (measured)

| Metric | Value |
|---|---|
| Total endpoints (method × path) | 1912 |
| `UNKNOWN` | 0 |
| Write endpoints | 728 |
| Unauthenticated writes | 21 (9 public-by-design, 12 review-required) |
| Classification split | AUTHENTICATED 881 · TENANT_SCOPED 837 · ADMIN 70 · SYSTEM 12 · PUBLIC 112 |

## Confirmed findings (this increment)

* **F4 (endpoint auth coverage)** — CONFIRMED / SCOPED. 21 unauthenticated
  writes exist; 12 are genuine review-required gaps (enterprise/vendor-governance
  writes). Enumerated and dispositioned in `ENDPOINT_SECURITY_REVIEW.md`.
* Initial dependency-only scans over-counted unauthenticated writes
  (123 → 30 → 24 → **21**) because many handlers authenticate **in-body**
  (`require_enterprise_auth(request)`, `require_hospital_or_enterprise_admin`,
  `Depends(require_manufacturer_auth)`); the generator now detects both, so the
  21 figure is evidence-based, not a false alarm.

## Changes implemented

* `backend/scripts/generate_endpoint_inventory.py` (new) — evidence-based
  inventory/classifier + artifact writer.
* `backend/tests/test_directive_002_endpoint_governance.py` (new) — enforces
  0-UNKNOWN, the no-new-unauthenticated-write allowlist, allowlist-shrink, and
  health-probe behavior.
* `backend/app/main.py` — `/ready` now emits a per-dependency `checks` block
  (database hard-gate; object_storage + configuration soft), DB-gated 503
  contract unchanged.
* SBOM artifact `docs/pilot-zero/directive-002/sbom/backend-sbom.cdx.json`.
* Docs: `ENDPOINT_INVENTORY.md` (generated), `ENDPOINT_SECURITY_REVIEW.md`,
  `DEPENDENCY_REVIEW.md`, `OBSERVABILITY_REVIEW.md`, `SBOM_REPORT.md`,
  `BUILD_REPRODUCIBILITY_REPORT.md` (extended), this report.

## Commands executed & results

| Command | Result |
|---|---|
| `python scripts/generate_endpoint_inventory.py --write` | 1912 endpoints, 0 UNKNOWN |
| `pytest tests/test_directive_002_endpoint_governance.py` | 6 passed |
| `pytest tests/test_directive_002_*` (all dir-002) | 22 passed |
| `ruff check app scripts tests` | All checks passed |
| `npm --prefix frontend run build` | 2761 modules, 4.99s, exit 0 |
| `cyclonedx-py requirements requirements-lock.txt` | CycloneDX 1.6, 100 components |
| `pip-audit -r requirements-lock.txt` | No known vulnerabilities |
| Full backend suite (clean DB) | see test-results note above (green) |

## Security & backward-compatibility impact

* No endpoint behavior changed except `/ready` (additive `checks` field; same
  status codes). No product routes, schemas, or auth flows altered.
* Net new control: unauthenticated writes can no longer be added silently.

## Remaining risks / deferred work

* **12 review-required unauthenticated writes** (enterprise_intake +
  vendor_governance) — securing deferred to **increment 3** with per-endpoint
  owner-contract confirmation and negative tests, to avoid breaking intended
  demo/integration flows.
* Uniform structured logging, startup probe, redis/queue soft health checks,
  SBOM license enrichment, frontend CycloneDX SBOM — documented follow-ups.
* F1/F5/F6 (increment 1 carry-over) remain open.

## Next recommended increment

**Increment 3 — close the 12 review-required unauthenticated writes** (add the
module's established guard + tenant scope + a negative test each), then F6 audit
actor wiring.
