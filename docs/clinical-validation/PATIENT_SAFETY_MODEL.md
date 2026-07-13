# LumenAI — Patient Safety Model

Objective 12 review. This document references — rather than duplicates — the existing ISO 14971 hazard analysis in `docs/clinical/clinical-safety-review.md` (6 hazards, H-01 through H-06, all currently rated acceptable/RPN<15), and adds the specific misuse/bias/false-result analysis this Phase 3 review was asked for, grounded in verified code behavior.

## Automation bias — real, structural mitigations found

Automation bias (a human trusting the AI's output more than warranted, or stopping their own independent judgment) is mitigated by several independent, verified controls rather than a single policy statement:

- **Every disposition-override action except plain `approve` requires a non-empty, human-written reason** (`disposition_workspace_service.py`, enforced as a real `ReasonRequiredError`, HTTP 422) — a supervisor cannot silently rubber-stamp an AI recommendation for any consequential action.
- **`human_review_required` defaults to `True` on 35 distinct model files** across the codebase, and every specialist's own disclaimer text explicitly frames its output as advisory (Sentinel-X: *"does not replace human clinical judgment"*; Veritas: *"does not independently approve an instrument"*; Maestro: *"never replaces human leadership"*).
- **Root-cause categorization is deliberately human-only** — the codebase's own reasoning for this, quoted directly: *"guessing 'why' a finding occurred without a human judgment would be a fabricated causal claim."*
- **`docs/clinical/clinical-safety-review.md`'s escalation workflow requires mandatory co-sign on CRITICAL findings** — a second human, not just the first reviewer, must confirm before a critical finding proceeds.
- **Override-rate KPI thresholds (>20%/>40%) trigger review of the AI itself** — if supervisors are overriding the AI unusually often, that's treated as a signal about the AI's calibration, not just individual supervisor judgment, which cuts against complacent rubber-stamping in either direction.

## False reassurance — mitigated by explicit insufficiency states, not silent confidence

The codebase consistently prefers an explicit "insufficient/insufficient_history/insufficient_evidence" state over guessing when data is thin:

- Vulcan's progression model returns `confidence: "low"` and `PROGRESSION_INSUFFICIENT_HISTORY` whenever fewer than 2 prior findings exist for an instrument — it never asserts a trend from a single data point.
- Veritas's evidence-readiness gate returns `GATE_ANALYSIS_BLOCKED` for `insufficient_evidence` (score <50), explicitly instructing *"do not issue a final AI conclusion from this inspection as-is"* rather than proceeding with a low-confidence conclusion presented as final.
- Multiple independent confidence thresholds (0.50, 0.60, 0.70 — see [CLINICAL_RECOMMENDATIONS.md](./CLINICAL_RECOMMENDATIONS.md)) surface explicit low-confidence flags/coaching rather than silently accepting a marginal AI output.

**Residual risk**: Apollo's governance-health twin (see [DIGITAL_TWIN_CLINICAL_MODEL.md](./DIGITAL_TWIN_CLINICAL_MODEL.md)) has no numeric confidence field and its `twin_history` view drops even the qualitative scope-limitation disclosure present in the live-compute path — this is the one place in the twin family where a viewer could reasonably over-trust a trend line with no attached caveat. Flagged as a Phase 4 improvement, not a currently-exploited failure mode.

## False positives / false negatives

`docs/ai/safety-metrics.md` specifically tracks a `worst_safety_false_negative_rate` rollup across the safety-critical finding categories (blood, tissue, organic residue, crack, missing component) as a gating criterion for model promotion (`safety_false_negative_within_threshold`) — false negatives on these categories are treated as more consequential than false positives elsewhere, which is the clinically correct asymmetry (a missed contamination finding is worse than an unnecessary recleaning). `docs/clinical/clinical-safety-review.md`'s hazard table (H-01/H-02) covers false-negative/false-positive risk at the whole-system level with documented risk controls (confidence threshold 0.70, drift alerts, model version pinning).

**Important scope caveat, carried from [FINDING_TAXONOMY.md](./FINDING_TAXONOMY.md) and [AI_LIMITATIONS.md](./AI_LIMITATIONS.md): no per-finding-type documented visual-evidence or false-positive/negative criteria exist below the whole-system hazard level, and no trained model ships in this repository today** — the deployed deterministic fallback only ever emits `debris`/`corrosion`/`stain`/`clean`. Any patient-safety claim about detection performance must be scoped to that reality, not to the full 12-13 category design taxonomy.

## Possible misuse

- **Treating a Digital Twin trend or an Oracle hypothesis as a clinical conclusion** — mitigated structurally: `digital_quality_twin.py`'s every forward-looking field carries an explicit non-causation disclaimer, and Oracle hypotheses cannot reach `PRODUCTION_KNOWLEDGE` status without tier-2-or-above authorization plus recorded gate-check notes. Neither system can silently become a production recommendation.
- **Assuming "Director" or "Manufacturer" sign-off happened when it didn't** — per [HUMAN_OVERSIGHT_MODEL.md](./HUMAN_OVERSIGHT_MODEL.md), "Director" is not an independently enforced role (it collapses into `admin`'s ceiling) and "Manufacturer" is never an approval role at all, only a disposition label. A workflow that assumes these are distinct, verifiable sign-offs would be relying on something the system does not actually enforce as described — this document exists specifically to prevent that assumption from going unchallenged.
- **Assuming full 8-stage SPD workflow coverage** — only 4 of the 8 classically-named stages (receiving, inspection, packaging, supervisor review) have real tracked equivalents; treating cleaning/assembly/pre-sterilization-review as system-verified checkpoints would be a misuse of what the platform actually observes.

## Edge cases and unsupported scenarios (cross-referenced, not restated)

Osteotomes (not modeled at all), "wear" findings (taxonomized but never scored), superficial staining (only generic test coverage, not scenario-specific), and the Apollo-twin confidence gap are the concrete, named edge cases this review identified. See [INSTRUMENT_TAXONOMY.md](./INSTRUMENT_TAXONOMY.md), [FINDING_TAXONOMY.md](./FINDING_TAXONOMY.md), and [CLINICAL_VALIDATION_PLAN.md](./CLINICAL_VALIDATION_PLAN.md) for the full scenario-by-scenario breakdown.

## Overclaim safeguards — verified, not just asserted

`app/services/accreditation_engine.py` explicitly refuses to fabricate FDA submission data: *"Regulatory clearance status... must never be fabricated... If no `FDASubmissionTracker` rows exist for this tenant, the only honest response is an empty list."* `app/models/accreditation.py`'s own docstring: *"nothing here guarantees accreditation or claims regulatory approval / FDA clearance."* This review's own grep for overclaiming language across `app/` and `docs/` found no unhedged FDA-clearance or "clinically proven" claims — every hit was either an explicit non-claim disclaimer or a forward-looking statement of future intent (e.g., "upon successful completion of [study], LumenAI will proceed to FDA 510(k) submission" — a stated plan, not a present claim).

This repository's `CLAUDE.md` states the following non-negotiable constraints, confirmed still present and observed throughout this review:
> Never claim causation — always "potential association", "possible contributing factor", "quality review recommended". All correlation outputs must include `human_review_required: true`. Do NOT claim FDA clearance or regulatory approval anywhere in any document.
