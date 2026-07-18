# LPA-DIR-011 — Candidate Model Execution Validation

**Purpose:** validate the candidate-model **execution path** at the engineering
level. **No production deployment; no clinical/diagnostic claim.** Candidate models
run only against approved/seeded Pilot Zero test datasets in a controlled research
environment; human review remains mandatory.

## Critical honesty statement

Per Directive 010, **no Directive-009-governed, readiness-certified candidate
model exists** and **no lab-acquired governed dataset exists**. Therefore this
phase validates the **execution contract and pipeline** (input validation →
inference path → output formatting → confidence → Unknown → human-review routing →
evidence linkage) exercised on **seeded test data** via the train→register→promote
API path. It does **not** report model accuracy, sensitivity/specificity, or any
diagnostic performance — those are out of scope and forbidden here.

## Verification (evidence: `test_candidate_model_training.py`, incl. API E2E)

| Item | Expected outcome | Observed | Status |
|---|---|---|---|
| **Input validation** | Only eligible/frozen data accepted; ineligible rejected | Eligibility gate enforced | ✅ Pass |
| **Inference execution** | Path runs; safe state when model unavailable | Train→infer path exercised; safe unavailable-model state | ✅ Pass (engineering) |
| **Output formatting** | Structured result contract, not free text | Result contract honored | ✅ Pass |
| **Confidence recording** | Confidence recorded; labeled model (not reviewer) confidence | Recorded per contract | ✅ Pass |
| **Unknown classifications** | Model may abstain; Unknown is a governed outcome | Unknown path preserved | ✅ Pass |
| **Human review routing** | Outputs route to mandatory human review; fail-closed | Routed; review authoritative | ✅ Pass |
| **Evidence linkage** | Model output linked into the evidence package + lineage | Linked to registry + evidence | ✅ Pass |
| **No production deployment** | `deployment_status` remains not-deployed | No deployment; governance state only | ✅ Pass |

## Boundaries

* **Registry-governed:** model entries carry artifact checksum + lineage + model
  card + governance flags (Directive 009); promotion honors the candidate-stage
  ladder with shadow/pilot-evidence gates.
* **Decision-support-only:** every output is advisory and human-reviewed; nothing
  is autonomous; contamination/safety-relevant outputs fail closed.
* **Not certified:** the exercised path is engineering validation on seeded data;
  a governed model against a certified dataset requires Directive 010 conditions
  C-2/C-3 and a future authorized experiment.

## Determination

**MODEL EXECUTION PATH VALIDATED (engineering level).** The candidate-model
input→inference→output→confidence→Unknown→human-review→evidence path operates
correctly on seeded data with fail-closed human review and no deployment. No
diagnostic performance is claimed or measured.
