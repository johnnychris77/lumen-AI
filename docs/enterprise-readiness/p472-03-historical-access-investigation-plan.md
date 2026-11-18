# P472-03 — Historical Access Investigation Plan

| | |
|---|---|
| Repository / PR | `johnnychris77/lumen-AI`, PR #181 (draft) |
| Prepared from | The repository only, at `48ef45f` and the batch 2 commits |
| Audience | Authorized production security personnel |
| Release status | **HOLD / NO-GO** |

## 0. What has and has not been done

**No investigation has been carried out.** The author of this plan had no
access to any production system, database, log store or deployment record, and
did not request or use any. Nothing in this document is a finding about
production. Section 7 is a summary of what can be said from the code alone;
it contains no log data because none was read.

This plan is read-only by design. It asks for nothing to be modified,
attributed, deleted or "cleaned up" during the investigation.

**Whether this is an incident is not decided here.** The code allowed access
that should not have been possible. Whether anyone used it is the question the
investigation answers. Until it does, the organisation's incident-response
owner should treat it as a suspected exposure (section 8).

---

## 1. Authorization required before starting

| Needed | From |
|---|---|
| Written authorization to read production logs and the production database for this purpose, naming the people and the time window | Security lead and the system owner |
| Confirmation of the legal basis and any notification clocks that start on discovery | Compliance / privacy officer, legal counsel |
| A named incident-response owner who receives the results | Security lead |
| Read-only database credentials (a role with `SELECT` only) and read access to the log store | Platform operations |
| Agreement on where working data is kept (an access-controlled location; **not** GitHub, a PR, an issue, chat or a shared drive) | Security lead |

Do not start on a verbal instruction. Do not use application administrator
credentials for database reads.

---

## 2. Scope: what was exposed, and how a request would look

Dates of first exposure cannot be taken from this repository: the files were
added in a single import on 2026-07-05, which is not when the code was first
deployed. **Take the start of each window from deployment records.** The end
of each window is the deployment of the fixing commit; none of these commits
has been deployed, so every window is still open on any environment running
`main`.

### 2.1 Unauthenticated access (highest priority)

| Finding | Routes | A matching request |
|---|---|---|
| AW-09 | 41 routes under `/api/enterprise/` (intake history, inspections, evidence, CAPAs, KPI and audit command center views, CSV/Power BI/PDF exports) | Any request with **no** `Authorization` header answered with 2xx |
| AW-10 | `GET /api/enterprise/vendor-governance/events`, `/summary`, `/capa-linkage-summary`, `/powerbi-csv` | The same |
| GD-1 counters | `GET /api/network/participants/count`, `/api/global-intelligence/network-stats`, `/api/infrastructure/platform-stats` | The same (aggregate figures only) |
| Health probes | `GET /api/capa/health`, `GET /api/enterprise/vendor-governance/health` | The same (returned all-tenant totals; the CAPA probe also returned a server file path) |

The most sensitive single route is
`GET /api/enterprise/audit-command-center` and its `.csv` and `.powerbi.csv`
forms, which returned audit-log entries of every tenant.

### 2.2 Authenticated cross-tenant access

| Finding | Routes | A matching request |
|---|---|---|
| AW-02 | 176 routes that depend on `resolve_tenant` (audit logs and exports, governance approvals, packet releases and holds, leadership packets, retention policies, legal hold, and others) | `X-LumenAI-Tenant-Id` and `X-Tenant-Id` both present **with different values** |
| AW-01 | `/api/tenant-analytics/*`, `/api/ml/*`, `/api/operations/*` | A tenant header naming a tenant the authenticated user has no membership in |
| AW-05 | 373 routes in 43 modules (capture devices, inspections, dataset registry, quality modules and others) | The same, from a user with no membership or more than one |
| AW-11 | `/api/capa/*` | Any CAPA id not created by the caller's tenant (the register had no tenant at all) |
| AW-12 | `POST /api/governance-sla-scanner/run`, `POST /api/governance-command-center/actions/run-sla-scan`, `POST /api/customer-operations-hub/actions/run-sla-scan`, `GET /api/governance-sla-scanner/status` | Any successful call by a tenant administrator: the response contained every tenant's results |
| GD-2 | The five `/api/enterprise/audit/…verify…` routes | A verification request for a resource id or hash belonging to another tenant |

