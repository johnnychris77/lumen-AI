# Pre-Sterilization Command Center

## Objective

Give SPD Technicians, Supervisors, Managers, Market Directors, Infection
Prevention, and Executive Leadership one place that answers:

> "Are these instruments clinically ready to move forward to packaging and
> sterilization?"

And when the answer is no:

> "Why not, what risk was found, where was it found, and what should SPD
> do next?"

This is LumenAI's pre-sterilization quality gate — it operates entirely
before packaging and sterilization (see
`docs/architecture/pre-sterilization-boundary.md`). It never monitors,
measures, or validates the sterilization cycle itself.

## Route

`/pre-sterilization-command-center` (frontend) —
`frontend/src/pages/PreSterilizationCommandCenter.tsx`.

API: `GET /api/pre-sterilization-command-center/dashboard`
(`backend/app/routes/pre_sterilization_command_center.py`) returns all ten
modules in one payload; each module also has its own granular endpoint
(e.g. `/high-risk-findings`, `/tray-readiness`) for a page or integration
that only needs one section.

## The ten modules

| # | Module | Endpoint | Answers |
|---|---|---|---|
| 1 | Clinical Inspection Readiness Score | `/clinical-inspection-readiness` | What fraction of reviewed inspections are ready for packaging right now? |
| 2 | Tray Readiness Score | `/tray-readiness` | Is this tray ready to proceed, and if not, which instrument in it is blocking? |
| 3 | Instrument Readiness Score | `/instrument-readiness` | What is the current state of this specific physical instrument? |
| 4 | Facility Readiness Score | `/facility-readiness` | Is this facility's readiness rate improving, declining, or stable? |
| 5 | High-Risk Findings Queue | `/high-risk-findings` | Which unresolved inspections have a critical finding (blood, tissue, bone, crack, insulation damage)? |
| 6 | Supervisor Review Queue | `/supervisor-review-queue` | Which inspections are waiting on a human decision? |
| 7 | Missing Anatomy Zone Coverage | `/missing-zone-coverage` | Which inspections didn't capture all the required high-risk zones? |
| 8 | Baseline Coverage | `/baseline-coverage` | What fraction of inspections had an approved baseline to compare against, and which instrument types don't have one? |
| 9 | Repair / Remove From Service Queue | `/repair-remove-queue` | Which retired instruments are repairable vs. permanently removed? |
| 10 | Executive Risk Dashboard | `/executive-risk-dashboard` | The roll-up: readiness, queues, facility rollup, and anatomy-zone failure trend in one view. |

See `docs/command-center/readiness-score-model.md` for exactly how each
readiness state and score is computed, and
`docs/command-center/quality-gate-workflow.md` for how an instrument moves
through the gate end to end.

## Personas

All six personas read the *same* dashboard payload — the page tailors
which modules are visible by default per persona (client-side, in
`PreSterilizationCommandCenter.tsx`'s `PERSONA_MODULES` map), because the
underlying platform only has four RBAC roles (`admin`, `spd_manager`,
`operator`, `viewer`). The persona selector is a lens on one dataset, not
six separate data pipelines:

| Persona | Maps to role | Default modules |
|---|---|---|
| SPD Technician | `operator` | Missing zone coverage, high-risk findings, instrument readiness — what to fix right now. |
| SPD Supervisor | `spd_manager` | Supervisor review queue, high-risk findings, tray/instrument readiness. |
| SPD Manager | `spd_manager` | All operational modules — full department view. |
| Market Director | `admin` | Facility readiness, executive risk, baseline coverage. |
| Infection Prevention | `admin` | High-risk findings, executive risk, missing zone coverage. |
| Executive Leadership | `admin` | Readiness summary, executive risk, facility readiness. |

## Data model change

`Inspection.inspected_zones_json` was added (nullable-safe, backfilled
automatically via `ensure_columns` — see `app/db/column_migrator.py`) to
persist which zones a technician tagged as inspected, so Module 7 can be
computed retroactively across history rather than only at the moment of
capture. `json.dumps(None)` (`"null"`) means "not tagged" (coverage
`not_assessed`); an explicit list — even empty — means coverage was
assessed. See `app/services/inspection_coverage.py::compute_coverage` for
the scoring logic this feeds.

## What this command center is not

- It is not a sterilization validation, biological indicator, or
  sterilizer-performance system.
- It does not fabricate CV localization (bounding boxes/heatmaps) — Stage
  7/8 of `docs/architecture/future-ai-roadmap.md` are explicitly not
  started.
- It does not auto-dispose of an instrument. Every state is advisory;
  Module 6 (Supervisor Review Queue) and Module 8's confirmation tracking
  exist specifically because a human decision is what actually clears an
  instrument, per Design Principle 4
  (`docs/architecture/design-principles.md`).
