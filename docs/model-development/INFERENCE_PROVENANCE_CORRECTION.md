# Inference Provenance Correction — Phase 1 Report

Branch: `feature/real-vision-pilot-readiness`. This documents the trace,
the corrections made so deterministic‑placeholder output is never presented as a
verified AI result, and a component‑by‑component readiness status.

## 1. Where every presented value originates (trace)

| Presented value | Origin today | Real AI? |
|---|---|---|
| `predicted_findings[*].probability/confidence` | `_pseudo(seed, idx)` — SHA‑256 of image hash, not pixels (`baseline_comparison_scoring_service`) | **No** — deterministic placeholder |
| `inspection_score` | baseline_match − weighted KPI deductions, all from `_pseudo` | **No** |
| `baseline_match_score` / "matched at X%" | `1.0 − deviation`, deviation from `_pseudo` + positive‑KPI count — **no pixel comparison** | **No** |
| `confidence` / `confidence_level` | mean of placeholder finding confidences | **No** |
| `clinical_decision`, `recommendation`, `risk_level` | policy over the placeholder findings above | derived from placeholder |
| `live_model_result.observation` | `live_inference_adapter.predict` — real model or honest `ai_unavailable` | **Yes** (or honest unavailable) |
| `ai_analysis.baseline_image_similarity` | `image_similarity_service` aHash on verified bytes | **Yes** (or None) |
| Identifier match (`identification_status`) | real decode vs approved baseline UDI | **Yes** |
| Baseline **record** resolution | real DB query | **Yes** |

Image bytes path: upload → real sha256 → optional consent‑gated retention
(`RetainedImage.image_bytes`). Real pixels reach the adapter **only** when
`RETAIN_INSPECTION_IMAGES` + per‑submission consent produced a retained row;
otherwise the adapter honestly reports no server‑side pixels — distinct from "no
model".

## 2. Corrections made (additive, provenance‑preserving)

1. **Authoritative AI surface** — `analyze_inspection` now returns an
   `ai_analysis` block derived **only** from the live contract:
   `status ∈ {AI_UNAVAILABLE, COMPLETED}`, `manual_inspection_required`,
   `observation` (None unless a real model produced one), supported/unsupported
   categories, `baseline_image_similarity`, `authorizes_release: False`,
   `human_review_required: True`. With no promoted model (today) this is
   `AI_UNAVAILABLE` even though the placeholder score is populated — so the
   placeholder can never be read as a verified AI result.
2. **Finding provenance** — every placeholder finding carries
   `verified_ai: False`, `provenance: "deterministic_placeholder"`, and
   `observation_source ∈ {"technician_declared", "heuristic"}`, so human
   declarations are distinguishable from heuristic output and neither is a model
   observation.
3. **Baseline similarity honesty** — `baseline_match_is_image_similarity: False`
   + `baseline_match_basis: "metadata_and_declared_findings_heuristic"`. A numeric
   **image** similarity is exposed only via `ai_analysis.baseline_image_similarity`
   and only when a real comparator evaluated two compatible decoded images;
   always labelled *visual similarity — not verified cleanliness*.
4. **Frontend** (`NewInspectionPage`) — the result card is now driven by
   `ai_analysis`: when `AI_UNAVAILABLE` the headline is "AI model unavailable —
   manual inspection required" (neutral, not the green success state), a banner
   states no AI observation/probability/interpretation was produced, the
   confidence field is labelled "Heuristic Confidence (not AI)", and the submit
   toast no longer claims "AI analysis complete".

No existing field was removed or renamed, so inspection records, baseline
governance, audit, tenant isolation, and the human‑review gate are unchanged; the
default behaviour for every existing test is byte‑compatible.

## 3. Acceptance tests (`tests/test_inference_provenance.py`, 8/8 passing)

1. No trained model → explicit `AI_UNAVAILABLE`. 2. Missing/invalid image → no
positive AI detection. 3. Metadata‑only baseline → no similarity %. 4. Identical
supported images → traceable real comparison (`exact_match`, 1.0, comparator
version). 5. Cross‑tenant model not used. 6. Technician‑declared findings
distinct from model observations. 7. Unsupported categories get no model
confidence. 8. No model result authorizes release.

## 4. Component readiness

**Functional now (real, non‑fabricated):**
- Live inference adapter (loads real promoted artifact, real features,
  calibration, abstention; honest `AI_UNAVAILABLE` otherwise).
- Feature‑based baseline image comparator (aHash/Hamming) with hash‑verified
  baseline bytes and compatibility‑first gating.
- Consent‑gated image retention; real sha256; identifier decode + match.
- Real training/calibration/registry pipeline and shadow/validation infra.
- Authoritative `ai_analysis` provenance surface + frontend presentation.

**Not functional yet (by design, honestly reported):**
- No promoted (`≥ Candidate`) model exists → live AI is `AI_UNAVAILABLE`.
- No ACTIVE baseline **images** with verified bytes seeded by default → baseline
  image similarity is `None` until manufacturers/vendors publish them.
- `ultralytics`/`cv2`/`numpy` not installed; the separate YOLO path stays dormant.

**Remaining to test real instrument photographs:** eligible dual‑reviewed ground
truth → trained+calibrated+**promoted** artifact → published ACTIVE baseline
images → consent‑based retention enabled. See `REAL_VISION_PILOT_PLAN.md`. Once
present, the serving path already in place uses the real model automatically.
