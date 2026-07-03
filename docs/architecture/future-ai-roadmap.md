# Future AI Roadmap

Ten stages, from the deterministic heuristics running today to full
computer-vision localization and network-scale intelligence. Every stage
must be built inside the architecture and ontology frozen in this
directory — a new stage is a new capability at an existing ontology link,
never a parallel system.

| Stage | Capability | Status |
|---|---|---|
| 1 | Heuristic baseline comparison and scoring | **Shipped.** `app/services/baseline_comparison_scoring_service.py` compares an inspection against its manufacturer/site baseline and produces evidence strength + baseline difference. Deterministic, not ML. |
| 2 | Instrument family classification | **Shipped (deterministic); ML not trained.** `app/services/instrument_anatomy.py::resolve_family` classifies by keyword matching today. Phase 17 (`app/services/ml/model_tasks.py`) defines the label space for a future ML classifier; training has not started (no labeled dataset yet). |
| 3 | Anatomy zone classification | **Shipped (deterministic pilot logic); ML not trained.** `app/services/instrument_zones.py::zone_fields` assigns a zone from instrument type + finding type, honestly labeled `assignment_method: "pilot_zone_assignment"` with confidence capped below 1.0 — this is explicitly *not* pixel-level localization. |
| 4 | Finding classification | **Partially shipped.** Findings come from declared/heuristic inputs today (`predicted_findings`); `app/models/cv_inference.py` and the Phase 17 feature store scaffold CV-derived features but store them `null` until a trained model exists. |
| 5 | Severity classification | **Partially shipped.** Rule-based severity/risk-score bucketing exists (`severity_from_risk_score` in `app/services/pilot_validation_service.py` and equivalents elsewhere); no learned severity model yet. |
| 6 | Zone-aware clinical decision support | **Shipped.** `app/services/baseline_comparison_scoring_service.py::ai_clinical_review` and `app/services/clinical_mentor.py::ai_mentor` combine zone risk, baseline comparison, and evidence strength into a recommendation with plain-language reasoning. |
| 7 | Heatmaps and bounding boxes | **Not started — deliberately.** The platform currently asserts the opposite: no fabricated bounding-box or heatmap language is emitted (`docs/clinical` / `test_ai_clinical_review.py::test_no_fabricated_localization`). This stage requires real pixel-level CV output before any visual overlay is shown. |
| 8 | Segmentation overlays | **Not started.** Depends on Stage 7 being real first. |
| 9 | Predictive instrument degradation | **Scaffolded.** `app/models/digital_quality_twin.py` (`QualityForecast`, `ScenarioSimulation`, `InterventionModel`) and `app/models/instrument_knowledge.py` (maintenance intervals, known failure modes) provide the data model; predictions are not yet driven by a trained degradation model. |
| 10 | Enterprise benchmarking and knowledge graph intelligence | **Shipped, ongoing.** `app/models/network_benchmark.py`, `app/models/global_intelligence.py`, `app/models/quality_intelligence.py` provide cross-tenant, anonymized benchmarking and risk-signal aggregation today; expands as more tenants and instrument families onboard. |

## How a stage graduates from scaffold to real

The Phase 17 model lifecycle governs every ML-backed stage (2, 3, 4, 5, 9):

```
Data → Labels → Training → Evaluation → Registry → Shadow Mode → Pilot → Validation → Deployment
```

- **Labels** come from the ontology's Learning Signal link — real
  supervisor decisions via `app/models/pilot_validation.py`
  (`PilotValidationCase`), not synthetic data.
- **Registry** entries (`app/models/model_registry.py`) start
  `experimental` and can only reach `validated` through a human-approved
  promotion that requires a completed checklist (including a minimum
  sample size) — no auto-promotion.
- **Shadow Mode** (`app/models/shadow_prediction.py`) lets a candidate
  model run silently, reconciled against the human's actual decision,
  before it ever drives or advises anything.
- **Pilot / Validation** is Phase 18's ground-truth review and go/no-go
  gate (`docs/validation/pilot-go-no-go-criteria.md`) — a model cannot be
  called "validated" without clearing that gate's critical-finding
  false-negative and supervisor-agreement thresholds.

A stage is not "shipped" in the sense of this roadmap until it has passed
through that full lifecycle with real data — a working heuristic (Stages
1, 2, 3, 6 today) is a legitimate v1 implementation of a layer, but it is
labeled honestly as heuristic/deterministic rather than presented as a
trained model.

## Priority signal from Phase 18

The pilot validation dashboard's `zone_performance_summary` (most-missed
zones, lowest-confidence zones) is the concrete input that should
prioritize which Stage 2–5 model gets trained first: whichever zone or
finding type shows the highest miss rate against real supervisor ground
truth is the next training priority, not a roadmap guess.
