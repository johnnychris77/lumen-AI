# Known Limitations — LumenAI Version 1.0

This document consolidates the known-limitations content already
documented, honestly, across many prior phases of this program. Nothing
here is new; it is gathered into one place per Section 11's requirement.

## Clinical / AI model limitations

- **The trained candidate model has never been wired into the live
  inspection path.** The deployed, real-time scoring pipeline
  (`app/ai/inference.py::LumenAIModel.predict()`) currently falls through
  to a deterministic, SHA-256-image-hash-seeded placeholder whenever no
  YOLO weights file is present — which is always true in this repository.
  The Genesis-trained pure-Python logistic-regression model exists and is
  registered, but no real inspection currently uses its weights.
- **The trained model itself, when it is used, is a foundation-scale
  logistic-regression baseline over Pillow-computed image features**
  (brightness, sharpness, aspect ratio) — not a trained computer-vision
  model with learned visual features. No causal or diagnostic claim is
  made. (`app/services/ml/explainability.py::KNOWN_LIMITATIONS`)
- **Supported findings are limited to `debris` and `corrosion`** (`blood`
  only when at least 3 validated training samples exist). Every other
  category is explicitly marked not-evaluated rather than guessed.
- **No visual explanation (saliency map / class-activation map) is
  generated.** This pipeline has no real trained vision model with real
  gradients to visualize; fabricating a heatmap would misrepresent it as
  something it is not.
- **No regulatory clearance is claimed anywhere** — not FDA, not any
  other body.
- **`human_review_required` is always `true`, regardless of confidence.**
  No finding is ever presented as a definitive conclusion.
- **No real facility pilot has ever been run.** All Advisory Mode
  interaction data in existence is either unit-test fixture data or
  output of an explicitly synthetic seed script
  (`backend/scripts/seed_pilot_data.py`, `random.Random(42)`).

## Engineering / operational limitations

- **No production deployment has ever served real customer traffic** —
  only a self-hosted demo instance exists.
- **No backup has ever been taken or restored.**
- **No disaster-recovery drill has ever been run** (the runbook is real
  and detailed; it is unexecuted).
- **No load-testing has ever been performed**; no performance targets have
  measured evidence behind them.
- **The exercised deployment path is single-instance** — no high
  availability, no database replication, no load balancer in practice.
- **Rollback has never been validated** beyond a demo-landing-page-only
  script; no Alembic downgrade has ever been executed.
- **Only 4 database migrations exist covering 417 tables**, with no
  downgrade path ever exercised (`docs/production-readiness/
  TECHNICAL_DEBT_REGISTER.md`).
- **The executive dashboard may serve fabricated/mock data with no UI
  indication** — flagged as a Critical finding in the technical debt
  register and not yet resolved.

## Security limitations

- **No security incident-response runbook exists.**
- **No penetration test has ever been conducted.**
- **Vulnerability remediation SLAs are documented but not enforced** by
  any code or CI gate.
- **Tenant-isolation automated test coverage is incomplete** (tracked as
  an open item in the security risk register).
- **A compliance document currently overclaims encryption-at-rest and
  Dependabot usage that do not exist in code** — flagged for correction
  regardless of release decision.
- **Alerting is not automatically triggered.** Notification dispatch code
  is real but disabled by default; a human or rule engine must invoke it
  manually today.

## Commercial / legal limitations

- **No BAA, MSA, DPA, Terms of Service, or Privacy Policy text exists
  anywhere in this repository** — every reference to these documents is a
  placeholder or an unchecked checklist item.
- **Pricing is unapproved and inconsistent** across at least 4 internal
  sources.
- **No dedicated customer support ticketing/case-management tooling
  exists.**
- **No on-call rotation exists.**

## Lumen Decision Engine & Observation Doctrine limitations

- **"Condition remains after recleaning" is not yet an automated
  re-check.** The Decision Engine records an `escalation_condition`
  string describing when supervisor review would be required, but there
  is no automated hook today that re-evaluates a specific inspection
  because a prior recleaning of the same physical instrument didn't
  resolve a finding.
- **Digital Twin trend is honestly reported as `not_available`** in the
  Result Contract's assessment layer — no real trend computation is wired
  in yet; this is not fabricated as "stable" or any other value.
- **The 4-panel Decision Engine frontend view is additive**, shown
  alongside the pre-existing `ClinicalDecisionPanel`, not a replacement —
  a human reviewer has not yet walked a real inspection through it
  end-to-end in a browser.
- **Policy simulation's `false_escalation_estimate` is a simple ratio**,
  not a validated statistical estimate — reported only when historical
  decision records exist to compute it from.

## Project Lens — First Real Computer-Vision Model limitations

