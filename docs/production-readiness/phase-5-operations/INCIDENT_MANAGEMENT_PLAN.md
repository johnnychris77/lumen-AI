# LPR-DIR-016 — Incident Management Plan (Phase 5)

**Basis:** doc inventory + code inspection at `bd94bc5`. **Finding up front:** no
dedicated incident-management / on-call / postmortem process document was found in
the repo (the `OPERATIONS_RUNBOOK.md` has a short "On-call" section only). This plan
**establishes the framework** and records the gap.

## Current state (honest)
- **OPS-INC-01 (MAJOR):** **no formal incident-response process** — no severity
  matrix, escalation policy, communication plan, on-call rotation, or postmortem
  template exists as an operational artifact. Detection also lacks alerting
  (OPS-OBS-02), so incidents may go unnoticed until a human observes them.
- The platform *does* have strong **forensic** support for RCA once an incident is
  known: hash-chained tamper-evident audit, immutable evidence, `/ready`
  per-dependency status, and a `docs/quality/rca-engine.md` (product RCA, not ops
  incident RCA).

## Proposed severity classification (to adopt)

| Sev | Definition | Example | Response |
|---|---|---|---|
| **SEV-1** | Platform down / data-integrity or tenant-isolation breach | DB down; cross-tenant leak (SEC-C-01 realized) | immediate page; all-hands; exec comms |
| **SEV-2** | Major degradation | heavy-endpoint saturation; auth outage | page on-call; ~30 min ack |
| **SEV-3** | Minor / single-tenant | report failure; slow dashboard | ticket; next business hours |
| **SEV-4** | Cosmetic / informational | log noise | backlog |

## Incident lifecycle (to adopt)
1. **Detect** — alert (to be built, OPS-OBS-02) / `/ready` 503 / user report.
2. **Triage & classify** — assign Sev; open incident channel.
3. **Respond** — follow the relevant runbook (`OPERATIONS_RUNBOOKS.md`): DB restore,
   auth outage, storage failure, rollback, etc.
4. **Communicate** — status updates on cadence by Sev; tenant comms for SEV-1/2.
5. **Escalate** — on-call → lead → COO/CISO per Sev + time-in-state.
6. **Resolve & verify** — `/ready` green + audit-chain re-verify + evidence checksum
   check.
7. **RCA + postmortem** — blameless postmortem within N days for SEV-1/2; track
   action items to closure.

## Security-incident tie-in
Any suspected auth-bypass / cross-tenant event (SEC-C-01, SEC-H-01) is **SEV-1** and
triggers the security IR path (rotate `SECRET_KEY`/webhook secrets, revoke tokens,
audit-chain review). The Phase 3 compliance gap "no formal IR/disclosure process"
is the same finding surfaced here (OPS-INC-01).

## Roll-up
| ID | Sev | Finding |
|---|---|---|
| OPS-INC-01 | MAJOR | No formal incident-response/on-call/postmortem process (framework proposed here) |
| (OPS-OBS-02) | MAJOR | No alerting → detection is human-dependent |

**Action (Phase 6):** adopt this framework as living runbooks, stand up on-call +
paging, and run one incident game-day (e.g. inject a DB outage in staging) to
validate the flow.
