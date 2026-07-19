# LPR-DIR-013 — Technical Debt Register (Phase 2)

**Basis:** keyword inventory over `backend/app` + contextual inspection of every
category. Classification: **Critical / Major / Minor / Future**. A raw keyword
count is not debt — each hit was read in context and reclassified as *real debt*
vs *domain vocabulary* vs *honest disclosure*.

## Keyword inventory (measured)

| Marker | Raw hits (app) | Real debt after inspection |
|---|---|---|
| TODO / FIXME / HACK / XXX | **0** | 0 |
| `deprecated` | 23 | 1 (audit shim); rest = domain enum/status values |
| `legacy` | 21 | ~2 (header-fallback / compat notes); rest = domain |
| `placeholder` | 54 | 0 hidden — all **honestly disclosed** inference/isolation states |
| `experimental` | 52 | 0 — all the model-registry stage ladder (domain enum) |
| `temporary` | 0 | 0 |
| `compat` | 0 | 0 |
| `shim` | 1 | 1 (deprecated `app.audit` → enterprise audit service) |
| `stub` | 11 | ~0 (test doubles / connector interfaces) |
| TODO/FIXME in tests | 0 | 0 |

**Key honesty point:** the large `placeholder`/`experimental` counts are **not
hidden debt**. `experimental` is the model-registry candidate-stage vocabulary
(`Experimental → Candidate → Validated Candidate → Pilot → Production`;
`experimental/pilot/validated/deprecated` approval stages). `placeholder` is the
deterministic-inference disclosure — the code literally logs
`"INFERENCE MODE: deterministic placeholder active — not a trained CV model"` and
documents it in `app/ai/inference_status.py`. This is disclosure, not concealment.

## Classified debt items

### Critical
**None.** No debt item permits cross-tenant exposure, audit bypass, evidence
corruption, unauthorized action, or false finalization. The security/governance
validation subset is green (28/28), fail-closed behavior is intact, and production
dependencies are fully pinned. (The one CRITICAL *architecture* finding, AR-15
webhook fail-open, is tracked in Phase 1 and is not an engineering-integrity/debt
item — it is a control gap scheduled for Phase 2 remediation.)

### Major

| ID | Item | Evidence | Why Major | Target |
|---|---|---|---|---|
| TD-01 | God-module `enterprise_intake.py` | 10,558 LOC, ~25 D–F funcs | Testability/maintainability hotspot | Phase 3 refactor |
| TD-02 | Utility duplication | `_row_to_dict`×66, `_actor`×57, `_tenant`×56, etc. | DRY; fix-does-not-propagate | Phase 3 |
| TD-03 | CI vs prod dependency-manifest divergence | Dockerfile installs pinned `requirements.txt`; CI installs mostly-unpinned `backend/requirements.txt` (7/27 pinned) | Determinism: CI tests ≠ shipped versions | Phase 2 |
| TD-04 | Config sprawl | central `Settings` exists but ~199/215 `os.getenv` reads bypass it (58 files) | Config drift; hard to audit | Phase 3 |
| TD-05 | Broad silent exception suppression | ~70 `except Exception: pass` (only ~10 log) | Observability; can mask failures | Phase 3 |

### Minor

| ID | Item | Evidence | Target |
|---|---|---|---|
| TD-06 | Deprecated audit shim | `app.audit.log_audit_event` (1 shim; emits DeprecationWarning, delegates to hash-chained writer) | Phase 2 (carryover B-01) |
| TD-07 | MD5 for non-security use | 29 bandit-High B324 (PRNG seed / cache / etag) — add `usedforsecurity=False` | Phase 3 |
| TD-08 | Logging inconsistency | 29 `print()` vs logging (some startup/seed, `# noqa` acknowledged) | Phase 3 |
| TD-09 | Formatter/type/dead-code not CI-gated | `ruff format`, `mypy`, `vulture` not in CI | Phase 2 (carryover AR-05) |

### Future
- Governed-aggregate Digital Twin, HA/scale characterization, ADR authoring —
  carried from Phase 1; not code-quality debt but tracked for continuity.

## Placeholder isolation (acceptance criterion)

Placeholder logic is **isolated and disclosed**: the deterministic inference path
is confined to `app/ai/inference.py` / `inference_status.py`, self-labels as "not a
trained CV model", and is gated behind safe unavailable-model states verified by
the Phase 1 candidate-model tests. No placeholder is presented as a trained/clinical
capability anywhere in code.

## Acceptance-criteria status

- ✓ No hidden Critical technical debt (0 TODO/FIXME; markers read in context).
- ✓ Duplicate business logic identified (TD-02 / SR-01, quantified).
- ✓ Dead code identified (vulture: 8 @≥80%, mostly framework params).
- ✓ Placeholder logic isolated (disclosed, gated).
- ✓ Technical debt prioritized (Critical/Major/Minor/Future above).