- **This sprint's registered model was trained exclusively on synthetic
  images.** This environment's real database contains zero real
  facility-sourced ACTIVE Ground Truth annotations
  (`docs/model-development/TRAINING_ELIGIBILITY_REPORT.md`) — the model
  was trained and evaluated against one declared experimental run of
  synthetic, class-correlated images pushed through the real governed
  review/Ground-Truth pipeline, per the sprint's own explicit "declared
  experimental run" allowance. It is registered `candidate_stage =
  "Experimental"` and can never be promoted to `"Candidate"` by this
  sprint's own registration code while trained on synthetic data.
- **The live inference adapter reports every real inspection as
  `not_promoted`/`unavailable` today** — by design, since no model has
  ever been trained on real clinical evidence. The deterministic
  placeholder (`baseline_comparison_scoring_service.analyze_inspection()`)
  remains the disclosed, active scoring path for this pre-pilot
  deployment; the new `live_model_result` key is additive and does not
  replace it.
- **No GPU-capable ML framework is installed in this environment** —
  torch, tensorflow, onnxruntime, scikit-learn, and numpy all fail to
  import (verified directly). The trained classifier is a pure-Python
  linear model (logistic regression) over 3 hand-engineered Pillow
  features (brightness, sharpness, aspect ratio), not a learned-visual-
  feature CNN.
- **The feature-based baseline comparator (`image_similarity_service.py`)
  is a real, first-stage perceptual hash (aHash), not a learned
  embedding** — appropriate as a first stage per the sprint's own
  guidance, but a coarser signal than a trained embedding model would
  provide.
- **`error_analysis.py`'s hardcoded negative-label constant
  (`"no_actionable_finding"`) does not match Project Lens's new taxonomy's
  negative label (`"no_observable_abnormality"`)** — every error this
  sprint's run produced was therefore categorized as
  `misclassification_between_findings` rather than correctly recognizing
  false-positive/false-negative cases against the new taxonomy. Disclosed
  in `docs/model-development/ERROR_ANALYSIS_REPORT.md`; not yet fixed.
- **`TrainingConfig.class_weighting = "balanced"` is recorded in every
  training run's configuration but not actually applied** by the
  pure-Python logistic-regression trainer — a real, disclosed gap between
  declared policy and implementation.

## False-PASS Remediation limitations (see `docs/model-development/FALSE_PASS_ROOT_CAUSE.md`)

- **No baseline image is stored anywhere in this schema.**
  `BaselineLibraryEntry` is metadata only (manufacturer/category/approval
  status) — there is no image column, no upload endpoint for one, and no
  stored bytes to compare an inspection image against. The real, tested
  `image_similarity_service.compare_against_baseline()` (Project Lens) is
  therefore not wired into the live disposition path — it has nothing to
  compare against. Adding baseline-image storage was explicitly out of
  scope for the false-PASS remediation ("do not add features").
- **The placeholder can no longer assert a false "Clean"/PASS for
  undeclared contamination (blood, bone, tissue, other organic residue,
  debris), but it still runs and still drives every other signal**
  (structural/condition KPIs — corrosion, rust, crack, etc. — and the
  numeric inspection score) exactly as before. Production mode still runs
  the deterministic placeholder; it has not been removed or replaced by a
  real model, because no real, eligible, non-synthetic-trained model
  exists in this environment (see the Project Lens limitations above).
- **The average-hash (aHash) comparator can collide on visibly different
  images with similar brightness/texture statistics** — confirmed directly
  (`FALSE_PASS_MANUAL_RETEST.md`, Run 4): two deliberately different
  fixture images hashed identically under this coarse, low-resolution
  perceptual hash. This does not affect the remediation's fix (the
  comparator is not wired into any decision path), but is a real, disclosed
  limitation of the comparator itself for any future use.

## Project Canvas — Annotation Workspace limitations

- **No dedicated thumbnail pipeline.** The image library, upload results
  table, and detail viewer all load the same full-resolution, auth-gated
  bytes endpoint (`GET /api/ml/images/{id}/bytes`) via a shared
  `AuthenticatedImage` component, fetched lazily per card rather than all
  at once — there is no separate, smaller thumbnail asset generated or
  stored anywhere.
- **No freehand/canvas annotation drawing tool.** Bounding boxes are
  entered as four numeric fields; polygon and segmentation-mask regions
  are entered as raw JSON coordinate text, not drawn on the image.
- **No fabricated due dates, workload estimates, or SLA figures.**
  Reviewer queues (`/review/primary`, `/review/secondary`,
  `/review/disagreements`, `/ground-truth`) show only counts of real,
  currently-queued items computed at request time — never an invented
  turnaround estimate.
- **A confirmation-banner UX defect was found and fixed via live browser
  testing, not caught by backend unit tests**: the primary/secondary/
  adjudication review workspaces previously unmounted their own success
  banner the instant the just-reviewed item emptied the queue (the whole
  two-column layout was gated on `queue.length > 0`). Fixed by gating on
  `queue.length > 0 || selected` and no longer clearing the selected
  item/context on a successful submission. See
  `docs/annotation-workspace/PRIMARY_REVIEW_GUIDE.md`.
- **The manual acceptance script
  (`docs/annotation-workspace/MANUAL_ACCEPTANCE_TEST.md`) has not yet been
  walked end-to-end by a human reviewer** — see
  `docs/product-truth-reset/PRODUCT_CAPABILITY_MATRIX.md` Section 11 for
  the Pilot-status rationale.

## What is NOT a limitation — verified strengths

- Real bcrypt/JWT/OIDC authentication and consistently enforced RBAC.
- Real hash-chained, tamper-evident audit logging.
- Real, CI-blocking dependency vulnerability scanning (has already caught
  a real CVE).
- Real secrets issuance (`secrets.token_urlsafe(40)`, SHA-256 hash only,
  never retrievable).
- A full backend regression suite of 3,516 tests passing cleanly, with a
  consistent, verified discipline of never fabricating a metric — every
  "insufficient_data" report in this codebase is genuine, not a cover for
  a missing feature.
