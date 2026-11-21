# P472-03 Batch 7 (B7.3) — Governance Decision Packets: GD-5 … GD-9, AUTH-1, AUTH-2, PA-1 (v1)

**Issue #189 · PR #181 (DRAFT) · baseline `c6ba66c`.** Prepared by the engineering author. **Nothing in this
document is a decision.** Every signature block is empty; no policy described as an option has been
implemented beyond what the "Current behaviour" row states (fail-closed floors from Batches 4–6). No
privilege has been provisioned, no historical ownership assigned.

"Engineering recommendation" means the author's view of the least-privilege option. It carries no authority.
The decision owner may choose any option, a variant, or none.

How to record a decision: complete the signature block in a **new version** of this file (never edit a
signed block), cite the decision ID in the implementing commit, and add the row to the governance decision
register (`gd1-gd4-governance-decision-register-v6.md`). An implementation that predates its signed decision
must be reverted.

---

## GD-5 — How a client selects its tenant

| | |
|---|---|
| Question | Is the tenant selected **only** by the `X-Tenant-Id` header, or may a route also take `tenant_id` in query/body/path (a "claim")? |
| Owner (role) | API / product owner, with the security architect consulted |
| Current behaviour (code) | Header selects among the caller's **verified** memberships (`principal_tenant`); any other channel is a claim that must **equal** the verified tenant (`refuse_other_tenants`, 403 otherwise). The B5.1 web client sends the header and repeats it where a route requires the parameter. |
| Option A — header only | Remove tenant parameters from all tenant-scoped routes (contract break for API clients); smallest attack surface; one place to audit. |
| Option B — header + equal claim (status quo) | Backwards-compatible; every claim is a second input that must keep being refused when unequal (the 1,913-route sweep checks this). |
| Option C — claim may select | **Rejected by the security baseline** (this was AW-04). Listed for completeness only. |
| Security implications | A and B are both fail-closed today. B keeps a larger surface whose correctness depends on the sweep remaining in CI. |
| Dependencies | API versioning / client inventory (no production client list was examined). |
| Implementation consequence | A: deprecate parameters, one release with 400 on presence, then remove. B: none. |
| Rollback criteria | A: re-accept equal claims if an integration partner is blocked and no migration path exists. |
| Engineering recommendation | B now, A as a versioned API change. |

Signature: Decision ☐A ☐B ☐other ____ · Name ____ · Role ____ · Date ____ · Reference ____ — **UNSIGNED**

---

## GD-6 — Genesis manufacturer updates: visibility, moderation, publisher identity

| | |
|---|---|
| Questions | (1) Who may see unpublished (draft / pending) updates? (2) Who may publish or reject — the submitting tenant, a platform curator, or nobody but a curator? (3) Is a publisher's identity public, pseudonymous, or hidden for published content? (4) Retention and visibility of rejected content. (5) May hospitals submit, or only verified manufacturer organisations (links GD-9)? |
| Owner (role) | Network / clinical governance, with the security owner consulted |
| Current behaviour (B6.1 `38251e6`, fail-closed floor) | Unpublished = submitting tenant only (others 404, no existence oracle). Publish/reject **only by the submitting tenant's leadership** (`admin`, `spd_manager`), audited (`genesis.manufacturer_update.{decision}`); cross-tenant review 404. Publisher filter may name only the caller's tenant (403). `supersedes_id` must be the submitter's own update. Submitter/reviewer/publisher identities redacted for non-owners (`owned_by_caller`). |
| **Gap the owner must see** | Narrowing publish/reject to the owner means a tenant can still **self-publish** its own content to the whole network feed. The B5.3 packet's proposed default (§3.3) was *no* self-publication (curator only). B6.1 did not designate a curator because that is this decision. Today, therefore, network-wide publication has **no second-party control**. |
| Option A — curator-moderated | A separately authorized platform curator role publishes/rejects; submitters cannot self-publish. Requires provisioning that role (and PA-1-style oversight for it). |
| Option B — self-publication (status quo floor) | Each tenant's leadership publishes its own updates. No new privileged role; no quality or safety gate on what reaches other hospitals. |
| Option C — manufacturer-only submission + curator | Only verified manufacturer organisations (GD-9) submit; curator publishes. Strongest provenance; depends on GD-9. |
| Publisher identity options | P1 public org name · P2 stable pseudonym (current redaction is closest to P2/P3) · P3 none. CLAUDE.md requires hospital identities in cross-hospital intelligence to be anonymised; a manufacturer's identity may be a different question. |
| Security implications | B leaves an unmoderated cross-tenant content channel (integrity / clinical-safety risk, not confidentiality). A and C add a privileged role that needs audited, purpose-bound access. |
| Dependencies | GD-9 (manufacturer identity) for C; PA-1 for any platform curator; clinical governance for content criteria. |
| Implementation consequence | A/C: new role + permission, review route restricted to it, migration of nothing (statuses unchanged); content already published under the open model needs a review decision (no production data examined). |
| Rollback criteria | Revert to the B6.1 floor (owner-only) if the curator role cannot be staffed; never revert to the pre-B6.1 any-tenant model. |
| Engineering recommendation | A or C, with P2. Until decided: keep the B6.1 floor and treat self-publication as an accepted-or-rejected risk **explicitly** (risk R-GENESIS-SELF-PUBLISH, register v6). |
| Tripwires affected | RB-T01, RB-T15…T23 (dispositions should not be finalized as ACCEPT-CONVERSION before GD-6 confirms the floor is the intended policy). |

