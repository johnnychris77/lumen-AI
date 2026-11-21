# Milestone 9 — Historical-Access Investigation (HIST) Authorization Package (v1)

**Issue #191 (M9.3) · PR #181 (DRAFT) · baseline `bed42c8`.** An approval-ready request for the people who can
authorize a read-only investigation of whether the defects fixed on this branch were used in production.

**Status: NOT REQUESTED / NOT APPROVED. No production system, log, database, deployment record or secret has
been accessed by the author or for this package.** Nothing here is a finding about production. It consolidates
and supersedes the scope sections of:
- `p472-03-historical-access-investigation-plan.md` (method, handling rules, report format, still
  authoritative);
- `p472-03-batch7-clinical-data-governance-packet-v1.md` §6;
- `p472-03-batch8-governance-and-forensic-workflows-v1.md` Part B.

## 1. Why an investigation is needed

The code fixed on this branch allowed access that should not have been possible: unauthenticated reads,
cross-tenant reads and writes, and privileged paths reachable with public literals. Passing tests and
0-finding sweeps show that **the code now refuses those requests**. They show nothing about whether anyone
made them before. Most of these reads left no application audit trail, so the answer depends on access/edge
logs and deploy history whose retention is unknown. **Every day of delay risks losing evidence.**

## 2. Scope — exposure windows

A window starts when the vulnerable code was deployed and ends when the fixing commit is deployed. Start dates
must come from deploy history, not from this repository. **None of the fixing commits on this branch has been
deployed**, so on any environment running `main`, every window below is still open.

| Group | Exposure | Fixed in code | What a matching request looks like (investigator) | Evidence likely available |
|---|---|---|---|---|
| A | AW-09, AW-10, GD-1 counters, health probes (unauthenticated) | Batch 1 `48ef45f`; GD-1 `440c0a1` | request with no `Authorization` header to the listed routes (plan §2.1) | edge/access logs |
| B | AW-01…AW-13 authenticated cross-tenant access | Batches 1–4 | tenant header/claim ≠ caller's membership (plan §2.2) | access logs; audit rows for writes |
| C | Genesis drafts, cross-tenant review/publish (RB-T01, T15…T23) | B6.1 `38251e6` | reads of `/api/genesis-ai/manufacturer-updates*` by non-submitters; publish/reject by non-owners | access logs; `audit_logs` publish/reject from B6.1 |
| D | GuardianX ledger reads (RB-T24…T28) | `3f479d9` | ledger reads where caller tenant ≠ entry audit tenant | access logs only |
| E | GuardianX foreign writes (RB-T29…T31, T33) | `6a661bb` | ledger rows whose writer tenant ≠ source owner | ledger rows + `audit_logs` |
| F | Explanation reads, foreign overrides, key injection (RB-T32, T34…T36); replay scope (RB-T37) | `c22a879` | explanation list/by-id/replay/package requests across tenants; `human_overrides_json` by another tenant's actor | explanation rows; **no audit events before Batch 8**; access logs |
| G | Manufacturer portal before AW-07 | `e615afd` | portal reads by identities without membership | access logs |
| **H** | **PA1-01** dev tokens active with `ENVIRONMENT`-only production | `829f36a` | any request authenticated as `*@local.dev`; bearer equal to a configured `DEV_*_TOKEN` | deploy env history; `audit_logs` actors `@local.dev`; access logs |
| **I** | **PA1-02** public `Bearer dev-token` / `demo-token` on `/api/demo/*`, incl. **data-deleting** `/api/demo/reset`, when `DEMO_MODE=1` | `829f36a` | `GET /api/demo/reset` and other `/api/demo/*`; deletions of `pilot_status` / `tenant_usage_counters` for `demo` / `default-tenant` | deploy env history of `DEMO_MODE`; access logs; DB row history if any |
| **J** | **AUTH_MODE=dev with ALLOW_DEV_AUTH_IN_PROD** in production: static dev token + **header-supplied admin role and any tenant** on enterprise routes | `829f36a` | enterprise requests with `Authorization: Bearer <DEV_AUTH_TOKEN>` and `X-LumenAI-Role` / `X-LumenAI-Tenant-Id` headers | deploy env history of `AUTH_MODE`; access logs; audit rows with header actors |
| **K** | Standing global-admin cross-tenant access (unfixed, PA1-10) | **not fixed** | `lumenai.security.tenant` WARNING lines "privileged cross-tenant access" / "platform-wide access" (only since the PA-1 logging change) | application logs |
| **L** | Admin minting via `ADMIN_BOOTSTRAP_TOKEN` (unfixed, PA1-08) | **not fixed** | `POST /api/admin/bootstrap`; `audit_logs` `admin_bootstrap_granted` (note: the event records the grantee, not the caller) | access logs; audit rows; `user_role_assignments` with `assigned_by='bootstrap'` |

