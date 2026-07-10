# Project Genesis — Shared Intelligence Layer

LumenAI OS v4.0 — Section 2

## A facade, not a relocation

"Move shared intelligence into reusable services" does not mean deleting
and re-homing the engines below into a new package — every one of them
already lives at a stable, importable path and was already usable from
any route file in this codebase. Actually relocating nine mature engines
(the largest, `knowledge_graph_service.py`, has 15+ public functions and
call sites across five prior sprints) would be a large, high-risk rewrite
with no functional benefit, since Python modules are already globally
importable — "available to every LumenAI application" was already true
before this sprint.

What Genesis adds is `app/services/platform_intelligence_gateway.py` — a
single, documented place any module can query to discover which engine
backs which capability, without needing to already know that engine's
home file.

## The nine named shared services, mapped to their real home

| Sprint's name | `get_shared_service(name)` key | Actual module |
|---|---|---|
| Digital Twin Engine | `digital_twin_engine` | `app.services.digital_twin_engine` |
| Knowledge Graph | `knowledge_graph` | `app.services.knowledge_graph_service` (Phase 21) |
| Clinical Reasoning | `clinical_reasoning` | `app.services.knowledge_graph_service` — `reasoning_chain`/`explain_inspection` live in the same Phase 21 engine, there is no separate file |
| Anatomy Engine | `anatomy_engine` | `app.services.anatomy_risk_service` |
| SPD Risk Engine | `spd_risk_engine` | `app.services.knowledge_graph_service` — SPD risk scoring is embedded in the same engine (`SPDRisk` label); no dedicated file exists |
| Computer Vision Gateway | — (see below) | `app.cv.pipeline` / `app.cv.registry` (`onnx_provider`/`mock_provider`) |
| Recommendation Engine | see `RECOMMENDATION_ENGINES` | six separate engines, one per sprint — deliberately not consolidated (see below) |
| Forecast Engine | `forecast_engine` | `app.services.insight_forecast_math` |
| Sentinel Engine | `sentinel_engine` | `app.services.sentinel_engine_service` |

## Recommendation engines are registered, not merged

Six recommendation-producing engines already existed before this sprint
— Sentinel's, Insight's, Horizon's AI-improvement recommender, Atlas's
alert engine, CAPA's, and Beacon's repair intelligence engine — each
encoding sprint-specific domain logic that doesn't generalize into one
shared implementation. `RECOMMENDATION_ENGINES` in the gateway registers
all six under one discoverable dict (`get_recommendation_engine(name)`)
so a new module can enumerate what recommendation sources exist, without
merging their logic.

## Computer Vision Gateway

The CV inference pipeline (`app/cv/pipeline.py`, provider abstraction in
`app/cv/registry.py` with `onnx_provider`/`mock_provider` implementations,
persisted via `app/models/cv_inference.py::CVInferenceRecord`, exposed at
`app/routes/cv.py`) already functions as this codebase's computer vision
gateway. It is referenced from `list_shared_services()`'s output as a
documentation pointer rather than a `SHARED_SERVICES` dict entry, since
its own `app/cv/registry.py` is already the correct discovery mechanism
for CV providers specifically.

## Endpoint

```
GET /api/platform/intelligence/services
```

Returns the shared-service and recommendation-engine registry (module
path + first line of each module's docstring) plus the CV gateway
pointer — a discovery endpoint, not a data endpoint. Callers still invoke
the actual engine (e.g. `digital_twin_engine.log_instrument_flow(...)`)
directly; this endpoint only tells a caller *which* engine to import for
a named capability.
