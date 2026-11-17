# P4.2 — Research Stack Security Triage & Controlled Integration

**Date:** 2026-11-17 · **Mode:** read-and-verify triage (no code changes, no merges).
**Scope:** the Stage 1–6D research/security PR stack (#159–#176) for safe integration into
`main`, incorporating the Codex findings on PRs #164 and #168 and the remediation in PR #176.

> A review submission, a ready-for-review status, and a green CI run are **necessary but
> not sufficient** — none of them is a formal security approval. SEC-174-02 and SEC-175-01
> remain **OPEN**. This document is a technical triage, not an approval.

---

## 0. Headline recommendation

**HOLD integration into `main`.** Confirmed, unresolved **P1** defects exist in the
integrated research code (PR #164 and #168 themes, verified against the stack tip), and the
entire stack is a single linear chain, so no part reaches `main` without carrying them. PR
#176's own CI is green and its targeted fixes verify, but it sits on top of the unremediated
research stack and has had **no independent human review**. No PR in the stack is
merge-ready **to `main`** today.

---

## Phase 1 — Verified Integration Matrix

### 1.1 Current `main`
`origin/main = 0f2ec588d24b7c64ccacd84adf67e89cb1ec1676` (unchanged by this stack).

### 1.2–1.5 Branch ancestry, merges, and what reached `main`

The stack is a **single linear chain** (each PR's base is the previous PR's head):

| PR | Stage | Head branch | Head SHA | Base (→ PR) | State |
|----|-------|-------------|----------|-------------|-------|
| #159 | Sci-evidence governance | docs/scientific-evidence-acquisition-v1 | 12d5ba5 | **main** | open |
| #160 | Stage 2 datasets | docs/dataset-qualification-stage2 | d1e884e | #159 | open |
| #161 | Stage 3 lab-evidence | docs/laboratory-evidence-protocol-stage3 | 03d8424 | #160 | open |
| #162 | Stage 4 provenance enforcement | feat/stage4-provenance-enforcement | a77412f | #161 | open (ready) |
| #163 | Stage 5A vision foundation | feat/stage5a-vision-research-foundation | ae193fe | #162 | open (ready) |
| **#164** | **Stage 5B anomaly localization** | feat/stage5b-anomaly-localization | f4bdec5 | #163 | open (ready) |
| #165 | Stage 5C scientific evidence | feat/stage5c-scientific-evidence | 5ca394d | #164 | open (ready) |
| #166 | Stage 5D instrument validation | feat/stage5d-instrument-validation | 8d119d3 | #165 | open (ready) |
| #167 | Stage 6A evidence benchmark | feat/stage6a-real-evidence-benchmark | 4776973 | #166 | open (ready) |
| **#168** | **Stage 6B real-image validation** | feat/stage6b-real-image-validation | 26c9260 | #167 | open (ready) |
| #169 | Stage 6C first benchmark | feat/stage6c-real-evidence-first-benchmark | 2003617 | #168 | open (**draft**) |
| #170 | Stage 6D real-instrument pilot | feat/stage6d-real-instrument-pilot | 77d96e3 | #169 | **MERGED 2026-11-17 17:31Z** (into #169 branch) |
| #171 | TRC-001 first real ingestion | trc-001-first-real-ingestion | 117e083 | #170 branch | open |
| #172 | SEC-171-01/02 owner revocation | security/sec-171-01-02-owner-revocation | 15fe228 | #171 | open |
| #173 | SEC-171-03/04 provenance migration | security/sec-171-03-04-provenance-migration | cc8a56b | #172 | open |
| #174 | SEC-173-01 centralized egress | security/sec-173-01-centralized-image-egress | c111d93 | #173 | open (**draft**) |
| **#176** | SEC-176 P4.1 remediation | security/p4-1-critical-findings-remediation | 66503d6 | #174 | open (**draft**) |

- **Merged into an upstream feature branch:** PR **#170 (Stage 6D)** is merged — but into
  `feat/stage6c-…` (the #169 branch), **not** `main`.
- **Reached `main`:** **nothing.** Every stack branch is a non-ancestor of `main`; the tip
  (#176) is **54 commits ahead** of `main`, none merged. `research_image_authorization_service.py`
  and the research code are absent from `main`.

### 1.6–1.7 Outstanding findings and which PRs carry unresolved P1/P2

Codex (chatgpt-codex-connector[bot]) completed automated code reviews on **#162–#168** after
they were marked ready-for-review (2026-11-17 ~18:12–18:22Z). Approximate finding counts
(badged by Codex; verified selectively below):

| PR | Codex findings (approx.) | Severity mix | Human review |
|----|--------------------------|--------------|--------------|
| #162 | ~9 | several P1 (provenance_governance consent/evidence/frozen-version; live_inference shadow/model-select) + P2 | none |
| #163 | ~9 | P1 (benchmark authz boundary, embedder identity, interpolation, model-card provenance, clinical consent) + P2 | none |
| **#164** | **13** | 8× P1, 5× P2 | none |
| #165 | ~13 | P1 (fit/calibration overlap, Anomalib map, backbone load, tenant path, reviewer evidence, clinical consent) + P2 | none |
| #166 | ~13 | P1 (tenant-path collision, single-token grouping, evidence binding, modality pooling) + P2 | none |
| #167 | ~10 | P1 (fit/calibration verified-normal, value validation, evidence, single-token leakage, PatchCore score) + P2 | none |
| **#168** | **8** | 7× P1, 1× P2 | none |
| #169 | not yet reviewed (draft) | — | none |
| #171 / #173 | reviewed earlier at 117e083 / cc8a56b (pre-P4.1) | fed into SEC-176 (#176) | none |
| #174 / #176 | not yet Codex-reviewed (draft) | — | none |

**Unresolved P1 or P2 defects: every ready PR #162 through #168.** The security PRs
#171–#174's earlier findings are addressed by #176 (see Phase 3); #176 and #174 have not been
automated-reviewed (draft). No PR in the stack has a human security approval.

---

## Phase 2 — Research Findings Triage (PR #164 and PR #168)

**Method.** Each finding was re-verified against the **stack tip** (the most-integrated
state, present in the working tree at `66503d6`), not only the original review commit — per
the task's explicit caution. Key fact:

- **#168 files** (`cohort_readiness.py`, `checkpoint.py`) — tip is **byte-identical** to the
  reviewed commit `26c9260`. Findings verify directly.
- **#164 files** (`anomaly_experiment.py`, `anomaly_localization.py`) — tip has **changed
  substantially** (≈371 insertions / 147 deletions) since reviewed commit `f4bdec5`;
  downstream stages (5C–6B) rewrote them. Each #164 finding was therefore re-checked against
  the rewritten tip. `anomaly_contract.py` is unchanged.

### 2.1 PR #164 (Stage 5B) — verified against tip

| # | Finding (theme) | File:line (tip) | Classification |
|---|-----------------|-----------------|----------------|
| 164-a | Single-tenant not enforced before fit | anomaly_experiment.py:148,158 | **Already remediated** — `assert_research_authorized` + `enforce_supplied_dataset_governance` (no cross-tenant mixing) now gate the boundary |
| 164-b | Per-image threshold leaks test distribution | anomaly_experiment.py:196,215 | **Already remediated** — dedicated calibration set + `fit_frozen_threshold`, frozen, applied to all held-out |
| 164-c | Heatmap reference published but not persisted | anomaly_experiment.py:217-220 | **Already remediated** — `artifact_store.store_heatmap(...)`; ref is `""` when no store |
| 164-d | Mask-shape mismatch silently truncates | anomaly_experiment.py:247-249 | **Already remediated** — `validate_mask(width,height)` excludes malformed masks |
| 164-e | `NaN` uncertainty breaks strict JSON | anomaly_contract.py:23,53 | **Already remediated** — `"unknown"` sentinel, no `float("nan")` |
| 164-f | PaDiM/PatchCore permanent `NotImplementedError` | anomaly_localization.py:130-191 | **Already remediated** — real `_AnomalibLocalizer` (Padim/Patchcore) implemented; execution BLOCKED only by the governed optional-dependency gate |
| 164-g | Localizer identity not validated vs config | anomaly_experiment.py:137-186 | **Confirmed & unresolved** — `run_anomaly_experiment` fits the supplied `localizer` but never checks its name/checkpoint against `config`; result records config's digest → misattribution risk once a real backend runs |
| 164-h | Duplicate-image leakage trusts `image_sha256` field | anomaly_experiment.py:48-53 | **Confirmed & unresolved (residual)** — token derived from the declared field, not computed from bytes; empty/stale hash ⇒ no `img:` token. Mitigated when other physical identities (specimen/session/instrument) are present; flagged via `grouping_limitations` when absent |
| 164-i | Non-binary labels marked "measured" | anomaly_experiment.py:236,255 | **Confirmed & unresolved** — `int(label)` accepts any value; `len(set)>1` lets `[0,2]` report measured metrics |
| 164-j | Empty/empty mask scored as total miss | calibration.py:`dice_iou` | **Confirmed & unresolved (P2)** — returns `0.0/0.0` for empty∩empty, depressing the mean over true-normal images |
| 164-k | AP tie-handling order-dependent | calibration.py:`average_precision` | **Confirmed & unresolved (P2)** — ties ranked by input order; identical predictions can yield different AP |
| 164-l | Blanket `except` → "blocked" | anomaly_experiment.py:317 | **Confirmed & unresolved (P2)** — `compare_localizers` converts any failure (leakage, governance, bug) into a dependency-`blocked` result |
| 164-m | Research-only guarantees overridable | anomaly_contract.py:60-63 | **Confirmed & unresolved** — `research_only`/`clinical_promotion_eligible`/`confirmed_diagnosis`/`human_review_required` are plain init fields; class not frozen ⇒ direct construction can violate the contract (the experiment path itself never overrides them) |

### 2.2 PR #168 (Stage 6B) — verified against tip (identical to review)

| # | Finding (theme) | File:line | Classification |
|---|-----------------|-----------|----------------|
| 168-a | Authorization validated by presence, not value | cohort_readiness.py:110-112 | **Confirmed & unresolved / governance** — `data_rights="denied"`, `retention_status="purged"` pass (non-empty only) |
| 168-b | Statistical sign-off by dict truthiness | cohort_readiness.py:219,223 | **Confirmed & unresolved / governance** — `{"approved": false}` counts as approval |
| 168-c | Unlabeled images pass ground-truth readiness | cohort_readiness.py:118-119 | **Confirmed & unresolved** — only blocked when `intended_use == "normal_training"`; omit it and unlabeled fit/calibration passes |
| 168-d | `repeat_of` not linked to original's token | cohort_readiness.py:81-85 | **Confirmed & unresolved** — only the repeat gets `repeat:<orig>`; the original image_id gets no matching token (mitigated when they share specimen/instrument/sha) |
| 168-e | Checkpoint evidence by truthiness | checkpoint.py:189,195-196 | **Confirmed & unresolved / governance** — any non-empty `license_evidence_ref`/`source_evidence_ref`/`approver_id` sets `rights_cleared` + `scientific_use_approved`; no record resolution or approver authentication |
| 168-f | `research_execution_only` doesn't force non-scientific policy | checkpoint.py:191-193,202 + anomaly_localization.py:155 | **Confirmed & unresolved** — `scientific_use_approved=False` is set, but the stored `compatibility_policy` is not forced non-scientific, and `_AnomalibLocalizer` defaults `backbone_scientifically_valid=True` |
| 168-g | Readiness dimensions not independent | cohort_readiness.py:50-59,95-112 | **Confirmed & unresolved (P2)** — `_REQUIRED_FIELDS` ∩ `_AUTHORIZATION_FIELDS` ⇒ missing authz trips both `metadata_completeness` and `verified_authorization` |
| 168-h | Scientific-use gate not in metric path | checkpoint.py:210 / scientific_authorization.py:481 | **Partially remediated** — `assert_scientific_checkpoint` now exists **and is called** from `scientific_authorization.py:481`; however `run_anomaly_experiment` and `generate_cohort_readiness_report` do **not** call it (the latter takes `scientific_checkpoint_approved` as a caller-supplied bool). Residual unless callers always route through the authorization resolver |

### 2.3 Classification summary

- **Confirmed & unresolved:** 164-g, 164-h, 164-i, 164-j, 164-k, 164-l, 164-m; 168-c, 168-d,
  168-f, 168-g, 168-h (residual). (12)
- **Requires governance decision** (defines what counts as valid authorization/approval —
  a policy call, not a pure code bug): 168-a, 168-b, 168-e (and the "value validation" aspect
  of 164-h/168-c). These must not be "closed" by code alone.
- **Already remediated at tip:** 164-a, 164-b, 164-c, 164-d, 164-e, 164-f. (6)
- **Not reproducible / insufficient evidence:** none outright dismissed; items marked
  remediated were confirmed by reading the tip code.

> **Cross-cutting (raised on #165/#166, still open):** `artifact_store` tenant-path
> `_safe_component` collision (distinct tenants collapsing to one directory) is a **Confirmed
> P1 tenant-isolation** gap at a different layer than 164-a, and remains open.

---

## Phase 3 — PR #176 Verification

- **Head SHA:** `66503d6adf629be1cfcf0d1cafc7f63068dd8974` (base `security/sec-173-01-…` `c111d93`).
- **CI (run 44146043444, on `66503d6`): all 7 checks green.**

| Check | Conclusion |
|---|---|
| Ruff (backend) | ✅ success |
| Secret scan | ✅ success |
| Backend tests (SQLite) | ✅ success |
| **Backend tests (PostgreSQL 16)** | ✅ success (completed 18:26:31Z — the Finding-D `pg_blocking_pids` gated test ran) |
| Dependency audit (report-only) | ✅ success |
| Frontend build | ✅ success |
| enterprise-quality-gate | ✅ success |

- **Regression evidence (local, P4.1):** new `test_sec176_critical_findings_remediation.py`
  (8 SQLite + 1 PG16-gated); full backend suite **4117 passed / 19 skipped**; proven genuine
  (6/8 fail against pre-fix source).
- **Review findings on #176:** **none** — no Codex review (it is a draft; Codex triggers on
  ready-for-review) and **no human review**.
- **Remaining security risks on #176 itself:** low for its own diff (narrow, fail-closed,
  invariant-preserving). But #176 is stacked on the **unremediated research stack**, so
  merging it anywhere upstream of `main` carries the Phase-2 P1s. #176 does **not** touch the
  research-benchmark files (`anomaly_experiment.py`, `cohort_readiness.py`, `checkpoint.py`),
  so it neither fixes nor regresses those findings.
- **Compatibility:** #176's changes (app startup registration, lazy migration-guard imports,
  OIDC 401, per-owner retrieval/retention) are orthogonal to the research code; green CI on
  the full stacked tree confirms compatibility.

**PR #176 is NOT merged and must not be merged here.**

---

## Phase 4 — Security Governance & Risk Register

### 4.1 Governance status (unchanged — no authoritative closure evidence)

- **SEC-174-02** — OPEN. No independent reachability decision recorded.
- **SEC-175-01** — OPEN. Requires a verified **non-author** reviewer; the SEC-176 fixes were
  authored by this AI workflow and **cannot be self-approved**.

### 4.2 Distinction of states (do not conflate)

1. **Technical remediation** — code written + tests green (e.g., SEC-176 on #176). ✔ for #176's scope.
2. **Automated review** — Codex findings (advisory, must be verified). Present for #162–#168.
3. **Human security approval** — a qualified non-author sign-off. **Absent everywhere.**
4. **Formal governance closure** — SEC-174-02 / SEC-175-01 disposition. **Not met.**

### 4.3 Consolidated risk register (verified P1/P2)

| ID | Risk | Loc | Sev | State | Required action |
|----|------|-----|-----|-------|-----------------|
| R-01 | Authorization/rights validated by presence not value | cohort_readiness, checkpoint | P1 | Confirmed/governance | Validate allowed states + resolve evidence records; **governance decision** on valid values |
| R-02 | Statistical/scientific sign-off by truthiness | cohort_readiness:223, checkpoint:189 | P1 | Confirmed/governance | Require affirmative field + authenticated reviewer |
| R-03 | Unlabeled images pass ground-truth / fit-calibration readiness | cohort_readiness:118 | P1 | Confirmed | Treat fit/calibration split as requiring `verified_normal` |
| R-04 | Tenant-path collision in artifact store | artifact_store.py | P1 | Confirmed | Injective/hashed tenant path component |
| R-05 | Localizer identity not validated vs config | anomaly_experiment.py | P1 | Confirmed | Reject localizer/config mismatch before fit |
| R-06 | Byte-hash not enforced (duplicate-image leakage) | anomaly_experiment, dataset_registry | P1 | Confirmed/residual | Compute digest from bytes or fail closed |
| R-07 | Consent/evidence not re-validated / not bound to entry | provenance_governance.py (#162), governance.py | P1 | Confirmed | Re-check rights at cohort build; bind evidence to entry |
| R-08 | Research-only contract overridable | anomaly_contract, anomaly_feasibility | P1 | Confirmed | Non-init/frozen guarantee fields |
| R-09 | Scientific-use gate not enforced in metric path | checkpoint/experiment | P1 | Partially remediated | Invoke gate inside metric-producing path |
| R-10 | Non-binary labels / AP ties / empty-mask metric errors | anomaly_experiment, calibration | P2 | Confirmed | Validate labels; group ties; define empty∩empty |
| R-11 | Readiness dimensions not independent | cohort_readiness:50-59 | P2 | Confirmed | Separate required-metadata from authorization fields |
| R-12 | Blanket `except` misattributes failures to "blocked" | anomaly_experiment:317 | P2 | Confirmed | Catch only dependency/checkpoint errors |
| SEC-174-02 | Reachability of training-eligibility / loader | — | — | OPEN | Independent decision |
| SEC-175-01 | Independent review closure | — | — | OPEN | Non-author sign-off |

---

## Phase 5 — Controlled Integration Recommendation

Intended target: **`main`**. The stack is linear, so `main` can only receive the chain head
(or a squash of it); any integration carries every upstream PR's state.

### 5.1 Genuinely merge-ready **to `main`** today
**None.** Every ready PR (#162–#168) carries confirmed, unresolved P1 defects in the
integrated code.

### 5.2 Blocked by confirmed defects
**#162, #163, #164, #165, #166, #167, #168** (and therefore everything stacked above them:
#169, #171–#174, #176). Per the rule *"if a P1 finding affects the intended integration
target, recommend HOLD"* → **HOLD** on integration to `main`.

### 5.3 Requiring targeted remediation (research findings R-01…R-12)
The research-benchmark P1/P2s (Phase 2) need a dedicated remediation cycle — analogous to
SEC-176 but for `cohort_readiness.py`, `checkpoint.py`, `anomaly_experiment.py`,
`anomaly_contract.py`, `artifact_store.py`, `provenance_governance.py`, `governance.py`.
Several (R-01, R-02, R-05-value-semantics) require a **governance decision** first.

### 5.4 Requiring independent human approval
**All** of #162–#176. SEC-175-01 is closed only by a verified non-author reviewer; the
SEC-176 author (this workflow) cannot self-approve. SEC-174-02 needs an independent
reachability decision.

### 5.5 Minimum verification before any integration into `main`
1. Remediate (or formally risk-accept, with recorded governance decisions) **all confirmed
   P1s** R-01…R-09 and the tenant-path R-04.
2. Re-run Codex (or a human reviewer) on the remediated heads; confirm no unresolved P1.
3. Green CI on each integrated head **including Backend tests (PostgreSQL 16)**.
4. Independent **non-author** security sign-off (closes SEC-175-01) and a recorded SEC-174-02
   disposition.
5. Confirm topology at merge time (the chain is linear and `main` is unchanged; a squash or
   an ordered fast-forward, never a force-push over shared history).

---

## 6. GO / HOLD / NO-GO per affected PR

| PR(s) | Recommendation | Rationale |
|-------|----------------|-----------|
| #159–#161 (docs/governance) | **HOLD** (low intrinsic risk) | No code defects identified, but they are the base of a chain that is on HOLD; may integrate first **only** if cleanly separable and independently reviewed |
| #162 | **HOLD** | Confirmed P1s in `provenance_governance.py` / `live_inference_adapter.py` (consent re-validation, evidence binding, frozen-version mutation, shadow abstention) |
| #163 | **HOLD** | Confirmed P1s (benchmark authz boundary, embedder identity, clinical consent, model-card provenance) |
| **#164** | **HOLD / targeted remediation** | 7 confirmed-unresolved findings at tip (R-05,R-06,R-08,R-10,R-12); 6 already remediated downstream |
| #165, #166, #167 | **HOLD** | Confirmed P1s incl. tenant-path collision (R-04), single-token leakage, evidence binding, clinical consent |
| **#168** | **HOLD / governance + remediation** | 7×P1 value-vs-presence/truthiness + 1×P2; R-01,R-02,R-03,R-09 need governance decisions |
| #169 (draft) | **HOLD** | Not yet reviewed; draft |
| #171 | **HOLD** | Carries all upstream research P1s; research ingestion path |
| #172, #173, #174 | **HOLD** | Security hardening, but stacked on unremediated research code; #174 draft |
| **#176** | **HOLD (do not merge)** | Own CI green incl PG16 and fixes verify, **but** no independent review (SEC-175-01 open), self-authored, and stacked on the unremediated stack |

**Overall: NO-GO for `main` integration of the stack as-is; HOLD pending (a) research-finding
remediation + governance decisions and (b) independent non-author security approval.**

---

## 7. Restrictions honored

No merges, no deployments, no production migrations, no real research-image ingestion, no
fabricated approvals, no self-issued independent sign-off, no unrelated feature development,
no findings closed without evidence, **no code modified** during this triage. Synthetic data
only. No FDA/regulatory clearance claimed. Work stops at the integration decision gate.
