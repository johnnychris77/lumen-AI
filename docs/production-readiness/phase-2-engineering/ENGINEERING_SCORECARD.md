# LPR-DIR-013 — Engineering Scorecard (Phase 2)

**Scale:** 0 (absent) – 5 (excellent). Scores are evidence-based (tool output +
inspection at `c9797b2`), not aspirational.

| Dimension | Score | Evidence / rationale |
|---|---|---|
| **Maintainability** | **3 / 5** | Avg complexity A(3.34), ~0 dead code, but one 10.5 kLOC god-module (SR-02) and helper duplication ×15–70 (SR-01) pull it down. |
| **Readability** | **4 / 5** | Lint-clean (ruff), consistent naming, purposeful docstrings; minor `routes/` vs `routers/` layering + `print()` inconsistency. |
| **Testability** | **4 / 5** | 3,696 tests / 8,404 asserts, 58% files with negative/authz tests, security subset 28/28; the god-module is the hard-to-test pocket. |
| **Dependency Health** | **3 / 5** | 0 Python CVEs, 0 Node CVEs, prod manifest fully pinned — but CI installs a mostly-unpinned divergent manifest (DH-01). |
| **Documentation** | **4 / 5** | 1,062 docs, actionable README/CLAUDE.md, intent-encoding docstrings; needs consolidation/index (DOC-02) and OpenAPI diff gate. |
| **Configuration** | **3 / 5** | Central frozen `Settings` + safe-default flags, SHA-256 secret storage — but ~199/215 env reads bypass it and no startup secret validation (CFG-01). |
| **Code Quality** | **4 / 5** | 0 TODO/FIXME, 0 bare excepts, ruff clean, low avg complexity; localized god-module + duplication are the deductions. |
| **Technical Debt** | **4 / 5** | No hidden Critical debt; markers are mostly domain vocab / honest disclosure; real debt is bounded and prioritized. |
| **Reliability** | **4 / 5** | Fail-closed paths explicit + test-verified, bounded startup retry, DR with measured RTO/RPO; ~70 silent excepts reduce observability (EH-01). |
| **Determinism** | **3 / 5** | Prod deps fully pinned, deterministic placeholder inference, `_seed`-based reproducibility — but CI unpinned manifest (DH-01) + config sprawl (CFG-01) inject non-determinism into the pipeline. |

## Aggregate

**Weighted engineering-integrity posture: 3.6 / 5 — "Good, with bounded,
mechanical conditions."**

- **Strengths (4–5):** readability, testability, code quality, documentation,
  reliability, technical-debt discipline.
- **Conditions (3):** maintainability, dependency health, configuration,
  determinism — every one traceable to a **specific, mechanical** fix (decompose
  one god-module, unify dependency manifests, route config through `Settings`,
  consolidate helpers). None requires architecture redesign.

No dimension scored ≤ 2. No dimension is blocked by a Critical engineering-integrity
defect.
