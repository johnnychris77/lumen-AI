# Milestone 9 — Governance Approval Matrix and Decision Packages (v1)

**Issue #191 (M9.3) · PR #181 (DRAFT) · baseline `bed42c8`.** Prepared by the change author for the people who
must decide. **No decision in this document is made, signed or implied.** Every decision is **PENDING**. Owners
are named by **role**; the release authority appoints the people.

The repository has **one collaborator** (the owner). No eligible second approver or independent reviewer exists
in the repository today; appointing them is the first action (§1, row 0).

Sources:
- full option analysis: `p472-03-batch7-governance-decision-packets-v1.md` (GD-5…GD-9, AUTH-1/2, PA-1);
- `p472-03-batch7-clinical-data-governance-packet-v1.md` (CLIN-1);
- `p472-03-b53-gd6-decision-packet-v1.md`, `p472-03-b54-guardianx-ledger-adr-v1.md`,
  `p472-03-batch8-guardianx-explanation-ownership-v1.md`;
- `m9-pa1-architecture-assurance-packet-v1.md`.

This matrix updates each package to the code at `bed42c8` and adds the approval record.

## 1. Approval matrix

| # | Decision | Owner (role) | Second approver (role) | Blocks | Status |
|---|---|---|---|---|---|
| 0 | Appoint the people below; appoint ≥1 independent security reviewer | **Release authority** | — | everything | **PENDING** |
| 1 | GD-5 tenant selection contract | API / product owner | — | — | **PENDING** |
| 2 | GD-6 Genesis visibility, moderation, publisher identity | network / clinical governance | security owner (consulted) | RB-T01, RB-T15…T23 dispositions | **PENDING** |
| 3 | GD-7 GuardianX ownership model, ownerless keys, explanations, legacy, retention | platform security + data governance | clinical owner | RB-T24…T37 dispositions; legacy availability | **PENDING** |
| 4 | GD-8 platform-wide commercial view; portfolio access (with PA-1) | commercial + security | — | PA1-04 | **PENDING** |
| 5 | GD-9 manufacturer grant/revoke authority | IAM owner | vendor management / legal | manufacturer onboarding; AW-07 closure | **PENDING** |
| 6 | AUTH-1 legacy users-table login | authentication owner | — | — | **PENDING** |
| 7 | AUTH-2 `users.role` effective on deploy; pre-deploy inventory | authentication + operations | security | **deployment** | **PENDING** |
| 8 | PA-1 privileged access (floor ratification + standing items) | platform security + compliance | independent security | **release** | **PENDING** |
| 9 | CLIN-1 release criteria for quarantined historical evidence | clinical owner + data governance | privacy / security | legacy availability | **PENDING** |
| 10 | HIST historical-access investigation authorization | security lead + system owner | privacy / legal | release (exposure unknown) | **PENDING** — package `m9-historical-access-authorization-package-v1.md` |
| 11 | Operations deployment-variable attestation | operations | security | **deployment** | **PENDING** — template §4 |
| 12 | Release decision | release authority | — | — | **PENDING** — `m9-enterprise-release-readiness-assessment-v1.md` |

## 2. How a decision is approved

1. **Record.** Open one GitHub issue per decision, linked to #191, citing this matrix row. Engineering
   answers questions in the issue and changes no code.
2. **Decide and sign.** The owner chooses an option, a variant, or none, and posts the signature block from
   their own account. Owner and second approver sign separately. Relayed signatures are void. A signature by
   the change author is void.
3. **Accepted risk.** Name the risk owner, compensating controls, expiry (≤ 6 months recommended) and review
   trigger.
4. **Implement after signing.** Use a separate commit citing the decision issue. Tests are written to the
   signed option. Any tripwire assertion change is listed in the decision record. An implementation that
   predates its decision and differs from it is reverted.
5. **Verify.** A non-author reviewer runs the affected tripwires (handbook) and records the disposition in
   the M9 ledger.
6. **Register.** A row moves to *signed + implemented + reviewed* only when steps 2–5 all have links.

Signature block (copy into the decision issue):

```
Decision: <ID>   Option: ____   Variant/conditions: ____
Accepted risks (owner, controls, expiry, review trigger): ____
Owner: name ____ role ____ date ____ (own GitHub account: ____)
Second approver: name ____ role ____ date ____ (own GitHub account: ____)
Implementation commit(s): ____   Reviewer disposition link(s): ____
```

## 3. Decision packages (state at `bed42c8`)

