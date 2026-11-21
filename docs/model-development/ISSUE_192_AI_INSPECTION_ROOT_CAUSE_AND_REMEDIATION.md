# Issue #192 — AI-Assisted Instrument Inspection: Root Cause, Architecture Assessment and Remediation Plan

**Base:** `main` at `0f2ec58`. **Branch:** `feature/192-inspection-ai-readiness-diagnostics` (separate from security PR #181,
which stays DRAFT / HOLD and is not touched).
**Environment:** local, isolated, non-production. No deployed database, artifact store, log or secret was accessed.

## 0. Verdict

**BLOCKED_NO_VALIDATED_MODEL.**

LumenAI has no trained vision model that is real-data, validated and eligible for live inference, in this
repository or anywhere this investigation could see.

What inspection #38 displayed is the platform's designed **fail-closed** outcome. It is not a crash, and it is
not a frontend rendering bug. AI-assisted defect detection cannot be "restored", because a validated capability
has never existed. It has to be built, validated and governed (§7).

Two smaller defects made the outcome hard to diagnose. Both are fixed on this branch:

1. **One generic message for every AI failure mode.** Every reason the AI produced nothing reached the user as
   "No eligible trained vision model". A model that ran and abstained was also mislabeled on the authoritative AI
   surface.
2. **The baseline flag conflated two different states.** "Manufacturer baseline image registered but not ACTIVE"
   appeared both when an image was still awaiting review or activation, and when an ACTIVE image existed but did
   not match the inspection's manufacturer / model / zone / view.

## 1. Pipeline trace (Task 1)

| Step | Code | What happens |
|---|---|---|
| Upload | `POST /api/inspections/upload-images` (`backend/app/routes/inspections.py`, ~L1260) | Stores the SHA-256 hash and a temporary processing image. Bytes are retained for training only if `RETAIN_INSPECTION_IMAGES` is set **and** the client sends `consent=true`. |
| Create | `POST /api/inspections` (`inspections.py` ~L605–L690) | Loads retained bytes (hash re-verified), then prefers the hash-verified, tenant-scoped processing image (`load_processing_bytes`). Calls `analyze_inspection(...)`. |
| Analysis | `analyze_inspection` (`baseline_comparison_scoring_service.py:1762`) | Resolves approved-baseline metadata. On a miss, returns the no-baseline / supervisor-review result. Otherwise builds the candidate identity (`_candidate_identity_for`, L380) and calls `_live_model_result` (L239). |
| Inference | `live_inference_adapter.predict` → `load_active_model` (`live_inference_adapter.py:62`, `:193`) | Serves a model only if all of these hold: a `ModelRegistryEntry` exists for **this tenant** with `model_id="lumenai-vision-lens"`, `training_status="trained"` and stage ≥ `Candidate`; the artifact file exists; its SHA-256 matches the registry; the preprocessing version matches; the label map is valid. Otherwise it returns `ai_unavailable` with a health state. |
| Image gate | `predict` | No bytes → unavailable. Quality reject/poor → abstain. Low calibrated confidence or unknown → abstain. |
| Baseline image | `_live_baseline_comparison` → `resolve_baseline_image` (`baseline_compatibility_service.py:120`) → `compare_against_baseline` | A separate channel. Only **ACTIVE**, tenant-scoped links resolve, through a fixed hierarchy matched by exact string equality: digital twin; then manufacturer + model + zone; then manufacturer + model + whole instrument; then organization family; then governed consensus. |
| AI gate | `analyze_inspection` L2051 | `ai_available = live.analysis_status == "completed" and not abstained`. If false (and not the demo fixture), the result is `_ai_unavailable_result` (L1609): no score, no confidence, no risk, human review required. |
| UI | `frontend/src/pages/NewInspectionPage.tsx` | `aiUnavailable = ai_analysis.status === "AI_UNAVAILABLE"` shows the banner. `baselineImageStatusText` and `BaselineEvidenceRow` render the baseline facts. |

### 1.1 Failure-mode determination (the issue's checklist)

