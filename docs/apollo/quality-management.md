# Project Apollo — Quality Management Center

LumenAI OS v4.7 — the Autonomous Clinical Quality Management System (CQMS).

## Naming disambiguation

This codebase already had an extensive quality management ecosystem across
five prior sprints before Apollo. Every one of the following was read in
full before Apollo added a single line of code:

| Concern | Pre-existing system | Apollo's relationship to it |
|---|---|---|
| `/api/quality` prefix | `app/routes/quality_dashboard.py` (v1.5) | Apollo mounts at `/api/apollo` instead |
| `/quality-*` frontend routes | `/quality-command-center`, `/quality-intelligence`, `/quality-dashboard` | Apollo takes bare `/quality` — confirmed free, positioned as the unifying front door |
| CAPA | `capa_service.py` + `capa_lifecycle_service.py` (canonical store + lifecycle) | Apollo extends `capa_suggestion_service.py`'s detectors; adds no 6th CAPA store |
| Root cause | `RootCauseAssignment` + `RCADraft`/`rca_engine_service` | Apollo adds a structuring layer only (Five Whys/Fishbone/Pareto/Trend) |
| Audits | `accreditation_engine.py` + `regulatory_standards_catalogue.py` | Apollo extends both with AAMI ST91/AORN/DNV/Internal/Vendor |
| Standards | `beacon_standards_service.py` + `p24_standards_service.py` | Apollo composes both plus the regulatory catalogue |
| Competencies | `competency_service.py`'s `CompetencyEvent` log | Apollo adds 4 new event types to the same log |
| Continuous Improvement | `ContinuousImprovementInitiative` (v1.5) | Apollo adds methodology/cost-savings/executive-visibility columns |
| Executive Quality Dashboard | `quality_command_center_service.py` + `vanguard_governance_service.py` | Apollo composes both, adding only the new Quality Maturity Index |

## The Quality Management Center

Frontend route `/quality` — 9 tabs, one unifying front door:

1. **Quality Dashboard** — the Executive Quality Dashboard composite (see `quality-digital-twin.md` and `capa-engine.md`)
2. **CAPA** — the CAPA Engine (`capa-engine.md`)
3. **Audit Center** — Joint Commission/AAMI ST79/AAMI ST91/AORN/CMS/DNV/Internal/Vendor (`audit-center.md`)
4. **Competencies** — Technician/Supervisor/Manager competency tracking (`competency-engine.md`)
5. **Policies** — versioned quality policies (`policy-intelligence.md`)
6. **Standards** — the Standards Knowledge Library (composed in `apollo_standards_library_service.py`)
7. **Education** — per-technician education completion (part of the Competency Center)
8. **Evidence** — Root Cause Intelligence's Pareto/Trend views (`apollo_rca_intelligence_service.py`)
9. **Improvement Projects** — the Continuous Improvement Portfolio (part of `policy-intelligence.md`'s sibling service, `apollo_improvement_portfolio_service.py`)

## New tables (genuinely new)

Only three tables are genuinely new in `app/models/apollo_quality.py`:

* `CustomerComplaint` — no complaint-intake model existed before Apollo.
* `QualityPolicy` — no clinical/quality policy versioning system existed before Apollo. Follows the same `supersedes_id`/`status` self-FK chain established by Beacon's `StandardsPublication` and Forge's `WorkflowDefinition`.
* `QualityTwinSnapshot` — no department-level quality composite existed. Distinct from `digital_twin_engine.py`'s facility/instrument-scoped workflow telemetry twin.

Every other Apollo capability is an additive extension of a pre-existing
file, or a pure composition service that reads real data from systems that
already existed — nothing is a fabricated capability, and every advisory
output carries `human_review_required: true` with the standard disclaimer.

## Definition of Done

LumenAI becomes a unified Clinical Quality Management System spanning CAPA,
Root Cause Intelligence, Audits, Competencies, Policies, Standards,
Continuous Improvement, and a department-level Quality Digital Twin, all
surfaced through one Executive Quality Dashboard. Human oversight remains
mandatory for all quality decisions — no CAPA closes, no root cause
finalizes, no audit finding resolves, and no policy publishes without an
explicit human action.
