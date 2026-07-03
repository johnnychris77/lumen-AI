# LumenAI Clinical Intelligence Architecture v1.0

**Status:** Frozen reference architecture (Phase 19.5). Every future feature,
model, API, dashboard, dataset, and report must be traceable to a layer in
this document and to the ontology in
`docs/architecture/lumenai-clinical-ontology.md`.

## 1. Mission Statement

> LumenAI is an AI-powered Pre-Sterilization Clinical Inspection Platform
> that prevents contaminated, damaged, or clinically unsafe surgical
> instruments from progressing to packaging and sterilization — by
> combining instrument intelligence, anatomy-aware computer vision,
> clinical reasoning, and human expertise.

### What LumenAI is not

- LumenAI is **not** a sterilization monitoring system.
- LumenAI is **not** a biological indicator system.
- LumenAI is **not** a sterilizer quality system.
- LumenAI **is** the intelligent clinical inspection gate that sits
  *before* packaging and sterilization — see
  `docs/architecture/pre-sterilization-boundary.md` for the exact workflow
  boundary and the terminology this implies.

LumenAI does not measure, monitor, or attest to whether a sterilization
cycle achieved sterility. It determines whether an instrument is clean,
intact, and correctly identified enough to *proceed toward* that cycle.

## 2. Architecture v1.0 — The Ten Layers

Each layer below names the real modules that implement it today (v1) so
this document stays a description of the system, not an aspiration.

### Layer 1 — Image Acquisition
Capture inspection images and metadata (instrument, site, facility,
department, tray, barcode/UDI, capture device).
*Implemented by:* `app/routes/inspections.py`, `app/models/inspection.py`,
`app/models/capture_device.py`, `app/services/ml/model_tasks.py` (identifier
decode).

### Layer 2 — Computer Vision
Detect visual characteristics from the captured image.
*Implemented by:* `app/models/cv_inference.py`, `app/services/ml/` (feature
store, evaluation). Honesty constraint: CV-derived features that are not
yet computed are stored as `null`, never fabricated.

### Layer 3 — Instrument Intelligence
Identify manufacturer, instrument family, model, and type.
*Implemented by:* `app/services/instrument_anatomy.py` (`resolve_family`),
`app/models/instrument_registry.py`, `app/models/manufacturer_reg.py`,
`app/models/baseline_library.py`.

### Layer 4 — Anatomy Intelligence
Understand anatomy zones, high-risk retention areas, required views, and
inspection coverage for the resolved instrument family.
*Implemented by:* `app/services/instrument_anatomy.py` (`anatomy_profile`,
`get_anatomy`), `app/services/instrument_zones.py` (zone taxonomy,
`HIGH_RETENTION_ZONES`), `app/services/inspection_coverage.py`.

### Layer 5 — Clinical Finding Intelligence
Detect blood, bone, tissue, organic residue, debris, rust, corrosion,
crack, wear, discoloration, pitting, missing component, and insulation
damage.
*Implemented by:* `app/services/baseline_comparison_scoring_service.py`
(`predicted_findings`), `app/services/clinical_mentor.py` (per-finding
`why_it_matters` / `clinical_significance` library).

### Layer 6 — Clinical Reasoning Engine
Interpret findings using anatomy, zone risk, manufacturer baseline,
supervisor knowledge, and SPD rules.
*Implemented by:* `app/services/baseline_comparison_scoring_service.py`
(`evidence_strength`, `baseline_difference`, `ai_clinical_review`),
`app/services/clinical_mentor.py` (`ai_mentor`).

### Layer 7 — Clinical Decision Engine
Recommend a disposition:

- READY FOR PACKAGING
- READY FOR STERILIZATION
- REQUIRES RECLEANING
- SUPERVISOR REVIEW
- REPAIR
- REMOVE FROM SERVICE

**Current implementation status:** the v1 scoring engine
(`app/services/baseline_comparison_scoring_service.py`, `_ACTION_TEXT`)
outputs a five-value outcome — `PASS`, `MONITOR`, `SUPERVISOR REVIEW`,
`REPROCESS`, `REMOVE FROM SERVICE` — which is the working v1 realization of
this layer, predating this document. It maps onto the target vocabulary
above as: `PASS`/`MONITOR` → *READY FOR PACKAGING* (with `MONITOR` flagging
a recheck note), `REPROCESS` → *REQUIRES RECLEANING*, `SUPERVISOR REVIEW`
→ *SUPERVISOR REVIEW*, `REMOVE FROM SERVICE` → *REMOVE FROM SERVICE*.
*REPAIR* and an explicit *READY FOR STERILIZATION* terminal state (distinct
from packaging) are not yet separated out in code. Per Phase 19.5 §10,
existing code is not being renamed to avoid breaking the ~2,300-test
regression suite that asserts on the current strings; new decision-engine
work should adopt the six-value vocabulary directly rather than extending
the five-value one.

### Layer 8 — Human Validation
Supervisor review and override — the point at which a human either
confirms or overrides the AI's recommendation, and in doing so creates
ground truth.
*Implemented by:* `app/models/supervisor_review.py`,
`app/routes/ai_clinical_review.py` (`/inspections/{id}/supervisor-review`).

### Layer 9 — Continuous Learning
Use validated supervisor feedback to improve models.
*Implemented by:* `app/models/pilot_validation.py` (ground-truth cases
derived from supervisor review, Phase 18), `app/models/model_registry.py`
+ `app/models/shadow_prediction.py` (Phase 17 model lifecycle: shadow →
pilot → validated, human-gated promotion only), `app/models/retained_image.py`
(opt-in labeled training image store).

### Layer 10 — Enterprise Intelligence
Dashboards, analytics, knowledge graph, predictive maintenance,
benchmarking, and executive intelligence.
*Implemented by:* `app/routes/pilot_analytics.py`, `app/routes/pilot_validation.py`,
`app/models/quality_intelligence.py`, `app/models/digital_quality_twin.py`,
`app/models/global_intelligence.py`, `app/models/instrument_knowledge.py`,
`app/models/network_benchmark.py`, executive scorecard/briefing routes.

## 3. How the Layers Compose

Layers 1–5 answer *"what is this instrument and what do we see on it?"*
Layer 6 answers *"what does that mean clinically, given where it is on
this instrument?"* Layer 7 turns that meaning into an operational
disposition. Layer 8 is the non-negotiable human checkpoint. Layers 9–10
turn every reviewed case into either a better model or better enterprise
visibility — never both silently; every promotion and every aggregate
claim is auditable back to real rows (see
`docs/architecture/lumenai-clinical-ontology.md`).

No layer may be skipped by a future feature. A feature that detects a
finding (Layer 5) without going through anatomy/zone context (Layer 4)
first is an architecture violation — see
`docs/architecture/architecture-enforcement-checklist.md`.
