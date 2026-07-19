# LPR-DIR-013 — Static Code Review (Phase 2)

**Basis:** direct inspection of implemented code at baseline `c9797b2` plus tool
runs (`ruff`, `radon`, `vulture`, `bandit`). Scope: `backend/app` (1,001 Python
files, ~174 kLOC), `backend/tests` (213 files, ~52.7 kLOC), `frontend/src`
(224 TS/TSX). **This directive changes no application code** — it reviews quality
and records findings for later change-controlled remediation.

## Summary metrics (measured)

| Metric | Value | Tool |
|---|---|---|
| App Python files / LOC | 1,001 / ~174,022 | `find`/`wc` |
| Avg cyclomatic complexity | **A (3.34)**, 6,694 blocks | `radon cc -a` |
| Lint | **All checks passed** | `ruff check` |
| Dead code (≥80% confidence) | **8 items** (mostly framework-required params) | `vulture` |
| TODO/FIXME/HACK/XXX in app | **0** | `grep` |
| Bare `except:` | **0** | `grep` |

Overall the code is **low-complexity on average and lint-clean**. The findings
below are concentrated in a small number of oversized modules and in repeated
utility helpers, not spread uniformly.

## Duplicate functions / repeated logic (measured, top-level `def`)

Copy-pasted small helpers reimplemented per-module rather than shared:

| Helper | Definitions | Nature |
|---|---|---|
| `_row_to_dict` | **66** | ORM row → dict serialization |
| `to_dict` / `_to_dict` | **71** combined | object serialization |
| `_actor` | **57** | resolve acting principal for audit |
| `_tenant` | **56** | resolve tenant scope |
| `_now` / `_now_iso` / `_utc_now` | **39** combined | timestamp |
| `_seed` | 24 | deterministic PRNG seed |
| `get_db` | 18 | session dependency |
| `_audit` | 16 | audit-write helper |
| `_truthy` | 15 | env/flag parsing |
| `_csv_text` / `_xlsx_bytes` | 19 combined | export rendering |

**Finding SR-01 (MAJOR) — utility duplication.** The same serialize / actor /
tenant / timestamp / export helpers are copy-pasted 15–70× across modules. Low
individual risk but a real maintainability and consistency cost (a fix to one copy
does not propagate). Recommend consolidating into a small shared `app/common/`
(serialization, actor/tenant resolution, time, export) in a later phase. Note the
`_actor`/`_tenant`/`_audit` duplication is *consistent* behavior repeated, not
divergent authority — the authoritative guards remain centralized (verified by the
Phase 1 auth/tenant tests), so this is a DRY debt, not a security defect.

## God modules / oversized modules (measured)

| Module | LOC | Worst functions (radon) |
|---|---|---|
| `routes/enterprise_intake.py` | **10,558** | F(66), F(60)×3, F(57), E(40), ~25 funcs rank D–F |
| `services/baseline_comparison_scoring_service.py` | 1,739 | mixed |
| `services/instrument_anatomy.py` | 1,590 | data-heavy taxonomy |
| `routes/executive_briefing_dashboard.py` | 1,382 | D(25) |
| `main.py` | 1,211 | app assembly |

**Finding SR-02 (MAJOR) — god-module `enterprise_intake.py`.** A single route
module of 10,558 lines concentrates ~25 D/E/F-complexity handlers (enterprise
packet/PDF/ZIP builders up to cyclomatic **66**). This is the dominant
maintainability and testability hotspot in the repository and the largest driver
of the complexity tail. Recommend decomposing by capability (governance packet,
vendor escalation, IP review, export readiness) into cohesive service modules with
thin route wrappers — a mechanical, behavior-preserving refactor for a later phase
under change control.

## God classes / god services

No single class dominates; the concentration is at the **module** level
(`enterprise_intake.py`) and the **runtime** level (one FastAPI app owns all
domains — carryover Phase 1 finding B-03/AR-01), not in individual classes. No
class exceeded a size that warranted a separate finding.

## Duplicate validation

Repeated inline validation (truthy parsing, tenant-id extraction, pagination
bounds) appears alongside the helper duplication above. Pydantic schemas provide
the authoritative request validation; the duplication is in small pre/post helpers,
folded into SR-01.

## Inconsistent naming / architecture

- Naming is broadly consistent (snake_case functions, `_private` helpers, `require_*`
  guards, `*_service.py` / `routes/*.py` layering).
- **Minor inconsistency:** both `app/routes/` and `app/routers/` exist, and several
  top-level `app/*.py` modules (e.g. `executive_decisions.py`, `portfolio_*.py`)
  sit outside the `routes`/`services` split. Recorded as OBSERVATION SR-03 — a
  layering-tidiness item, not a defect (imports resolve; tests pass).

## Utility abuse

No evidence of a "grab-bag" utility god-module; the opposite problem exists
(helpers duplicated rather than centralized — SR-01).

## Positives (evidence-backed)

- 0 TODO/FIXME/HACK, 0 bare excepts, ~8 dead-code items at high confidence.
- Average complexity A (3.34); the D–F tail is localized to `enterprise_intake.py`
  and a handful of analytics builders.
- Lint clean under the project standard (`ruff`).

## Findings roll-up

| ID | Sev | Finding |
|---|---|---|
| SR-01 | MAJOR | Utility helper duplication (serialize/actor/tenant/time/export) 15–70× |
| SR-02 | MAJOR | God-module `routes/enterprise_intake.py` (10,558 LOC, complexity tail) |
| SR-03 | OBSERVATION | `routes/` vs `routers/` + top-level modules layering tidiness |
