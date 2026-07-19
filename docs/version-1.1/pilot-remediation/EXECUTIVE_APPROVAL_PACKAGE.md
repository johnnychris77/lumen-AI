# LPR-DIR-028 — Executive Approval Package (Workstream 5)

Approval artifacts to be countersigned by each required role **against demonstrated
evidence**, not against plans. **No approval is granted here.** Each sign-off block is a
template; an approval counts only when signed with the referenced evidence attached (recorded
in `PILOT_ENTRY_EVIDENCE_TRACKER.md`).

## Approval principle (honesty)
> A role owner SHALL NOT sign until the evidence their approval depends on **exists and is
> verified**. Signing against a plan (rather than demonstrated capability) is not a valid
> approval and does not satisfy the Pilot Entry Gate.

## Approval blocks

### CTO — Technical readiness
- **Depends on:** managed env up (WP-06/WP-03), regression green on the deployed RC, migration
  head verified, monitoring live.
- **Decision:** ☐ Approved ☐ Denied — Evidence refs: ______  Signature/date: ______

### CISO — Security readiness
- **Depends on:** secrets management + TLS (WP-06), fail-closed webhook proof, prod `SECRET_KEY`
  guard active, SEC-H-01/02 status disclosed.
- **Decision:** ☐ Approved ☐ Denied — Evidence refs: ______  Signature/date: ______

### Quality (CQO) — Quality system
- **Depends on:** baseline review sign-offs, audit hash-chain integrity, capture/validation SOPs,
  human-review enforcement evidence.
- **Decision:** ☐ Approved ☐ Denied — Evidence refs: ______  Signature/date: ______

### Clinical (CMTO / Clinical Operations) — Clinical readiness
- **Depends on:** signed site + sponsor, equipment qualification, operator competency, site
  escalation SOP.
- **Decision:** ☐ Approved ☐ Denied — Evidence refs: ______  Signature/date: ______

### Operations (COO) — Operational readiness
- **Depends on:** executed deploy + rollback + DR drills, alerting/on-call live, runbooks proven.
- **Decision:** ☐ Approved ☐ Denied — Evidence refs: ______  Signature/date: ______

### Executive Sponsor (CEO) — Pilot authorization
- **Depends on:** all five approvals above + written pilot protocol + scope/risk acceptance.
- **Decision:** ☐ Approved ☐ Denied — Evidence refs: ______  Signature/date: ______

## Attachments to accompany a real submission
Pilot protocol; risk register + acceptance; evidence tracker (all COMPLETE for pilot-blocking
items); data agreement; site + sponsor agreements. **Constraints reaffirmed:** advisory-only
AI, mandatory human review, no causation/diagnostic claims, no FDA/regulatory-clearance
claims, no production authorization.

## Current status
**All six approvals: PENDING** (unchanged from LPR-DIR-027). This package makes them
*actionable* by defining exactly what evidence each approver requires — it does **not** grant
any of them.
