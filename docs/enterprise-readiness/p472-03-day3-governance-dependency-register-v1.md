# P472-03 — Day 3: Governance Dependency Register (v1)

**Program:** P472-03 Enterprise Tenant Isolation · **PR #181 (DRAFT)**

Items that Day 3 technical remediation **could not and did not** resolve because they require a
governance decision, an architecture change, or an independent-review action. The AI agent is
explicitly forbidden to make these calls. Each is routed to its owner.

---

## GDR-1 — AW-07: manufacturer identity has no verified binding (ARCHITECTURE + GOVERNANCE)

- **What:** `require_manufacturer_auth` returns the client-supplied `X-Manufacturer-ID` header after
  authenticating the user, with no check that the user represents that manufacturer. Reproduced: a
  tenant-A hospital admin obtains `manufacturer_id="manufacturer-beta"`. Consumed by 7 routes in
  `app/routes/industry_collaboration.py` (manufacturer portal, baselines, quality trends, …).
- **Why not fixed in Day 3:** there is **no user↔manufacturer membership model** in the schema. A
  correct fix is a new authorization primitive, not a narrowly-scoped patch.
- **Proposed direction (for design/governance, not implemented):** a `ManufacturerMembership`
  table (user_email, manufacturer_id, role, is_enabled) and a `resolve_manufacturer` dependency that
  mirrors `resolve_tenant` — the manufacturer is the one the authenticated principal is a verified
  member of; a header naming any other manufacturer is refused (403). Until then, the manufacturer
  surface must be treated as **unauthorized for cross-manufacturer data**.
- **Owner:** Architecture + Security governance. **Status: BLOCKED / OPEN.**

## GDR-2 — PA-1: platform-admin / dev cross-tenant access decision (GOVERNANCE)

- **What:** `principal_tenant` grants a global-`admin` or development principal any tenant it names,
  with no membership check. Pinned as an explicit open governance item by
  `test_the_platform_administrator_rule_is_unchanged_and_explicit`.
- **Day 3 technical half (done, commit `b7b2295`):** the access is now **logged**
  (`lumenai.security.tenant`) whenever such a principal resolves to a non-member tenant. Access
  behaviour and return value are unchanged.
- **Residual (governance-owned, NOT done):**
  1. Whether this cross-tenant privilege should exist at all, and under what break-glass control.
  2. A **tamper-evident** audit sink (the resolver is a pure function with no DB handle; the current
     log is a standard security log, not a hash-chained audit row).
- **Owner:** Security governance. **Status: PARTIAL / OPEN.**

## GDR-3 — Open-finding closure (INDEPENDENT REVIEW)

- **What:** AW-04, AW-08a, AW-08b, AW-08c each have a strict-xfail tripwire test that now **XPASSes**
  (RED in CI) because the code is remediated. Closing a finding = removing its marker; this is the
  independent-review step, deliberately **not** performed by the AI agent.
- **Action required:** an independent human reviewer confirms each remediation (evidence in the Day 3
  Remediation Report and Regression Evidence Index) and then removes the marker to close the finding.
- **Owner:** Independent human security reviewer. **Status: OPEN (awaiting review).**

## GDR-4 — GD-3 category B (cross-tenant intelligence sharing) (GOVERNANCE, carried forward)

- **What:** GD-3 shipped the tenant-private floor (baselines are tenant-private, NULL-quarantined).
  Controlled cross-tenant *sharing* (category B) remains **design-only** and **blocked** pending
  (a) AW-07 remediation and (b) governance approval. Day 3 did not implement any sharing.
- **Owner:** Clinical + Security governance. **Status: BLOCKED / design-only.**

## GDR-5 — Release authorization & gate sign-offs (GOVERNANCE)

- GD-1…GD-4 governance decisions, clinical-workflow approval, and enterprise release authorization
  are **not** AI decisions. Disposition stays **PR #181 DRAFT / P472-03 OPEN / Release HOLD-NO-GO /
  Independent Human Security Review PENDING**.
- **Owner:** Program governance + independent reviewer.

---

### Summary

| ID | Item | Type | Day 3 outcome | Owner | Status |
|----|------|------|---------------|-------|--------|
| GDR-1 | AW-07 manufacturer binding | Architecture + Governance | reproduced, documented, proposed design | Architecture/Sec | BLOCKED/OPEN |
| GDR-2 | PA-1 admin cross-tenant | Governance | logging added; decision deferred | Security gov | PARTIAL/OPEN |
| GDR-3 | Finding closure (AW-04/08a/08b/08c) | Independent review | tripwires left red by design | Independent reviewer | OPEN |
| GDR-4 | GD-3 category B sharing | Governance | untouched (design-only) | Clinical/Sec gov | BLOCKED |
| GDR-5 | Release / gate sign-offs | Governance | unchanged | Program gov | PENDING |
