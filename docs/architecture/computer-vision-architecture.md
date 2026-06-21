# Computer Vision Architecture — Milestone P4

## Overview

LumenAI's Computer Vision (CV) subsystem provides automated inspection of surgical instruments via image analysis. It is designed as a provider-agnostic pipeline: the same API contract is fulfilled by a deterministic mock provider in development/CI and can be swapped to real ML backends in production via a single environment variable.

---

## Provider Abstraction Layer

### BaseCVProvider (ABC)

`app/cv/base.py` defines four abstract methods that every provider must implement:

| Method | Input | Output |
|---|---|---|
| `analyze(req)` | `CVAnalysisRequest` | `CVInferenceResult` |
| `identify_instrument(image_url)` | `str` | `InstrumentIdentity` |
| `read_identifiers(image_url)` | `str` | `IdentifierReads` |
| `compare_baseline(image_url, baseline_url)` | `str, str` | `BaselineComparisonResult` |

### Provider Registry

`app/cv/registry.py` — `CVRegistry` singleton:

- Providers are registered by name string: `CVRegistry.register("mock", MockCVProvider)`
- Active provider selected at runtime via `CV_PROVIDER` environment variable (default: `mock`)
- `CVRegistry.get_provider()` returns a cached instance; `CVRegistry.reset()` clears it (used in tests)

### Supported Provider IDs

| `CV_PROVIDER` value | Description |
|---|---|
| `mock` | Deterministic PRNG-based provider — stable for CI and demos |
| `onnx` | Local ONNX Runtime model (CPU/GPU) |
| `openai` | OpenAI Vision API (GPT-4o) |
| `roboflow` | Roboflow Inference Server |
| `custom` | Any `BaseCVProvider` subclass registered externally |

---

## Mock Provider Design

`app/cv/mock_provider.py`

### Determinism

All outputs are seeded from a hash of the input `image_url`:

```python
seed = int(hashlib.md5(url.encode()).hexdigest()[:8], 16)
rng  = random.Random(seed)
```

Same URL → same inference result on every call, across processes and restarts. This makes the mock safe for snapshot tests and demo environments without requiring GPU or network access.

### Known Instrument Registry

A hardcoded `_KNOWN_INSTRUMENTS` dict maps URL substrings to instrument profiles:

- `frazier-suction-8fr` → Frazier Suction Tube 8Fr (lumened, confidence 0.945)
- `kerrison-rongeur-3mm` → Kerrison Rongeur 3mm (non-lumened, confidence 0.912)

Unrecognized URLs fall through to a low-confidence generic response.

### Finding Catalogue

10 finding types with per-type deduction weights and probability distributions:

| Category | Severity | Contamination Weight | Damage Weight |
|---|---|---|---|
| blood / retained blood residue | high/critical | 25 | 0 |
| bone debris | medium/high | 15 | 0 |
| soft tissue residue | medium | 12 | 0 |
| bioburden / organic residue | low/medium | 10 | 0 |
| corrosion / pitting | medium/high | 5 | 20 |
| crack / hairline fracture | critical | 0 | 35 |
| insulation defect | critical | 0 | 40 |
| mechanical damage | medium/high | 0 | 25 |
| staining / discolouration | low | 8 | 0 |
| foreign body | high | 18 | 10 |

**Lumened instrument risk amplification:** `_detect_findings()` applies a 1.4× risk factor when `instrument_category` contains "lumened" or "scope", increasing the probability of findings being included.

### Score Aggregation

`_aggregate_scores(regions) → (contamination_score, damage_score, overall_cleanliness_score)`

```
contamination_score  = max(0, 100 − sum(contamination_deductions))
damage_score         = max(0, 100 − sum(damage_deductions))
overall              = contamination_score × 0.60 + damage_score × 0.40
```

Scores are bounded to [0, 100].

---

## Inference Schema

`app/schemas/cv.py`

### CVAnalysisRequest

| Field | Type | Default | Description |
|---|---|---|---|
| `image_url` | str | `""` | Primary inspection image URL |
| `image_data_b64` | str | `""` | Alternate base64-encoded image |
| `context` | Literal | `"inspection"` | inspection / baseline_comparison / barcode_scan / training |
| `instrument_name` | str | `""` | Hint for recognition |
| `instrument_category` | str | `""` | lumened / non-lumened / scope / etc. |
| `baseline_image_url` | str | `""` | Reference image for comparison |
| `tenant_id` | str | `"default-tenant"` | Multi-tenant isolation |
| `requested_capabilities` | list[str] | all 12 | Subset of capabilities to run |

