# LPZ-DIR-002 — Placeholder Isolation Policy

**Directive:** LPZ-DIR-002 — Security & Engineering Gate (Phase 8)
**Finding:** F8 — placeholder scorer indistinguishable from a validated model.

---

## Problem confirmed on this branch

`app/services/baseline_comparison_scoring_service.py` produces deterministic
scores from image features. Those scores were emitted **without a
machine-readable capability envelope** declaring them non-validated and
ineligible for Ground Truth or performance reporting. A downstream consumer
(export, dashboard, GT-approval path) had no structural signal distinguishing
a deterministic placeholder result from a trained-model result.

This is a Pilot Zero safety issue: the directive forbids representing the
placeholder scorer as trained computer vision.

## Policy (the contract this increment establishes)

`app/security/engine_capability.py` is the single source of truth for engine
capability. Every inference-engine result is governed by an
`EngineCapability` envelope carrying explicit, machine-readable flags rather
than letting consumers infer capability from the presence of a score.

**Maturity ladder** (least → most capable):

```
PLACEHOLDER → EXPERIMENTAL_MODEL → CANDIDATE_MODEL →
TECHNICALLY_VALIDATED_MODEL → PILOT_ELIGIBLE_MODEL → PRODUCTION_MODEL
```

**Placeholder envelope** (`placeholder_capability()`), fixed and restrictive:

| Field | Value |
|---|---|
| `engine_type` | `PLACEHOLDER` |
| `validation_status` | `NOT_VALIDATED` |
| `intended_use` | `research_and_engineering_only` |
| `human_review_required` | `True` |
| `clinical_use_permitted` | `False` |
| `ground_truth_eligible` | `False` |
| `performance_reporting_eligible` | `False` |

**Enforcement primitives:**

* `is_ground_truth_eligible(cap)` / `is_performance_reporting_eligible(cap)` —
  consumers must gate on these flags.
* `assert_not_placeholder_for_ground_truth(cap)` — a fail-closed guard that
  raises `ValueError` if a placeholder (or any non-GT-eligible) result is
  routed toward approved Ground Truth.

## What this increment delivers

* The capability contract, the placeholder declaration, and the guard
  (`app/security/engine_capability.py`).
* Tests pinning the restrictive envelope and the fail-closed guard
  (`tests/test_directive_002_placeholder_isolation.py`).

## What is explicitly deferred (increment 2+)

Per execution rule "do not do everything in one PR", the following are
**not** done here and are tracked as the next controlled increment:

1. Stamping every scoring result (`baseline_comparison_scoring_service` and
   any other scorer) with a `capability` block in its output payload.
2. Calling `assert_not_placeholder_for_ground_truth` inside the actual
   Ground Truth approval path.
3. Gating the performance-reporting aggregation on
   `is_performance_reporting_eligible`.
4. Surfacing the capability envelope in the result contract and UI disclosure.

Until (1)–(4) land, F8 is **structurally remediated (contract exists)** but
**not fully closed**. This is stated honestly in the findings register and the
progress report — the directive must not be marked complete on this basis.

## Non-negotiable claims (unchanged)

* No document or output may claim the placeholder is trained computer vision.
* No claim of FDA clearance, HIPAA, SOC 2, ISO 13485, IEC 62304, ISO 14971,
  or 21 CFR Part 11 compliance is made anywhere in this increment.
