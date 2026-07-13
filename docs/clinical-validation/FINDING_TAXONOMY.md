# LumenAI — Finding Taxonomy

Objective 4 review. **`finding_type` is a free-text `String(40)` column** (`app/models/inspection_finding.py`) — there is no enum class or database constraint anywhere. This review found **five different, only-partially-overlapping finding-type vocabularies** coexisting in the codebase. This is the single most important terminology-consistency finding in this document set and is reported in full rather than picking one list and presenting it as the whole truth.

## The five vocabularies found

| Vocabulary | Location | Members |
|---|---|---|
| A. Scoring engine (`KPI_LABELS`) | `baseline_comparison_scoring_service.py` | blood, bone, tissue, other_organic_residue, debris, rust, corrosion, discoloration, pitting, crack, insulation_damage, missing_component (12) |
| B. Trend service | `finding_trend_service.py` (its own comment: "the twelve categories the v1.5 spec tracks") | blood, bone, tissue, other_organic_residue, debris, rust, corrosion, crack, **wear**, pitting, missing_component, insulation_damage (12 — swaps `discoloration` for `wear` vs. A) |
| C. Education content | `clinical_mentor.py`'s `FINDING_EDUCATION` | Union of A and B, 13 keys (adds `wear` on top of A) |
| D. Agent-level subsets | `contamination_agent.py` (5: blood, bone, tissue, debris, **"other"**) and `damage_agent.py` (7: rust, corrosion, crack, pitting, wear, missing_component, insulation_damage) | Note: uses `"other"`, not `"other_organic_residue"` — a spelling inconsistency with vocabulary A |
| E. Frontend dashboard | `frontend/src/pages/Dashboard.tsx`'s `CATEGORY_LABELS` | blood, bone, tissue, debris, corrosion, crack, insulation_damage, `other` (8 real finding types) + `baseline_match` and `barcode_qr_keydot` (not finding types at all — a baseline-comparison result and a barcode-decoding feature, respectively, bundled into the same display dict) |

**The stable core present in every vocabulary**: blood, bone, tissue, debris, corrosion, crack, insulation_damage. **Present in some but not all**: rust, discoloration, pitting, missing_component, other_organic_residue, wear. **`wear` is a special case** — `finding_trend_service.py`'s own comment states it plainly: *"'wear' has no dedicated scoring KPI in the detection engine today, so it will always report 0 — an honest gap, not a fabricated count."* It is taxonomized in three of the five vocabularies but functionally unimplemented in the scoring engine.

## The scope-defining fact: what the deployed model actually produces

**This taxonomy question is secondary to a larger one: no trained model weights ship in this repository.** `app/ai/inference.py`'s `_deterministic_fallback()` — which is what actually runs absent a real YOLO model file — only ever emits:
```python
issue_options = ["stain", "debris", "clean", "corrosion"]
```
That is, **the currently-running inference code produces only 2 real finding categories (`debris`, `corrosion`)** plus two non-finding placeholders (`stain`, `clean`). Every other member of the 12-13-category taxonomy above (rust, pitting, wear, discoloration, missing_component, other_organic_residue, blood, bone, tissue, insulation_damage) is part of the platform's *scoring and education design*, ready to be populated once a real trained model is deployed — but is not what the shipped code currently classifies. **Any clinical-facing description of "what LumenAI detects" must lead with this distinction**, per [CLINICAL_SCOPE.md](./CLINICAL_SCOPE.md).

## Verification against the brief's 5 named examples

| Brief example | Real in code? | Notes |
|---|---|---|
| Rust | Yes | Vocabularies A/B/C/D; absent from D's contamination subset and E (frontend) |
| Pitting | Yes | Vocabularies A/B/C/D; absent from E (frontend) |
| Wear | Nominally yes, functionally no | Present in B/C/D; explicitly documented as unscored (always 0); absent from A (the core scoring KPI list) and E |
| Missing components | Yes | Vocabularies A/B/C/D; absent from E |
| Discoloration | Yes | Vocabularies A/C/D's severity scale; **absent from B** (trend service uses `wear` instead) and from D's damage-agent set and E |

None of the brief's five examples are fictional, but none is universally present either — this is exactly the inconsistency this review exists to surface.

## Severity model

`severity_index` (`InspectionFinding`) — confirmed exact mapping (`baseline_comparison_scoring_service.py`, `sentinelx_risk_agent_service.py`):

| Index | Label | Derived from probability `p` |
|---|---|---|
| 0 | none | `p ≤ 10%` |
| 1 | minor | `11–30%` |
| 2 | moderate | `31–60%` |
| 3 | severe | `> 60%` |

A richer, KPI-specific label layer (`_SEVERITY_SCALES` in `app/ai/inference.py`) sits on top of the same 0-3 index — e.g. blood: none/trace/visible/heavy; rust: none/surface rust/moderate rust/heavy rust; crack/missing_component/insulation_damage/pitting: none/cosmetic wear/functional concern/structural failure.

**Other severity-adjacent fields on `Inspection`** (each independently computed, not derivatives of `severity_index` alone):
- `risk_score` (0-100, `app/analytics/risk_engine.py`) — a **sixth** finding-vocabulary variant lives in its `_ISSUE_BASE` dict (debris=45, stain=45, blood=60, bone=55, tissue=55, corrosion=70, crack=85, insulation_damage=85, other=30).
- `risk_level`: `low` (≥85) / `medium` (≥65) / `high` (≥40) / `critical` (<40).
- `overall_cleaning_assessment`: exactly 3 values — `"Clean"`, `"Residual contamination suspected"`, `"Cleaning failure"`.
- `disposition`: exactly 5 values — `PASS` / `MONITOR` / `SUPERVISOR REVIEW` / `REPROCESS` / `REMOVE FROM SERVICE`.

## Supporting evidence and limitations — what is and isn't documented

**Per-finding-type visual-evidence criteria (what specific pixels/patterns justify "corrosion" vs. "pitting" vs. "wear") do not exist anywhere in this codebase**, in code or docs. The closest analog is `clinical_mentor.py`'s `FINDING_EDUCATION` dict, which the file's own header labels *"Advisory/educational — not device-specific IFU"* and *"paraphrased summaries... not quotations of AAMI/AORN copyrighted material"* — general SPD knowledge narrative, not model-specific evidentiary criteria. `docs/clinical/clinical-performance-report.md` explicitly names corrosion-vs-pitting and residue-vs-tissue discrimination as a known, currently-unresolved model weakness ("Model tuning targeting improvement in borderline categories... is planned before the live study"), and its Limitations section states plainly that pre-market data is mock/synthetic and the multi-site reader study is pending.

**This review's finding**: this level of per-finding-type evidentiary detail should not be invented for this document set — it would need to come from real model training documentation or a completed validation study, neither of which exists yet. `docs/clinical/clinical-safety-review.md` documents false-positive/false-negative risk at the whole-system hazard level (ISO 14971 table), which is the honest level of granularity currently available.
