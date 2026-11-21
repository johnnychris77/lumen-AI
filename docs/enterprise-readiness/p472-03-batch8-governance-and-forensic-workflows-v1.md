# P472-03 Batch 8 — Governance Approval Workflow and Historical-Access Forensic Plan (v1)

**Issues #190 (B7.8) / #189 · PR #181 (DRAFT).** This document defines **how** the decisions and the investigation
should be carried out, and what evidence each must leave behind. **No decision is made, no signature is recorded and
no production system is accessed by this document or by its author.**

Inputs: governance register v6, decision packets (`p472-03-batch7-governance-decision-packets-v1.md`), CLIN-1 packet
(`p472-03-batch7-clinical-data-governance-packet-v1.md`), PA-1 investigation
(`p472-03-batch8-pa1-privileged-access-investigation-v1.md`), HIST plan (`p472-03-historical-access-investigation-plan.md`).

## Part A — Decision and approval workflow (GD-5…GD-9, AUTH-1, AUTH-2, PA-1, CLIN-1)

### A1. Roles (named by role; people are appointed by the release authority)

| Role | Responsibility | Must not be |
|---|---|---|
| Decision owner (per item, see A3) | chooses an option and signs | the change author |
| Second approver | independent check of the owner's decision on PA-1, GD-7, CLIN-1, AUTH-2 | in the owner's reporting line for PA-1 |
| Security reviewer | confirms the implementation matches the signed option; dispositions tripwires | an author of the change under review |
| Release authority | appoints the above; issues the release decision | — |
| Engineering (author) | prepares packets, implements **only after** signature, records evidence | an approver of its own work |

### A2. Steps for every decision

1. **Open a decision record** (one GitHub issue per decision, linked to #190): packet link, options, engineering
   recommendation, affected tripwires and risks.
2. **Owner review.** The owner reads the packet and may ask engineering for evidence. Engineering answers in the
   record and changes no code.
3. **Decision.** The owner chooses an option, or rejects all options and asks for new ones. For an **accepted risk**
   the record must name the risk owner, the compensating controls, an **expiry date** (≤ 6 months recommended) and
   the review trigger.
4. **Signature.** The record needs name, role, date and the option chosen, posted by the owner's own account (not
   relayed by engineering). PA-1, GD-7, CLIN-1 and AUTH-2 also need the second approver's signature.
5. **Implementation.** Only after step 4. It goes in a separate commit that references the decision record. Tests must
   be written to the signed option, and the affected tripwires keep their assertions unless the decision changes the
   expected behaviour (then the assertion amendment is listed in the decision record).
6. **Verification.** The security reviewer runs the review kit for the affected tripwires
   (`backend/scripts/p472_03_tripwire_review_kit.py run --ids …`), inspects the authorization predicate and records
   ACCEPT-CONVERSION / REJECT-CONVERSION / ACCEPT-RISK / PENDING in the disposition ledger.
7. **Register update.** The governance register moves the item to *signed + implemented + reviewed* only when steps
   4–6 all have evidence links.

### A3. Decision index (status at Batch 8: all **UNSIGNED**)

| ID | Decision | Owner (role) | Second approver | Blocks | Packet |
|---|---|---|---|---|---|
| GD-5 | tenant selection contract | API / product owner | — | — | B7.3 |
| GD-6 | Genesis visibility, moderation, publisher identity | network / clinical governance | — | RB-T01, RB-T15…T23 dispositions | B7.3 |
| GD-7 | GuardianX ownership (T/P), legacy attribution, retention; **explanation ownership floor (Batch 8) to confirm or replace** | platform security + data governance | clinical owner | RB-T24…T37 dispositions; legacy release | B7.3 + Batch 8 explanation doc |
| GD-8 | platform-wide commercial view; portfolio access (PA1-04) | commercial + security | — | PA1-04 | B7.3 + PA-1 inv. |
| GD-9 | manufacturer grant/revoke authority | IAM | — | AW-07 closure | B7.3 |
| AUTH-1 | legacy users-table login | authentication owner | — | — | B7.3 |
| AUTH-2 | `users.role` applied; pre-deploy inventory | authentication + operations | security | **deployment** | B7.3 |
| PA-1 | platform-admin / dev-token / environment gates (RB-T38…T40) | platform security + compliance | independent security | **release** | B7.3 + Batch 8 PA-1 inv. |
| CLIN-1 | release of quarantined historical evidence (ledger + pre-Batch-8 explanations) | clinical owner + data governance | privacy/security | legacy availability | B7.4 |

