# Pilot Validation Report

> This template mirrors the payload returned by
> `GET /api/pilot-validation/report`
> (`generate_validation_report()` in `app/services/pilot_validation_service.py`).
> Populate each section from that live report — do not hand-author numbers.

## 1. Study Scope

- **Total cases reviewed:** _(from `study_scope.total_cases_reviewed`)_
- **Instrument families reviewed:** _(from `study_scope.instrument_families_reviewed`)_
- **Zones covered:** _(from `study_scope.zones_covered`)_
- **Target cohort size:** 100 lumen images (`study_scope.target_cases`)

## 2. Dataset & Model Version

- **Dataset version:** _(`dataset_version`)_
- **Model version:** _(`model_version`)_

## 3. Results

### 3.1 Clinical Performance Metrics
_(from `results.clinical_performance_metrics`)_

| Metric | Value |
|---|---|
| Accuracy | |
| Precision | |
| Recall | |
| F1 | |
| False positive rate | |
| False negative rate | |
| Supervisor agreement rate | |
| Override rate | |

### 3.2 Critical Safety Metrics
_(from `results.critical_safety_metrics.by_finding_type`)_

| Finding type | FN rate | FN count | TP count | Meets safety threshold |
|---|---|---|---|---|
| Blood | | | | |
| Tissue | | | | |
| Organic residue | | | | |
| Crack | | | | |
| Missing component | | | | |

### 3.3 Zone Performance
_(from `results.zone_performance`)_

| Zone | Cases | Missed | Miss rate | Accuracy | Mean confidence | Overrides |
|---|---|---|---|---|---|---|

## 4. Safety Findings
_(from `safety_findings`)_

- False negatives: **\_\_**
- High-confidence AI/supervisor disagreement: **\_\_**
- Low-confidence critical findings: **\_\_**
- Missing baseline cases: **\_\_**
- Missing required zones: **\_\_**
- Critical missed findings: **\_\_** (list case IDs, finding type, zone)

## 5. Limitations
_(from `limitations`)_

- Sample size may be below the statistical threshold needed for tight
  confidence intervals.
- Zone assignment is instrument-type-derived, not pixel-level image
  localization.
- Findings are quality indicators requiring human review — not clinical
  diagnoses.
- Association between AI findings and reprocessing outcomes does not imply
  causation.

## 6. Recommendations
_(from `recommendations`)_

## 7. Next Training Priorities
_(from `next_training_priorities`)_

## 8. Go / No-Go
_(from `go_no_go`)_

- **Decision:** GO / NO-GO
- **Reasons:**

See `docs/validation/pilot-go-no-go-criteria.md` for the full gate
definition.

## Disclaimers

- This report does not constitute FDA clearance or regulatory approval of
  any kind.
- All findings require sterile processing quality review before action.
- LumenAI never claims causation — findings are potential associations
  only.