| Failure mode | Finding | Evidence |
|---|---|---|
| No model registered | **Most likely for #38.** No real-data model exists to register. No weight file (`.onnx/.pt/.pth/.safetensors/.pkl/.joblib/.h5/.tflite`) or Lens artifact is tracked in git. `backend/model_artifacts/` is git-ignored. | `e2e-verification.json` → `inventory` |
| Registered but ineligible (not promoted) | Possible only if someone ran the synthetic experimental pipeline on the deployment. `register_lens_model` forces `Experimental` for non-real data (`lens_model_registration.py:40`). `Experimental` < `Candidate` → `not_promoted`. | control N2 |
| Unavailable runtime | Not applicable. The Lens model is pure Python with no GPU or extra dependency; the legacy YOLO path (`app.ai.inference`) is separate and not on this route. | — |
| Failed load | Reachable if an artifact were registered: `render.yaml` declares **no persistent disk**, and the artifact directory (`LUMENAI_MODEL_ARTIFACT_DIR`, default `model_artifacts`) lives inside the container. Any artifact created on a running instance disappears on redeploy (`artifact_missing`). | `render.yaml`; test `test_artifact_dir_is_not_persistent_on_render` |
| Unsupported class | Not the cause. Unsupported classes are listed, never scored. | adapter contract |
| No invocation | **Ruled out.** Inference is invoked on every image inspection that reaches the AI gate. Control N1 shows the adapter is called and reports its state; control M1 shows the loader and predictor execute when a model passes the gates. | controls N1, M1 |
| Frontend mapping defect | **Partial.** The UI faithfully rendered the backend contract, but the contract (a) used one message for six different causes, and (b) left `ai_analysis.status="COMPLETED"` and `manual_inspection_required=false` when a model abstained. The top-level result was already AI_UNAVAILABLE, so this was inconsistent but not a false pass; it was reachable only with a promoted model. Fixed. | §5 |

### 1.2 What can and cannot be said about inspection #38

The production database was **not** accessed, so #38's stored record was not read. From the code, its message set
is produced only by `_ai_unavailable_result` together with `baseline_image_registered=true` and
`baseline_image_active=false`.

To confirm #38 exactly, an authorized operator can read these fields from its stored analysis JSON:

- `live_model_result.model.status` and the last entry of `live_model_result.limitations` (the adapter's
  reason);
- `baseline_evidence.comparison_status`, `resolution_scope` and `resolution_reason`.

After this branch is deployed, new inspections carry `ai_unavailable_reason.code` and
`baseline_evidence.baseline_image_status_code` directly.

## 2. Model readiness (Task 2)

| Item | State |
|---|---|
| Real-data model artifacts | **None** (repository and tracked files). Docs agree: `FIRST_MODEL_SCOPE.md`, `REAL_VISION_MODEL_READINESS.md`. |
| Only trainable model | Project Lens hierarchical classifier. Stage A is a quality rule; Stage B is binary logistic regression; Stage C is one-vs-rest. Inputs are **3 Pillow scalar features** (brightness, sharpness, aspect ratio) — not a convolutional or transformer vision model. |
| Classes (synthetic experimental) | `no_observable_abnormality`, `probable_blood_like_residue`, `probable_bone_like_fragment`, `probable_corrosion_like_degradation`, `probable_plastic_or_insulation_fragment`, `probable_retained_debris`, `probable_tissue_or_organic_residue`. Not evaluated: `probable_lint_or_fiber`, `probable_unknown_foreign_material`. |
| Validation metrics | Synthetic test split only, n=16 (`EVALUATION_REPORT.md`): accuracy 0.5625, macro-F1 0.7143. Two classes have 0 recall. Temperature 1.85, ECE 0.147, abstention threshold 0.5 (`CALIBRATION_REPORT.md`). **No real-image metric exists.** |
| Dependencies | Pillow and the standard library only. |
| Deployment config | `RETAIN_INSPECTION_IMAGES="true"` in `render.yaml` (still requires per-upload consent). **No persistent disk; no artifact store.** No model registered per tenant. `MIN_STAGE_FOR_LIVE_SERVING="Candidate"`. |
| Governance gap (new finding **G-192-1**) | `register_lens_model` sets `Candidate` automatically for any trained run with `data_provenance=="real"`, and `Candidate` is enough for live serving. A real-data model that merely trained would therefore be served to clinicians (with human review) **without any validation or clinical sign-off in the serving path**. This is not exploitable today because no real data exists, but it must be closed before real data is used (§7, step P0). |

## 3. Baseline comparison (Task 3)

**Lifecycle** (`app/models/baseline_image_library.py`): DRAFT → PENDING_REVIEW → APPROVED → ACTIVE. ACTIVE is
reachable only from APPROVED. Other states are SUSPENDED, SUPERSEDED, REJECTED and ARCHIVED.

