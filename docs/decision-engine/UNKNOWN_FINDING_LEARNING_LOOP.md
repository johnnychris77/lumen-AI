# Unknown-Finding Learning Loop

Implemented in `app/services/unknown_finding_service.py` and
`app/models/lumen_decision_engine.py::UnknownFindingReview`.

## When it triggers

The Lumen Decision Engine detects a present signal (probability ≥ 0.5)
for a KPI that is not in the deployed model's `supported_categories`
(currently `debris`, `corrosion`; `blood` only once ≥3 validated training
samples exist per `KNOWN_LIMITATIONS.md`). Rather than guess a category,
it reports `probable_unknown_foreign_material` with `confidence: null`
(never a fabricated probability) and opens an `UnknownFindingReview`.

## Captured fields

Original image reference (via the inspection), instrument family, anatomy
zone, model output (type + raw probability), model confidence, baseline
similarity, evidence limitations, model version — plus, once worked,
supervisor classification, supervisor comments, second-review status,
adjudicated label, dataset eligibility, usage rights.

## Workflow

```
unknown finding -> supervisor classification -> clinical/data review
-> second expert validation -> candidate dataset -> sufficient examples
accumulated -> retraining -> independent validation -> governed model
promotion
```

`unknown_finding_service.classify_finding()` is role-gated to
`admin`/`spd_manager` and only ever writes to the review record — it
**never** modifies production code, the observation taxonomy, or model
behavior. `record_second_review()` records the adjudicated label and
dataset eligibility for a future training cycle. Retraining and promotion
reuse the existing, previously-built `candidate_promotion.py` ladder from
prior phases rather than duplicating it.

## Routes

`GET /api/unknown-findings`, `POST /api/unknown-findings/{id}/classify`,
`POST /api/unknown-findings/{id}/second-review` — all `admin`/`spd_manager`
only.
