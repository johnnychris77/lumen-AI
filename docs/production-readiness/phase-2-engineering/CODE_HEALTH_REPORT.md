# LPR-DIR-013 — Code Health Report (Phase 2)

**Basis:** `radon cc` (cyclomatic complexity), `vulture` (dead code), `ruff`,
plus module-size measurement. Baseline `c9797b2`.

## Complexity

| Measure | Value |
|---|---|
| Blocks analyzed | 6,694 (classes/functions/methods) |
| **Average complexity** | **A (3.34)** — healthy |
| Rank distribution | Overwhelmingly A/B; D–F tail is localized |

**Worst offenders (rank D–F), by module:**

| Module | Notable functions (complexity) |
|---|---|
| `routes/enterprise_intake.py` | `get_enterprise_infection_prevention_review_packet` **F(66)**, three F(60) packet/PDF builders, F(57), F(49), E(40), E(37), E(35)×2 — ~25 functions D–F |
| `routes/digest_delivery.py` | `create_inspection` F(53) *(large orchestration handler)* |
| `routes/executive_digest.py` | `_build_digest` E(35) |
| `routes/pilot_analytics.py` | `pilot_executive_scorecard` D(25), `clinical_outcomes` D(24) |
| `routes/enterprise_dashboards.py` | `enterprise_executive_scorecard` D(27) |

The complexity tail is dominated by **report/packet/dashboard builders** — long,
branch-heavy assembly functions. They are not algorithmically subtle; the
complexity is *structural* (many optional sections). Decomposition into per-section
builders would drop each below the D threshold without behavior change.

## Function / class length

- No class flagged as a god-class (concentration is at module + runtime level).
- The longest functions are the F-rank packet builders above (hundreds of lines
  each). These co-locate with SR-02 (`enterprise_intake.py`) and are the primary
  function-length debt.

## Nesting

Deep nesting correlates with the D–F functions (branch-heavy section assembly).
No pathological nesting was found outside those builders; the average-A profile
confirms most functions are flat.

## Coupling / cohesion

- **Cohesion:** good at the service/route layer (`*_service.py` own domain logic,
  `routes/*` are mostly thin) — except the low-cohesion god-module
  `enterprise_intake.py`, which mixes many capabilities (governance packet, vendor
  escalation, IP review, export readiness, audit command center) in one file.
- **Coupling:** the Phase 1 dependency review found layered direction intact and no
  circular dependency in the validated pipeline; import-cycle detection is still not
  CI-gated (carryover AR-05). No new cycle surfaced in this pass.

## Duplication

Quantified in `STATIC_CODE_REVIEW.md` (SR-01): serialize/actor/tenant/time/export
helpers duplicated 15–70×. This inflates LOC and maintenance surface but keeps
behavior consistent (same helper repeated, not divergent).

## Dead code (vulture ≥80% confidence)

8 items total, and most are **not removable**:
- `connection` in `models/audit_log.py` SQLAlchemy event listeners — required
  callback signature parameter.
- `grant_type` (`routes/auth.py`), `barcode_id` (`routes/predictions.py`) —
  API-contract form/query fields intentionally accepted.
- 1 genuine `unreachable 'else'` in `services/benchmark_engine.py:784` and a few
  unused locals (`shared_by`, `acted_by`, `args`) — trivially removable.

**Net:** effectively **no meaningful dead code**. This is a strong health signal
for a 174 kLOC codebase.

## Maintainability index (qualitative)

Given avg complexity A, near-zero dead code, zero TODO/FIXME, and lint-clean
status, the **baseline maintainability is good**, dragged down in specific places
by (a) the `enterprise_intake.py` god-module and (b) helper duplication. Both are
mechanical, low-risk refactors — not redesigns.

## Health findings roll-up

| ID | Sev | Finding |
|---|---|---|
| CH-01 | MAJOR | Complexity tail concentrated in `enterprise_intake.py` packet builders (up to F/66) |
| CH-02 | MINOR | Long branch-heavy report/dashboard builders elsewhere (D/E rank) |
| CH-03 | OBSERVATION | No import-cycle / complexity gate in CI (carryover AR-05) |
| CH-04 | POSITIVE | Avg complexity A(3.34); ~0 real dead code; 0 TODO/FIXME; lint clean |