### 3.1 GD-5 — tenant selection contract
- **Question.** Is the tenant selected only by the `X-Tenant-Id` header (A), or by header plus an equal claim
  in query, body or path (B, status quo)?
- **Code at `bed42c8`.** B is implemented. `principal_tenant` checks the header against verified memberships;
  `refuse_other_tenants` returns 403 when a claim differs. Both options fail closed.
- **Recommendation (no authority).** B now; A as a versioned API change.
- **Evidence.** 1,913-route sweep, 0 findings on both DBs.

`Signature: ☐A ☐B ☐other — UNSIGNED`

### 3.2 GD-6 — Genesis manufacturer updates
- **Question.** Who sees unpublished content; who publishes (owner, curator, or manufacturer + curator); the
  publisher identity model.
- **Code.** The B6.1 floor:
  - unpublished content is visible to the submitter only;
  - publish/reject is done by the **submitting tenant's own leadership**, so self-publication to the network
    has no second-party control (R-GENESIS-SELF-PUBLISH);
  - identities are redacted for non-owners.
- **Options.**
  - A: curator-moderated.
  - B: self-publication (status quo).
  - C: manufacturer-only submission plus curator.
  - Publisher identity: P1 public, P2 pseudonym, P3 none.
- **Recommendation.** A or C, with P2.
- **Blocks.** RB-T01, RB-T15…T23 should not be accepted before GD-6 confirms the floor.

`Signature: ☐A ☐B ☐C · identity ☐P1 ☐P2 ☐P3 — UNSIGNED`

### 3.3 GD-7 — GuardianX ownership
- **Code.** Fail-closed floor (`3f479d9`, `6a661bb`, `c22a879`):
  - ledger and explanation reads and writes are owned by the single real tenant on the hash-chained audit
    trail;
  - owned source types (inspection, workflow_execution) must belong to the writer;
  - writes into an ownerless key already used by another tenant are refused;
  - explanation creation and override write audit events;
  - unattributable legacy rows are quarantined;
  - replay is limited to the GD-2 scope.
- **Still undecided.**
  1. Option T (tenant-owned columns) vs P (platform-wide, privileged reader).
  2. Ownerless-key semantics: fresh keys are first-writer today (R-GX-OWNERLESS-KEYS), with a concurrent
     first-write race (R-GX-WRITE-RACE).
  3. Chain-only attribution of legacy rows.
  4. Retention.
  5. Explanation content sealing (R-GX-EXPLAIN-SEAL).
- **Recommendation.** T; chain-only legacy rows stay quarantined unless CLIN-1 releases them row by row;
  namespace ownerless keys.
- **Blocks.** RB-T24…T37 dispositions. RB-T28 is read-side only.

`Signature: ☐T ☐P · ownerless keys ____ · legacy chain-only ☐yes ☐no · retention ____ — UNSIGNED`

### 3.4 GD-8 — platform-wide commercial view and portfolio access
- **Code.**
  - The platform-wide view is available only to the PA-1 privileged class (global `admin`; dev tokens
    outside production) and is logged only.
  - Portfolio grants (`portfolio_authz.py`) are dead code; the literal dev-token grant is inert in production.
- **Options.**
  - A: remove.
  - B: a named commercial-analytics role, aggregate-only with k-anonymity, purpose-logged.
  - C: status quo.
  - Portfolio: none, or an anonymised, purpose-bound, audited named role.
- **Constraint.** Hospital identities in cross-hospital data must be anonymised. "Fixing" the dead keys would
  give every `tenant_admin` all-tenant, non-anonymised access.
- **Recommendation.** A unless there is a named need, then B.

`Signature: ☐A ☐B ☐C · portfolio ____ — UNSIGNED`

### 3.5 GD-9 — manufacturer membership authority
- **Code.**
  - Grants gated closed (`GRANTS_APPROVED = False`).
  - Expiry enforced; audited revocation service.
  - Pre-Batch-5 rows are unprovenanced and still active.
- **Options.**
  - A: central IAM operator with dual control.
  - B: delegated manufacturer admin.
  - C: status quo; in practice this pushes changes to unaudited DB edits.
- **Recommendation.** A, expiry ≤ 12 months, re-certify existing rows.

`Signature: ☐A ☐B ☐C · expiry ____ — UNSIGNED`

### 3.6 AUTH-1 — legacy users-table login
- **Code.** `_verify_user` is disabled (401) since `e226ee2`.
- **Options.** A: remove. B: implement properly (bcrypt, lockout, rate limit, audit, MFA).
- **Recommendation.** A.

`Signature: ☐A ☐B — UNSIGNED`

