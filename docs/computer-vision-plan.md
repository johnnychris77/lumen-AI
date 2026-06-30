# LumenAI Computer-Vision Plan

**Status:** Draft for review
**Author:** Engineering
**Scope:** Replace the deterministic placeholder scoring with real image-based
detection and severity grading, behind the existing API and results panel.

> ⚠️ This document plans an engineering build. It does **not** claim FDA
> clearance or regulatory approval. Every AI output remains advisory:
> `human_review_required: true`, no causation language, qualified human review
> mandatory before any clinical action.

---

## 1. Goal

Today the inspection score, KPI probabilities, and severities come from
`baseline_comparison_scoring_service` — a **deterministic placeholder** that
derives numbers from the image hash, baseline presence, and declared findings.
It does **not** look at pixels, so it assigns a small probability to every KPI
(e.g. "Bone 11%" on an image with no bone) and cannot grade severity such as
the *degree* of rust.

The goal is a real vision pipeline that, from the uploaded inspection image(s):

1. **Detects** contamination and instrument-condition KPIs that are actually
   present (not a value on every KPI).
2. **Grades severity** per finding (e.g. rust: none → light → moderate → severe).
3. **Localizes** findings (regions/heatmap) so reviewers can see *where*.
4. Feeds the **same** `analysis` response shape, so the results panel and
   downstream logic (pass/fail, escalation, history) need **no rework**.

## 2. Design principle: keep the contract, swap the engine

The frontend and governance logic already consume a stable contract:

```jsonc
{
  "analysis_status": "completed",
  "baseline_source": "manufacturer",
  "baseline_match_score": 0.94,
  "inspection_score": 94,
  "risk_level": "low",
  "predicted_findings": [
    {"type": "rust", "probability": 0.08, "confidence": 0.76,
     "severity": "none", "status": "clear"}
  ],
  "kpi_summary": { "...": false },
  "identification": { "barcode_detected": true, "...": false },
  "findings_summary": ["No blood detected", "..."],
  "confidence": 0.85, "confidence_level": "High",
  "pass_fail": "PASS", "reason": ["..."],
  "critical_flags": [], "explainability": { "..." : "..." },
  "recommendation": "Accept inspection. Continue routine processing.",
  "human_review_required": true
}
```

The CV model becomes a **drop-in producer of `predicted_findings` +
`identification` + region evidence**. `resolve_baseline`, the
critical-threshold escalation, pass/fail, summary, and explainability stay where
they are and keep working. This means the model can ship incrementally without
touching the UI.

New optional fields the model adds (panel already has a placeholder for the
first one):

```jsonc
"evidence_regions": [
  {"type": "rust", "bbox": [x, y, w, h], "score": 0.71}
],
"severity_scores": { "rust": {"grade": "moderate", "score": 0.55} },
"model": {"name": "lumen-cv", "version": "1.0.0", "mode": "cv"}
```

## 3. KPI → vision-task mapping

| KPI group | KPIs | Vision task |
|---|---|---|
| Contamination | blood, bone, tissue, bioburden, debris, other organic residue | Multi-label classification + segmentation of residue regions |
| Condition | rust, discoloration, corrosion, pitting, crack, insulation damage, missing component | Multi-label classification + **severity regression/ordinal** per condition |
| Identification | barcode, QR/UDI, KeyDot detected + match | Barcode/QR decode (pyzbar/ZXing) + OCR/template match vs. baseline |

Identification is the **easiest, highest-confidence** win and needs no training
data — it's decoding, not learning. Recommend shipping it first (Phase 1).

## 4. Severity grading ("degree of rust")

Two viable approaches, in increasing data cost:

- **Ordinal head (preferred when labeled):** the model outputs an ordinal grade
  per condition (none/light/moderate/severe). Maps directly to the existing
  severity buckets and to a probability for the panel.
- **Affected-area proxy (works with weak labels):** segment the affected region,
  compute `affected_area / instrument_area`, and bucket it. Gives a defensible,
  explainable severity (“rust covers ~22% of the visible surface”) even before
  fine-grained severity labels exist.

The affected-area proxy is the pragmatic first step — it produces a *real,
image-derived* severity without per-pixel severity labels.

## 5. Model approach — phased, lowest-risk first

### Phase 0 — Honest placeholder (DONE / can tighten now)
Stop fabricating per-KPI numbers where we can. The panel already labels output
as placeholder; we can optionally suppress non-declared KPI probabilities until
the model ships. *No training data required.*

