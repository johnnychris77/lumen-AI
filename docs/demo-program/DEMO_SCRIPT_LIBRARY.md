# LumenAI — Demo Script Library

Objectives 9 (Demo Story Library) and 12 (Demo Script Library — timed presentations) review. Stories are cross-referenced against real automated test coverage wherever possible, reusing the scenario table already built in `docs/clinical-validation/CLINICAL_VALIDATION_PLAN.md` rather than duplicating it.

## Demo Story Library (Objective 9)

Each story below states Background / Objective / Expected AI behavior / Learning points. Test-coverage citations are carried forward from `docs/clinical-validation/CLINICAL_VALIDATION_PLAN.md`'s scenario table — reuse that document's exact test names when asked to substantiate a claim.

### 1. Retained Blood
- **Background**: A borescope image shows visible retained blood in a lumen after cleaning.
- **Objective**: Demonstrate the platform's core contamination-detection narrative and severity scaling.
- **Expected AI behavior**: Classified as a `blood` finding (present in every internal finding-type vocabulary); severity scored via the probability→severity_index mapping; `_SEVERITY_SCALES` labels progress none/trace/visible/heavy.
- **Learning points**: Blood is part of the "stable core" finding taxonomy present in all five internal vocabularies (`docs/clinical-validation/FINDING_TAXONOMY.md`) — a safe, uncontroversial example to lead with. Test coverage: `test_ranking_engine.py`, `test_cv_pipeline.py`.

### 2. Corrosion Progression
- **Background**: The same instrument shows corrosion at increasing severity across 3 consecutive inspections.
- **Objective**: Demonstrate Vulcan's progression model and its honest refusal to over-claim from thin data.
- **Expected AI behavior**: Vulcan's progression model (`vulcan_progression_service.py`) classifies `rapidly_worsening` (non-decreasing sequence, net_change ≥ 2) or `slowly_worsening` (net_change == 1); never asserts a trend from a single observation.
- **Learning points**: This is a genuinely well-designed, honestly-hedged model — any single decrease anywhere in the sequence disqualifies both "worsening" states. Test coverage: `test_vulcan_reliability.py::test_repeated_corrosion_creates_progression_signal`.

### 3. Poor Image Quality
- **Background**: A technician submits a blurry or poorly-lit inspection image.
- **Objective**: Demonstrate that low evidence quality produces an honest "recapture" signal rather than a confident-looking but unreliable conclusion.
- **Expected AI behavior**: Veritas's evidence-readiness score is penalized for image quality; explicit recapture guidance is surfaced.
- **Learning points**: This is a strong "we don't fake confidence" story — pair it with Veritas's evidence-readiness gate (`insufficient_evidence` → `GATE_ANALYSIS_BLOCKED`, "do not issue a final AI conclusion from this inspection as-is"). Test coverage: `test_veritas_evidence.py::test_poor_image_quality_requires_recapture_guidance`.

### 4. Baseline Missing
- **Background**: An instrument has no approved baseline on file.
- **Objective**: Demonstrate that missing reference data degrades confidence honestly rather than silently assuming a match.
- **Expected AI behavior**: `baseline_comparison_scoring_service.resolve_baseline`'s governance check ensures an unapproved/superseded baseline is never used to drive final scoring; readiness score is penalized for missing/uncertain baseline match.
- **Learning points**: Direct evidence the system won't quietly use bad reference data. Test coverage: `test_veritas_evidence.py::test_unapproved_baseline_cannot_drive_final_scoring`, `test_superseded_baseline_is_not_selected`.

### 5. Repair Recurrence
- **Background**: An instrument returns for repair on the same issue multiple times.
- **Objective**: Demonstrate the platform's repeat-failure/root-cause signal.
- **Expected AI behavior**: Vulcan's reliability model surfaces repeat-repair history; `rca_engine_service.py`'s root-cause categorization remains human-only (never AI-inferred causally) per `docs/clinical-validation/CLINICAL_RECOMMENDATIONS.md`.
- **Learning points**: Good opportunity to state the "never claim causation" discipline explicitly and show it's enforced in code, not just policy.

### 6. Digital Twin Deterioration
- **Background**: An instrument's digital twin shows a declining quality/reliability trend over several inspections.
- **Objective**: Demonstrate forward-looking, honestly-hedged forecasting.
- **Expected AI behavior**: `digital_quality_twin_service.py`'s `QualityForecast` pairs every projection with `confidence_score`, `human_review_required=True`, and an explicit non-causation disclaimer.
- **Learning points**: Contrast with Apollo's governance-health twin, which has no numeric confidence field — if this story is told at the instrument level, stay on `digital_quality_twin_service.py`, not Apollo, per `docs/demo-program/DEMO_MASTER_PLAN.md`'s twin-readiness guidance.

### 7. Evidence Conflict
- **Background**: Two evidence sources disagree (e.g. an anatomy-zone mismatch between two images of the same instrument).
- **Objective**: Demonstrate that conflicting evidence is surfaced, not silently resolved by picking a side.
- **Expected AI behavior**: A `VeritasEvidenceConflict` row is created; conflict resolution requires a named responsible reviewer role.
- **Learning points**: A strong "we don't guess when data disagrees" story. Test coverage: `test_veritas_evidence.py::test_anatomy_zone_mismatch_creates_evidence_conflict`.

### 8. Workflow Variation
- **Background**: An inspection follows a non-standard path (e.g. missing a stage, or an OR-priority instrument jumping the queue).
- **Objective**: Demonstrate the real (partial) workflow-stage tracking honestly.
- **Expected AI behavior**: Only 4 of the classical 8 SPD stages (receiving, inspection, packaging, supervisor review) have real, code-tracked equivalents, per `docs/clinical-validation/HUMAN_OVERSIGHT_MODEL.md` — do not claim full 8-stage tracking in this story.
- **Learning points**: Frame as "supports, not replaces" the full SPD cycle — an honest scope statement, not a gap to hide.

