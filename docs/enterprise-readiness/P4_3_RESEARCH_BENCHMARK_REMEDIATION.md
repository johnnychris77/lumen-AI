# P4.3 — Research Benchmark Integrity & Governance Remediation

**Date:** 2026-11-17 · **Branch:** `security/p4-3-research-benchmark-remediation`
(from `c111d93` = `origin/security/sec-173-01-centralized-image-egress`, **isolated from PR
#176**). **No merge. No deployment. No production migration. Synthetic data only.**

Remediates the confirmed research-benchmark defects (RGI-01…RGI-13) triaged in
`P4_2_RESEARCH_STACK_SECURITY_TRIAGE.md`. SEC-174-02 and SEC-175-01 remain **OPEN**. A green
CI run is necessary but is **not** a security approval, and no finding is closed by a passing
test alone.

---

## 1. Reviewed baseline (Phase 1)

| Item | SHA |
|---|---|
| `origin/main` | `0f2ec588` (unchanged; nothing from the stack reached it) |
| PR #164 head (Stage 5B) | `f4bdec5` |
| PR #168 head (Stage 6B) | `26c9260` |
| PR #174 head (P4.3 baseline) | `c111d93` |
| PR #176 head (P4.1 security) | `fdaee8e` |

**Baseline choice & isolation.** The research files at `c111d93` (#174) are **byte-identical**
to the stack tip, so `c111d93` carries the latest-integrated research code while remaining a
sibling of #176. P4.3 changes touch **only** `backend/research/lens_vision/*` and tests — **no
`app/`, no `alembic/`, no models** — so PR #176's security controls (all in `app/`) are not
weakened by construction, and migration integrity is unaffected.

**Findings reproducibility (verified against the tip, not just the review commit):** #168's
`cohort_readiness.py`/`checkpoint.py` are identical to the reviewed commit (findings verify
directly); #164's `anomaly_experiment.py`/`anomaly_localization.py` were rewritten downstream,
so each #164 finding was re-checked — several were already remediated and are not re-fixed.

---

## 2. Findings matrix & dispositions (Phase 5 classification)

| RGI | Finding | Classification | Action |
|-----|---------|----------------|--------|
| RGI-01 | Authorization satisfied by presence, not value | Confirmed (+ governance for registry) | Fail-closed value validation; registry resolution flagged as governance |
| RGI-02 | Sign-off by dict truthiness | Confirmed | Affirmative `approved is True` + reviewer + no revocation |
| RGI-03 | Scientific gate not in metric path; execution-only not forced non-scientific | Confirmed | Force execution-only policy non-scientific; derive eligibility in metric path; `require_scientific` hard gate |
| RGI-04 | Tenant-path collision + traversal in artifact store | Confirmed (P1) | Injective hex encoding, hex-only ref guard, atomic write |
| RGI-05 | Duplicate/repeat leakage trusts declared hash | Confirmed | Byte-derived SHA token; `repeat_of`→original linkage |
| RGI-06 | Unlabeled images pass ground-truth readiness | Confirmed | Split-based GT eligibility (fit/calibration require verified_normal) |
| RGI-07 | Readiness dimensions overlap | Confirmed (P2) | Authorization fields removed from `_REQUIRED_FIELDS` |
| RGI-08 | Localizer identity not validated vs config | Confirmed | `checkpoint_id` on localizers + mismatch raises |
| RGI-09 | Non-binary labels marked measured | Confirmed | `_binary_label` rejects out-of-domain labels |
| RGI-10 | Empty-mask Dice/IoU convention | **Requires scientific-methodology decision** | Documented; **behaviour unchanged** (see §4) |
| RGI-11 | AP tie order-dependence | Confirmed (P2) | Tied scores grouped (order-independent AP) |
| RGI-12 | Blanket `except` mislabels failures | Confirmed (P2) | Categorized exceptions; unexpected ones propagate |
| RGI-13 | Research-only guarantees overridable | Confirmed | `init=False` guarantee fields (AnomalyResult, AnomalyRegion) |

**Already remediated at tip (not re-fixed):** per-image→frozen calibration threshold, heatmap
persistence, mask-shape validation, NaN→"unknown" sentinel, Anomalib PaDiM/PatchCore
implementation, single-tenant enforcement at the fit boundary.

---

## 3. Implemented fixes (Phase 6) — file by file

- **`artifact_store.py` (RGI-04).** Replaced the lossy `_safe_component` (which stripped
  characters, so `a/b` and `ab` collided, and kept `.` enabling `..` traversal) with an
  **injective hex encoding** of each identity component; refs are hex-only and
  defense-checked (`_is_hex_component`) before touching the filesystem; writes are **atomic**
  (`tmp` + `os.replace`); cross-tenant resolve and stored-payload tenant checks preserved.
- **`cohort_readiness.py` (RGI-01/02/06/07/05).** Authorization fields removed from
  `_REQUIRED_FIELDS`; value validation (`_DATA_RIGHTS_GRANTED`, `_RETENTION_ACTIVE`) rejects
  `denied`/`purged`/unknown; `valid_statistical_signoff` requires affirmative approval +
  reviewer; ground-truth eligibility keyed on the **split**; `image_identity_tokens` links an
  original to its repeats (`repeat:<own_image_id>`).
- **`checkpoint.py` (RGI-03).** `research_execution_only=True` now forces the stored
  `compatibility_policy["scientifically_valid"] = False`.
- **`anomaly_experiment.py` (RGI-03/05/08/09/12).** Byte-derived `_effective_sha` identity
  token; localizer↔config `checkpoint_id` validation; checkpoint-derived
  `scientifically_eligible` + `scientific_metrics_published` + `technical_test` flags and a
  `require_scientific` hard gate in the metric path; `_binary_label` validation; categorized
  exception handling in `compare_localizers` (unexpected exceptions propagate).
- **`anomaly_localization.py` (RGI-08).** `checkpoint_id` identity on `AnomalyLocalizer`,
  `StubLocalizer`, and `_AnomalibLocalizer`.
- **`calibration.py` (RGI-11/10).** AP groups tied scores (order-independent); `dice_iou`
  carries the RGI-10 governance note (behaviour unchanged).
- **`anomaly_contract.py` / `anomaly_feasibility.py` (RGI-13).** Guarantee fields are
  `field(init=False)` — not caller-overridable.

**Security invariants preserved:** no clinical-performance claims; research-only outputs
unchanged; fail-closed everywhere; no fabricated authorization/approval records; no PR #176
`app/` controls touched; no retention-policy semantics changed (RGI-01 only tightens).

---

## 4. Findings requiring governance / scientific-policy decisions (STOPPED — not implemented)

1. **RGI-10 — empty-mask Dice/IoU convention.** Changing empty∩empty from `0.0` to perfect
   agreement (or excluding it) alters published-metric interpretation → **authorized
   scientific-methodology decision required**. Behaviour left unchanged; documented in code.
2. **RGI-01 — institutional-authorization registry.** Value validation is implemented;
   resolving `institutional_authorization_ref` against a **verified institutional
   authorization registry** (vs. accepting a well-formed reference) is an institutional
   governance decision. The canonical granted/active vocabularies are conservative defaults
   pending governance confirmation.
3. **RGI-02 — authorized-reviewer registry & scope binding.** The structural affirmative
   check is implemented; authenticating the reviewer against an authorized-reviewer registry
   and binding the sign-off to tenant/dataset/checkpoint/intended-use is enforced in the
   scientific-authorization layer and remains a governance item.

These are **not** closed and remain blocking where applicable.

---

## 5. Tests & results (Phase 6)

- **New regression suite** `tests/test_p4_3_research_benchmark_remediation.py` — **14 tests**
  covering RGI-01,02,03,04,05,06,07,08,09,11,13. **Failing-before-fix confirmed:** against the
  stashed pre-P4.3 source the module fails at import (the remediation APIs —
  `InvalidLabelError`, `LocalizerConfigMismatchError`, `valid_statistical_signoff`,
  `scientifically_eligible`, injective artifact encoding — do not exist in the baseline).
- **Updated existing tests** (encoded the old, now-corrected behaviour): `test_stage6b_corrections`
  (canonical affirmative sign-off), `test_stage5b_anomaly_localization` (technical-test
  flagging), `test_stage6a_benchmark` (authorization vs metadata dimension).
- **Research suites** (stage5b/5c/5d/6a/6b/6c/6d + project_lens): **114 passed, 6 skipped**.
- **Full backend suite** (fresh `test.db`): **4123 passed, 18 skipped** (exit 0, 465s).
- **Ruff** (`research/lens_vision app tests`): **All checks passed**.
- **Frontend build**: ✅ built.
- **Alembic / migration integrity:** P4.3 adds/alters **no** migration — integrity unchanged
  from baseline. (The `alembic heads` CLI error on this branch is the separate, pre-existing
  P4.1 **Finding #1** — eager `app.db.migration_guards` import — already remediated in PR #176;
  out of P4.3 scope.)
- **PostgreSQL 16:** P4.3 changes are pure-Python research logic with no DB/row-lock surface;
  the PG16-gated suite is unaffected and runs in CI's **Backend tests (PostgreSQL 16)** job.

---

## 6. Residual risk register

| ID | Residual risk | Status |
|----|---------------|--------|
| RR-01 | Institutional-authorization registry resolution (RGI-01) | OPEN — governance |
| RR-02 | Authorized-reviewer registry + sign-off scope binding (RGI-02) | OPEN — governance |
| RR-03 | Empty-mask metric convention (RGI-10) | OPEN — scientific methodology |
| RR-04 | No real scientific benchmark has run (all BLOCKED pending governed data + licensed checkpoint) | OPEN — by design |
| SEC-174-02 | Reachability disposition | OPEN |
| SEC-175-01 | Independent non-author review | OPEN |

---

## 7. Independent reviewer checklist

- [ ] Re-verify each RGI fix against the branch head; confirm no new P1 within scope.
- [ ] Confirm P4.3 touches no `app/`, `alembic/`, or model files (PR #176 controls intact).
- [ ] Run `tests/test_p4_3_research_benchmark_remediation.py` + full backend suite + Ruff.
- [ ] Confirm **Backend tests (PostgreSQL 16)** green on the PR head.
- [ ] Decide RR-01/RR-02 (governance) and RR-03 (scientific methodology) — these stay OPEN
      and blocking until an authorized decision is recorded.
- [ ] Confirm the reviewer is a **non-author** (closes SEC-175-01 only then).

---

## 8. Integration recommendation

**HOLD → remediation review gate.** P4.3 corrects the confirmed, in-scope research-benchmark
defects with fail-closed behaviour and regression tests, but: (a) RGI-10 and the RGI-01/02
registry layers require authorized governance/methodology decisions; (b) the fix sits on the
unmerged research+security stack; (c) no independent non-author review has occurred. **Do not
merge into `main` and do not authorize an enterprise pilot** until the governance decisions are
recorded and an independent reviewer signs off. SEC-174-02 and SEC-175-01 remain OPEN.

*No merges, deployments, production migrations, real-image ingestion, fabricated
authorizations/approvals, clinical claims, or self-issued approval. Stopped at the review gate.*
