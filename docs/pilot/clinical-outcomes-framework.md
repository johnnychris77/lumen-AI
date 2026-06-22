# LumenAI Clinical Outcomes Framework

> **Disclaimer:** LumenAI reports sterile processing **quality indicators** only. This system does not provide clinical diagnoses, patient outcome data, or infection surveillance data. All outputs require qualified human review before any care pathway decisions. LumenAI does not claim FDA clearance for diagnostic use.

## Purpose

The clinical outcomes framework provides structured quality indicators to help sterile processing departments (SPDs) identify potential instrument quality concerns, track contamination trends, and evaluate process improvements over time.

## What This Framework Measures

| Indicator | Description |
|---|---|
| Contamination events | Inspections where `stain_detected = true` |
| Contamination rate | Contamination events / total inspections × 100 |
| High-risk instruments | Inspections with `risk_score ≥ 70` |
| Critical structural issues | Detected issues: `crack` or `insulation_damage` |
| Severity distribution | Count of inspections by risk score tier |
| Period trend | Comparison of contamination events to prior equivalent period |

## Severity Tiers

| Tier | Risk Score Range | Action Guidance |
|---|---|---|
| Critical | ≥ 85 | Immediate quality review — do not use pending investigation |
| High | 70–84 | Priority quality review within 24 hours |
| Medium | 40–69 | Standard review queue |
| Low | < 40 | Routine monitoring |

## Benchmark Reference

- **AAMI ST79 / IAHCSMM:** Contamination rate benchmark (indicative): **< 2%** of processed instruments
- This benchmark is indicative only and must be contextualised by instrument type, specialty, and site workflow
- Status values: `below_benchmark` or `review_recommended`

## Trend Analysis

The framework compares contamination events in the current period against the prior equivalent period:

| Trend Value | Meaning |
|---|---|
| `improving` | Fewer events than prior period |
| `stable` | Same count as prior period |
| `monitoring_required` | More events than prior period |

**Important:** Trend direction is a quality signal, not a causal determination. "Monitoring required" does not indicate patient harm. Association does not imply causation.

## API Endpoint

```
GET /api/pilot-analytics/clinical-outcomes?days=90
```

## Language Constraints

All clinical outputs must use:
- "potential association" — not "causes"
- "possible contributing factor" — not "linked to"
- "quality review recommended" — not "intervention required"
- "investigation candidate" — not "confirmed issue"
- "near-miss signal" — not "near-miss event" (no patient outcome implied)

`human_review_required: true` is hardcoded on all responses.
