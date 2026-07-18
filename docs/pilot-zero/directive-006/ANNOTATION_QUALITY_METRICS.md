# LPZ-DIR-006 — Annotation Quality Metrics

**Purpose:** define the metrics used to monitor the health of the annotation and
Ground Truth process. Metrics measure the **process**, not any AI model. This
directive does not compute model performance; every metric here is computed from
real annotation/review records (never fabricated or back-filled).

Guardrails: no metric asserts clinical or regulatory performance. Where data is
insufficient, the metric reports "insufficient data", never a fabricated number.

## Metric definitions

| Metric | Definition | Purpose |
|---|---|---|
| **Inter-reviewer agreement** | Share of reviewed annotations where primary and secondary agreed before adjudication. | Taxonomy/guideline clarity; reviewer calibration. |
| **Annotation completeness** | Share of annotations with all required fields (taxonomy term, region, evidence, confidence, quality). | Data quality gate. |
| **Review turnaround time** | Time from annotation created → secondary review submitted → adjudicated/approved. | Throughput/backlog health. |
| **Ground Truth approval rate** | Share of candidates that reach `ACTIVE` Ground Truth. | Selectivity of approval. |
| **Rejected annotations** | Count/share ending in `Rejected`. | Upstream quality (capture/annotation) signal. |
| **Consensus rate** | Share of disagreements resolved by Consensus/Third Reviewer vs. escalated to Panel. | Escalation load. |
| **Unknown classification frequency** | Share of annotations recorded as `unknown_finding` / `unable_to_determine`. | Taxonomy coverage; learning-loop input (high is not "bad" — it is honest). |
| **Version changes** | Average immutable versions per annotation. | Churn/stability signal. |
| **Audit completeness** | Share of lifecycle transitions with a complete attributable audit event. | **Governance integrity — target 100%.** |

## Interpretation rules

* **Unknown frequency is not a failure metric.** A healthy process records
  uncertainty rather than forcing classification; a *rising* trend may indicate a
  taxonomy gap worth a governed vocabulary update.
* **Agreement is diagnostic, not a target to game.** Very high agreement with low
  independence may indicate reviewers are not truly blind — read alongside
  blind-review compliance.
* **Approval rate near 100%** may indicate rubber-stamping; read with audit
  completeness and separation-of-duties compliance.
* **Audit completeness < 100%** is a governance defect and takes priority over
  any throughput metric.

## Reporting cadence and ownership

* Owned by the **Quality Auditor**; reviewed with the Program Administrator.
* Reported per tenant and per instrument family where volume allows; suppressed
  or marked "insufficient data" below a minimum count to avoid misleading
  figures.
* Trends matter more than single values; report direction over time.

## Thresholds

This directive intentionally does **not** set numeric pass/fail thresholds —
doing so credibly requires baseline data from the operating lab, and premature
thresholds invite gaming. Thresholds are set later, from observed baselines,
under a separate authorized directive. The one exception is **audit
completeness**, whose target is **100%** by definition.

## System mapping

`annotation_analytics_service` (Section 11) already computes agreement,
completeness, status distributions, and Unknown frequency live from
`Annotation` / `AnnotationReview`; the `/annotations/analytics/summary` route
exposes them. Governance additions recorded for a future authorized change:
add turnaround-time and version-churn aggregates, and an explicit
audit-completeness check, to the analytics surface.
