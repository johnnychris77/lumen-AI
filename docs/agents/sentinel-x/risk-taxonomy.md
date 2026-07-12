# Project Sentinel-X — Risk Taxonomy

LumenAI AI Specialist, Section 2.

## Nine categories, multi-label

A finding may belong to multiple categories at once —
`sentinelx_risk_taxonomy_service.classify_categories` returns a list, never
a single enum.

| Category | Assigned when |
|---|---|
| Patient Safety | the finding_type carries the SPD Risk Matrix's `highest` weight |
| Clinical Quality | any real finding_type is present |
| Inspection Quality | evidence readiness score < 75 |
| Instrument Integrity | a condition/mechanical finding_type, or a declining Digital Twin trend |
| Workflow | Aegis process variation detected |
| Operational | recurrence_count > 0 or repair recurrence |
| Education | Knowledge Graph clinical recommendation confidence < 0.5 |
| Compliance | evidence readiness score < 75 (paired with Inspection Quality) |
| Enterprise | recurrence_count >= 3 (an enterprise-notable pattern) |

Every category is assigned only when a real, already-computed signal from
another specialist or the Knowledge Graph supports it — never a guess.