Signature block template (copy into each decision record):

```
Decision: <ID>   Option chosen: ____   Accepted risks (owner, expiry): ____
Owner: name ____ role ____ date ____        Second approver: name ____ role ____ date ____
Implementation commit(s): ____   Reviewer disposition link(s): ____
```

## Part B — Historical-access forensic plan (HIST) — **not started; needs authorization**

### B1. Questions

1. Were any of the defects listed in B2 exploited before their fixes were deployed? By whom, against which tenants,
   and which data was read, written or deleted?
2. Did any cross-tenant write (GuardianX evidence or explanation, human override, Genesis publication) change data
   another tenant or a clinician relied on?
3. Was any privileged path (dev token, demo reset, platform admin) used in production?

### B2. Exposure windows to examine (from code history; deployment dates must come from the deploy log)

| Exposure | Introduced | Fixed in code | Evidence that might exist |
|---|---|---|---|
| AW-01…AW-13 tenant-isolation findings | per findings register | Batches 1–4 | edge/access logs (request path, tenant headers, status) |
| Genesis (RB-T01, T15…T23) | — | `38251e6` | access logs; `audit_logs` publish/reject events |
| GuardianX ledger reads (RB-T24…T28) | v5.2 | `3f479d9` | access logs only (reads were not audited) |
| GuardianX foreign writes (RB-T29…T31, T33) | v5.2 | `6a661bb` | ledger rows + their `audit_logs` (writer's tenant ≠ source owner) |
| **Explanation reads, overrides, key injection (RB-T32, T34…T36)** | v5.2 | **`c22a879`** | explanation rows (`created_by`, `human_overrides_json`); **no audit events before Batch 8**; access logs |
| Replay audit chain without GD-2 scope (RB-T37) | v5.2 | `c22a879` | access logs |
| PA1-02 demo reset with public token | `routes/demo.py` | **not fixed** | access logs for `/api/demo/*`; deploy history of `DEMO_MODE` |
| PA1-01 dev tokens with `ENVIRONMENT`-only production | — | **not fixed** | deploy env history; `@local.dev` actors in `audit_logs` |

### B3. Evidence preservation (first action once authorized; before anything else)

* Freeze and copy, with SHA-256 manifests and chain-of-custody records:
  - edge/load-balancer/application access logs for the full retention window;
  - the deploy and environment-variable history of every service (Render dashboard export);
  - a **read-only snapshot** of the production database (logical dump to restricted storage).
* Legal hold on log retention. Retention periods are not stated in the repository and must be confirmed with the
  platform provider.
* Nothing is modified, re-attributed or deleted in production during the investigation. That includes the
  quarantined GuardianX rows (GD-7 / CLIN-1).

### B4. Method (on the preserved copy, never on production)

1. Re-run `guardianx_ledger_ownership.classify_entries` (read-only) over the snapshot, plus an explanation
   equivalent, **which is not written yet** (it would use `guardianx_source_ownership.explanation_owner`).
   List rows whose writer tenant differs from the source owner, explanations with overrides by a different actor's
   tenant, and keys holding rows from several tenants.
2. Match access-log requests to the exposure windows. For each fixed route, the before/after requests in the review
   kit (`p472_03_tripwire_review_kit.py`) give the signature of an exploit request.
3. Search `audit_logs` for `@local.dev` actors and dev-mode tenants, and access logs for `Bearer dev-token` /
   `demo-token` use.
4. Produce a sanitised report: counts and anonymised tenant labels only, **no PHI**, no hospital names (anonymisation
   rule), and potential association language only.

### B5. Production-access authorization request (to be completed and signed by the authorizers)

```
Request: read-only access to production logs, deploy history and a database snapshot for the P472-03
         historical-access investigation (scope: B2; method: B4; preservation: B3).
Requested by (role): ____    Investigator(s) (named, not the change author for any reviewed fix): ____
Data handled: access logs (may contain IPs, user identifiers), database snapshot (may contain PHI-adjacent data)
Controls: least privilege (read-only), restricted storage, access logged, time-boxed to ____ days,
          destruction or retention of copies per ____ policy.
Approvals: Security owner ____ date ____ · Privacy/compliance ____ date ____ · Data governance ____ date ____
           Release authority ____ date ____
Status: NOT REQUESTED / NOT APPROVED — no production access has occurred.
```
