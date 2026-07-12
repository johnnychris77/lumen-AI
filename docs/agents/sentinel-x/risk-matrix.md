# Project Sentinel-X — SPD Risk Matrix & Dynamic Risk Scoring

LumenAI AI Specialist, Sections 3 & 4.

## SPD Risk Matrix (Section 3)

`app/models/sentinelx_risk.py`'s `SPD_RISK_MATRIX` maps real finding_type
strings (this codebase's actual CV/taxonomy vocabulary) onto three
configurable weight tiers:

| Tier | Finding types |
|---|---|
| Highest | blood, bone, tissue, organic residue, debris, corrosion, rust, crack, insulation damage/breach, missing component, damaged O-ring, obstruction |
| Medium | wear, worn cutting edge, pitting, loose joint, damaged hinge, damaged ratchet |
| Low | discoloration, staining, surface degradation |

An unrecognized finding_type defaults to `medium` (never silently `low`) —
`spd_risk_weight`/`spd_risk_weight_value` in `app/models/sentinelx_risk.py`.

## Dynamic Risk Scoring (Section 4)

`sentinelx_risk_scoring_service.compute_risk_score` produces a 0-100 score
where **higher = more risk** — deliberately the inverse convention of
Vulcan's reliability score and Veritas's readiness score (both "higher is
better"), so a caller can never mistake one score type for another.

| Factor | Points |
|---|---|
| Finding severity × SPD weight | 0-54 |
| Anatomy-zone high-risk | 0 or 10 |
| Recurrence | 0-25 |
| Digital Twin condition trend | -5 to +20 |
| Evidence readiness gap (Veritas) | 0-15, or 10 if no evidence assessment exists |
| Repair recurrence (Vulcan) | 0 or 15 |
| Supervisor concern | 0 or 10 |
| Process variation (Aegis) | 0 or 8 |
| Knowledge confidence (low/unknown) | 0-10 |

## Categories

| Range | Level |
|---|---|
| 80-100 | Critical |
| 60-79 | High |
| 40-59 | Moderate |
| 20-39 | Low |
| 0-19 | Very Low |

`risk_level(score)` in `app/models/sentinelx_risk.py` is the single source
of truth for this banding. Every score's `score_breakdown` is persisted
verbatim so the contribution of each factor is always explainable.
