# LCID Unknown-Finding Guide

## Workflow

```
Unknown
  -> Supervisor Classification
  -> Clinical Review
  -> Candidate Dataset
  -> Future Taxonomy Review
```

This reuses, rather than duplicates, the Unknown-Finding Learning Loop
already built for the Lumen Decision Engine
(`docs/decision-engine/UNKNOWN_FINDING_LEARNING_LOOP.md`,
`app.models.lumen_decision_engine.UnknownFindingReview`,
`app.services.unknown_finding_service`):

1. **Unknown** — the Decision Engine observes a signal outside the
   validated taxonomy and opens an `UnknownFindingReview`
   (`status="pending_supervisor"`).
2. **Supervisor Classification** —
   `unknown_finding_service.classify_finding()` (admin/spd_manager only)
   records a classification; this **never** itself changes production
   code, taxonomy, or model behavior.
3. **Clinical Review / second expert validation** —
   `unknown_finding_service.record_second_review()` records an adjudicated
   label and marks `dataset_eligible`.
4. **Candidate Dataset** — `unknown_finding_service.promote_to_candidate_dataset()`
   (new this sprint) registers the review as a `DatasetRegistryEntry` in
   the `UNLABELED` state — a *candidate* for future annotation, not
   auto-approved Ground Truth. Requires the caller to supply the real
   stored image (`retained_image_id`/`image_sha256`); this service never
   fabricates an image reference the review doesn't itself store.
5. **Future Taxonomy Review** — accumulating enough adjudicated candidate
   examples is a governance decision for a future retraining cycle
   (reusing `candidate_promotion.py`'s existing ladder), not something
   this sprint automates.

## Do not automatically expand the taxonomy

No code path in this sprint adds a new value to
`observation_taxonomy.OBSERVATION_TAXONOMY` from review data — taxonomy
expansion remains a manual, reviewed code change.
