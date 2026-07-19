# LPR-DIR-012 — Duplication & Deprecation Review

**Basis:** code at `c9797b2`. **No code is deleted in this directive** — removal
requires (1) proven unreachable/deprecated, (2) low risk, (3) tests confirm no
behavioral change, (4) documented. Items below are recorded for later phases.

## Duplication findings

| ID | Item | Evidence | Type | Action | Delete now? |
|---|---|---|---|---|---|
| DUP-01 | Audit writer | `app.audit.log_audit_event` (deprecated) + `enterprise_audit_service.record_enterprise_audit_event` | Duplicate writer / shim | Migrate callers, then remove shim | No (callers remain) |
| DUP-02 | Billing webhook handler | Two handlers on `POST /api/billing/webhook` (`billing.stripe_webhook`, `billing_webhooks.billing_webhook`) | Duplicate endpoint | Confirm intended; deprecate other | No (verify first) |
| DUP-03 | Risk-monitoring systems | Consolidated per ADR 0009 | Previously duplicate, resolved | None | N/A |
| DUP-04 | Header-fallback auth routes | Directive 002 F1 migration pending | Compatibility path | Complete migration | No |

## Deprecation findings

| ID | Item | Status | Action |
|---|---|---|---|
| DEP-01 | `app.audit` shim | Deprecated (emits DeprecationWarning; observed in validation run) | Retire after caller migration |
| DEP-02 | Legacy baselines `IMAGE_EVIDENCE_MISSING` | Marked (Atlas migration) | Retain for audit; no action |
| DEP-03 | Auth header-fallback | Deprecated in favor of typed principal | Retire after F1 |

## Dead-code / unused review

* **Unused endpoints:** route inventory shows **0 UNKNOWN** classification and all
  1,912 endpoints resolve to handlers; no orphan endpoint confirmed. DUP-02 is a
  *duplicate*, not dead.
* **Unused models / abandoned migrations:** 13 migrations present; not proven
  abandoned in this pass — a migration-history audit is recommended (later phase).
* **Obsolete tests / dead flags / unreachable code:** none *proven* in this pass.
  Automated dead-code + import-cycle detection is **not yet run in CI** (see
  DEPENDENCY_RISK_REGISTER D-04) and should be added before any deletion campaign.
* **Docs for removed components:** none confirmed; the ADR/architecture docs
  largely match implemented reality (some decisions undocumented — ADR-01).

## Determination

The only concrete, low-risk cleanup candidates are the **deprecated audit shim**
(DUP-01/DEP-01, after caller migration) and the **duplicate billing webhook**
(DUP-02, after confirming the intended handler). Neither is deleted in this
directive; both are Class A corrections for a later phase, gated on automated
dead-code / import-cycle detection being active in CI first.