The Manufacturer Baseline form (`POST /api/baselines/{entry_id}/reference-image` →
`register_manufacturer_reference_image`) **always ends at PENDING_REVIEW**. Two further steps are needed, each
by a role in `administrator / clinical_reviewer / reviewer` (mapped from `admin / clinical_reviewer /
spd_manager`):

- `POST /baseline-library/images/{id}/review` (decision approve) → APPROVED;
- `POST /baseline-library/images/{id}/activate` → ACTIVE, subject to the activation gate.

The UI for both steps is `BaselineImageDetailPage` and `/baselines/review`.

**Why #38 got no ACTIVE comparison.** One of two causes, which were indistinguishable before this branch:

- **(a) Governance not completed.** The image was registered but not reviewed and/or activated.
  - Now reported as `AWAITING_REVIEW` or `AWAITING_ACTIVATION`.
  - Fix (operational): an authorized reviewer completes review and activation.
- **(b) Identity mismatch.** An ACTIVE image existed, but resolution failed, because matching uses exact strings
  for manufacturer, model and zone/view within the tenant. For example, "Hopkins II" ≠ "Hopkins 2", or the
  inspection was created under a different tenant than the image.
  - Now reported as `ACTIVE_NOT_MATCHED`.
  - Fix: correct the inspection identity. Longer term, use canonical instrument IDs (§7, step P5).

**Baseline matching is not defect detection.** The comparator is an average-hash Hamming similarity
(`image_similarity_service`). An exact or close match says the image looks like the reference. It says nothing
about blood, bone, tissue or debris. Control B4 shows a real `exact_match` comparison while AI correctly stays
`AI_UNAVAILABLE` with `confidence=None`.

## 4. Architecture assessment

**Sound — keep:**
- Fail-closed live gate: there is no placeholder path in clinical mode, and the demo fixture is segregated.
- Artifact checksum and preprocessing-version checks.
- Tenant-scoped model and baseline lookups.
- Hash-verified image bytes.
- A baseline channel kept separate from AI observations.
- `authorizes_release=false` always.
- Calibrated abstention.

**Weak — must change before clinical AI:**
1. The model class cannot represent visual contamination: 3 global scalar features, trained on synthetic
   images.
2. Artifacts live on ephemeral container disk, with no versioned, checksummed, durable artifact store.
3. Serving eligibility is a stage string, not a signed validation and clinical-approval record (G-192-1).
4. The only per-tenant model visibility is per inspection. There is no read-only "model readiness" view for a
   tenant admin; the admin-only `/v1/system/inference-status` covers only the legacy YOLO path.
5. Baseline identity matching is free-text exact equality.
6. Two inference stacks coexist: the legacy `app.ai.inference` YOLO wrapper with a deterministic fallback, and
   Lens. Only Lens is on the inspection path; the legacy one should be retired or explicitly isolated.

## 5. Changes on this branch

All changes are additive and fail-closed. No gate is relaxed, no model is promoted, and no score is
produced.

| Change | Where |
|---|---|
| Reason-code classifier, with ten codes: `NO_MODEL_REGISTERED`, `MODEL_NOT_PROMOTED`, `ARTIFACT_MISSING`, `ARTIFACT_INTEGRITY_FAILED`, `MODEL_LOAD_FAILED`, `NO_IMAGE_BYTES`, three `ABSTAINED_*` codes, and `UNKNOWN`. Each carries an operator message and an administrator action; none contains file paths, registry ids, tenants, hospitals or image content. | `backend/app/services/ai_availability_diagnostics.py` |
| The adapter emits `unavailable_reason_code` explicitly. | `live_inference_adapter.py` |
| The result carries `ai_unavailable_reason` and `ai_analysis.unavailable_reason`, on both the AI-unavailable and no-baseline paths. The explanation, `model_label`, `recommended_action` and limitations now state the actual cause. | `baseline_comparison_scoring_service.py` |
| Abstention now fails closed on the authoritative surface: `ai_analysis.status = AI_UNAVAILABLE`, `manual_inspection_required = true`, observation removed. The raw abstention is kept in `live_model_result` for audit. | `_apply_ai_unavailable_reason` |
| Baseline evidence gains `baseline_image_status_code` and `baseline_image_lifecycle_states` (this tenant, this scope, state names only). The existing `baseline_image_active` keeps its meaning. | `_baseline_evidence` |
| The UI shows the reason message and code, plus distinct baseline texts for awaiting review, awaiting activation, active-not-matched, suspended and not-usable. | `NewInspectionPage.tsx` |
| 26 regression tests. | `backend/tests/test_issue192_ai_availability_diagnostics.py` |
| Isolated end-to-end script and its evidence. | `backend/scripts/issue192_e2e_verification.py`, `docs/model-development/evidence/issue192/e2e-verification.json` |