### 3.7 AUTH-2 — `users.role` effective on deploy
- **Code.** Role resolution: assignment table, then `users.role`, then `viewer`. Any deployed `users.role`
  value becomes effective at deploy, which can raise privilege. **No production data examined.**
- **Related PA-1 findings.**
  - PA1-08: the `ADMIN_BOOTSTRAP_TOKEN` path writes `admin` assignments.
  - PA1-11: any admin can grant `admin`.
- **Options.** A: accept plus a read-only inventory by an authorized operator before deploy. B: assignment
  table only.
- **Recommendation.** A, with B as fallback. The inventory should also list current `admin` assignments and
  whether `ADMIN_BOOTSTRAP_TOKEN` is set.

`Signature: ☐A ☐B · inventory reference ____ — UNSIGNED`

### 3.8 PA-1 — privileged access
- **Code.** The environment-gate floor is author-remediated (`829f36a`): canonical determination,
  fail-closed startup, call-time gates, `ALLOW_DEV_AUTH_IN_PROD` removed.
- **Unchanged.**
  - global-admin cross-tenant reach with log-only record (PA1-10);
  - no break-glass;
  - `ADMIN_BOOTSTRAP_TOKEN` minting (PA1-08);
  - bootstrap tenant admins re-enabled at every start (PA1-07, PA1-09);
  - admin-grants-admin (PA1-11);
  - portfolio (PA1-04);
  - staging (PA1-05);
  - vocabulary (PA1-12);
  - non-`app.main` entry points (PA1-13).
- **Decisions.** The nine questions in `m9-pa1-architecture-assurance-packet-v1.md` §5.
- **Recommendation.** Ratify the floor; break-glass for global admin; one-shot or remove the bootstrap token;
  a recorded approval and expiry for bootstrap admins.
- **Blocks.** Release. RB-T38…T40 acceptance goes with this decision.

`Signature (owner + second approver): floor ☐ratify ☐amend ☐replace · admin ☐A remove ☐B break-glass ☐C standing · bootstrap token ____ · bootstrap admins ____ · staging ____ — UNSIGNED`

### 3.9 CLIN-1 — quarantined historical evidence
- **Classes.**
  - legacy vendor baselines (NULL tenant);
  - ownerless CAPAs;
  - GuardianX ledger entries and pre-Batch-8 explanations with no provable owner;
  - unsealed pre-B5.4 entries;
  - Genesis content published under the open model;
  - pre-Batch-5 manufacturer memberships;
  - `users.role` rows.
- **Release criteria (proposed).** Packet §5: the class decision is signed; the row meets the evidence
  standard; a clinical owner confirms there is no unreviewed outcome change; data governance confirms no PHI
  and the correct tenant; an audit event per release; counts reconciled.
- **Prohibited.** Heuristic attribution; rewriting audit rows or hashes.
- **Operational check needed.** The clinical owner should confirm that no ownerless CAPA is clinically urgent.

`Signature (clinical owner + data governance + privacy/security): criteria ☐approve ☐amend · CAPA urgency check done ☐ — UNSIGNED`

## 4. Operations deployment-variable attestation (template; row 11)

Before any deployment of this branch, an operations owner, **not the change author**, completes this from
the deployment platform. Values marked † are recorded as *present/absent* only, never their value.

| Variable | Required for the new startup check | Web service | Worker service |
|---|---|---|---|
| `APP_ENV` | `production` (same as `ENVIRONMENT`) | ____ | ____ |
| `ENVIRONMENT` | `production` | ____ | ____ |
| `AUTH_MODE` | `oidc` | ____ | ____ |
| `OIDC_ISSUER_URL`, `OIDC_AUDIENCE` | set | ____ | ____ |
| `ENABLE_DEV_AUTH` | `false` or absent | ____ | ____ |
| `DEMO_MODE` | absent | ____ | ____ |
| `ALLOW_DEV_AUTH_IN_PROD` | absent (no longer honoured) | ____ | ____ |
| `SECRET_KEY` † | present, strong | ____ | ____ |
| `ADMIN_BOOTSTRAP_TOKEN` † | absent unless PA-1 decides otherwise (PA1-08) | ____ | ____ |
| `BOOTSTRAP_TENANT_ADMINS` | per PA-1 decision (PA1-07/09) | ____ | ____ |
| `DEV_AUTH_TOKEN` † | absent or irrelevant (dev auth off) | ____ | ____ |

`Attested by (operations): name ____ role ____ date ____ · Security countersign ____ — NOT ATTESTED`

**Status: no decision is signed. HOLD / NO-GO.**
