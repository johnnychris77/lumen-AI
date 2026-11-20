# Governance Decision Register (v8 — PA-1 remediation)

**PR #181 (DRAFT) · PA-1 remediation (Issue #190) · Issue #189** · supersedes v7 (preserved). **No decision is signed. No signed approval exists
in the repository, the PR or issues #187–#190.** Decision packets with options, implications, dependencies and
rollback criteria: `p472-03-batch7-governance-decision-packets-v1.md` (GD-5…GD-9, AUTH-1/2, PA-1) and
`p472-03-batch7-clinical-data-governance-packet-v1.md` (CLIN-1, HIST).

| ID | Decision | Owner (role) | Engineering recommendation (no authority) | Current code (fail-closed floor) | Status |
|---|---|---|---|---|---|
| GD-1 … GD-4 | as v2/v3 | per v2 | — | enforced floors | **PENDING sign-off** |
| GD-5 | tenant selection: header only vs header + equal claim | API / product | B now, A versioned | header + equal claim | **PENDING** |
| GD-6 | Genesis visibility, moderation, publisher identity | network / clinical governance | curator-moderated (A or C), pseudonymous publisher | owner-only visibility and review; **self-publication possible** | **PENDING — blocks RB-T01, RB-T15…T23 disposition** |
| GD-7 | GuardianX ownership (T/P), legacy attribution, retention, write-side source check, **explanation ownership** | platform security (+ CLIN-1) | T; chain-only legacy stays quarantined | ledger + explanations owned by single tenant on audit trail (B6.2 + Batch 8 `c22a879`); legacy rows of both unreadable; owned sources must be the writer's; ownerless keys first-writer, one namespace | **PENDING — blocks RB-T24…T37 dispositions; must confirm or replace the Batch 8 explanation floor** |
| GD-8 | commercial platform-wide view | commercial + security | remove | PA-1 class only, logged | **PENDING** |
| GD-9 | manufacturer grant/revoke authority, proofing, expiry | IAM | central IAM + dual control, expiry ≤ 12 months | grants gated closed; audited revocation service | **PENDING** |
| AUTH-1 | legacy users-table login | authentication | remove | disabled, logged | **PENDING** |
| AUTH-2 | `users.role` applied; pre-deploy inventory | authentication + operations | accept + inventory | applied | **PENDING — blocks deployment** |
| PA-1 | platform-admin / dev-token / environment gates | platform security + compliance | break-glass + single production signal + refuse at startup + remove public demo token | **`829f36a` (user-directed remediation, not a signed decision):** one production signal (APP_ENV or ENVIRONMENT); startup refuses conflicts, `ENABLE_DEV_AUTH`, `AUTH_MODE`≠`oidc` (the `ALLOW_DEV_AUTH_IN_PROD` exception removed), `DEMO_MODE`; demo routes 403 in production. **Unchanged:** standing global-`admin` cross-tenant rule, break-glass/purpose binding absent, PA1-04 dead portfolio grants, PA1-05 dev mode outside production, PA1-07 bootstrap administrator | **PENDING — UNSIGNED; blocks release.** The decision must ratify or replace the floor (and the removed exception), and decide the unchanged items |
| CLIN-1 | release criteria for quarantined historical evidence | clinical owner (+ data governance) | criteria in B7.4 §5 | all quarantined, none released | **PENDING** |
| HIST | historical-access investigation | incident response / security lead (+ legal) | authorize the read-only plan with B7.4 §6 scope additions | not started; no production access | **PENDING — authorization required** |

**Separation of evidence:** author technical evidence ≠ independent verification (none) ≠ governance approval
(none) ≠ release authorization (none). **HOLD / NO-GO.**


Batch 8 adds the approval workflow (owner, second approver, signature record, accepted-risk expiry): `p472-03-batch8-governance-and-forensic-workflows-v1.md`. **No decision is signed.**

PA-1 remediation (`829f36a`) implemented the environment-gate floor under the user's explicit direction. That is
**not** a PA-1 or GD-8 signature: no reviewer, owner or second approver has acted. No portfolio-wide access was
activated, no administrator bootstrapped and no privileged role provisioned.