The complete route lists are in
`p472-03-batch1-remediation-review.md` (section 7),
`p472-03-batch2-remediation-review.md` and the CSV beside the
application-wide matrix. Use those lists as the filter; do not retype them.

---

## 3. Evidence sources

What the application itself records, from the code. Everything about the
hosting platform must be confirmed with platform operations: this repository
does not state it.

| Source | What it holds | Limits |
|---|---|---|
| Web server access log (uvicorn, standard output) | Timestamp, client address as seen by the process, method, path with query string, status | **No headers**: it does not show whether a request carried a token or which tenant headers it sent. Behind a proxy the client address is the proxy's unless forwarded headers are configured |
| Hosting platform request log / edge log | Possibly the true client address, user agent, response size | Existence, fields and **retention are unknown from the repository**. Confirm first: on many plans retention is days, not months |
| `audit_logs` table | `tenant_id`, `actor_email`, `actor_role`, `action_type`, `resource_type`, `resource_id`, `request_method`, `request_path`, `client_ip`, `details`, `created_at` | Written only by handlers that call the audit service. **Most read routes write nothing.** `tenant_name`, and on some routes actor and role, were client-supplied before the fixes. Rows written without a tenant carry `default-tenant` |
| Hash-chained enterprise audit events (inside `audit_logs.details`) | `event_hash`, `previous_event_hash`, and `request_id` / `correlation_id` **when the client sent them** | The server does not generate a request id, so most rows have none |
| Export events (`audit_logs`, action types containing `export`) | That an export was produced, its hash and filters | The exports that needed no authentication recorded an empty tenant and an "unknown" actor |
| `tenant_memberships` | Who was a member of which tenant, role, enabled flag | Current state only. No history of when a membership was granted or removed |
| `user_role_assignments`, `users` | Global roles, including who holds `admin` | Current state only |
| Authentication | Login issues a signed token with `sub`, `iat`, `exp` | **No login-event table was found.** Successful and failed logins are visible only if the access log or the platform log shows calls to the login route |
| `capture_devices` | Device registrations with `tenant_id` and creation time | A registration in a tenant by a user who was not a member is direct evidence of AW-05 |
| CAPA register (`capas`, a separate SQLite file on the application container when the main database is PostgreSQL) | CAPA rows; `tenant_id` empty for rows written before batch 1 | On a container file system this file may not survive a redeploy. Establish whether it still exists before anything else touches the container |
| Vendor governance events | In process memory only | **Not recoverable.** Lost at every restart; never persisted |
| Deployment history | Which commit ran when | Needed to bound every window |

Two consequences to state plainly in the report: for unauthenticated reads the
only evidence is an access or edge log, and if its retention has lapsed the
honest conclusion is "cannot be determined", not "no evidence of access".

---

## 4. Order of work

1. **Preserve.** Before any query, ask platform operations to extend or export
   retention for the access and edge logs covering the windows, and to take a
   read-only snapshot of the database and of the CAPA SQLite file. Record who
   did it and when. This is the only step with a clock on it.
2. **Bound the windows** from deployment history: first deployment of each
   affected route, and the commit running now.
3. **Unauthenticated access (2.1).** From the access or edge log, select 2xx
   responses on the listed paths. Because the access log has no headers,
   separate anonymous from authenticated requests by correlation: the
   application's own web client always sends a token and is preceded by a
   login and by calls to authenticated routes from the same client; a request
   to an export path with no surrounding session, from an address that never
   logged in, or with a non-browser user agent is a candidate.
4. **Split-header and foreign-tenant requests (2.2).** Not visible in the
   access log. Use the database instead:
   - `audit_logs` rows where `actor_email` had no enabled membership in the
     row's `tenant_id` (join to `tenant_memberships`; remember that table has
     no history, so a miss is a lead, not proof);
   - rows in tenant-owned tables created by a user who is not a member of the
     row's tenant, wherever the table records its creator (`capture_devices`,
     operations workflows and executions, image labels, governance approvals,
     packet releases and holds, retention policies);
   - SLA events in a tenant whose creation time matches a scanner run
     triggered by another tenant's administrator
     (`action_type` in `governance_sla_scanner_run`,
     `command_center_run_sla_scan`, `customer_operations_hub_run_sla_scan`).
     The audit row of each such run stored the full all-tenant result in
     `details`: those rows are themselves cross-tenant data held in the
     triggering tenant's audit log, and should be counted.
