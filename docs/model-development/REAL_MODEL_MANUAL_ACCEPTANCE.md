# Real Model Manual Acceptance — Project Vision Sprint 2 (Section 20)

This is the exact-filename doc Sprint 2 Section 20/21 requires. The full
10-scenario manual acceptance package — known-good, blood-like, debris,
corrosion-like, poor-quality, unknown/out-of-scope, same-filename-changed-
bytes, no-approved-baseline, approved-compatible-baseline, and
artifact-unavailable cases, each recording image ID, Ground Truth, model
ID/version, expected/actual behavior, confidence, abstention, baseline
status, recommendation, reviewer, date, and pass/fail — is
`MANUAL_MODEL_ACCEPTANCE.md` (Project Lens Sprint 4). This doc exists to
satisfy the required filename and record what Sprint 2 added on top of it.

See `MANUAL_MODEL_ACCEPTANCE.md` for the full 10-case package. Sprint 2
additions verified against that same package:

- **`inspection_id` and `image{lcid_image_id, sha256, width, height}`** are
  now present on every case's result contract (Section 16) — additive keys,
  none of the 10 cases' existing pass/fail verdicts changed.
- **Case 7 (same-filename, changed bytes)** is additionally pinned by the
  automated test `test_same_filename_different_bytes_is_distinct_identity`
  in `tests/test_project_lens.py` — proving that identity in this pipeline
  is always the actual image bytes' sha256, never a filename or any other
  caller-supplied label.
- **Artifact-unavailable case (Case "artifact-unavailable")** now has two
  automated companions covering the two ways an artifact can fail
  independently of "no model registered at all":
  `test_missing_artifact_file_returns_artifact_missing` (artifact file
  deleted from disk after registration) and
  `test_checksum_mismatch_blocks_loading` (artifact file corrupted on
  disk) — both return the safe `ai_unavailable` contract, never a
  fabricated score.
- **`settings.ai_strict_no_placeholder`** (Section 15, off by default
  everywhere including real production) is a separate, opt-in switch, not
  one of the 10 scenarios above — see `LIVE_INFERENCE_INTEGRATION.md` and
  `REAL_MODEL_CURRENT_STATE_TRACE.md` Section 8 for what it changes when
  enabled. No case in this package requires it to be on to reach its
  documented result.

## Sign-off

Same sign-off status as `MANUAL_MODEL_ACCEPTANCE.md`: automated,
pipeline-validation only, on the one declared experimental dataset. This
package is **not** a substitute for a qualified human reviewer repeating
the walkthrough against real, expert-reviewed clinical images before any
clinical or regulatory claim is made — consistent with this sprint's
correct-completion statement: the candidate is ready for independent
validation and prospective shadow-mode evaluation, not for a clinical or
production-readiness claim.