### CVInferenceResult

Key fields:

| Field | Type | Description |
|---|---|---|
| `inference_id` | str | `inf-{hex12}` unique per call |
| `status` | Literal | success / partial / failed |
| `instrument_identity` | InstrumentIdentity | Recognition result |
| `identifier_reads` | IdentifierReads | Barcode / QR / KeyDot values |
| `regions` | list[RegionOfInterest] | Annotated finding regions |
| `contamination_score` | float [0–100] | Higher = cleaner |
| `damage_score` | float [0–100] | Higher = less damaged |
| `overall_cleanliness_score` | float [0–100] | Weighted composite |
| `baseline_comparison` | BaselineComparisonResult? | Only if baseline URL supplied |
| `ranking_inputs` | dict | P3-compatible input dict |

### BoundingBox

Normalized coordinates — all values in [0.0, 1.0] (validated by Pydantic `Field(ge=0.0, le=1.0)`):

```
(x, y) = top-left corner
width, height = fractional dimensions
```

---

## Pipeline Stages

`app/cv/pipeline.py`

```
CVAnalysisRequest
       │
       ▼
CVRegistry.get_provider()
       │
       ▼
provider.analyze(req)          ← all 12 capabilities orchestrated internally
       │
       ├─► instrument_identity    (recognize by URL/hint/barcode)
       ├─► identifier_reads       (barcode / QR / KeyDot)
       ├─► regions                (finding detection + BBoxes)
       ├─► scores                 (contamination / damage / overall)
       ├─► baseline_comparison    (if baseline_image_url set)
       └─► ranking_inputs         (P3-compatible dict)
       │
       ▼
_persist(result, db)           ← optional; writes CVInferenceRecord
       │
       ▼
CVInferenceResult
```

---

## API Endpoints

Base path: `/api/enterprise/cv/`

All endpoints require `Authorization: Bearer <token>` and `X-LumenAI-Role: operator` (or higher).

| Method | Path | Description |
|---|---|---|
| `POST` | `/analyze` | Full CV pipeline (single image) |
| `POST` | `/baseline-compare` | Dedicated baseline comparison |
| `POST` | `/analyze-and-rank` | CV + P3 ranking in one round-trip |
| `GET` | `/inference/{inference_id}` | Retrieve persisted result by ID |
| `GET` | `/history` | List recent inferences (optional `?tenant_id=`) |
| `GET` | `/kpi-summary` | Aggregated KPIs from DB |
| `GET` | `/provider/info` | Active provider metadata |

### POST /analyze

Request body: `CVAnalysisRequest`

Response: `CVInferenceResult` (200) or warning-annotated result if `image_url` is missing.

### POST /analyze-and-rank

Runs `run_analysis()` then passes `ranking_inputs` to the P3 ranking engine.

Response shape:
```json
{
  "cv": { /* CVInferenceResult */ },
  "ranking": {
    "inspection_score": 74.5,
    "risk_level": "Moderate",
    "recommended_action": "...",
    ...
  }
}
```

### GET /kpi-summary

Reads from `cv_inference_records` table. Returns:

```json
{
  "total_analyses": 42,
  "recognition_rate_pct": 88.1,
  "blood_detections": 7,
  "baseline_comparisons_run": 15,
  "avg_baseline_match_pct": 91.3
}
```

---

## P3 Integration

`ranking_inputs` is a `dict[str, Any]` populated by `MockCVProvider._build_ranking_inputs()`:

| Key | Source |
|---|---|
| `finding_category` | Most severe region's `finding_category` |
| `severity` | Most severe region's `severity` |
| `confidence_score` | Most severe region's `confidence` |
| `instrument_name` | `instrument_identity.instrument_name` |
| `instrument_category` | `instrument_identity.instrument_category` |
| `barcode_value` | `identifier_reads.barcode_value` |
| `qr_code_value` | `identifier_reads.qr_value` |
| `baseline_status` | Derived from `baseline_comparison.verdict` |
| `overall_cleanliness_score` | `overall_cleanliness_score` |

`baseline_status` mapping:

| Verdict | `baseline_status` |
|---|---|
| `"pass"` | `"baseline_pass"` |
| `"review_required"` | `"baseline_review"` |
| `"fail"` | `"baseline_fail"` |
| no comparison | `""` |

