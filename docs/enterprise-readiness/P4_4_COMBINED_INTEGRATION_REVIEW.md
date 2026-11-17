# P4.4 — Combined Integration Review & Release Decision

**Date:** 2026-11-17 · **Mode:** read-and-verify + isolated combined-integration validation.
**No merge into `main`. No deployment. No production migration. Synthetic data only.**

Technical completion is **not** governance authorization. A green CI run, automated (Codex)
review, and this (author) review are **not** independent approval. SEC-174-02, SEC-175-01,
RGI-01, RGI-02 and RGI-10 remain **OPEN**.

---

## 1. PR & branch topology

```
main (0f2ec588, unchanged)
 └─ … research stack #159–#169, #170 (Stage 6D, MERGED into #169 branch only) …
     └─ #171 → #172 → #173 → #174  security/sec-173-01-centralized-image-egress (c111d93)   ← common parent
         ├─ #176  security/p4-1-critical-findings-remediation   head fdaee8e   (P4.1 security)
         └─ #177  security/p4-3-research-benchmark-remediation   head b35e552   (P4.3 research)
```
- `merge-base(#176, #177) = c111d93` (= #174 head). Both PRs branch from the same parent.
- **Combined integration branch:** `p4-4-combined-integration` = **`7c0f679`** (local,
  validation-only; built as `c111d93` + merge #176 + merge #177). Source SHAs: #176 `fdaee8e`,
  #177 `b35e552`, parent `c111d93`.
- **Nothing is on `main`** (unchanged `0f2ec588`).

## 2. CI status (per-PR, current heads)

| PR | Head | Ruff | Secret scan | Backend (SQLite) | **Backend (PG16)** | Frontend | Dep audit | enterprise-quality-gate |
|----|------|------|-------------|------------------|--------------------|----------|-----------|--------------------------|
| #176 | fdaee8e | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| #177 | b35e552 | ✅ | ✅ | ✅ | ✅ (completed 19:24Z) | ✅ | ✅ | ✅ |

Both PRs: **all 7 checks green** on their current heads. (A green CI run is necessary, not
sufficient — not an approval.)

## 3. Artifact compatibility findings (Phase 1)

Independent exercise of the P4.3 tenant-scoped artifact store (`research/lens_vision/artifact_store.py`):

| Property | Result |
|---|---|
| New-format round-trip + tenant-scoped resolve | ✅ |
| Atomic write (tmp + `os.replace`), no leftover `.tmp`, complete JSON | ✅ |
| Cross-tenant resolve denied; collision (`a/b` vs `ab`) distinct, no cross-read | ✅ |
| Path traversal (`..` component / crafted `artifact://../..` ref) blocked, stays in `base_dir` | ✅ |
| Empty requesting tenant → fail-closed (`TenantAccessError`) | ✅ |
| **Legacy (plaintext) reference retrieval post-upgrade** | ❌ **BREAKING** — returns `None` |
| Legacy on-disk artifact files | **Preserved (not destroyed)**, but unreachable via the new hex scheme |

**Verdict — artifact compatibility: CONDITIONAL.** The security properties are correct, but the
RGI-04 fix changed the `artifact://` reference encoding from plaintext to injective **hex**, so
pre-upgrade references do not resolve and legacy on-disk artifacts are orphaned (non-destructively).

**Exact issue:** `resolve()` now requires hex-only ref components (traversal/collision defense);
a legacy `artifact://<plaintext_tenant>/<run>/<image>` ref fails the hex guard and legacy files
live at plaintext paths the new scheme never reads.

**Non-destructive remediation (proposed; not implemented — no artifacts exist):**
1. **Scope reality:** research artifact refs are **run-scoped** (produced and consumed within a
   single experiment run's result; not persisted across versions in a DB), and **all real
   benchmarks are BLOCKED** (no governed data / licensed checkpoint), so **no legacy artifacts
   exist** in any environment today → no migration required now.
2. **If any environment persisted research heatmaps:** run a one-time **offline re-key
   migration** — read each legacy `base_dir/<plaintext>/…json`, verify its stored `tenant_id`,
   and write it to the new hex path atomically, leaving originals in place (or archived). This
   is non-destructive and re-emits valid refs.
3. **Rejected:** a plaintext-legacy fallback inside `resolve()` — it would **reintroduce the
   RGI-04 collision/traversal vulnerability** on reads. Do not weaken `resolve()`.

## 4. Institutional governance decision package (RGI-01/02)
See `P4_4_INSTITUTIONAL_GOVERNANCE_DECISIONS.md` — authorization-record and reviewer-approval
schemas, verification controls, options/risks, recommended Option A (registry/ledger resolution
+ scope binding). **No approvals created; both OPEN and release-blocking for real data.**

## 5. Scientific methodology decision package (RGI-10)
See `P4_4_SCIENTIFIC_METRIC_METHODOLOGY.md` — four-case Dice/IoU analysis; only empty∩empty
(case 1) is contested; recommend **(b) exclude empty∩empty from the aggregate** (+ report
`n_masked_images`). **Implementation preserved (unchanged); OPEN and blocking for published
pixel metrics.**

## 6. Combined integration test evidence (Phase 5)

Environment: Python 3.11, local SQLite (`conftest` default) except where noted; branch
`p4-4-combined-integration` @ `7c0f679`. Commands and results:

| Check | Command | Result |
|---|---|---|
| Both remediation sets present | marker greps (P4.1 auth/OIDC/migration + P4.3 artifact/cohort/experiment) | ✅ both present |
| No security weakening | `grep "Bearer dev-token"` | only pre-existing `demo.py`/dashboard (untouched by either PR); no new |
| **Full backend suite (SQLite)** | `rm -f test.db && pytest tests/ -q` | **4131 passed, 19 skipped** (exit 0, 478s) |
| Focused: research-regression + authz/tenant + artifact + withdrawal/retention + migration | `pytest <16 targeted files> -q` (separate DB) | **197 passed, 11 skipped** |
| Ruff | `ruff check app research/lens_vision tests` | **All checks passed** |
| Migration head / history | `alembic heads` / `alembic history` | single head `f1a2b3c4d5e6`; 19-edge linear chain |
| Frontend production build | `npm run build` | ✅ built |
| Secret scan | (CI job) | ✅ green on each PR; combined runs in CI |
| Dependency audit | (CI job, report-only) | ✅ green on each PR |

**PostgreSQL 16 / deterministic concurrency (Finding D, SEC-174-01):** the 19 skipped *locally*
are PG16-gated (no PG16 instance in this environment) — not executed here. They executed
**green on #176 and #177 independently in CI**, and the **combined branch's PG16 ran GREEN in
CI** on validation PR **#178** (head `553c82c`, which carries combined code `7c0f679`): *Backend
tests (PostgreSQL 16)* **completed success** (2026-11-17 19:52:26Z, run 44160328620). All 7
combined-CI jobs are green (Ruff, Secret scan, Backend SQLite, Backend PG16, Frontend build,
Dependency audit, enterprise-quality-gate).

**Fresh-DB migration (`alembic upgrade head`):** Postgres-targeted. On SQLite it fails on a
**pre-existing** Postgres-only DDL (`d4e8a1c93f57`, GPAE `ALTER COLUMN … TYPE`) — untouched by
P4.1/P4.3 (0 occurrences in the integration diff), **not a P4.4 regression**. Fresh-DB migration
is validated against real PG16 in CI's **Backend tests (PostgreSQL 16)** job.

## 7. Remaining P1/P2 findings & residual risk register

| ID | Risk | Status |
|----|------|--------|
| RR-A1 | Artifact legacy-reference compatibility (RGI-04 encoding change) | OPEN — non-destructive re-key required only if artifacts exist (none today) |
| RR-01 | Institutional-authorization registry resolution (RGI-01) | OPEN — governance |
| RR-02 | Authorized-reviewer registry + scope binding (RGI-02) | OPEN — governance |
| RR-03 | Empty-mask Dice/IoU convention (RGI-10) | OPEN — scientific methodology |
| RR-04 | No real scientific benchmark has run (all BLOCKED) | OPEN — by design |
| SEC-174-02 | Reachability of training-eligibility / loader | OPEN |
| SEC-175-01 | Independent non-author review closure | OPEN |

No confirmed **P1 security** defect remains unresolved **in code** within P4.1/P4.3 scope (the
P4.2-confirmed research P1s are fixed by #177; the P4.1 image-auth P1s by #176). The remaining
blockers are governance decisions + independent review + legacy-artifact compatibility handling.

## 8. SEC-174-02 disposition requirements
An authorized reviewer must independently determine whether `compute_training_eligibility` /
`load_research_samples` are reachable from any route and record **Remediate / Quarantine /
Accept** in `SEC-174-02_DISPOSITION.md`. OPEN until recorded.

## 9. SEC-175-01 independent-review requirements
A **verified non-author** security reviewer (not this AI workflow, not the PR author) must review
PRs #171–#177 at their exact heads and record the decision per
`INDEPENDENT_SECURITY_REVIEW_INSTRUCTIONS.md`. Author/automated review does not close it.

## 10. Independent reviewer checklist (what a qualified non-author must inspect)
- [ ] Reproduce heads: #176 `fdaee8e`, #177 `b35e552`, parent `c111d93`; rebuild the combined
      branch and confirm **no conflicts** and **both remediation sets present**.
- [ ] Re-run: full backend suite, the 16-file focused subset, Ruff, frontend build; confirm the
      counts above.
- [ ] **Run Backend tests (PostgreSQL 16)** on the combined commit and confirm the Finding-D /
      SEC-174-01 concurrency tests execute (not skip) and pass.
- [ ] Independently re-verify the artifact store (collision/traversal/cross-tenant/atomic) and
      the legacy-reference handling decision.
- [ ] Decide RR-01/RR-02 (institutional governance) and RR-03 (scientific methodology); record
      dispositions — these stay OPEN and blocking until then.
- [ ] Record SEC-174-02 disposition and the SEC-175-01 independence declaration.
- [ ] Confirm no `app/`-layer security control weakened and no clinical/performance claim added.

## 11. Recommended merge order (when, and only when, all gates pass)
1. Resolve the research stack's own governance/review (the upstream #162–#169 Codex findings are
   a separate track — see P4.2; they are **not** fixed by #176/#177).
2. Integrate the research+security chain #159→…→#174 per the P4.2 plan.
3. Merge **#176** (security remediation) then **#177** (research remediation) — order is
   interchangeable (disjoint files, no conflict); both before any `main` integration.
4. Apply the legacy-artifact re-key migration **only if** any environment persisted research
   artifacts (none today).
5. Integrate to `main` **only after** all §12 gates are satisfied.

## 12. Release decision — GO / HOLD / NO-GO

**Overall: HOLD (NO-GO for `main` integration / enterprise pilot today).**

GO requires ALL of:
- [x] Required technical checks pass on the combined commit (SQLite full suite, Ruff, build,
      migration head) — **met locally**; **combined PG16 ran GREEN in CI on PR #178** (all 7 jobs green).
- [x] Confirmed P1 **security** defects resolved in code (P4.1 #176, P4.3 #177) — **met**.
- [~] Artifact compatibility demonstrated — **security met; legacy-reference handling is a
      documented conditional** (re-key only if artifacts exist).
- [ ] Institutional authorization (RGI-01) + reviewer verification (RGI-02) **approved by
      authorized decision-makers** — **NOT met (OPEN)**.
- [ ] Scientific methodology (RGI-10) **approved + documented** — **NOT met (OPEN)**.
- [ ] Required **independent non-author** reviews complete — **NOT met (OPEN; author/CI/Codex
      do not count)**.
- [ ] SEC-174-02 and SEC-175-01 **authorized dispositions** — **NOT met (OPEN)**.

Because governance decisions, independent review, and the SEC dispositions are OPEN, the
recommendation is **HOLD**. The technical remediation is review-ready; governance authorization
is not technical completion.

---

*No merges, deployments, production migrations, real-image ingestion, fabricated
authorizations/approvals, self-issued independent approval, or unapproved performance claims.
Stopped at the independent approval gate.*