## 6. End-to-end verification (Task 5)

Run with `cd backend && python scripts/issue192_e2e_verification.py --out <file>`. It uses a throwaway SQLite
database and a temporary artifact directory, and drives the real `analyze_inspection` → adapter → registry →
resolver/comparator path.

| Control | AI outcome | Reason code | Baseline status | Real comparison | confidence / score |
|---|---|---|---|---|---|
| N1 no model registered | AI_UNAVAILABLE | NO_MODEL_REGISTERED | — | no | null / null |
| N2 synthetic experimental model (stays `Experimental`) | AI_UNAVAILABLE | MODEL_NOT_PROMOTED | — | no | null / null |
| N3 artifact file missing | AI_UNAVAILABLE | ARTIFACT_MISSING | — | no | null / null |
| N4 artifact checksum mismatch | AI_UNAVAILABLE | ARTIFACT_INTEGRITY_FAILED | — | no | null / null |
| N5 eligible model, no image bytes | AI_UNAVAILABLE | NO_IMAGE_BYTES | — | no | null / null |
| B1 reference PENDING_REVIEW | AI_UNAVAILABLE | NO_MODEL_REGISTERED | AWAITING_REVIEW | no | null / null |
| B2 reference APPROVED, not activated | AI_UNAVAILABLE | NO_MODEL_REGISTERED | AWAITING_ACTIVATION | no | null / null |
| B3 ACTIVE reference, inspection model typed differently | AI_UNAVAILABLE (supervisor review) | NO_MODEL_REGISTERED | ACTIVE_NOT_MATCHED | no | null / null |
| B4 ACTIVE reference, matching identity | AI_UNAVAILABLE | NO_MODEL_REGISTERED | ACTIVE_RESOLVED | **yes (`exact_match`)** | null / null |
| B5 another tenant's ACTIVE reference | AI_UNAVAILABLE | NO_MODEL_REGISTERED | NOT_REGISTERED | no | null / null |
| **M1 engineering mechanics (not clinical)** | AI_UNAVAILABLE | ABSTAINED_LOW_CONFIDENCE | — | — | null / null |

Every control returned `human_review_required: true`.

**About M1.** M1 is **not** a demonstration of clinical AI and not a finding.

- The synthetic, experimental Lens model was force-staged to `Candidate` **inside the throwaway database
  only**, solely to prove that the loader and predictor execute and report provenance.
- Model `lumenai-vision-lens`, version `0.1.0-e2e-synthetic`, preprocessing `lens-pillow-features-v1`.
- The artifact SHA-256 matched its registry record. It listed 6 eligible classes plus
  `no_observable_abnormality`; 2 classes were not evaluated.
