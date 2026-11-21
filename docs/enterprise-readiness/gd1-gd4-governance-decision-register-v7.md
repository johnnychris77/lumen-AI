# Governance Decision Register (v7 — Batch 8)

**PR #181 (DRAFT) · Batch 8 (Issue #190) · Issue #189** · supersedes v6 (preserved). **No decision is signed. No signed approval exists
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
| PA-1 | platform-admin / dev-token / environment gates | platform security + compliance | break-glass + single production signal + refuse at startup + remove public demo token | standing access; gates split across APP_ENV / ENVIRONMENT; DEMO_MODE public `dev-token`; dead portfolio grants (Batch 8 investigation) | **PENDING — blocks release; RB-T38…T40 failing** |
| CLIN-1 | release criteria for quarantined historical evidence | clinical owner (+ data governance) | criteria in B7.4 §5 | all quarantined, none released | **PENDING** |
| HIST | historical-access investigation | incident response / security lead (+ legal) | authorize the read-only plan with B7.4 §6 scope additions | not started; no production access | **PENDING — authorization required** |

**Separation of evidence:** author technical evidence ≠ independent verification (none) ≠ governance approval
(none) ≠ release authorization (none). **HOLD / NO-GO.**


Batch 8 adds the approval workflow (owner, second approver, signature record, accepted-risk expiry): `p472-03-batch8-governance-and-forensic-workflows-v1.md`. **No decision is signed.**
