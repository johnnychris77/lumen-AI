# Pilot Studies

## Status: framework complete, live multi-site pilot pending

LumenAI's pilot validation framework (Phase 18) is fully built and
tested: ground-truth capture from real supervisor reviews, clinical
performance metrics, zone performance, the safety review queue, the
validation report generator, and the go/no-go readiness gate. See:

- `docs/validation/pilot-validation-protocol.md` — the protocol
- `docs/validation/ground-truth-review-workflow.md` — how ground truth is
  captured
- `docs/validation/clinical-performance-metrics.md` — what's measured
- `docs/validation/pilot-go-no-go-criteria.md` — the readiness gate

## Prior pilot activity

An earlier-phase pilot exercise (Bon Secours, tenant `bon-secours-pilot`)
exercised the platform end-to-end with seeded baseline and inspection
data (10 instruments, 25 baselines, 50 inspections) — see
`docs/pilot/pilot-findings-analysis.md` for the full findings. That
review identified and closed several adoption-blocking gaps (image
capture workflow friction, silent scoring gaps, missing
facility/department/tray persistence) that are now resolved in the
current architecture (Phase 20's `Inspection.facility_name`/`department`/
`tray_id` fields, the multi-agent scoring pipeline).

**This prior activity used seeded/demo data, not a completed live
clinical pilot with real supervisor-adjudicated ground truth at the
target cohort size (100 lumen images per
`docs/validation/pilot-validation-protocol.md`).**

## What a completed pilot study entry looks like

Once a site completes its Phase 18 pilot cohort, its entry here should
include:

- Site name/tenant (anonymized in any externally-shared version per the
  cross-hospital anonymization requirement)
- Study period and instrument families covered
- The full `/api/pilot-validation/report` output at study completion
- The go/no-go decision and rationale
- Whether the site's data contributed to a published benchmark
  (`docs/evidence/benchmark-reports.md`)

## Next milestone

The next real milestone for this section is running the Phase 18
protocol against a live site with real supervisor reviews accumulating
toward the 100-image target cohort — see
`docs/validation/pilot-validation-protocol.md` §2 for the exact target
criteria that would move an entry from "in progress" to "complete" here.
