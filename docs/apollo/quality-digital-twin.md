# Project Apollo — Quality Digital Twin & Executive Quality Dashboard

LumenAI OS v4.7, Sections 9 & 10.

## Quality Digital Twin (Section 9)

`QualityTwinSnapshot` (table `apollo_quality_twin_snapshots`) is a
genuinely new, department-scoped composite — no department-level quality
twin existed before Apollo. It is explicitly distinct in kind from
`digital_twin_engine.py`'s facility/instrument-scoped workflow telemetry
twin: this tracks governance health, not instrument flow.

Eight equally weighted dimensions compose the `overall_score`:

| Dimension | Source | Department-scoped? |
|---|---|---|
| `compliance_score` | `accreditation_engine.compute_accreditation_readiness` | No — tenant-wide (accreditation has no department dimension) |
| `audit_readiness_score` | same as compliance_score | No — tenant-wide |
| `competency_score` | `competency_service.competency_summary` averaged across technicians who logged inspections in this department | Yes |
| `education_score` | pct of department technicians with ≥1 completed education article | Yes |
| `knowledge_score` | knowledge-contribution events per department technician | Yes |
| `policy_maturity_score` | published-vs-total ratio across all `QualityPolicy` rows | No — policies aren't department-tagged |
| `capa_health_score` | `capa_lifecycle_service.lifecycle_summary` closure rate | No — CAPAs aren't department-tagged |
| `continuous_improvement_score` | Improvement Portfolio completion rate | No — initiatives aren't department-tagged |

Where a dimension isn't natively department-scoped, the tenant-wide value
is used as an honest proxy and `factors_json` explicitly records which
sub-scores are department-scoped vs. tenant-wide — never a fabricated
department split with no underlying data.

```
GET  /api/apollo/quality-twin/{department}
GET  /api/apollo/quality-twin/{department}/history
```

Use `department=unspecified` for inspections with no `department` set
(consistent with how other services handle optional groupings).

## Executive Quality Dashboard (Section 10)

Composes two pre-existing systems rather than re-deriving their numbers a
third time:

* `quality_command_center_service.quality_command_center_summary` (v2.9) —
  recurring findings, CAPA lifecycle, root causes, first-pass yield,
  education impact, technician/vendor/manufacturer trends.
* `vanguard_governance_service.governance_dashboard` (v4.6) — policy
  compliance, knowledge adoption, workflow compliance, audit readiness,
  training completion.

The only genuinely new computation is the **Quality Maturity Index** — a
documented weighted composite:

| Component | Weight | Source |
|---|---|---|
| Compliance / audit readiness | 0.30 | `governance.audit_readiness.overall_readiness_score` |
| CAPA health | 0.20 | CAPA lifecycle closure rate |
| Competency | 0.20 | `quality_command_center_summary.education_impact_avg_pct` |
| Continuous improvement | 0.15 | Improvement Portfolio completion rate |
| Policy currency | 0.15 | 100 minus 10 points per overdue policy review (an honest proxy — no independent "policy currency" metric exists) |

```
GET  /api/apollo/executive-dashboard
```

Returns `compliance_score`, `audit_readiness`, `open_capas`,
`capa_closure_rate_pct`, `competency_status`, `high_risk_policies`
(overdue reviews), `upcoming_reviews` (due within 30 days),
`continuous_improvement`, `quality_maturity_index`, and
`quality_maturity_index_weights` for full transparency into the composite.
Every field carries `human_review_required: true` — nothing here
authorizes an operational decision on its own.
