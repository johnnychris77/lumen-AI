# P4.5 — Enterprise Risk Register

**Scope:** open risks across the Stage 1–6D research + security integration (#176/#177/#178).
**No automatic risk acceptance.** Every "Accept" requires an authorized decision-maker's record.
Risks are typed: **[TECH]** technical defect, **[POL]** institutional policy gap, **[ASSURE]**
independent-assurance requirement.

## 1. Register

| ID | Type | Description | Sev | Likelihood | Affected | Consequence | Existing mitigation | Residual | Decision-maker | Closure evidence required | Status |
|----|------|-------------|-----|-----------|----------|-------------|---------------------|----------|----------------|---------------------------|--------|
| RK-01 | [POL] | RGI-01 institutional authorization not verified against a registry (only value-validated) | High | Med (if real data used) | research cohort build | Unauthorized/unverifiable cohort used for research | `cohort_readiness` value validation; real benchmarks BLOCKED | Med→Low while BLOCKED | Institutional research-governance authority | Approved registry policy + wiring, or documented risk acceptance | OPEN |
| RK-02 | [POL] | RGI-02 reviewer not authenticated/scope-bound (only structural sign-off) | High | Med (if metrics published) | scientific sign-off | Unauthorized/mis-scoped approval gates metrics | `valid_statistical_signoff`; publication BLOCKED | Med→Low while BLOCKED | Scientific-governance authority | Approved reviewer-registry policy + scope binding | OPEN |
| RK-03 | [POL] | RGI-10 empty-mask Dice/IoU convention (current 0.0 biases aggregates) | Med | N/A (no metrics published) | pixel metrics | Biased/incomparable published pixel metrics | Behaviour preserved; no metrics published | Low while BLOCKED | Scientific-methodology authority | Recorded a/b/c decision + aligned code/tests | OPEN |
| RK-04 | [TECH] | Legacy artifact-reference compatibility (RGI-04 hex change) | Med | **Very Low** (see §2 decision) | research artifact store | Pre-upgrade refs unreadable; legacy files orphaned (non-destructive) | No production caller; refs run-scoped; BLOCKED | Very Low | Release authority (on inventory evidence) | Pre-upgrade env inventory + offline re-key if any found | OPEN (conditional) |
| RK-05 | [ASSURE] | SEC-174-02 latent out-of-gate byte reads undispositioned | Low | Low (latent, no route) | `compute_training_eligibility`, `load_research_samples` | If later wired to a route: ungated/cross-tenant byte read | Latent; not reachable; documented criteria | Low | Independent non-author security reviewer | Disposition form completed (A/B/C) | OPEN |
| RK-06 | [ASSURE] | SEC-175-01 independent non-author review not performed | High (process) | Certain until done | whole stack | Release without independent assurance | Author + CI + Codex only (insufficient) | High until closed | Qualified non-author reviewer | Reviewer decision recorded in handoff + independence declaration | OPEN |
| RK-07 | [ASSURE] | Upstream research-stack Codex findings (#162–#169) are a **separate** open track, not fixed by #176/#177 | High | Certain (open) | #162–#169 research + ml services | Integrating the chain carries those P1/P2s | P4.2 triage documents them; not remediated here | High for chain integration | Research + security owners | Separate remediation + independent review of #162–#169 | OPEN |
| RK-08 | [TECH/ASSURE] | No real scientific benchmark executed (all BLOCKED pending governed data + licensed checkpoint) | N/A | By design | research benchmarking | No validated performance exists | Fail-closed BLOCKED gates | By design | Institutional + scientific authorities | Governed data + checkpoint + RK-01/02/03 closed | OPEN (by design) |
| RK-09 | [TECH] | Fresh-DB `alembic upgrade head` is Postgres-only (pre-existing DDL `d4e8a1c93f57`) | Low | Low | migration on non-PG engines | SQLite fresh migration fails (not used in prod) | Migrations target PG; CI PG16 runs them; single head | Low | Release authority | PG16 migration evidence (CI) | OPEN (pre-existing, informational) |

## 2. Legacy artifact-reference compatibility — decision record (RK-04)

**Change:** P4.3/RGI-04 replaced the artifact-store path/ref encoding from lossy plaintext
(`_safe_component`) to **injective hex**, closing a tenant-collision + path-traversal
vulnerability.

**Assessment questions (per Phase 5):**
1. **Do legacy artifacts exist?** **Repo-level inventory evidence [VF]:** `ResearchArtifactStore`
   is instantiated **only in tests** (all `tmp_path`); **no production/app caller**; no persistent
   config path binds it; **no committed `artifact://` data or heatmap files**; the research
   benchmark path is BLOCKED (no governed data / licensed checkpoint), so no run has persisted a
   heatmap. → *Code/config evidence says none exist.* **Limitation:** this is **repo evidence,
   not a live-environment filesystem inventory**; per the brief, "no artifacts exist" must be
   **confirmed by an environment inventory** before an upgrade relies on it.
2. **Do old references remain readable?** **No** — a pre-upgrade plaintext ref fails the hex-only
   guard in `resolve()` and returns `None` (verified by ad-hoc exerciser). Legacy on-disk files
   are **preserved (not destroyed)** but unreachable via the new scheme.
3. **Is the offline re-key reversible?** **Yes** — it reads each legacy plaintext file, verifies
   its stored `tenant_id`, and writes a hex-path copy; originals are left in place (or archived),
   so it is non-destructive and reversible (delete the hex copies to roll back).
4. **Tenant isolation preserved?** **Yes/strengthened** — re-key verifies the stored tenant and
   uses the injective hex path; distinct tenants cannot collide.
5. **Migration evidence required?** Only if (1)'s environment inventory finds artifacts; then the
   re-key run's before/after inventory is the evidence. Otherwise none.
6. **Release blocker?** **Not on its own for `main` integration**, **conditional** on a
   pre-upgrade **environment filesystem inventory** confirming no `artifact://`-scheme research
   artifacts exist in any target environment. If any are found, run the reversible offline re-key
   **before** upgrading that environment.

**Recommended disposition (advisory; authorized decision required):** proceed with RGI-04 as-is;
make a **pre-upgrade environment artifact inventory** a release checklist item; keep the offline
re-key script ready as the remedy. Do **not** add a plaintext fallback to `resolve()` (would
reintroduce the vulnerability). **Do not perform any production migration.**

**Decision record (DO NOT prepopulate):**
| Field | Value |
|---|---|
| Decision-maker (name / role) | |
| Environment inventory performed? (evidence ref) | |
| Artifacts found? (yes/no + count) | |
| Disposition (Proceed / Re-key first / Block) | |
| Conditions | |
| Date / signature | |

## 3. Risk-type summary
- **Technical defects [TECH]:** RK-04 (conditional), RK-09 (pre-existing/informational). No
  confirmed unresolved **P1 security** defect in code within P4.1/P4.3 scope.
- **Institutional policy gaps [POL]:** RK-01, RK-02, RK-03, RK-08 — require authorized
  institutional/scientific decisions; **no auto-acceptance.**
- **Independent-assurance requirements [ASSURE]:** RK-05 (SEC-174-02), RK-06 (SEC-175-01), RK-07
  (upstream chain review) — require a qualified non-author reviewer.
