# LPR-DIR-027 — AI Governance Certification (Workstream 6)

Verification of AI-governance software controls present in IRC-1 (`5c22345`).

| Control | Evidence in IRC-1 | Certification |
|---|---|---|
| **AI advisory only** | Decision engine + inspection routes emit advisory outputs; causation guard / disclosure language in `app/ai/inference.py` (placeholder inference labeled "not a trained CV model"); no auto-disposition | ✅ **Present** (code) |
| **Mandatory human review** | `human_review_required: True` hard-set on the live result contract — `lumen_decision_engine.py:427`, `inspections.py:514`, `:529`, `:941` | ✅ **Present + enforced** (code) — every result requires human review |
| **Unknown handling** | `unknown_finding_service.py` + `observation_taxonomy.py`; unknown-finding → candidate-dataset learning loop; contamination safety fail-closed states | ✅ **Present** (code) |
| **Confidence reporting** | Confidence surfaced in scoring/result services (`veritas_baseline_matching_service.py`, `vulcan_reliability_score_service.py`, decision contract) | ✅ **Present** (code) |
| **Model registry** | `olympus_model_registry_service.py`; model-registry ML-lifecycle + artifact-integrity columns (migrations `bd866f763e40`, `b7c3d9f1a204`); model-card generation | ✅ **Present** (code) |
| **Promotion controls** | Candidate→Validated promotion ladder + deployment gates from ML-governance sprints; SHA-256-only API-key storage; artifact-integrity hashing | ✅ **Present** (code) |

## Determination

**AI-governance software controls are PRESENT and verifiable in IRC-1.** The system is
architected advisory-only with **mandatory human review enforced on every result**, honest
unknown handling with contamination fail-closed safety, confidence reporting, a model
registry, and promotion gates. No causation is claimed; no diagnostic authority is
asserted.

**Honest caveat:** these controls are **verified as software behavior**, not as governance
over a *trained, validated production model in clinical use* — the live path uses a
deterministic placeholder/feature baseline explicitly disclosed as **not a trained CV
model**, and no model has completed prospective clinical validation. So AI *governance
mechanisms* are certified present; AI *clinical performance* is **not** certified and is
out of scope for this entry gate. `human_review_required: true` remains mandatory on all
correlation/decision outputs.
