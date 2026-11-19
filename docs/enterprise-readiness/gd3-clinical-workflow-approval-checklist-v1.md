# GD-3 — Clinical-workflow approval checklist (v1)

| | |
|---|---|
| Reviewed commit | `1ff863d` |
| Purpose | Let the clinical-operations / instrument-inspection workflow owner decide whether the GD-3 quarantine is acceptable, and under what conditions |
| Status | Prepared by the author; **PENDING OWNER APPROVAL** · no production attribution performed |

Detail and the migration evidence are in
`gd3-quarantine-impact-and-attribution-proposal.md`. This checklist is the
**approval instrument**. Every "Required approval" cell is **Pending**; none is
filled, because no owner decision has been made.

## 1. Per-workflow impact and approval

For each workflow: previous behaviour → post-GD-3 behaviour (while a tenant's
baselines are quarantined), operational interruption, patient-safety / quality
implication, authorized fallback, responsible owner, required approval.

| Workflow | Previous | Post-GD-3 (quarantined) | Interruption | Safety / quality implication | Authorized fallback | Owner (role) | Approval |
|---|---|---|---|---|---|---|---|
| Instrument inspection | Scored against any approved baseline | Routed to supervisor review when no owned baseline resolves | Inspection completes; no auto score | **Safe direction** — abstains rather than scoring against an unowned baseline; no false "pass" | Supervisor review / manual assessment | Instrument-inspection workflow owner | Pending |
| Borescope comparison | Compared to resolved baseline | "No manufacturer/vendor baseline" → supervisor review | Comparison not auto-produced | Safe direction; avoids comparing to an unverified-owner baseline | Supervisor review | Clinical operations | Pending |
| Vendor baseline matching | Matched across shared library | `no_match` for quarantined rows → review queue | Matching returns none | No incorrect match surfaced | Baseline review queue | Baseline-workflow owner | Pending |
| Manufacturer baseline matching | (same shared library) | Same as above; manufacturer-managed category not built | Same | Same | Review queue | Baseline-workflow owner + IAM (AW-07) | Pending (AW-07 blocker) |
| Baseline approval | Any admin could approve for all | Quarantined id resolves as not-found until attributed | Cannot approve unowned rows | Prevents one tenant approving another's baseline | Attribution first (§2) | Baseline-workflow owner | Pending |
| Scoring & confidence | Numeric baseline-match metrics | `baseline_found False`; metrics unavailable; confidence lowered | Scores withheld | Safe; no fabricated confidence | Supervisor review | Clinical quality lead | Pending |
| Inspection history | Showed baseline-derived metrics | Baseline metrics null for affected inspections | Lower/zero baseline metrics shown | Display honesty; no misleading metric | — | Clinical quality lead | Pending |
| Governance reporting | Packet embedded baseline audit trail | Empty baseline-trail section; counts 0 for that tenant | Thinner packet | No foreign data in packet (improvement) | — | Compliance / quality | Pending |
| Supervisor review / exceptions | Fallback path | Receives the additional abstained inspections | Higher review volume | Workload increase; manageable | Staffing / triage | Clinical operations | Pending |

**Net:** the change is in the **safe direction** (abstain → supervisor review,
never a wrong score), but it **increases supervisor-review volume** and removes
baseline-derived metrics for affected tenants until attribution. That workload and
metric change is the decision the workflow owner must accept before deployment.

**What is NOT affected:** inspections resolving from the network
`BaselineLibraryEntry` library (separate, not quarantined); CV inference
provenance (P4.7.2); no inspection is blocked.

## 2. Attribution-readiness checklist (per baseline) — no production attribution permitted

A quarantined baseline may be released to a tenant **only** when all of these are
satisfied and recorded. **None has been performed.**

- [ ] **Verifiable ownership evidence** — one of: original submission audit event
      naming the submitting tenant; approving administrator's tenant membership at
      approval time; or a signed statement from the data owner. (Never inferred
      from names, headers, instrument associations, or usage.)
- [ ] **Authorized reviewer** — the person attributing holds an authorized
      baseline-governance role and is named in the record.
- [ ] **Audit logging** — a `baseline_attributed` audit event (design item; not
      built) recording tenant, evidence reference, reviewer, timestamp.
- [ ] **Post-attribution validation** — after `tenant_id` is set: baseline visible
      to only the assigned tenant (cross-tenant read still not-found); the owning
      tenant's scoring now resolves it; no other tenant's scoring does.
- [ ] **Controlled change window** — attribution performed deliberately, never as
      an automatic migration step.

Ambiguous / orphaned / manufacturer-published rows stay quarantined; a
manufacturer baseline intended for many tenants waits for the (unbuilt,
unapproved) platform-shared / access-grant mechanism and the AW-07 fix.

## 3. Sign-off (unsigned)

| Role | Name | Decision | Date |
|---|---|---|---|
| Instrument-inspection workflow owner | _unassigned_ | _pending_ | — |
| Clinical operations | _unassigned_ | _pending_ | — |
| Clinical quality lead | _unassigned_ | _pending_ | — |
| Baseline-workflow owner | _unassigned_ | _pending_ | — |

Until signed, quarantine stays, no baseline is attributed, GD-3 stays open, HOLD /
NO-GO.
