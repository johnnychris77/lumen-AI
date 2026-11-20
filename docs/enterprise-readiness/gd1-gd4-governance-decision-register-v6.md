# Governance Decision Register (v6 — Batch 7)

**PR #181 (DRAFT) · Issue #189** · supersedes v5 (preserved). **No decision is signed. No signed approval exists
in the repository, the PR or issues #187–#189.** Decision packets with options, implications, dependencies and
rollback criteria: `p472-03-batch7-governance-decision-packets-v1.md` (GD-5…GD-9, AUTH-1/2, PA-1) and
`p472-03-batch7-clinical-data-governance-packet-v1.md` (CLIN-1, HIST).

| ID | Decision | Owner (role) | Engineering recommendation (no authority) | Current code (fail-closed floor) | Status |
|---|---|---|---|---|---|
| GD-1 … GD-4 | as v2/v3 | per v2 | — | enforced floors | **PENDING sign-off** |
| GD-5 | tenant selection: header only vs header + equal claim | API / product | B now, A versioned | header + equal claim | **PENDING** |
| GD-6 | Genesis visibility, moderation, publisher identity | network / clinical governance | curator-moderated (A or C), pseudonymous publisher | owner-only visibility and review; **self-publication possible** | **PENDING — blocks RB-T01, RB-T15…T23 disposition** |
| GD-7 | GuardianX ownership (T/P), legacy attribution, retention, write-side source check | platform security (+ CLIN-1) | T; chain-only legacy stays quarantined; add write-side check | audit-trail read gate; legacy unreadable; writes not source-scoped | **PENDING — blocks RB-T24…T28 disposition** |
| GD-8 | commercial platform-wide view | commercial + security | remove | PA-1 class only, logged | **PENDING** |
| GD-9 | manufacturer grant/revoke authority, proofing, expiry | IAM | central IAM + dual control, expiry ≤ 12 months | grants gated closed; audited revocation service | **PENDING** |
| AUTH-1 | legacy users-table login | authentication | remove | disabled, logged | **PENDING** |
| AUTH-2 | `users.role` applied; pre-deploy inventory | authentication + operations | accept + inventory | applied | **PENDING — blocks deployment** |
| PA-1 | platform-admin / dev-token cross-tenant access | platform security + compliance | break-glass (purpose, approval, expiry, hash-chained audit) | standing access; log line only; dev-token gating split across `APP_ENV` / `ENVIRONMENT` | **PENDING — blocks release** |
| CLIN-1 | release criteria for quarantined historical evidence | clinical owner (+ data governance) | criteria in B7.4 §5 | all quarantined, none released | **PENDING** |
| HIST | historical-access investigation | incident response / security lead (+ legal) | authorize the read-only plan with B7.4 §6 scope additions | not started; no production access | **PENDING — authorization required** |

**Separation of evidence:** author technical evidence ≠ independent verification (none) ≠ governance approval
(none) ≠ release authorization (none). **HOLD / NO-GO.**