- Test image: a procedurally generated random-pixel PNG (no PHI, no patient, no instrument).
- The model ran, scored quality "Excellent", and **abstained** (`confidence_below_threshold`: calibrated
  confidence 0.5136, below the artifact's data-derived abstention threshold of 0.70). After this branch's fix,
  every clinician-facing field is null.
- The script leaves no model above `Experimental` (`models_left_promoted_in_throwaway_db: 0`).

**Acceptance status (issue #192):**
- Real inference on a consented, governed image with a validated model: **BLOCKED_NO_VALIDATED_MODEL** — handed
  off to §7.
- ACTIVE baseline comparison: **independently verified** (B4). It is clearly marked unavailable, with a named
  cause, in B1, B2, B3 and B5.
- No simulated findings, no invented confidence, no production activation.

## 7. Remediation plan — model development, validation and clinical governance

Each phase has an owner role and an exit criterion. Nothing below is authorized by this document.

| Phase | Work | Exit criterion (measurable) | Owner (role) |
|---|---|---|---|
| **P0 Serving gate** (engineering, before any real data) | Close G-192-1: live serving requires a signed validation record (model id + version + artifact SHA-256 + evaluation report hash + clinical approver + intended-use statement + expiry), not just `candidate_stage`. Registration alone never makes a model servable. Add a read-only, tenant-scoped "model readiness" endpoint for tenant admins (reason code, stage, artifact integrity; no paths). | A tripwire test proves a real-data trained model without a validation record is `MODEL_NOT_PROMOTED`. | Engineering + security review |
| **P1 Durable artifact store** | A versioned object store or persistent disk. The registry stores a URI plus SHA-256; the artifact is verified on load (already implemented) and on deploy. | After a redeploy, the registered model still loads (no `ARTIFACT_MISSING`). | Platform/ops |
| **P2 Governed data** | Consented, de-identified instrument and borescope images under a data-use agreement: no PHI, usage rights recorded, per-site provenance, capture protocol (device, lighting, zones). Use the existing retention, consent and LCID registry path. | Per class: ≥ N positive images from ≥ 3 sites and ≥ 2 capture devices, with N set by the pre-registered power calculation (at minimum, enough for a 95% CI half-width ≤ 0.10 on sensitivity). | Data governance + clinical sites |
| **P3 Ground truth** | Expert SPD/clinical reviewers following a written protocol; dual independent labels with adjudication; inter-rater agreement reported. | Cohen's/Fleiss' κ ≥ 0.6 per class before a class is eligible; disagreements adjudicated and logged. | Clinical owner |
| **P4 Model** | A model class able to represent localized residue: for example a pretrained vision backbone with a supervised head, and/or anomaly localization against ACTIVE references (prior research-stage work: PRs #163–#170). Training uses a leakage-safe split grouped by physical instrument, session and site. | Pre-registered protocol frozen before the test set is opened. | ML engineering |
| **P5 Validation** | A held-out site and device; per-class sensitivity, specificity, PPV and NPV with 95% CIs; calibration (ECE); abstention rate; subgroup analysis; false-pass analysis that prioritizes sensitivity for contamination classes. | Each class meets pre-registered thresholds. Example: sensitivity ≥ 0.90 with the lower 95% CI ≥ 0.80 for blood/bone/tissue residue, ECE ≤ 0.05, abstention ≤ 20%. A class that fails stays "not evaluated". | ML + biostatistics |
| **P6 Clinical governance** | Model card; intended use ("assistive; human decides; potential association only"); risk analysis; clinical-owner and quality sign-off; **no regulatory-clearance claim**. Baseline identity becomes canonical (manufacturer/model IDs rather than free text). | Signed validation record (P0) exists for the exact artifact hash. | Clinical owner, quality, release authority |
| **P7 Shadow → pilot** | Shadow mode first: the model runs and is logged, but nothing is shown to clinicians. Compare against human outcomes, then run a limited pilot with monitoring (drift, abstention, disagreement) and a kill switch (demote → `MODEL_NOT_PROMOTED`). | Shadow agreement report reviewed and signed; pilot criteria met. | Clinical owner + engineering |

## 8. Acceptance criteria for this branch (measurable)

1. Every non-usable live outcome carries exactly one code from `ALL_REASON_CODES`. Tests cover all ten, and the
   adapter-emitted codes are covered end to end.
2. No reason message contains `/`, `id=` or the word "tenant" (test).
3. For every control in §6: `confidence`, `inspection_score` and `risk_level` are null; `human_review_required`
   is true; `ai_analysis.manual_inspection_required` is true.
4. An abstaining model yields `ai_analysis.status == "AI_UNAVAILABLE"` and `observation == null`, with the raw
   abstention retained in `live_model_result` (tests, with and without an approved baseline).
5. `baseline_image_status_code` distinguishes AWAITING_REVIEW, AWAITING_ACTIVATION, ACTIVE_NOT_MATCHED,
   ACTIVE_RESOLVED and NOT_REGISTERED. Another tenant's ACTIVE image is invisible (test).
6. A synthetic-trained model is never served (`MODEL_NOT_PROMOTED`, test and control N2).
7. Full backend suite green; Ruff clean; frontend build succeeds.

**Results (local, SQLite, this branch's code on base `0f2ec58`):**
- Full backend suite (`cd backend && python -m pytest tests/ -q`): **3875 passed, 2 skipped, 0 failed**
  (424.88s).
- New tests (`tests/test_issue192_ai_availability_diagnostics.py`): **26 passed**.
- `ruff check backend/app backend/tests`: all checks passed.
- `npm --prefix frontend run build`: succeeded.
- PostgreSQL 16 was not run for this branch; no schema or migration change is involved. CI is the reference.

## 9. Not done, and why

- **No production access.** #38's stored record and the deployed registry were not read.
- **No model was promoted, deployed or enabled.** No validated model exists, and promotion requires clinical
  governance.
- **No admin readiness endpoint was added.** That is proposed in P0, to avoid adding a new route surface while
  the tenant-isolation review in PR #181 is still open.
- **PR #181 untouched.** It remains DRAFT / HOLD.
