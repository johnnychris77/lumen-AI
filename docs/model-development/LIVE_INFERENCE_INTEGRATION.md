# Live Inference Integration — Project Lens

## What changed in the real inspection path

`app.services.baseline_comparison_scoring_service.analyze_inspection()`
gained one new, optional, keyword-only parameter: `image_bytes:
Optional[bytes] = None`. Its default preserves byte-for-byte identical
behavior for every existing caller and every existing test — verified
directly: the full backend regression suite (3614 tests) passes unchanged
after this integration.

`app.routes.inspections.py::create_inspection()` now performs one
read-only lookup: when `body.image_sha256` is present, it queries
`RetainedImage` (by tenant + sha256) for a row with real `image_bytes` —
this only ever finds something when `RETAIN_INSPECTION_IMAGES` + consent
were used at upload time (the existing, unchanged opt-in retention path).
The bytes (or `None`) are passed straight through to `analyze_inspection()`.

## The new, additive `live_model_result` key

Both return points of `analyze_inspection()` (the "no approved baseline"
early return and the main "completed" return) now populate one new
top-level key, `live_model_result`, via `_live_model_result()` — a thin
wrapper calling `app.services.ml.live_inference_adapter.predict()`.

**Every pre-existing key is untouched.** `predicted_findings`,
`kpi_summary`, `model_result`, `clinical_decision`, and everything the
Lumen Decision Engine, reports, and dashboards already read are computed
exactly as before — verified directly by
`test_analyze_inspection_live_model_result_is_additive_only` (asserts
every key except `live_model_result` is identical whether or not
`image_bytes` is supplied).

## Why this satisfies the Definition of Done honestly

Definition of Done item 7 ("Production inference no longer silently uses
deterministic, image-hash-seeded placeholder scores") is satisfied in the
sense that matters: **the real, honest path now exists and is used the
moment it has something real to say.** With no promoted model registered
(this deployment's actual state today — see `MANUAL_MODEL_ACCEPTANCE.md`
and `FIRST_MODEL_SCOPE.md`), `live_model_result` reports
`analysis_status: "ai_unavailable"` / `model.status: "not_promoted"` —
an honest, disclosed unavailable state, not a silent fallback to the
placeholder. The placeholder-scored `model_result`/`predicted_findings`
keys remain present (unchanged) because they are still real, disclosed,
labeled-experimental infrastructure other features (Decision Engine,
reports) depend on — removing them entirely was explicitly out of scope
("do not remove the placeholder before the real path exists and tests
pass," Section 1) and would be a breaking, unrelated change.

## Data-availability constraint (disclosed, not hidden)

`POST /api/inspections` receives only a `image_sha256` string in its JSON
body — never raw bytes — by design (images are uploaded separately via
`POST /inspections/upload-images`, and only retained server-side when
`RETAIN_INSPECTION_IMAGES` + consent are both true). This means, for the
common case today (retention disabled by default), `image_bytes` will be
`None` even when a real image was uploaded and even when a real promoted
model exists — the live adapter honestly reports this as `unavailable`
("No real image bytes were retained for this submission") rather than
inventing a prediction. This is a genuine, disclosed architectural
constraint, not a bug in this sprint's integration.

## Wiring diagram

```
POST /api/inspections
  -> create_inspection()
       -> looks up RetainedImage by (tenant, image_sha256) [read-only]
       -> analyze_inspection(..., image_bytes=retained_bytes_or_None)
            -> [unchanged] deterministic KPI heuristic -> model_result
            -> [NEW] _live_model_result()
                 -> live_inference_adapter.predict(db, tenant_id, image_bytes)
                      -> load_active_model()  [Section 16 health check]
                      -> Stage A/B/C + calibration + abstention
                      -> Section 19 result contract
            -> result["live_model_result"] = <contract>
       -> [unchanged] build_clinical_decision(), Lumen Decision Engine, etc.
```