The `build_ranking_request_from_result(result)` helper in `pipeline.py` extracts this dict for direct use in P3 `score_inspection()` calls.

---

## Data Model

`app/models/cv_inference.py` — `CVInferenceRecord`

Table: `cv_inference_records`

Denormalized for fast KPI queries without JSON parsing:

| Column group | Columns |
|---|---|
| Identity | `inference_id`, `tenant_id`, `context`, `provider`, `status` |
| Image refs | `image_url`, `baseline_image_url` |
| Instrument | `instrument_recognized`, `instrument_name`, `instrument_category`, `instrument_confidence`, `match_method` |
| Identifiers | `barcode_value`, `qr_value`, `key_dot_value` |
| Scores | `contamination_score`, `damage_score`, `overall_cleanliness_score` |
| Baseline | `baseline_compared`, `baseline_match_pct`, `baseline_verdict` |
| Finding counts | `finding_count`, `blood_count`, `bone_count`, `tissue_count`, `corrosion_count`, `crack_count`, `insulation_count`, `residue_count` |
| Audit | `result_json` (full CVInferenceResult JSON), `processing_ms`, `created_at` |

---

## Training Data Requirements

### Image Standards

| Attribute | Requirement |
|---|---|
| Resolution | ≥ 1920×1080 (4K preferred for borescope) |
| Format | JPEG, PNG, TIFF |
| Lighting | Controlled, consistent (diffuse ring light recommended) |
| Background | Non-reflective matte black or white |
| Metadata | EXIF stripped before storage (PHI risk) |

### Dataset Composition (per instrument class)

| Split | Min images |
|---|---|
| Train | 500 |
| Validation | 100 |
| Test | 100 |

For each instrument class, the dataset must include:
- Clean instrument (negative examples): 40%
- Single finding type: 40%
- Multiple concurrent findings: 20%

### Finding Annotation Format

Bounding boxes in normalized [0,1] coordinates (matching `BoundingBox` schema). Each annotation includes:
- `label` — finding type string
- `finding_category` — canonical category name
- `severity` — low / medium / high / critical
- `confidence` — annotator confidence score
- `annotator_id` — for inter-annotator agreement tracking

Minimum inter-annotator agreement (Cohen's κ): **0.80** before label is accepted.

### Baseline Image Requirements

- One approved reference image per instrument model per vendor
- Captured at standard angle (0°, 45°, 90°) for SSIM comparison
- Re-photographed after any refurbishment
- Stored in `baseline_image_url` field; referenced during comparison pipeline stage

---

## Deployment Roadmap

### Phase 1 — Mock Provider (current)

- Deterministic mock for CI and demo
- All 12 capabilities simulated
- Full API surface available

### Phase 2 — ONNX Local Inference

- Train YOLOv8-based detection model on annotated instrument dataset
- Export to ONNX (opset 17)
- Register as `onnx` provider: `CV_PROVIDER=onnx`
- Target: ≤ 200ms per image on CPU, ≤ 40ms on GPU

### Phase 3 — Cloud Provider Hybrid

- Route borescope (high-resolution) images to `openai` or `roboflow` provider
- Route standard inspection images to local ONNX
- Provider selected per-request via `requested_capabilities` hint

### Phase 4 — Active Learning Loop

- Low-confidence inferences (< 0.70) flagged for human review
- Reviewed annotations fed back into training pipeline
- Model versioned and promoted via `model_versions` field in `CVInferenceResult`

### Infrastructure Requirements

| Environment | Provider | GPU | Latency target |
|---|---|---|---|
| CI / Dev | mock | none | < 10ms |
| Staging | onnx (CPU) | none | < 500ms |
| Production | onnx (GPU) | 1× T4 or equivalent | < 150ms |
| High-res | openai Vision | n/a | < 3s |

---

## Security Considerations

- All CV endpoints require authenticated requests (Bearer token + role header)
- Image URLs are logged in `cv_inference_records` — ensure no PHI in URLs before storage
- `image_data_b64` payloads are not persisted; only the URL is stored
- Provider API keys (`OPENAI_API_KEY`, `ROBOFLOW_API_KEY`) must be injected via environment secrets, never hardcoded
- ONNX model files must be checksum-verified on load to prevent model poisoning

See `docs/architecture/cv-data-governance.md` for full data handling policy.
