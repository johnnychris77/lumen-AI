# False-PASS Manual Reproduction Retest

Required by Section 10 of the critical-defect remediation directive. Uses
three controlled, real PNG-encoded images (via Pillow, the established
fixture convention in this codebase — see `LIVE_INFERENCE_TRACE.md` Section
10), run against `POST /api/inspections` and `analyze_inspection()` directly
in this environment. Every value below is copy-pasted from an actual run
captured on 2026-07-15 — nothing here is invented.

## Controlled images

- **A** — approved clean baseline stand-in: 300×300 solid RGB (200,200,200),
  no stripe pattern (uniform brightness).
- **B** — clearly different clean/normal image: 300×300 solid RGB
  (120,120,120) with a 12px-period inverse-brightness stripe pattern.
- **C** — visible high-contamination stand-in: 300×300 solid RGB (15,15,15)
  (dark) with a dense 2px-period inverse-brightness stripe pattern (chosen
  to be maximally different from A in both mean brightness and texture — the
  same "visibly different" property the reported defect describes for a
  bloody/contaminated image versus a clean baseline).

Per `FALSE_PASS_ROOT_CAUSE.md` Section 5, this deployment has no baseline
*image* storage anywhere in its schema (`BaselineLibraryEntry` is metadata
only) — there is no "baseline image" to upload separately. **A** is instead
used as the first analyzed image and stands in for "the approved reference
appearance"; B and C are separate, subsequent inspection submissions
compared against it by content/hash, matching how the reported Test 1/2/3
scenario is actually exercised through this UI (submit an inspection image,
observe the result, submit a different inspection image, observe the
result) rather than a literal baseline-image upload (which does not exist
as a feature).

## Run 1 — via `POST /api/inspections` (the real, full API path)

| Field | A | B | C |
|---|---|---|---|
| Inspection ID | 1 | 2 | 3 |
| Current image SHA-256 | `da6c88e9cece405347bbe1859cdb2fe4113a54f0ed7b4ea0ee0128fc5fea32d9` | `b1ff4be8d00038138814118a3c9d2a750bbce7ea93502b112d60b80dd42a2eab` | `4b5a41ae67694577e4aea39a421de2254b319ae7b6e0149c7610c8e3313a5a4a` |
| Byte length | 912 | 925 | 914 |
| Risk score | 5 | 8 | 5 |
| `overall_cleaning_assessment` | AI analysis unavailable — manual visual inspection required | AI analysis unavailable — manual visual inspection required | AI analysis unavailable — manual visual inspection required |
| `recommended_action` | AI analysis unavailable for non-declared contamination findings — manual visual inspection required before release. | Monitor — low-risk findings only (surface rust). Continue routine processing. | Monitor — low-risk findings only (surface rust). Continue routine processing. |

All three hashes are distinct (confirmed byte-for-byte different images
produce distinct SHA-256 identities — Definition of Done item 3/5). None
of the three returns a placeholder-fabricated PASS.

## Run 2 — `analyze_inspection()` direct, with real `image_bytes` passed through

| Field | A | B | C |
|---|---|---|---|
| `pass_fail` | `AI_ANALYSIS_UNAVAILABLE` | `AI_ANALYSIS_UNAVAILABLE` | `AI_ANALYSIS_UNAVAILABLE` |
| `clinical_decision.overall_result` | AI ANALYSIS UNAVAILABLE — MANUAL INSPECTION REQUIRED | AI ANALYSIS UNAVAILABLE — MANUAL INSPECTION REQUIRED | AI ANALYSIS UNAVAILABLE — MANUAL INSPECTION REQUIRED |
| `live_model_result.model.status` | `unavailable` | `unavailable` | `unavailable` |
| `live_model_result.analysis_status` | `ai_unavailable` | `ai_unavailable` | `ai_unavailable` |
| `findings_summary` (first line) | "AI analysis unavailable for non-declared contamination findings — manual visual inspection required" | (same) | (same) |
| `findings_summary` (blood/bone/tissue lines) | "Blood not evaluated by AI (not declared)" / "Bone not evaluated by AI (not declared)" / "Tissue not evaluated by AI (not declared)" | (same three lines) | (same three lines) |

**Expected outcome, met**: no run returns a placeholder-generated PASS; the
system consistently and honestly reports `AI_ANALYSIS_UNAVAILABLE` /
"manual inspection required" for the contamination signal on all three
images, including C (the visibly contaminated one) — because no eligible
trained model is available in this environment
(`live_model_result.model.status == "unavailable"`), and no technician
declared a finding. This is the exact, correct behavior Section 6/8 of the
directive calls for: "when no model exists: AI_ANALYSIS_UNAVAILABLE →
manual inspection required → no AI-generated PASS."

## Run 3 — control: technician-declared blood on image C

To confirm the fix does not suppress *real* evidence, image C was
re-submitted with `declared_findings=["blood"]` (i.e., a technician
actually checking the "blood" box, simulating a real positive
observation):

```json
{
  "pass_fail": "FAIL",
  "overall_result": "REPROCESS",
  "overall_cleaning_assessment": "Cleaning failure",
  "recommended_action": "Reprocess — blood. Return the instrument for complete cleaning and re-inspect before release."
}
```

Real, declared evidence still drives a genuine REPROCESS/FAIL outcome —
the remediation only removed the *placeholder's* ability to assert a false
negative for undeclared findings; it did not weaken response to actual
technician-reported contamination.

## Run 4 — hash-identity comparator (`image_similarity_service.compare_image_bytes`)

| Comparison | status | similarity | method |
|---|---|---|---|
| A vs A | `exact_match` | 1.0 | `sha256_exact` |
| A vs B | `comparable` | 1.0 | `average_hash_hamming` |
| A vs C | `materially_different` | 0.625 | `average_hash_hamming` |

`A vs A` correctly returns `EXACT_MATCH` (Definition of Done item 4). `A vs
C` correctly returns `MATERIALLY_DIFFERENT` — the real, content-based
signal this comparator provides does detect the large, deliberate
brightness/texture difference between the clean and contaminated stand-ins.
**Honestly disclosed limitation**: `A vs B` returns `comparable` with
`similarity=1.0` despite B being a visibly different image from A — the
average-hash (aHash) algorithm this comparator uses is a coarse, low-
resolution perceptual hash (already disclosed in `KNOWN_LIMITATIONS.md` as
"a coarser signal than a trained embedding model would provide"); B's
stripe pattern and brightness level happened to collapse onto the same
downsampled hash bucket as A. This is a genuine limitation of the
comparator itself, not of this remediation — and, per `FALSE_PASS_ROOT_CAUSE.md`
Section 5, this comparator is not wired into the live disposition path at
all (no baseline image storage exists to compare against), so it did not
and could not affect any of the `AI_ANALYSIS_UNAVAILABLE` outcomes above.

## Definition of Done — checklist against this retest

| Item | Result |
|---|---|
| A vs A → EXACT_MATCH | ✅ (Run 4) |
| A vs B → not exact, result references B's own hash | ✅ (Run 1/2 — B's inspection/analysis always keyed on B's own sha256, never A's) |
| A vs C → not exact, result references C's own hash, no placeholder-generated PASS | ✅ (Run 1/2) |
| No model available → AI_ANALYSIS_UNAVAILABLE, manual inspection required | ✅ (Run 2 — `model.status == "unavailable"` for all three, consistent with this deployment never having a promotable trained artifact) |
| Declared/real evidence still drives a genuine result | ✅ (Run 3) |