### 9. Repeat Failure (distinct from Repair Recurrence — this is a cross-instrument/family signal)
- **Background**: Multiple instruments of the same family show the same failure mode.
- **Objective**: Demonstrate family-level reliability signal aggregation.
- **Expected AI behavior**: Vulcan/Pulse-level rollups surface recurring finding types across an instrument family (see `pulse_alert_service.py`'s coverage-decline/repeat-repair alert types).
- **Learning points**: Ties into the notification-fragmentation finding in `docs/ux-review/HUMAN_FACTORS_REVIEW.md` — if demoing this live, use the Pulse Command Center's own Alerts tab rather than expecting it to surface via the main bell icon, since that pipeline is currently disconnected from Pulse's alerts.

### 10. Supervisor Override
- **Background**: A supervisor disagrees with an AI recommendation and overrides it.
- **Objective**: Demonstrate mandatory reason-capture on every consequential override.
- **Expected AI behavior**: `disposition_workspace_service.py` enforces a real `ReasonRequiredError`/HTTP 422 for every disposition-override action except plain `approve`.
- **Learning points**: **Honest staging note**: per `docs/demo-program/ROLE_BASED_DEMOS.md`'s Supervisor demonstration, a reachable UI control for this action was not found during this review. If this story must be told live, verify a working override control exists before the demo, or narrate the enforcement from the code/API behavior rather than performing a UI click that isn't there yet.

### 11. Education Recommendation
- **Background**: A technician's inspection history shows a recurring knowledge gap (e.g. consistently missing a specific anatomy zone).
- **Objective**: Demonstrate Sage's adaptive learning capability.
- **Expected AI behavior**: Sage's competency-gap detection generates a `SageLearningPlan` requiring human (educator/supervisor/manager) approval before being assigned; microlearning modules are built only from approved education content (`clinical_mentor.FINDING_EDUCATION`), never fabricated for unsupported finding types.
- **Learning points**: Good pairing with the "human approval on every AI-drafted plan" theme running through this whole story library.

## Demo Script Library — timed presentations (Objective 12)

Each script below sequences the stories above and the role-based demos in `docs/demo-program/ROLE_BASED_DEMOS.md` into a fixed runtime. All scripts inherit the staging notes from that document (orphaned-route navigation, the Supervisor-approval caveat, ROI-figure framing) — they are not repeated here in full, only referenced.

### 5-minute overview
1. (1 min) One-sentence platform framing + Dashboard KPI cards.
2. (2 min) Technician demo — New Inspection through AI Prediction Panel (Story #1, Retained Blood).
3. (1 min) One evidence/confidence explainability moment (finding card with probability, severity, recommendation).
4. (1 min) Close on the audit-trail/human-review-required theme.

### 15-minute executive briefing
1. (2 min) Dashboard + Executive Command Center KPIs.
2. (3 min) Technician demo (Story #1 or #2).
3. (3 min) Supervisor demo, staged per the honest caveat in `ROLE_BASED_DEMOS.md`.
4. (3 min) Executive Brief — Vanguard board-report generation (a genuine generated-artifact moment).
5. (2 min) ROI Center, framed explicitly as "estimated value from disclosed benchmarks."
6. (2 min) Q&A buffer.

### 30-minute hospital demonstration
1. (5 min) Platform overview + architecture framing (reference `docs/architecture/` diagrams).
2. (8 min) Full Technician demo (Story #1 + Story #3, Poor Image Quality, to show both the happy path and an honest low-confidence path).
3. (8 min) Full Supervisor demo (Story #7, Evidence Conflict, plus the Digital Twin beat).
4. (5 min) Manager/Director dashboard tour (Network Dashboard, Quality Dashboard).
5. (4 min) Q&A, with the AI Specialist Collaboration honesty framing on standby if asked "how do these AI pieces talk to each other."

### 45-minute manufacturer demonstration
1. (5 min) Platform overview.
2. (10 min) Manufacturer Portal demo (Manufacturer Portal, Instrument Registry, Baseline Governance — with the read-only-screen caveat).
3. (10 min) Reliability Trends / Failure Analytics (Instrument Forensics, narrated over the raw-JSON progression data per the honest-framing note).
4. (5 min) Story #5 (Repair Recurrence) and Story #6 (Digital Twin Deterioration).
5. (10 min) Research Collaboration tour + Q&A.
6. (5 min) Buffer.

### 60-minute investor presentation
1. (5 min) Market framing (see `docs/demo-program/INVESTOR_PRESENTATION.md` for the honest, non-inflated version of this section).
2. (10 min) Full Technician + Supervisor demo pair.
3. (10 min) Director/Executive dashboard tour, including the Vanguard board-report and strategy-generation moments.
4. (10 min) AI Specialist Collaboration demo, using the corrected Objective-8 framing from `ROLE_BASED_DEMOS.md` — this should be presented as a **strength** (deliberate, gated, auditable specialist invocation) rather than downplayed.
5. (10 min) Clinical/production readiness honesty section — reference the three existing scorecards (`docs/production-readiness/PRODUCTION_READINESS_SCORECARD.md`, `docs/clinical-validation/CLINICAL_READINESS_SCORECARD.md`, `docs/ux-review/UX_SCORECARD.md`) directly rather than contradicting them with more optimistic ad-hoc claims.
6. (10 min) Roadmap + Q&A.
7. (5 min) Buffer.
