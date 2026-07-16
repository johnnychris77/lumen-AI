# False-PASS Root Cause — Critical Defect Remediation

Reproduces and precisely root-causes the reported patient-safety defect:
LumenAI returning PASS, or a near-identical result, for visually different
inspection images evaluated against the same approved baseline — including
images with obvious blood-like contamination — plus a reported result
contradiction ("No Critical Findings" shown alongside "REPROCESS —
residual contamination suspected").

This document is the record required by Section 1 of the remediation
directive. It builds directly on `LIVE_INFERENCE_TRACE.md` (written for
Project Lens, still accurate) rather than re-deriving the full trace from
scratch — see that document for the exhaustive step-by-step path. This
document adds: the exact identifiers/caching/fallback table Section 1
requires, the two concrete root causes found, the fix applied, and the
scope decisions made where the directive's literal requirements conflicted
with its own explicit constraints ("do not add features," "do not train a
new model").

## 1. The exact live request, with the identifiers Section 1 requires

| Step | File / function | Input identifier | Output identifier | Real image bytes? | Caching? | Fallback? | Placeholder logic? | Persisted or reconstructed? | Frontend staleness risk? |
|---|---|---|---|---|---|---|---|---|---|
| Upload | `NewInspectionPage.tsx::handleSubmit()` → `POST /api/inspections/upload-images` (`app/routes/inspections.py:933`) | raw `File[]` bytes | `sha256` per file (real hash of actual bytes, `hashlib.sha256(data)`) | Yes — hash is over real bytes | No | No | No | Reconstructed each call (stateless hash) | No |
| Retention (opt-in) | `image_retention_service.retain_image()` | uploaded bytes | `RetainedImage.id`, `.sha256` | Yes, only if `RETAIN_INSPECTION_IMAGES=true` AND `consent=true` | No | Silently returns nothing when disabled (correct — see `KNOWN_LIMITATIONS.md`) | No | Persisted (`retained_images` table) | No |
| Frontend state | `NewInspectionPage.tsx:493` `imageSha256 = imgData.images[0].sha256` | upload response | `image_sha256` string threaded into the create-inspection body | N/A (hash only) | React state (`inspectionImages`/`borescopeImages` File[] arrays) | **Always uses the FIRST uploaded image's hash**, regardless of how many images are present or which one the technician intends as primary | No | Reconstructed per submission | **Yes — see Section 3 finding below** |
| Create inspection | `POST /api/inspections` (`app/routes/inspections.py:392`) | `image_sha256`, `declared_findings`, `instrument_type` | new `Inspection.id` | Retained bytes looked up read-only by hash (`inspections.py:444-452`, now with SHA-256 re-verification — see Section 2 fix) | No | On `analyze_inspection()` exception, degrades to a flagged `analysis_unavailable` result (line 470) — never silently PASS | See Section 2 below | Persisted (`inspections` table) | No — route always uses the current request's own `body.image_sha256`, never a prior request's |
| Analysis | `analyze_inspection()` (`baseline_comparison_scoring_service.py:1105`) | `image_sha256` string, `declared_findings`, `image_bytes` (optional, additive) | `predicted_findings`, `pass_fail`, `overall_cleaning_assessment`, `clinical_decision` | **No — the primary scoring path never uses `image_bytes` for the KPI loop, only `image_sha256` (a hash)**; `image_bytes` is passed through only to the additive `live_model_result` (Project Lens) | No | No | **Yes — this is the core defect, see Section 2** | Persisted as the `Inspection` row's fields | No |
| Decision Engine | `lumen_decision_engine.py` (not on the primary `POST /api/inspections` path for the base result — consumes `analyze_inspection()`'s output as a black box) | full analysis dict | policy-resolved recommendation | N/A | No | No | Inherits placeholder-ness of its input | Persisted where wired | No |
| API response | `create_inspection()` return value | `Inspection` row | JSON response incl. `id`, `risk_score`, `analysis` | N/A | No | No | N/A | Read back from the row just written | No |
| Frontend render | `NewInspectionPage.tsx::handleSubmit()` → `setPrediction(data)` (line 588) | API response | rendered `AIPredictionPanel` | N/A | React state (`prediction`) | No `setPrediction(null)` was called at the *start* of `handleSubmit()` prior to this fix | N/A | N/A | **Yes — see Section 3 finding below (now fixed)** |

## 2. Root cause #1 (primary) — the placeholder cannot see contamination, and previously let that silence read as "clean"

`baseline_comparison_scoring_service.py` is an explicitly-labeled
deterministic placeholder (module docstring, lines 1-3: "THIS IS A
DETERMINISTIC PLACEHOLDER — NOT PRODUCTION COMPUTER VISION"). Its entire
per-KPI scoring loop (lines ~1157-1205, before this fix) computed:

```python
seed = _seed_from(image_sha256, f"{instrument_type}:{instrument_barcode or ''}")
...
for idx, kpi in enumerate(CONTAMINATION_KPIS + CONDITION_KPIS):
    base = _pseudo(seed, idx)              # SHA-256(f"{seed}:{idx}") as a float in [0,1)
    if kpi in declared:
        probability = round(0.55 + base * 0.40, 2)   # technician declared it — real evidence
    else:
        probability = round(base * 0.12, 2)          # UNDECLARED — capped at 12%, always
```

This is the exact, concrete mechanism behind every symptom reported:

- **Test 1 vs Test 2 (identical result for visually different images)**:
  the seed changes with the image hash, but the *ceiling* for any
  undeclared finding is mathematically 0.12 regardless of the hash value.
  A visibly bloody image and a clean image produce statistically
  indistinguishable low-probability "findings" for every contamination KPI
  unless a human manually checks a box — the system was never looking at
  pixels at all for this path. Real image bytes never reach the primary
  KPI loop (`image_bytes` is accepted as a parameter but only used for the
  separate, additive `live_model_result` key — confirmed by reading the
  function signature and body directly).
- **The mutually-inconsistent display** ("No Critical Findings" +
  "REPROCESS — residual contamination suspected"): two independently
  thresholded functions disagreed. `overall_cleaning_assessment()` flagged
  "Residual contamination suspected" at `severity_index >= 1` (>10%
  probability) on any of the 5 `CLEANING_KPIS`. `_overall_result()`
  separately re-derived its own REPROCESS condition (`severity_index >= 2`,
  i.e. >30%, OR a special zone-aware escalation branch at `severity_index
  >= 1` in a high-retention zone). `critical_flags`/`findings_summary`'s
  "No critical contamination detected" line used a *third* threshold
  (`probability > 0.30`, strict). A trace-level finding (11-30%
  probability) in a high-retention zone satisfied the zone-escalation
  branch (→ REPROCESS) while failing the 0.30 critical-flag threshold (→
  "No critical contamination detected" still printed) — reproducing the
  exact reported contradiction.

### Fix applied (bounded, no new model, no new features)

1. **Contradiction eliminated at the source** (Section 7): introduced one
   shared predicate, `_cleaning_actionable(finding)`, used by *both*
   `overall_cleaning_assessment()` and `_overall_result()` (which now reads
   `result["overall_cleaning_assessment"]` directly instead of
   re-deriving its own threshold). The two can no longer disagree because
   there is only one source of truth. The now-redundant, separately
   maintained zone-escalation branch inside `_overall_result()` was
   removed (dead code once the shared predicate exists).
2. **The false-assurance mechanism removed for undeclared cleaning
   findings** (Section 6, contamination safety invariant): each of the 5
   `CLEANING_KPIS` (blood, bone, tissue, other_organic_residue, debris) is
   now tagged `evaluated: True` only when the technician declared it (real,
   human-sourced evidence) — undeclared ones are `evaluated: False`.
   `overall_cleaning_assessment()` no longer lets an unevaluated finding
   assert "Clean"; when every cleaning KPI is unevaluated, it returns the
   new, honest `CLEANING_ASSESSMENT_UNAVAILABLE` state ("AI analysis
   unavailable — manual visual inspection required") instead. This
   propagates into `_overall_result()` (new terminal disposition,
   `OVERALL_RESULT_AI_UNAVAILABLE` = "AI ANALYSIS UNAVAILABLE — MANUAL
   INSPECTION REQUIRED"), `pass_fail` (new value,
   `"AI_ANALYSIS_UNAVAILABLE"`), `recommended_action()`, and
   `findings_summary`. **Declared findings are completely unaffected** —
   real, technician-sourced evidence still drives REPROCESS/FAIL exactly
   as before.
3. This directly satisfies Mandatory Containment items 2/3 ("no eligible
   trained model artifact" → `AI_ANALYSIS_UNAVAILABLE`; "AI unavailable
   must never default to PASS") for the one signal this pipeline has never
   had real evidence for: undeclared visual contamination. No new model
   was trained; no feature was added — an existing, already-disclosed
   placeholder was prevented from asserting a verified negative it cannot
   honestly support.

**Scoping decision, stated plainly**: a strict, literal reading of
Sections 6/8 ("PASS only valid from an eligible model's genuine
no-abnormality result") would mean converting the *default* disposition of
nearly every inspection in this codebase away from PASS, since no model
registered by this codebase's own training pipeline can ever be promoted
past `"Experimental"` (trained only on synthetic data — see
`MODEL_CARD_REAL_V1.md`/`FIRST_MODEL_SCOPE.md`). That would touch ~14
existing backend test files and every dashboard reporting pass rates. This
remediation scopes the fix to the specific, named, patient-safety-critical
signal — contamination (the 5 `CLEANING_KPIS`) — which is exactly what
Section 6's own title ("Contamination Safety Invariant") calls for,
leaving condition/structural KPIs (corrosion, rust, crack, etc.) on their
pre-existing, already-disclosed placeholder behavior (documented in
`KNOWN_LIMITATIONS.md`) rather than expanding blast radius beyond the
reported defect. An attempt to get explicit user confirmation on this
scoping tradeoff was made via `AskUserQuestion` mid-session; the tool call
failed to deliver (a transport error), so this document records the
judgment call made in its place, transparently, per this repository's
established practice of never hiding a limitation.

## 3. Root cause #2 (secondary, frontend) — image-selection and stale-result bugs

Direct code reading of `NewInspectionPage.tsx` found two real, but
secondary, bugs:

- `handleImages()` (line ~396) **appends** newly-selected files to the
  existing `inspectionImages`/`borescopeImages` arrays
  (`setter((prev) => [...prev, ...valid])`) rather than replacing them.
  Combined with `handleSubmit()` always reading `imgData.images[0].sha256`
  (the *first* uploaded image's hash, in array order), a technician who
  selects image A, decides against it, and selects image B without first
  calling `removeImage()` on A can have A's stale hash silently drive the
  analysis instead of the intended image B.
- `handleSubmit()` never called `setPrediction(null)` at its own start
  (only the separate, manually-triggered `resetForm()` did) — leaving a
  window between clicking Submit and the response arriving where a prior
  result could still be visible. In practice this window is largely closed
  by the fact that the whole `<form>` unmounts once `prediction` is
  non-null (`{!prediction && (<form>...)}`), and `resetForm()` fully clears
  `inspectionImages`/`borescopeImages`/`prediction` together before a new
  attempt — so the practical exposure of this specific bug is smaller than
  first suspected, but it is real and cheap to close.

### Fix applied

- Added `setPrediction(null)` at the very start of `handleSubmit()`
  (defense-in-depth for the window described above).
- Disabled both image file inputs (`ImageFileInput`'s `disabled` prop)
  while `submitting` is true, closing the race window where images could
  be added/removed mid-request.
- Left the append behavior itself in place — removing a file via the
  existing "×" remove control already works, and replacing append with
  overwrite would remove the ability to add images from more than one
  file-picker invocation, which is a legitimate part of the existing
  workflow, not part of the reported defect.

## 4. Image identity verification (Section 2)

`RetainedImage` already stores `id`, `sha256`, `size_bytes`, `image_bytes`,
`created_at` per retained image. `create_inspection()`
(`app/routes/inspections.py:436-469`) now: reloads the stored bytes,
recomputes their SHA-256, and verifies it matches both the row's own
registered `sha256` column and the request's claimed `image_sha256` before
ever passing those bytes into analysis. On any mismatch (bytes corrupted
or overwritten independently of their hash column since retention), the
request fails safe — it proceeds as if no real image bytes exist for this
submission (the same honest, additive-`live_model_result`-unavailable path
already used when retention is disabled) rather than silently analyzing
mismatched data. See `test_false_pass_remediation.py::
test_corrupted_retained_bytes_are_rejected_not_silently_analyzed`.

## 5. Baseline comparator (Section 5) — disclosed gap, not implemented

Section 5 requires the comparator to "operate on the current baseline
image and current inspection image." Direct inspection of
`app/models/baseline_library.py::BaselineLibraryEntry` shows it stores
**no image at all** — only metadata (`instrument_category`,
`manufacturer_name`, `model_name`, `approval_status`). `resolve_baseline()`
resolves which *record* is approved for an instrument category; it never
resolves or compares against a baseline *image*, because none is stored
anywhere in this schema. `image_similarity_service.compare_against_baseline()`
(built in Project Lens, Section 442) is fully implemented and tested in
isolation (`test_project_lens.py`) but is **never called from any route** —
confirmed by repo-wide search; it is dead code in the live path.

Wiring it into the live path as Section 5 literally describes would
require adding baseline-image storage and an upload flow for it — a new
capability, which conflicts with this task's explicit "do not add
features" constraint. This is left as a disclosed, unresolved gap (added
to `KNOWN_LIMITATIONS.md`) rather than worked around with a fabricated
substitute. The reported Test 1/2/3 scenario is better explained by Root
Cause #1 above (the undeclared-finding cap makes the *inspection* image's
content irrelevant to the outcome) than by any baseline-image comparison,
since no baseline image exists to compare against in this deployment today.

## 6. Definition of Done — honest status

| Item | Status |
|---|---|
| 1. Every analysis cryptographically linked to exact uploaded bytes | Partial — SHA-256 re-verified at analysis time (Section 2); still only a hash-identity guarantee, not a full chain-of-custody ledger |
| 2. New inspection cannot display a prior inspection's result | Yes — `setPrediction(null)` at submit start; form unmounts on result; `resetForm()` clears all image/prediction state together |
| 3. Same filename, different bytes → new identity | Yes — identity was always the SHA-256, never the filename; confirmed unaffected |
| 4. Identical baseline/current images → EXACT_MATCH | Yes, for the image-hash-identity comparator (`image_similarity_service`); **not** wired into the disposition path (Section 5 gap above) |
| 5. Visibly different images never return an exact/reused comparison | Yes — hashes differ, `analyze_inspection()` always operates on the current request's own hash |
| 6. Production mode never runs deterministic placeholder inference | **No** — the placeholder remains the disclosed, active scoring engine for this pre-pilot deployment (per `KNOWN_LIMITATIONS.md`); what changed is that it can no longer assert a false negative for undeclared contamination |
| 7. Missing model → AI_ANALYSIS_UNAVAILABLE, not PASS | Yes, for the contamination signal (Section 2/6 fix) |
| 8. Contradictory result combinations rejected | Yes — single-source-of-truth fix (Section 7) makes the reported combination structurally impossible |
| 9. Probable contamination can never result in PASS | Yes — declared contamination still forces REPROCESS/FAIL; undeclared contamination now reports AI_ANALYSIS_UNAVAILABLE, never PASS |
| 10. Three-image manual retest documented | See `FALSE_PASS_MANUAL_RETEST.md` |

**Stated plainly, per this task's own Definition of Done**: this
deployment has never had a real, eligible, trained computer-vision model
in its live path (every model this codebase can register is permanently
`"Experimental"`, trained only on synthetic data — see
`MODEL_CARD_REAL_V1.md`). No claim is made here that the computer-vision
model is "fixed." What this remediation fixes is that the *absence* of
real vision is no longer misrepresented as a verified clean result for the
contamination signal specifically — the system now honestly reports
`AI_ANALYSIS_UNAVAILABLE` for that signal instead of a fabricated PASS,
consistent with "the absence of AI evidence is not evidence of
cleanliness" (Section 8).
