# LPZ-DIR-002 — Endpoint Security Review (increment 2)

Companion to the generated `ENDPOINT_INVENTORY.md`. Every classification here
is derived from the live app's resolved dependency tree **and** the handler
source (in-body guards), by `scripts/generate_endpoint_inventory.py` — not by
guesswork.

## Coverage summary (generated)

| Metric | Value (increment 2) | Value (increment 3) |
|---|---|---|
| Total endpoints (method × path) | 1912 | 1912 |
| `UNKNOWN` (unclassifiable) | **0** | **0** |
| Write endpoints (POST/PUT/PATCH/DELETE) | 728 | 728 |
| **Unauthenticated writes** | 21 | **10** (all PUBLIC_BY_DESIGN) |
| AUTHENTICATED / TENANT_SCOPED / ADMIN / SYSTEM / PUBLIC | 881 / 837 / 70 / 12 / 112 | 882 / 855 / 70 / 12 / 93 |

> **Increment 3 update:** the 11 REVIEW_REQUIRED enterprise/vendor-governance
> writes below have been **secured** (or found already-guarded). The remaining
> 10 unauthenticated writes are exactly the 9 PUBLIC_BY_DESIGN paths
> (`/api/billing/webhook` has two handlers). The detector was also corrected —
> it previously missed in-body guards named with a leading underscore
> (`_require_vendor_baseline_approval_access`), which is why
> `.../baselines/{baseline_id}/approve` was mis-listed as unauthenticated in
> increment 2 when it was already guarded by `require_hospital_or_enterprise_admin`.

Authentication is detected from any of: a security dependency in the route
tree (`get_current_user`, `require_roles`, `require_tenant_roles`, any
`require_*` guard, enterprise auth), or an equivalent guard called in the
handler body (e.g. `require_enterprise_auth(request)`,
`require_hospital_or_enterprise_admin(request)`). Many handlers use the
in-body pattern, which a naive dependency-only scan would mis-report as
unauthenticated — this review accounts for both.

## The 21 unauthenticated write endpoints — per-endpoint disposition

### PUBLIC_BY_DESIGN (intended open integration points — no change)

| Method | Path | Why public | Auth mechanism (non-bearer) |
|---|---|---|---|
| POST | `/api/auth/login` | issues the session token | credentials in body |
| POST | `/api/billing/webhook` (×2 handlers) | Stripe → server callback | Stripe signature |
| POST | `/api/integrations/webhook/{system_name}` | inbound push integration | HMAC (`WEBHOOK_SECRET_*`), per handler docstring |
| POST | `/api/manufacturers/register` | self-service manufacturer signup | handler docstring: "no auth required" |
| POST | `/api/mobile/auth/token-refresh` | refresh flow | refresh token in body |
| POST | `/api/admin/bootstrap` | first-admin bootstrap | one-time/guarded bootstrap |
| POST | `/api/capture/ingest` | edge capture device ingest | `X-Device-Key` header |
| POST | `/api/billing/upgrade` | delegates to checkout creation | verified inside `create_checkout` |
| POST | `/api/baseline-ranking/audit-evidence` | pure stateless compute (no DB, no persistence) | n/a — returns derived evidence from request body |

**Remediation:** none. Securing these with bearer auth would break intended
integrations (Stripe, webhook producers, device capture, login). Their
contracts are documented; the governance test allowlists them explicitly.

### REVIEW_REQUIRED → REMEDIATED (increment 3)

These wrote/approved tenant-scoped enterprise data with **no** authentication
guard. All are now secured: `require_enterprise_auth(request)` added to the
enterprise_intake and vendor_governance handlers (matching the module's
established guard), except `.../baselines/{baseline_id}/approve` which was
already guarded by `require_hospital_or_enterprise_admin` (a detector
false-negative, now fixed). Each is verified either by a direct
anonymous-request 401 test or by the allowlist test (it is no longer in the
unauthenticated-writes set). Negative tests live in
`tests/test_directive_002_endpoint_governance.py::TestSecuredWritesRejectAnon`.

| Method | Path | Handler | Risk |
|---|---|---|---|
| POST | `/api/enterprise/baseline-aware-score` | `enterprise_intake.calculate_enterprise_baseline_aware_score` | Medium (compute; reads baselines) |
| POST | `/api/enterprise/baselines/{baseline_id}/review` | `enterprise_intake.review_manufacturer_baseline` | **High** (approval write) |
| POST | `/api/enterprise/instruments/{instrument_id}/baseline` | `enterprise_intake.upload_instrument_baseline` | High (baseline write) |
| POST | `/api/enterprise/intake/{finding_id}/baseline-comparison` | `enterprise_intake.compare_finding_to_manufacturer_baseline` | Medium |
| POST | `/api/enterprise/vendor-baseline-subscription/baselines` | `enterprise_intake.create_enterprise_vendor_baseline_record` | High |
| POST | `/api/enterprise/vendor-baseline-subscription/baselines/upload-image` | `enterprise_intake.upload_vendor_baseline_image` | High (upload) |
| POST | `/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/approve` | `enterprise_intake.approve_enterprise_vendor_baseline_record` | **High** (approval write) |
| POST | `/api/enterprise/vendor-baseline-subscription/match` | `enterprise_intake.match_enterprise_vendor_baseline_record` | Medium |
| POST | `/api/enterprise/vendor-governance/events` | `vendor_governance.create_vendor_governance_event` | **High** (governance write, no `request` param at all) |
| POST | `/api/enterprise/vendor-governance/events/{event_id}/create-capa` | `vendor_governance.create_capa_for_vendor_event` | High |
| POST | `/api/enterprise/vendor-governance/events/{event_id}/link-capa` | `vendor_governance.link_vendor_event_to_existing_capa` | High |

**Recommended remediation (increment 3):** add the module's established guard
(`require_hospital_or_enterprise_admin(request)` for `enterprise_intake`;
`require_enterprise_auth(request)` for `vendor_governance`) and a tenant-scope
check, with a negative test per endpoint. **Not done in this increment** because
(a) each needs its intended-caller contract confirmed with the owning workstream
to avoid breaking a demo/integration flow (execution rule: "do not silently
secure an endpoint if doing so could break an intended public integration"), and
(b) it is a focused, testable change better isolated in its own PR than bundled
into endpoint governance.

## Enforcement control delivered this increment

`backend/tests/test_directive_002_endpoint_governance.py`:

* `test_no_endpoint_is_unknown` — fails if any route becomes unclassifiable.
* `test_unauthenticated_writes_stay_within_reviewed_allowlist` — fails if a
  **new** unauthenticated write is added outside the 21 reviewed here.
* `test_allowlist_has_no_stale_entries` — forces the allowlist to shrink as
  endpoints are secured (prevents a permanently-stale exception list).
* health/readiness probe behavior.

This converts endpoint security from a one-time audit into a **continuously
enforced invariant** without the risk of mass-securing 21 endpoints blind.

## Other coverage gaps (documented, not yet enforced)

* **Ownership verification** (object-by-ID belongs to caller's tenant) is not
  yet asserted uniformly; tracked with the F1 route-migration inventory.
* **Per-endpoint audit coverage** is uneven; the audit-actor contract
  (`AUDIT_ACTOR_SPECIFICATION.md`) is the basis for closing it.

No claim of HIPAA, SOC 2, ISO 13485, IEC 62304, ISO 14971, FDA clearance, or
21 CFR Part 11 compliance is made here.