## 3. Questions the investigation answers

1. For each group, was any matching request made in production? By which identity, from where, against
   which tenant, and what was read, written or deleted?
2. Did any cross-tenant write (GuardianX ledger or explanation, override, Genesis publication) alter data
   another tenant or a clinician relied on?
3. Were dev tokens, demo tokens or header-trusting dev auth ever active in production (H, I, J)? Was
   `/api/demo/reset` ever called there?
4. Who holds global `admin`, how was each granted (L), and what cross-tenant access did they use (K)?
5. Does any finding meet the organisation's definition of a security incident or a reportable breach? That
   determination belongs to the incident-response owner and legal, not to this team.

## 4. Order of work (on preserved copies, never on production)

1. **Preserve first.** Copy, with SHA-256 manifests and chain-of-custody records:
   - edge, load-balancer and application access logs for the full retention window;
   - application logs (for K);
   - deploy and environment-variable **history** for web and worker services, values of secrets
     redacted to present/absent;
   - a read-only logical snapshot of the production database to restricted storage.
   Request a legal hold on log retention.
2. **Environment history (H, I, J, L).** Establish, per service and time range, the values of `APP_ENV`,
   `ENVIRONMENT`, `AUTH_MODE`, `ENABLE_DEV_AUTH`, `DEMO_MODE`, `ALLOW_DEV_AUTH_IN_PROD`, and the presence of
   `ADMIN_BOOTSTRAP_TOKEN` / `DEV_AUTH_TOKEN`. If H/I/J were never possible in a period, close them for that
   period with evidence.
3. **Database (read-only snapshot).** Run the read-only classifier `guardianx_ledger_ownership.classify_entries`
   and an explanation equivalent. The equivalent is **not written yet**: it would use
   `guardianx_source_ownership.explanation_owner`, and needs a separately reviewed read-only script. Search
   `audit_logs` for `@local.dev` actors, `admin_bootstrap_granted`, and header-derived actors. List
   `user_role_assignments` with `role='admin'`.
4. **Access logs.** Match requests to the windows in §2. The review kit's before/after requests give the
   signature of each exploit request.
5. **Report.** A sanitised report:
   - counts and anonymised tenant labels only;
   - **no PHI** and no hospital names;
   - "potential association" language only;
   - no conclusions on causation.

## 5. Handling rules (from the plan; binding)

- Read-only. Nothing in production is modified, attributed, deleted or "cleaned up" during the
  investigation. That includes quarantined GuardianX rows (GD-7 / CLIN-1).
- Least-privilege credentials (`SELECT` only; read-only log access). Never application admin credentials.
- Working data stays in an access-controlled location agreed by the security lead: **not** GitHub, a PR, an
  issue, chat or a shared drive.
- Investigators are named and are not authors of any fix being assessed.
- Time-boxed; copies destroyed or retained per the stated policy at the end.

## 6. Authorization request (to be completed and signed by the authorizers — not by engineering)

```
Request:      Read-only investigation of historical access for P472-03 (scope §2 groups A–L; method §4; rules §5)
Requested by (role): ____________________   Date: __________
Investigator(s) (named; not an author of any reviewed fix): ____________________
Incident-response owner: ____________________
Systems: production access/edge logs ☐  application logs ☐  deploy/env history ☐  DB read-only snapshot ☐
Data handled: access logs (IPs, user identifiers); DB snapshot (may contain PHI-adjacent data)
Controls: SELECT-only role; read-only log access; restricted storage at ____; access logged;
          time-boxed to ____ days; copies destroyed/retained per ____ policy by ____
Legal basis / notification clocks confirmed by (privacy/legal): ____________ date ______
Approvals:
  Security lead ____________ date ______      System owner ____________ date ______
  Privacy / compliance ____________ date ____  Data governance ____________ date ______
  Release authority (informed) ____________ date ______
Status: NOT REQUESTED / NOT APPROVED — no production access has occurred.
```

## 7. Immediate recommendations for the incident-response owner (no action taken by engineering)

1. Open a **suspected-exposure** record now. Whether it becomes an incident is decided by the investigation.
2. Preserve logs now (§4.1), even before the full authorization, if policy allows preservation without
   analysis.
3. On every deployed environment, confirm the PA-1 variables against the refusal list (governance matrix §4).
   If `DEMO_MODE`, `ENABLE_DEV_AUTH`, `AUTH_MODE=dev` or `ADMIN_BOOTSTRAP_TOKEN` is set in production, remove
   it through the normal change process.
