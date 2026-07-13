# LumenAI — Product Backlog

Organizes the entries in `docs/product-evolution/FEATURE_REQUEST_REGISTER.md` into the required backlog states. Every item remains traceable to its Feature ID and evidence source.

## Approved

Recommended for immediate Version 1.1 planning — each has clear evidence, low-to-medium effort, and no architecture-expansion risk.

| Feature ID | Title | Classification | Evidence Source |
|---|---|---|---|
| FR-001 | Reachable Supervisor Approve/Return Action | Workflow Improvement, Clinical | `docs/ux-review/USER_JOURNEYS.md` |
| FR-003 | Wire Orphaned Routes into Primary Navigation | User Experience | `docs/ux-review/NAVIGATION_ARCHITECTURE.md` |
| FR-005 | Fix Atlas Enterprise Dashboard N+1 Query Pattern | Performance | `docs/release-management/PERFORMANCE_LOG.md` |
| FR-006 | Consistent AI Inference Queuing | Performance | `docs/release-management/PERFORMANCE_LOG.md` |
| FR-007 | Mount Orphaned Veritas Panel / Wire GuardianX Tab | AI, Reporting | `docs/ux-review/UX_GUIDELINES.md` |
| FR-008 | Bind Human-Review-Required Disclaimer to Real Flag | Clinical, AI | `docs/ux-review/UX_GUIDELINES.md` |

## Planned

Evidence-backed and scoped, but requiring more design/sequencing work before an Approved disposition.

| Feature ID | Title | Classification | Evidence Source |
|---|---|---|---|
| FR-002 | Consolidate the Three Inspection-Creation Flows | Workflow Improvement | `docs/ux-review/USER_JOURNEYS.md`; `pilot-lessons-learned.md` §2b |
| FR-004 | Consolidate Duplicated Dashboard KPIs | Dashboard, Reporting | `docs/ux-review/DASHBOARD_STANDARDS.md` |
| FR-009 | Add Missing `Inspection` Model Fields | Infrastructure | `pilot-lessons-learned.md` §4 |

## Research

Needs further scoping before a target version can be committed.

| Feature ID | Title | Classification | Evidence Source |
|---|---|---|---|
| FR-010 | Add Missing Aggregate Reports (7 sub-items) | Reporting, Analytics | `pilot-lessons-learned.md` §5 |

## Deferred

None this cycle — every evidence-backed item found was scoped into Approved/Planned/Research above.

## Rejected

None this cycle. No feature proposal reached this register without a real evidence source, per this program's own governance discipline (see `docs/product-evolution/FEATURE_GOVERNANCE.md`) — there was nothing to reject on "it would be nice" grounds because no such proposal was accepted into the register in the first place.

## Pilot Requested

**Genuinely empty.** This is the backlog category this program's mission statement most directly points to as the primary evidence source, and it has zero entries because no real pilot has launched yet (`docs/product-evolution/CUSTOMER_FEEDBACK_REPORT.md`). This category should be the first one populated once a real pilot customer begins providing feedback — do not backfill it with the internal-dogfooding findings above, which are correctly categorized as Planned/Research/Approved on their own merits, not mislabeled as pilot requests.

## Future Release

Items explicitly out of scope for Version 1.1 because they would expand the frozen Version 1.0 architecture (per this program's own boundary):

- A general-purpose backlog-prioritization framework (`docs/commercial-readiness/PRODUCT_OPERATIONS_GUIDE.md`'s finding that none exists) — this is a process gap, not a product feature, and belongs to Product Operations, not Version 1.1's feature set.
- Real trained-model deployment to replace the deterministic inference fallback (`docs/clinical-validation/FINDING_TAXONOMY.md`) — this is correctly a major undertaking outside a minor-version patch cycle, requiring its own clinical validation study before any release.
- Secrets-rotation automation and a real security incident-response runbook (`docs/commercial-readiness/LEGAL_GOVERNANCE_PACKAGE.md`) — security-operations process work, tracked separately from product features.

## Traceability discipline

Every item above carries forward its Feature ID from `FEATURE_REQUEST_REGISTER.md` and its evidence-document citation — no item in this backlog exists without both, per this program's non-negotiable evidence standard.