5. **Exports.** List export events in the windows; for each, the tenant,
   actor, filters and hash. Exports with an empty tenant or actor "unknown"
   are the previously unauthenticated ones.
6. **Ownerless and mixed records** (inputs to governance decisions GD-2 and
   GD-4): count CAPA rows with an empty tenant; count audit hash chains whose
   events span more than one `tenant_id` value.
7. **Privileged accounts.** List accounts holding the global role `admin`
   (they can name any tenant by design) and review their activity across
   tenants in the windows.
8. **Conclude per finding**: accessed (with counts), not accessed (state the
   evidence that supports a negative), or cannot be determined (state which
   evidence is missing and why).

All database work is `SELECT` only, on a snapshot where possible. Nothing is
updated, re-attributed or deleted. If a query would need a write to proceed,
stop and record why.

---

## 5. Handling rules

- Raw logs, query results, IP addresses, e-mail addresses, tenant names and
  record contents stay in the agreed access-controlled location. **None of it
  goes into GitHub** in any form: not a commit, PR, issue, comment, gist or CI
  artifact.
- Do not copy secrets, tokens, API keys, instrument images, patient
  information or raw log lines into any report. Refer to records by table and
  primary key.
- Record every query run, who ran it and when (an investigation log), so the
  work can be repeated and reviewed.
- The investigation must not use the vulnerable routes to "confirm" exposure
  against production. Reproduction belongs in a non-production environment
  with synthetic tenants; the repository's tests already do it.

---

## 6. What the sanitized report contains

Counts and conclusions only:

| Item | Example of acceptable content |
|---|---|
| Windows | "Route group X: exposed from deployment D1 to present" |
| Evidence available | "Access log retained N days; covers M% of the window" |
| Per finding | "N anonymous 2xx requests to export paths from K distinct sources; J judged not to be the web client" |
| Tenants affected | A count, and identifiers held only in the restricted annex |
| Data categories | "Audit log entries, quality findings, CAPA records" — categories, not contents |
| Gaps | What could not be determined and why |
| Recommendation | Notify / do not notify, with the reasoning |

The restricted annex (identities, addresses, record keys) is kept with the
incident record, not with the report.

---

## 7. Summary from the code alone (no production data)

- The defects in section 2 were real and reproducible: each has a test in the
  repository that failed before its fix and passes after.
- The 41 enterprise quality routes and 4 vendor-governance reads returned data
  to a request with no credentials at all. No skill was needed beyond knowing
  the URL, and the URLs are in the web client's JavaScript.
- The cross-tenant defects needed a valid account on some tenant, or a global
  role with no tenant.
- Reads through these routes left no application-level trace. A clean
  `audit_logs` table says nothing about whether they were read.
- Vendor governance events cannot be investigated at all: they were never
  stored.
- Nothing here indicates that any of it was exploited. Nothing here indicates
  that it was not.

---

## 8. Incident-response recommendations

For the incident-response owner to accept, change or reject:

1. **Open a suspected-exposure record now**, with discovery dated to the
   application-wide review (`5ab34f2`, `90fb1a6`), and let the compliance
   officer decide which notification clocks, if any, have started. Do not wait
   for the investigation to decide whether to open it.
2. **Preserve logs today** (step 1 of section 4). Every day of delay may
   remove evidence.
3. **Reduce exposure on any deployed environment before the fixes ship.** The
   fixes are in an unmerged draft PR and nothing has been deployed. Options
   that need no application change, for the system owner to choose from:
   block the unauthenticated enterprise export paths at the proxy; restrict
   the deployment to known networks; take the environment out of service. This
   plan recommends that one of them is chosen; it does not choose.
4. **Rotate nothing blindly.** No credential is known to have leaked through
   these routes. The CAPA health probe disclosed a server file path, not a
   secret. If the investigation finds access to audit-log exports, review what
   those exports contained before deciding on rotation.
5. **Review holders of the global `admin` role** and remove any that are not
   needed; that role reaches every tenant by design and leaves no access log.
6. **After the investigation**, decide notification to affected tenants with
   legal counsel, from the evidence. If evidence for the unauthenticated
   window is missing, that uncertainty is itself something tenants may need to
   be told; that is a decision for counsel and the compliance officer.
7. **Add what was missing**, as engineering follow-ups outside this PR: a
   server-generated request id on every request and log line; an
   authentication-event log; an audit event for refused requests; an access
   log for platform-administrator cross-tenant actions; a retention period for
   access logs that is written down.