### Phase 1 — Identification + classical CV (weeks, no training data)
- Barcode/QR/UDI decode (pyzbar / OpenCV), KeyDot template match.
- Baseline image registration + **difference/SSIM map** between inspection and
  the approved baseline image → a real, explainable `baseline_match_score`,
  `baseline_deviation_score`, and a coarse "where it differs" heatmap.
- Classical residue heuristics (color/texture thresholds in HSV/Lab) as a
  *labeled-as-heuristic* contamination signal.
- **Outcome:** identification is fully real; baseline match + evidence heatmap
  are real; contamination is honest-heuristic. Drops into the same contract.

### Phase 2 — Learned multi-label detector (needs labeled data)
- A single backbone (e.g. EfficientNet/ConvNeXt or a YOLO-class detector for
  localization) with multi-label heads for contamination + condition.
- Severity head (ordinal) or affected-area proxy from Phase 1 segmentation.
- Replaces the heuristic contamination/condition probabilities with learned
  ones; keeps Phase 1 identification and baseline-diff.

### Phase 3 — Active learning + monitoring
- Reviewer corrections (the existing supervisor/override flow) become labels →
  continuous improvement.
- Drift monitoring, per-instrument-type calibration, confidence thresholds.

## 6. Training data — the key decision

This is the input that sets the timeline:

- **If you have labeled images** (instruments with known defect/contamination
  type, ideally with regions and severity): we go straight toward Phase 2.
  Useful volumes to target — a few hundred examples per KPI to start, more for
  rare/critical classes (crack, missing component).
- **If not:** Phases 0–1 ship **real value with zero training data** (ID decode,
  baseline-diff evidence, honest heuristics) while we build a labeling pipeline:
  - Capture inspection images already flowing through the app (governed: no PHI,
    SHA-only storage today — would need an opt-in image-retention path).
  - Reviewer dispositions become weak labels.
  - A small clinical SME labeling effort on a curated set for the critical KPIs.

> Governance note: the platform currently stores **only SHA-256 hashes**, not
> raw images. Training requires a deliberate, consented **image-retention store**
> with PHI controls — a prerequisite work item, not an afterthought.

## 7. Where it runs (infra options)

| Option | Latency | Cost | Notes |
|---|---|---|---|
| In-process (CPU, classical CV) | low | included | Fine for Phase 1 (decode, SSIM, heuristics) |
| Separate model service (CPU) | med | $ | Phase 2 small models; isolates heavy deps from the API |
| GPU model service / managed inference | low | $$ | Only if model size/throughput needs it |

Recommendation: keep **Phase 1 in-process** behind the existing
`/api/inspections` flow; introduce a **separate inference service** (same response
contract via an internal call) when the learned model lands, so the API node
stays light and the model can scale/deploy independently.

## 8. Validation & governance (non-negotiable)

- Every output keeps `human_review_required: true`; no causation language.
- No FDA/regulatory claims anywhere.
- Report metrics per KPI: sensitivity/specificity, PR-AUC, and **calibration**
  (a "70%" must mean 70%). Critical classes (crack, missing component, blood)
  optimize for **recall** — missing a contaminated/damaged instrument is the
  costly error.
- Hold-out test set per instrument type; no leakage of an instrument across
  train/test.
- Shadow-mode first: run CV alongside the placeholder, log agreement, don't
  change dispositions until validated.

## 9. Milestones

1. **M1 (Phase 1):** identification decode + baseline-diff evidence map +
   honest heuristics, same API. No training data. Ships real evidence + the
   image heatmap the panel is already placeholdered for.
2. **M2:** image-retention store with PHI controls + labeling pipeline.
3. **M3 (Phase 2):** learned multi-label detector + severity grading; shadow
   mode → validated → enabled per instrument type.
4. **M4 (Phase 3):** active learning from reviewer corrections + drift
   monitoring.

## 10. Immediate next decision for you

1. **Do you have labeled inspection images today?** (type/region/severity)
   - Yes → we scope M3 first and build the labeling/retention plumbing in
     parallel.
   - No → we ship **M1 now** (real ID + baseline-diff evidence, no data needed)
     and stand up the labeling pipeline (M2) toward the learned model.
2. **Are you able to retain raw inspection images** (with consent/PHI controls)?
   Without retention there is no training set — this gates M3.

Either path, **M1 delivers real, image-derived value (identification + baseline
evidence map) with no training data**, and it slots into the exact panel and API
you already have.
