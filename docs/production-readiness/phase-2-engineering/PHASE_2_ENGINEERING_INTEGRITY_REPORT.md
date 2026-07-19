# LPR-DIR-013 — Phase 2 Engineering Integrity Report

Production Readiness Program · Phase 2 · Code Quality, Technical Debt & Engineering
Integrity · Baseline `c9797b2`.

## 1. Executive summary

This phase reviewed the **implementation quality** of the LumenAI repository against
implemented code and tool evidence — no architecture redesign, no new features, no
new APIs, no scope change, and **no application code modified** (documentation/
assessment only, consistent with the v1.0 architecture freeze; findings are queued
for later change-controlled remediation).

The implementation is **fundamentally sound**: average cyclomatic complexity
**A (3.34)** across 6,694 blocks, **lint-clean** (`ruff`), **~0 meaningful dead
code** (`vulture`), **0 TODO/FIXME/HACK**, **0 bare excepts**, **0 Python CVEs**
(`pip-audit`), **0 Node CVEs** (`npm audit`), a **fully-pinned production
dependency manifest**, and a **3,696-test / 8,404-assertion** suite whose
security/tenant/audit/evidence subset passes **28/28**.

Quality debt is **bounded, localized, and mechanical** — five MAJOR items, no
Critical engineering-integrity defect. The dominant items are one 10,558-line
god-module, copy-pasted utility helpers, a CI-vs-production dependency-manifest
divergence, configuration sprawl around a good central `Settings`, and broad silent
exception suppression in advisory paths.

**Exit decision: PASS WITH CONDITIONS.** No production deployment is authorized.

## 2. Static review

- Avg complexity **A (3.34)**; ruff clean; ~0 real dead code.
- **SR-01 (MAJOR):** utility duplication — `_row_to_dict`×66, `to_dict/_to_dict`×71,
  `_actor`×57, `_tenant`×56, `_now*`×39, export/audit helpers — copy-pasted, not
  shared. DRY/maintainability, not a security defect (authoritative guards remain
  centralized and test-verified).
- **SR-02 (MAJOR):** god-module `routes/enterprise_intake.py` (10,558 LOC, ~25 D–F
  functions, worst **F/66**) — the top maintainability/testability hotspot.
- SR-03 (OBSERVATION): `routes/` vs `routers/` + top-level module layering tidiness.

## 3. Technical debt

