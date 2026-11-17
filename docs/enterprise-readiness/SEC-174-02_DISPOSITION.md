# SEC-174-02 — Disposition Template

> **Provenance of the finding:** SEC-174-02 was first recorded in the **self-authored** PR #174 security review (produced by the same AI workflow that implemented the code). It is **not** an externally-sourced finding. Its technical facts below were re-verified against the code at head `d88c01a`, but the disposition decision belongs to an independent human reviewer.

**Status:** **OPEN** (undispositioned). This template collects the evidence; the final decision field is left for the human reviewer.

---

## 1. Finding description

Two services read raw retained-image bytes (`RetainedImage.image_bytes`) **without** routing through the centralized authorization gate (`assert_image_bytes_readable` / `may_read_image_bytes`) introduced in PR #174:

- `app/services/ml/training_eligibility_service.py` (`compute_training_eligibility`) — queries `RetainedImage` by annotation `retained_image_id` and assembles training samples that include `image_bytes`. The query is **not tenant-scoped** and applies **no `source` exclusion**.
- `research/lens_vision/data_loader.py` (`load_research_samples`) — loads research samples including `image_bytes`; it is tenant-scoped and passes through `authorize_research_entry`, but does **not** route through the central byte-access gate.

## 2. Severity

**Low** (as recorded). Rationale: both are **latent** — neither is reachable from any HTTP route today.

## 3. Affected code paths

| Path | Line (at `d88c01a`) | Concern |
|---|---|---|
| `app/services/ml/training_eligibility_service.py` | ~106 (`db.query(RetainedImage).filter(RetainedImage.id == ann.retained_image_id)`) | no tenant filter; no `source` exclusion; builds samples with `image_bytes` |
| `research/lens_vision/data_loader.py` | ~26 (`load_research_samples`) | reads `image_bytes` not via the central gate |

## 4. Evidence

- **Reachability (re-verified at `d88c01a`):** a repository search for route/pipeline callers of `compute_training_eligibility(` and `load_research_samples(` returns **no caller** in `app/routes/` or the research pipeline entrypoints — only a doc-comment reference to `compute_training_eligibility` in `experimental_dataset_generator.py`. Neither function is wired to an HTTP endpoint. → **not a live egress path today.**
- **No regression test** currently asserts gate enforcement or tenant scoping for these two functions.
- The central gate and its enforcement at live egress points are covered by `tests/test_sec17301_centralized_image_egress.py` (these two functions are explicitly out of that suite's scope).

## 5. Impact (if the latent condition were realized)

If either function were later wired to an HTTP endpoint (or invoked on untrusted input), research-image bytes could be read without the per-owner authorization + attestation check, and `compute_training_eligibility` could additionally read across tenants (no tenant filter). No current code path exposes this.

## 6. Remediation / risk-treatment options

- **Option A (gate — recommended):** route both functions' byte reads through `assert_image_bytes_readable` (or apply the `eligible_entries` source-exclusion pattern), and add a tenant filter to `compute_training_eligibility`'s `RetainedImage` query. **Acceptance criteria:** a regression test shows (a) research-source rows excluded from both functions' output, and (b) cross-tenant rows unreadable through `compute_training_eligibility`.
- **Option B (quarantine):** add an explicit guard that raises if either function is called in a request context, until gated. **Acceptance criteria:** a test shows the guard raises when invoked with a request-scoped caller.
- **Option C (formal risk acceptance):** the human reviewer records written acceptance that both functions remain unexposed, with a tracked action to gate them before any future exposure. **Acceptance criteria:** signed acceptance + a tracking issue referenced here.

## 7. Residual risk

With the finding open and unexposed: **Low** today. If any of the three options is applied: **negligible** for A/B; for C, residual risk is the governance risk that a future change wires these up without gating — mitigated by the tracked action.

## 8. Recommended disposition

**Option A** (gate + tenant filter + regression test) is the lowest-residual-risk closure and small in scope. Pending the human reviewer's decision, the finding stays **OPEN**. This recommendation is advisory from the implementing workflow and is **not** a closure.

---

## 9. Human reviewer decision (to be completed — DO NOT prepopulate)

| Field | Value |
|---|---|
| Reviewer name / org / role | |
| Independence declaration (non-author) | |
| Decision (Remediate A / Quarantine B / Accept C / Other) | |
| Rationale | |
| Required follow-up actions + owner | |
| Review date | |
| Disposition status (Open / Accepted / Closed) | |
| Signature or approved review-record reference | |

*No disposition is issued by this template. The finding remains OPEN until a qualified non-author reviewer records a decision above.*
