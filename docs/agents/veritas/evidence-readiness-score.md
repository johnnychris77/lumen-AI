# Project Veritas — Evidence Readiness Score

LumenAI AI Specialist, Section 8.

## 0–100 composite, with a transparent breakdown

`veritas_readiness_score_service.compute_evidence_readiness_score` starts at
100 and applies itemized penalties, returned verbatim in
`VeritasEvidenceReadinessAssessment.score_breakdown_json`:

| Factor | Penalty |
|---|---|
| Baseline match quality (exact/compatible/partial/uncertain/mismatch/unavailable) | 0-40 |
| Baseline governance status (approved/conditionally approved/other) | 0-25 |
| Image quality (excellent/acceptable/limited/insufficient) | 0-30 |
| Anatomy-zone coverage (complete/acceptable/incomplete/insufficient/not assessed) | 0-30 |
| Instrument identity confidence (high/moderate/low) | 0-15 |
| Evidence provenance completeness | 0 or -10 |
| Supervisor validation status | 0 or -5 |
| Model compatibility | 0 or -20 |
| Conflicting evidence present | 0 or -15 |

Score is clamped to [0, 100].

## This evaluates evidence quality, not instrument cleanliness

The brief is explicit that this score answers a different question than
Vulcan's Instrument Reliability Score — the two are never conflated or
combined into a single number.

## Categories

| Range | Category |
|---|---|
| 90-100 | Strong Evidence |
| 75-89 | Moderate Evidence |
| 50-74 | Limited Evidence |
| 0-49 | Insufficient Evidence |

`readiness_category(score)` (in `app/models/veritas_evidence.py`) is the
single source of truth for this banding.