- **No hidden Critical debt.** 0 TODO/FIXME; keyword markers read in context are
  overwhelmingly **domain vocabulary** (model-stage ladder, baseline status) and
  **honest disclosure** (deterministic placeholder self-labeled "not a trained CV
  model"), not concealment.
- Major: TD-01 god-module, TD-02 duplication, TD-03 manifest divergence, TD-04
  config sprawl, TD-05 silent excepts. Minor: TD-06 audit shim, TD-07 MD5
  non-security use, TD-08 logging, TD-09 no format/type/dead-code gate.
- Placeholder logic is isolated, disclosed, and gated by safe unavailable-model
  states.

## 4. Dependency health

- `pip-audit`: **no known vulnerabilities**. `npm audit --omit=dev`: **0
  vulnerabilities**. Scanners (`pip-audit`, `npm audit`, `safety`, `bandit`) run in
  CI.
- **DH-01 (MAJOR):** the production image installs the fully-pinned root
  `requirements.txt`, but CI installs `backend/requirements.txt` with only **7/27**
  pinned — CI can validate against different versions than ship. Determinism gap.
- Minor/observation: no unused-dep scan, no container-image CVE scan, Actions not
  SHA-pinned, no license scan gated.

## 5. Testing

- 212 files, **3,696 tests**, **8,404 assertions**; 58% of files carry
  negative/authz (401/403) tests; 29 tenant-isolation, 83 audit.
- Live subset (auth, authz, tenant, audit-chain, evidence): **28 passed, 0 failed**.
- Gaps: no coverage % computed this phase (limitation), full suite not run this
  phase (subset method), and the god-module is the likely branch-coverage gap
  (TQ-02). Persistent `test.db` is an order-dependence footgun (TQ-03).

## 6. Configuration review

- Central **frozen `Settings`** with typed helpers and safe-default flags; secret
  API keys stored as **SHA-256 hash only**; secret-scan gated in CI.
- **CFG-01 (MAJOR):** ~199/215 env reads bypass `Settings` (58 files); no startup
  validation of required secrets — dovetails with Phase 1 AR-15.
- CFG-03 (MINOR): hard-coded bind host / tmp dir in CV utilities should be
  config-driven.

## 7. Documentation review

- 1,062 docs; actionable README + CLAUDE.md; runbooks + architecture set present;
  docstrings encode intent + honesty constraints; suppressions annotated with
  rationale.
- DOC-01 (MINOR) no OpenAPI CI diff gate; DOC-02 (MINOR) large corpus needs
  consolidation/index + ownership.

## 8. Engineering scorecard

Maintainability 3 · Readability 4 · Testability 4 · Dependency Health 3 ·
Documentation 4 · Configuration 3 · Code Quality 4 · Technical Debt 4 ·
Reliability 4 · Determinism 3 → **aggregate 3.6 / 5 ("Good, with bounded,
mechanical conditions").** No dimension ≤ 2. (`ENGINEERING_SCORECARD.md`.)

## 9. Critical findings

**None (engineering integrity).** No code-quality/debt defect permits cross-tenant
exposure, audit bypass, evidence corruption, unauthorized action, false
finalization, or unrecoverable data loss; fail-closed paths raise explicitly and
are test-verified (28/28), production deps are pinned, and there are no known CVEs.

*Cross-reference:* the **one CRITICAL finding in the program** is the Phase 1
architecture item **AR-15 / TB-02** (webhook fail-open → cross-tenant injection),
which is an architecture/control gap already tracked and scheduled for Phase 2
remediation — it is **not** an engineering-integrity/code-quality defect and is not
re-counted here. It remains release-blocking pre-production.

## 10. Major findings

| ID | Finding |
|---|---|
| SR-02 / TD-01 | God-module `enterprise_intake.py` (10,558 LOC, complexity to F/66) |
| SR-01 / TD-02 | Utility helper duplication (serialize/actor/tenant/time/export) 15–70× |
| DH-01 / TD-03 | CI installs mostly-unpinned `backend/requirements.txt`; prod installs pinned `requirements.txt` |
| CFG-01 / TD-04 | Config sprawl — ~199/215 env reads bypass central `Settings`; no startup secret validation |
| EH-01 / TD-05 | ~70 broad silent `except: pass` in advisory/analytics paths (observability) |

## 11. Recommendations

1. **Unify dependency manifests (DH-01)** — Phase 2, low effort, high determinism
   payoff: make CI install the pinned production manifest (or a pinned superset).
2. **Decompose `enterprise_intake.py` (SR-02)** — behavior-preserving split into
   per-capability service modules with thin routes; add branch tests as you split.
3. **Consolidate helpers (SR-01)** into a shared `app/common/` (serialization,
   actor/tenant, time, export).
4. **Route config through `Settings` + startup validation (CFG-01)** — align with
   the Phase 1 AR-15 remediation (require signing secrets at startup, fail closed).
5. **Narrow + log silent excepts (EH-01)**; standardize on the logger (EH-03).
6. **Activate CI gates:** `ruff format --check`, `mypy` (types present, ungated),
   `vulture`, import-cycle, coverage %, OpenAPI diff, container-image scan
   (TD-09/DH-05/DOC-01/CH-03 — several are carryover AR-05).
7. **Annotate non-security MD5 with `usedforsecurity=False` (TD-07)** to keep
   bandit signal clean and intent explicit.

None of these is a redesign; all are mechanical and change-controlled.

## 12. Phase 3 readiness

The codebase is **ready to proceed to Phase 3** with the five MAJOR conditions
carried as a tracked, prioritized backlog (recommendation order above), plus the
still-open Phase 1 architecture items (AR-15 CRITICAL release-blocking; AR-16/17/18
MAJOR). Entry conditions for Phase 3: (1) unify dependency manifests; (2) land the
Phase 1 AR-15 webhook remediation; (3) begin the `enterprise_intake.py`
decomposition; (4) stand up the missing CI quality gates. Phase 3 must not add
features, AI specialists, or scope, and must preserve the frozen architecture and
all fail-closed / tenant-isolation / audit-integrity invariants.

## Exit decision

**PASS WITH CONDITIONS.** Implementation quality is good and free of Critical
engineering-integrity defects; the five MAJOR conditions are bounded, mechanical,
and suitable for later phases under change control. **No production or clinical
deployment is authorized.**

## Validation commands & results

| Command | Result |
|---|---|
| `ruff check backend/app backend/tests` | **All checks passed** |
| `ruff format --check backend/app` | 854/999 would reformat → formatter not gated (TD-09) |
| `black --check backend/app` | 935/999 would reform → project standard is ruff, not black (tooling mismatch, not a defect) |
| `radon cc backend/app -a` | Avg **A (3.34)**, 6,694 blocks; D–F tail localized to `enterprise_intake.py` |
| `vulture backend/app --min-confidence 80` | 8 items (mostly framework-required params); ~1 real |
| `bandit -r backend/app` | 29 High (MD5 non-security), 10 Medium, 142 Low; SQL sites allowlisted+`# nosec` |
| `pip-audit -r requirements.txt` | **No known vulnerabilities** |
| `npm audit --omit=dev` (frontend) | **found 0 vulnerabilities** |
| `pytest` (auth/authz/tenant/audit/evidence subset) | **28 passed, 0 failed** |
| `mypy` | **not run** — not installed / not gated (limitation) |
| import-cycle / dead-code / coverage gates | **not gated in CI** (limitation, carryover AR-05) |

**Limitations:** full test suite and coverage % not computed this phase
(representative subset used); `mypy`/`vulture`/`radon`/`bandit`/`black` were
installed ad-hoc for this review (not in the committed dev manifest — DH-07);
bandit's MD5/B608 findings were characterized by inspection (non-security /
allowlisted), not merely by count.
