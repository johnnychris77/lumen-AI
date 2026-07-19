# LPR-DIR-014 — AI Governance Security (Phase 3)

**Basis:** code inspection + `test_candidate_model_training`, promotion/ladder tests
at `f889d95`.

## Governance controls (verified)

| Control | Implementation | Evidence |
|---|---|---|
| Model registry | `ModelRegistryEntry` with `candidate_stage` ladder (Experimental→Candidate→Validated Candidate→Pilot→Production) + `artifact_checksum` | `models/model_registry.py` |
| Promotion gate | `candidate_promotion.py` / `deployment_gates.py` — stage advance requires satisfied checklist | `services/ml/*` |
| Dataset registry | `DatasetRegistryEntry` governs eligibility; leakage-safe splits | Phase 1 |
| Inference authorization | Inference behind auth/tenant; safe unavailable-model states | `ai/inference.py` |
| Human review | Human authoritative; AI cannot finalize | `test` human-review |
| Override workflow | Supervisor disposition/override recorded + audited | decision-engine |

## The three non-negotiable AI-safety invariants (validated)

1. **AI never finalizes decisions.** Model output is advisory; final disposition
   requires a human reviewer (boundary 9–10). No autonomous-close path surfaced.
2. **Unknown never becomes approved.** Unknown is a governed, non-approving outcome;
   the decision engine routes Unknown to escalation, not to PASS.
3. **Absence of finding never means clean.** The contamination-safety invariant
   (false-PASS remediation) ensures "no declared finding" is not treated as evidence
   of cleanliness; fail-closed decision states apply.

These are the core trust properties of a clinical inspection-intelligence platform
and they are **implemented and test-backed**.

## Honesty posture (verified)
- The live inference path is a **deterministic placeholder**, self-labeled in code
  ("INFERENCE MODE: deterministic placeholder active — not a trained CV model") and
  gated by safe unavailable-model states. No governed/certified model exists; **no
  diagnostic/clinical performance is claimed** — consistent with the program's
  "no claim without evidence" mandate.
- Confidence values are surfaced with disclosure, not as clinical certainty.

## Findings
| ID | Sev | Finding |
|---|---|---|
| SEC-AI-01 | MEDIUM | Dataset integrity: frozen dataset not lock-enforced (=SEC-DP-03/AR-17) — affects model-lineage reproducibility |
| SEC-AI-02 | OBSERVATION | Experiment registry is not yet a first-class record (planned); model lineage relies on registry + checksums |

**Positive:** the AI-authority guardrails (no final authority, Unknown ≠ approved,
absence ≠ clean), model-stage gating, checksum-pinned artifacts, and honest
placeholder disclosure are all present and test-verified. The only security-relevant
gap is dataset-freeze enforcement (shared with data protection).