Signature: Decision ____ · Publisher identity ____ · Name ____ · Role ____ · Date ____ — **UNSIGNED**

---

## GD-7 — GuardianX evidence-ledger ownership, legacy quarantine, audit chain, retention

| | |
|---|---|
| Questions | (1) Ownership model: tenant-owned (Option T) or platform-wide with a privileged reader (Option P)? (2) May legacy rows be attributed from the audit chain alone (no sealed content digest)? (3) Retention period. (4) Who may read quarantined rows, and how are they released? (5) Must `source_id` resolve to an object the writer's tenant owns? |
| Owner (role) | Platform-security owner, with clinical operations (CLIN-1) and data governance |
| Current behaviour (B6.2 `3f479d9`, `00aec32`) | No schema change. Reads, lists and verify are allowed only for the single real tenant on the entry's hash-chained audit trail (`audit_owner_tenant`); entries with no audit event, only `default-tenant`, or several tenants are readable by **no tenant**. Replay of workflow executions and rules is tenant-scoped. Integrity sealing since B5.4. Dry-run classifier `classify_entries` is read-only. |
| **Gap the owner must see** | Until `6a661bb` writes were not source-scoped (reproduced: tenant B wrote under A's inspection and A's ownerless key; B's explanation appeared in A's replay). Batch 7 adds a fail-closed floor (`guardianx_source_ownership`): owned types (inspection, workflow_execution) must belong to the writer; ledger writes into an ownerless key already used by another or an unprovable owner are refused. **Still undecided (this decision):** what an ownerless key means (namespace? registration? refuse?), explanation ownership (RB-T32, explanations still readable cross-tenant), and contaminated rows written before Batch 7 — the dry-run classifier would attribute them to the injector, so any migration must also check source ownership. |
| Option T — tenant-owned | Add `tenant_id` + `ownership_status`; attribute only rows the reviewed dry run lists as attributable; others quarantined. Write path refuses foreign `source_id` where the source type has an owner table. |
| Option P — platform-wide | Single ledger; tenant users lose ledger reads entirely; a platform-security reader (PA-1 class) with purpose + audit. Write contamination still needs a source-ownership check. |
| Audit-chain preservation | Either option must not rewrite `audit_logs` rows or hashes (ORM refuses updates; migration must not touch them). Attribution writes go to the ledger table only, with a new audit event per attribution. |
| Retention options | none (status quo: never deleted) · fixed period aligned to the accreditation evidence retention requirement · legal-hold aware. Owner must name the governing requirement; engineering has none on file. |
| Dependencies | CLIN-1 (release of quarantined rows), PA-1 (any platform reader), HIST (whether past cross-tenant reads happened). |
| Implementation consequence | T: migration (add columns, guarded downgrade), write-path ownership check, release workflow. P: route removal for tenant users (contract break), privileged route. |
| Rollback criteria | Migration downgrade refused while attributed/quarantined rows exist (same guard as `b5a2c7e19d40`); rollback to the B6.2 read gate, never to unscoped reads. |
| Engineering recommendation | T, chain-only legacy rows stay quarantined unless CLIN-1 releases them row by row, write-side source check added with T. |
| Tripwires affected | RB-T24…T28 (RB-T28's write-side gap is flagged in its review packet). |

Signature: Option ☐T ☐P · Legacy chain-only attribution ☐yes ☐no · Retention ____ · Name ____ · Role ____ · Date ____ — **UNSIGNED**

---

## GD-8 — Commercial platform-wide health view

| | |
|---|---|
| Question | Should a platform-wide (all-tenant) commercial health view exist, and for whom? |
| Owner (role) | Commercial owner + security owner |
| Current behaviour | API: available only to the PA-1 privileged class (platform admin; development tokens outside production), logged to `lumenai.security.tenant`. UI no longer offers it (B5.1). |
| Option A — remove | Delete the platform-wide branch (`allow_platform_wide`); simplest. |
| Option B — keep for a named role | Restrict to a dedicated commercial-analytics role (not general platform admin), aggregate-only, with k-anonymity threshold and purpose logging. |
| Option C — status quo | PA-1 class only; depends entirely on PA-1. |
| Security implications | Any platform-wide view is a cross-tenant read; tenant identities must not be exposed (anonymisation requirement). |
| Dependencies | PA-1. |
| Rollback criteria | B → A if the threshold or logging cannot be verified. |
| Engineering recommendation | A unless a named business need exists; otherwise B. |

Signature: ☐A ☐B ☐C · Name ____ · Role ____ · Date ____ — **UNSIGNED**

---

## GD-9 — Manufacturer membership: grant/revoke authority and audit

| | |
|---|---|
| Questions | Who may grant / revoke; identity proofing; role catalogue; whether manufacturer principals are a separate identity class from hospital tenants; expiry policy; approval workflow and what `grant_reference` must cite; HTTP exposure; re-certification of rows inserted before Batch 5. (Full list: `p472-03-b52-manufacturer-iam-lifecycle-v1.md` §4.) |
| Owner (role) | IAM owner, with vendor management / legal for proofing |
| Current behaviour (B5.2 `de80b7b`) | Expiry enforced; audited, idempotent revocation **service** (no HTTP route); grants **gated closed** (`GRANTS_APPROVED = False`); role catalogue `{manufacturer_viewer}`; no self-grant; migration `b5a2c7e19d40` with guarded downgrade. Existing rows keep NULL provenance. |
| Option A — central IAM operator, dual control | Platform IAM operator grants and revokes with a second approver; manufacturer admins request only. |
| Option B — delegated to manufacturer admin | A verified manufacturer admin grants within its own organisation; platform IAM revokes. Scales; needs strong proofing of the admin. |
| Option C — status quo | No grants possible (gate closed); memberships only via direct DB change, which bypasses audit. **Operationally this pushes people to unaudited DB edits.** |
| Security implications | C is the riskiest in practice (unaudited edits). A has the strongest control. B's risk depends on proofing. |
| Dependencies | GD-6 (if manufacturers become submitters), identity provider capabilities (OIDC claims). |
| Implementation consequence | Open the gate in a reviewed commit citing this decision; add routes with the chosen permission; re-certification job for pre-Batch-5 rows. |
| Rollback criteria | Close the gate (`GRANTS_APPROVED = False`) — revocations keep working. |
| Engineering recommendation | A, with mandatory expiry ≤ 12 months and re-certification of existing rows. |

Signature: ☐A ☐B ☐C · Expiry ____ · Name ____ · Role ____ · Date ____ — **UNSIGNED**

---

## AUTH-1 — Legacy users-table password login

| | |
|---|---|
| Question | Enable password login against the `users` table, or remove the path? |
| Owner (role) | Authentication owner |
| Current behaviour (B5.5 `e226ee2`) | `_verify_user` explicitly disabled and logged; `/api/auth/login` via this path returns 401 (it never worked against the canonical schema — it queried columns that do not exist). |
| Option A — remove | Delete the path and its route branch; JWT/OIDC remain the credential sources. |
| Option B — implement properly | bcrypt over `users.hashed_password`, lockout, rate limiting, audit, MFA decision; a new credential source to review. |
| Security implications | B adds attack surface (credential stuffing) and a second identity store. |
| Rollback criteria | A is reversible from git history if a documented need appears. |
| Engineering recommendation | A. |

Signature: ☐A ☐B · Name ____ · Role ____ · Date ____ — **UNSIGNED**

## AUTH-2 — `users.role` now applied (deployment inventory)

| | |
|---|---|
| Question | Accept that a principal with a `users` row and no role-assignment row now receives `users.role` (previously the broken query fell back to `viewer`), and require an inventory before deployment? |
| Owner (role) | Authentication owner + platform operations |
| Current behaviour | Resolution order: assignment table → `users.role` by email; exact-case match wins; disagreeing case variants → `viewer`; any DB error → logged, `viewer`. |
| Risk | Any deployed `users.role` values silently become effective at deploy time (possible privilege **increase**). **No production data was examined.** |
| Option A — accept + inventory | Read-only inventory of `users.role` values (by an authorized operator) reviewed before deploy. |
| Option B — ignore `users.role` | Make the assignment table the only role source; `users.role` informational. |
| Rollback criteria | B can be applied as a one-line change if the inventory finds unexpected privileged roles. |
| Engineering recommendation | A, with B as fallback. |

Signature: ☐A ☐B · Inventory reference ____ · Name ____ · Role ____ · Date ____ — **UNSIGNED**

---

## PA-1 — Platform-administrator and development-token cross-tenant access

| | |
|---|---|
| Question | Should a platform administrator (and, outside production, a development token) be able to act in any tenant? If yes: under what purpose binding, approval, time limit and tamper-evident oversight? |
| Owner (role) | Platform-security owner, with compliance / privacy |
| Current behaviour (code: `app/auth/tenant_scope.py` `principal_tenant`, `principal_claim_tenant`) | Platform admins (global role `admin`) and development principals resolve to **any named tenant** (or their own, or `default-tenant`) with no membership check. Each such resolution emits a WARNING to the `lumenai.security.tenant` logger — **a standard log, not a hash-chained audit record**. Development-token acceptance is gated by **environment variables with two different names**: `app/deps.py` enables the dev token map only when `ENABLE_DEV_AUTH` is true **and** `APP_ENV` is not `production`/`prod`; `app/enterprise_auth.py` rejects non-JWT bearer tokens only when `ENVIRONMENT == "production"`. The startup configuration check (`Settings.validate()`, called from `app/main.py`) **logs** `DEV_AUTH_TOKEN must not remain dev-token in production` but does **not** refuse to start. Whether a deployment sets all of these consistently was **not** examined (no production access). No purpose, ticket, approval or expiry is captured for privileged access. |
| Option A — remove | No cross-tenant access for anyone; operations needing it use explicit per-tenant membership (provisioned, audited, expiring). |
| Option B — break-glass | Cross-tenant access only through a purpose-bound session: ticket reference + justification, second-person approval, short expiry (e.g. 4 h), hash-chained audit event per access, alert to security on use, periodic review. |
| Option C — status quo | Standing access with log-only detection. |
| Security implications | C is a standing cross-tenant privilege whose only evidence is a mutable log line; it also undermines every tenant-isolation tripwire (the sweep's identities are not platform admins). |
| Dependencies | GD-7 Option P and GD-8 Option B both depend on B; HIST (the investigation must also cover past privileged access). |
| Implementation consequence | B: session model, approval workflow, durable audit sink (the resolver currently has no DB handle — the sink must be added at the dependency layer), alerting. |
| Rollback criteria | B → A if approvals or the audit sink cannot be operated; never B → C. |
| Engineering recommendation | B (or A if no operational need is shown). Development tokens: unify the gating on one environment variable and make the startup check **refuse** to start in production with dev auth enabled or the default token (a fail-closed change that still needs this decision's owner to confirm the deployment variables). Tracked as risk R-DEVTOKEN-GATING. |

Signature: ☐A ☐B ☐C · Name ____ · Role ____ · Date ____ — **UNSIGNED**

---

## Summary

| ID | Owner (role) | Engineering recommendation | Blocks |
|---|---|---|---|
| GD-5 | API/product | B now, A versioned | — (both options fail-closed) |
| GD-6 | Network/clinical governance | A or C + pseudonymous publisher | RB-T01, RB-T15…T23 disposition; self-publication risk |
| GD-7 | Platform security (+ CLIN-1) | T; write-side source check | RB-T24…T28 disposition; legacy evidence availability |
| GD-8 | Commercial + security | A | — |
| GD-9 | IAM | A, expiry ≤ 12 months | manufacturer onboarding (no grants possible) |
| AUTH-1 | Authentication | A (remove) | — |
| AUTH-2 | Authentication + ops | A + inventory | **deployment** |
| PA-1 | Platform security + compliance | B (break-glass) | release (standing cross-tenant privilege) |

**No decision is signed. Release HOLD / NO-GO.**
