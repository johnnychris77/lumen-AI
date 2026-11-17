# Independent Security Review — Instructions (LumenAI Research-Image Controls)

**Who may perform this review:** a qualified security engineer / auditor who **did NOT author the implementation** (PRs #171–#175) and is **not** the AI workflow that produced them. Confirming this independence is itself the closure condition for **SEC-175-01**. If you authored any of this code or the prior review documents, **stop** — you cannot perform this review.

**Scope:** the research-image security controls across PRs #171–#175. Mode is read-and-verify; you are not required to modify code. Data is synthetic only.

---

## 1. Access PRs #171–#175

- Repository: `github.com/johnnychris77/lumen-AI`.
- Pull requests: #171 (research ingestion), #172 (withdrawal/concurrency), #173 (migration + associations), #174 (centralized image-byte authorization), **#175** (audit durability + PG16 concurrency).
- PR #175 branch: `security/sec-174-01-audit-pg16-concurrency`; base `security/sec-173-01-centralized-image-egress`.
- Record the **current head SHA** of PR #175 yourself (it advances with each documentation commit) and scope your review to that SHA.

## 2. Inspect the complete stacked diff

```bash
git fetch origin
# Full research-image security delta from before PR #171 to PR #175 head:
git log --oneline origin/main..origin/security/sec-174-01-audit-pg16-concurrency
# Review each PR's diff individually, and the cumulative diff:
git diff origin/security/sec-173-01-centralized-image-egress...origin/security/sec-174-01-audit-pg16-concurrency
```
Key files: `backend/app/services/research_image_authorization_service.py`, `backend/app/routes/{ml_images,trc001_research,dataset_registry,inspections}.py`, `backend/app/services/baseline_image_library_service.py`, `backend/app/services/ml/dataset_builder.py`, `backend/app/db/migration_guards.py`, `backend/app/models/research_image_authorization.py`, `backend/research/lens_vision/{trc001_intake,scientific_authorization,data_loader}.py`.

## 3. Review the security findings register

Read `docs/enterprise-readiness/P3_SECURITY_REVIEW_HANDOFF.md` (evidence register + verification matrix + control architecture) and the committed evidence `P3_SECURITY_CLOSURE_EVIDENCE.md`. Treat all prior review documents as **self-authored** inputs to be independently re-verified, not as settled conclusions.

## 4. Verify the GitHub Actions results

For the PR #175 head you are reviewing, confirm all 7 checks are green on that exact SHA: Ruff, Secret scan, Backend tests (SQLite), **Backend tests (PostgreSQL 16)**, Dependency audit, Frontend build, enterprise-quality-gate. Open the **Backend tests (PostgreSQL 16)** job and confirm the pytest summary shows the PostgreSQL-gated tests **ran** (compare passed/skipped counts against the SQLite job — the PG16 job should show ~9 more passed / ~9 fewer skipped). Do not accept a prior run's SHA as evidence for a different head.

## 5. Execute the synthetic-data security tests

```bash
cd backend
rm -f test.db            # the local suite shares a persistent sqlite file; reset for a clean run
python -m pytest tests/test_sec17301_centralized_image_egress.py \
                 tests/test_sec17104_image_authorization.py \
                 tests/test_sec17401_denied_access_audit.py \
                 tests/test_trc001_provenance_migration.py \
                 tests/test_trc001_research_api.py tests/test_trc001_research_oidc.py -q
ruff check app tests
```
Expect all passed (PostgreSQL-gated tests skip on SQLite). Synthetic images only; do not ingest real images.

## 6. Verify PostgreSQL 16 concurrency evidence

Run the gated tests against a **real, isolated PostgreSQL 16** database (do not substitute SQLite):
```bash
# point DATABASE_URL at an isolated PostgreSQL 16 instance, then:
cd backend && python -m pytest tests/test_sec17401_pg16_concurrency.py \
                                tests/test_trc001_ingestion.py -q
```
Confirm the lock-contention tests assert real blocking via `pg_blocking_pids()` (not timing), and that withdrawal/revocation leave no stale authorization. Independently executing these (rather than relying on the authors' CI) is the strongest evidence and is encouraged.

## 7. Assess SEC-174-02

Use `docs/enterprise-readiness/SEC-174-02_DISPOSITION.md`. Independently confirm whether `compute_training_eligibility` and `load_research_samples` are reachable from any route, decide Remediate / Quarantine / Accept, and complete the decision table there. The finding stays **OPEN** until you record a decision.

## 8. Document SEC-175-01 completion

Record your independence declaration and review outcome in the **Reviewer decision** section of `P3_SECURITY_REVIEW_HANDOFF.md`. Completing that section by a verified non-author reviewer is what closes SEC-175-01. An AI workflow's self-review does **not** close it.

## 9. Submit a written review decision

Provide a written decision (PASS / CONDITIONAL PASS / FAIL / INSUFFICIENT EVIDENCE) with: the exact reviewed SHA, your independence declaration, per-finding dispositions (incl. SEC-174-02), residual-risk assessment, and integration + enterprise-pilot recommendations. File it as a PR review on #175 and/or a signed record referenced from the handoff document.

---

### Reminders
- Do not treat green CI as approval; green CI is necessary, not sufficient.
- Do not merge or deploy as part of the review.
- Owner attestation is a technical ownership assertion — confirm that institutional/IRB approval and expert ground-truth remain separate **organizational** controls, not inferred from the code.
- If you find a specific defect, report it precisely; only then should a further remediation cycle begin.
