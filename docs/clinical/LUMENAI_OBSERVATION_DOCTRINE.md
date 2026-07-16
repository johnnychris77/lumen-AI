# LumenAI Observation Doctrine

This is the permanent operating philosophy for LumenAI's clinical reasoning
and inspection workflow, superseding any prior document that implied
LumenAI makes lab-confirmed identifications or diagnostic conclusions.

## What LumenAI does

LumenAI observes probable visual findings, measures deviation from an
approved baseline, evaluates evidence quality, applies the organization's
approved policy, recommends a next action, teaches and guides the
technician, and escalates ambiguous, high-risk, or policy-defined
exceptions to a supervisor.

## What LumenAI does not do

LumenAI does not make lab-confirmed identifications, diagnose exact
biological composition, certify cleanliness or sterility, autonomously make
irreversible decisions, override manufacturer instructions or
organizational policy, or replace technician/supervisor judgment.

## Section 1 — Observation Language

Every model-produced finding is described with probability-based, visually
descriptive language — never a confirmed-substance claim, never an age
estimate for organic material. The exact required phrases (implemented in
`app/services/observation_taxonomy.py::DISPLAY_LABELS`):

- Probable blood-like organic residue
- Probable dried organic residue
- Probable bone-like fragment
- Probable tissue-like organic residue
- Probable retained debris
- Probable corrosion-like surface degradation
- Probable rust-like discoloration
- Probable lint or fiber
- Probable plastic or insulation fragment
- Probable unknown foreign material
- No observable abnormality within the model's validated scope
- Image insufficient for evaluation

Permitted appearance attributes (visual description only, never a lab
conclusion): red, dark red, red-brown, dark brown, dried-appearing,
crusted, smeared, particulate, fibrous, adherent.

## Section 2 — Initial Observation Taxonomy

Exactly 10 categories are implemented (`observation_taxonomy.OBSERVATION_TAXONOMY`):
`probable_blood_like_residue`, `probable_bone_like_fragment`,
`probable_tissue_or_organic_residue`, `probable_retained_debris`,
`probable_corrosion_like_degradation`, `probable_lint_or_fiber`,
`probable_plastic_or_insulation_fragment`, `probable_unknown_foreign_material`,
`no_observable_abnormality`, `insufficient_image_quality`.

Categories the current deployed model has no real detection signal for at
all (currently: `probable_lint_or_fiber`) are always reported as
`NOT_EVALUATED_BY_CURRENT_MODEL` — never a fabricated zero probability.
This mirrors the pre-existing "unsupported categories" honesty contract in
`baseline_comparison_scoring_service._build_model_result()`.

## Section 3 — Three Result Layers

Every recommendation separates:

- **A. Observation** — what was probably seen (category, display label,
  confidence, status).
- **B. Assessment** — model confidence, model version, image quality,
  anatomy zone and its risk, baseline similarity/deviation/source/version,
  Digital Twin trend, evidence limitations, unsupported categories.
- **C. Policy + Recommendation** — the resolved organizational policy and
  an advisory, explainable recommended action, with a supervisor
  requirement that is never silently assumed.

Implemented as the Result Contract in `app/services/lumen_decision_engine.py`
and rendered as four distinct frontend panels
(`frontend/src/components/DecisionEnginePanel.tsx`) — see Section 15.

## Section 4 — Contamination Safety Rule

A high baseline similarity score must never cancel a probable contamination
observation. Example: 96% baseline similarity + a probable blood-like
observation still recommends "Reclean and reinspect," because the finding
was observed even though the overall instrument appearance remains similar
to baseline. This rule is enforced unconditionally in code
(`lumen_decision_engine._build_completed_contract`), not as configurable
policy data — no policy, however permissive, can cancel it. See
`test_lumen_decision_engine.py::TestContaminationSafetyRule` for the
regression test.

Routine probable contamination recommends recleaning without automatic
supervisor escalation. Supervisor involvement is required only when the
finding remains after recleaning, the material is unknown, evidence is
conflicting, the image is insufficient, applicable policy requires
approval, structural integrity is in question, or a repeated-failure
threshold is met — see `SUPERVISOR_ESCALATION_MODEL.md`.

## Section 17 — Safety and Legal Language

Preferred: probable, observed, visually consistent with, suspected,
requires review, recommended, baseline similarity, baseline deviation,
image insufficient. Avoided: confirmed blood, definitely contaminated,
sterile, safe for patient use, clinically cleared, guaranteed clean,
diagnosis, exact age of residue.

This wording reduces overstatement. It does not, by itself, eliminate
legal or regulatory risk — legal, clinical, and regulatory review is still
required before any customer-facing claim is made from this system's
output.

## See also

- `docs/decision-engine/LUMEN_DECISION_ENGINE.md`
- `docs/decision-engine/BASELINE_DECISION_POLICY.md`
- `docs/decision-engine/POLICY_RESOLUTION_HIERARCHY.md`
- `docs/decision-engine/SUPERVISOR_ESCALATION_MODEL.md`
- `docs/decision-engine/UNKNOWN_FINDING_LEARNING_LOOP.md`
- `docs/decision-engine/RECOMMENDATION_LANGUAGE_STANDARD.md`
- `docs/decision-engine/POLICY_SIMULATION.md`
