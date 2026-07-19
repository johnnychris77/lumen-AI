# LPR-DIR-012 — Phase 1 Architecture Review Report

## 1. Executive summary

Production Readiness Program **Phase 1 — Foundation** froze the LumenAI Version 1.0
architecture and reviewed every material subsystem against **implemented code** at
baseline `c9797b2` (147 models, 489 services, 205 route modules / 1,912 endpoints,
13 migrations, 212 backend test files, 9 ADRs, 11 CI workflows). Validation executed
this phase: **186 tests passed, 0 failed**; `ruff` clean; endpoint inventory
**0 UNKNOWN**, 10 unauthenticated writes (all PUBLIC_BY_DESIGN).

**Architecture decision: ARCHITECTURE FROZEN — PASS WITH CONDITIONS.** The
safety-critical *internal* architecture (auth, tenant isolation, authorization,
audit chain, evidence integrity, human authority) is coherent and test-verified.
PR review surfaced **one CRITICAL finding at the external-integration edge**
(AR-15/TB-02 — webhooks fail open, permitting cross-tenant injection when a signing
secret is unset), plus three MAJOR code-confirmed gaps (audit atomicity AR-16,
dataset-freeze enforcement AR-17, image dedup race AR-18). All four are pre-existing,
now tracked, and remediable under change control; AR-15 is a **mandatory
pre-production condition**. The freeze decision stands **because no production or
clinical deployment is authorized** and the finding is contained and scheduled for
Phase 2. **No production or clinical deployment is authorized.**

## 2. Architecture freeze status

**LUMENAI VERSION 1.0 ARCHITECTURE FROZEN** (`ARCHITECTURE_FREEZE_DECLARATION.md`).
Class C expansion prohibited; Class A/B corrections permitted under
`ARCHITECTURE_CHANGE_CONTROL.md`. Preserved invariants verified by the validation
run.

## 3. Current-state architecture

Modular monolith: React SPA → FastAPI runtime (API gateway + services + models) →
PostgreSQL (authoritative) + object storage + hash-chained audit. Governed pipeline
Instrument→Inspection→Image→Metadata→Annotation→GT→Baseline→Digital Twin→Dataset→
Model→Human Review→Evidence→Audit→Report. Containerized (Docker/Compose/Helm/K8s).
(`CURRENT_STATE_ARCHITECTURE.md`.)

## 4. System inventory summary

Every material component inventoried across platform layers, security/identity,
inspection intelligence, governed knowledge, supporting services, and AI governance
— each with classification, auth/tenant/audit requirement, failure behavior, tests,
owner, lifecycle, and readiness (`SYSTEM_INVENTORY.md`).

## 5. Module ownership

Role-based ownership assigned; **no critical module ownerless**. Accountable owner,
tech maintainer, data steward, security approver, quality approver, business owner
distinguished per module (`MODULE_OWNERSHIP_MATRIX.md`). Knowledge-concentration is
a MAJOR risk (AR-11).

## 6. Boundary assessment

Clean, test-verified safety boundaries (auth/tenant chain, image ownership, single
audit writer, append-only history, AI-inside-human-authority). MAJOR findings:
deprecated audit shim (B-01), governance-in-code (B-02), god-runtime (B-03).
**No CRITICAL *internal-module* boundary defect** (the CRITICAL AR-15 finding is at
the external-integration trust boundary — see §10/§16, not a module-to-module
breach). (`MODULE_BOUNDARY_REVIEW.md`.)

## 7. Dependency assessment

Layered direction intact; no circular dependency in the validated pipeline. SPOFs
(single DB/runtime) mitigated by DR + scaling. CI-enforcement of import-cycle and
dependency scanning is a gap (`SYSTEM_DEPENDENCY_MAP.md`,
`DEPENDENCY_RISK_REGISTER.md`). No CRITICAL, release-blocking dependency risk.

## 8. Data authority assessment

Every major data object has **one authoritative system of record**; immutability/
append-only enforced and test-verified for image bytes, annotation, GT, baseline,
model, and audit; deletion is retention-first. **Correction (DA-01/AR-17, MAJOR):**
dataset "immutable after approval" is **not code-enforced** — `dataset_builder`
writes `split_assignment`/`image_quality` without checking the parent version's
`frozen` flag. Competing sources otherwise resolved
(`DATA_OWNERSHIP_AND_AUTHORITY.md`).

## 9. Interface assessment

1,912 endpoints; **0 UNKNOWN**; 10 unauthenticated writes all PUBLIC_BY_DESIGN;
privilege-escalation defenses tested. Findings: duplicate billing webhook (I-01),
deprecated header-fallback (I-02), OpenAPI schema-diff not CI-gated (I-04). No
insecure/orphan endpoint surfaced (`INTERFACE_AND_API_INVENTORY.md`).

## 10. Trust-boundary assessment

The internal safety-critical boundaries (3–12: auth, tenant, authorization, service,
storage, model, human review, evidence archive) are test-verified and fail-closed.
**Correction (TB-02/AR-15, CRITICAL):** boundary 13 (external integration) does
**not** hold — `integrations.webhook_ingest` and `billing.stripe_webhook` accept
unsigned payloads when their secret is unset, with no startup validation, and
`webhook_ingest` trusts the `X-Tenant-Id` header, permitting cross-tenant injection
on a public write. **TB-01/AR-16 (MAJOR):** audit is not atomic with the business
write (`TRUST_BOUNDARY_ARCHITECTURE.md`).

## 11. Failure and recovery assessment

"Absence ≠ success" invariants implemented and test-backed; DR executed with
measured RTO/RPO; `/ready` DB hard-gate. MAJOR: production-scale HA unproven;
**FR-01/AR-16** audit-write not atomic with the business write; **FR-02/AR-18**
duplicate-request protection is best-effort (`image_sha256` indexed, not unique;
check-then-insert race) (`FAILURE_AND_RECOVERY_ARCHITECTURE.md`).

## 12. ADR assessment

9 ADRs implemented; **core decisions Implemented but Undocumented** (monolith, DB
strategy, audit-chain, dataset immutability, placeholder isolation, deployment) —
MAJOR ADR-01. No obsolete/conflicting ADRs. No speculative ADRs created
(`ARCHITECTURAL_DECISION_REGISTER.md`).

## 13. Duplication and deprecation findings

Deprecated audit shim (DUP-01/DEP-01) and duplicate billing webhook (DUP-02) are
the only concrete low-risk cleanup candidates; **no code deleted** this directive
(automated dead-code/import-cycle detection must run in CI first)
(`DUPLICATION_AND_DEPRECATION_REVIEW.md`).

## 14. Module readiness scorecard

READY (7 safety-critical core), READY WITH CONDITIONS (majority), NOT READY (1:
Vision inference — no governed model), PLACEHOLDER-isolated (unavailable-model),
DOCUMENTED ONLY/OUT OF SCOPE (physical lab). No READY module carries an unresolved
Critical finding (`MODULE_READINESS_SCORECARD.md`).

## 15. Architecture risk summary

**1 CRITICAL** (AR-15, webhook fail-open — release-blocking, pre-production
condition), **12 MAJOR** (including AR-16 audit atomicity, AR-17 dataset-freeze
enforcement, AR-18 dedup race), minor/observation risks. The internal
safety-critical categories (tenant/auth/audit-chain/evidence) remain mitigated and
test-verified; AR-15 is an external-edge input-validation gap
(`ARCHITECTURE_RISK_REGISTER.md`).

## 16. Critical findings

**One (AR-15 / TB-02) — external-integration webhook fails open.**
`integrations.webhook_ingest` verifies its HMAC only when `WEBHOOK_SECRET_{SYSTEM}`
is set, and `billing.stripe_webhook` parses unsigned JSON when
`STRIPE_WEBHOOK_SECRET` is unset; there is **no startup validation** requiring these
secrets, and `webhook_ingest` derives the tenant from the attacker-controllable
`X-Tenant-Id` header. A valid deployment configuration therefore permits
**cross-tenant data injection on a public write**. This finding was surfaced during
PR review, verified against code, and **corrects the initial "no critical findings"
assessment** (honesty mandate: no unresolved critical finding is hidden or
downgraded). It is pre-existing, is now tracked as release-blocking (AR-15), and is a
**mandatory pre-production remediation**; no production or clinical deployment is
authorized, so it does not block the *architecture-freeze* decision.

The other governed defenses remain test-verified (186/186): no defect permitting
audit-chain forgery, evidence corruption, false finalization, unsafe AI authority,
unrecoverable data loss, or *internal* cross-tenant/privilege escalation was found.

## 17. Major findings

B-01 audit shim · B-02 governance-in-code · B-03 god-runtime · AR-04/ADR-01 missing
ADRs · AR-05 CI-enforcement gaps · AR-06 HA unproven · AR-07 no governed model ·
AR-08 scalability uncharacterized · AR-11 knowledge concentration · **AR-16 audit
write not atomic with business write** · **AR-17 frozen dataset not lock-enforced**
· **AR-18 image dedup check-then-insert race (`image_sha256` not unique)**.

## 18. Technical debt requiring later phases

Governance-in-code enforcement; audit-shim + billing-webhook cleanup; missing ADRs;
CI activation for dep-scan/import-cycle/OpenAPI-diff/dead-code; HA + scale
characterization; Directive 005 doc consolidation; governed aggregate Digital Twin.

## 19. Architecture decision

**ARCHITECTURE FROZEN — PASS WITH CONDITIONS.** The architecture is sufficiently
coherent and test-verified in its internal safety-critical structure to freeze. The
one CRITICAL finding (AR-15, webhook fail-open) is an external-edge input-validation
gap that is pre-existing, contained, tracked, and remediable — it is a **mandatory
pre-production condition**, not an architecture-invalidating defect, and the freeze
holds specifically because **no production or clinical deployment is authorized**.
AR-15 (CRITICAL) plus the MAJOR conditions (AR-16/17/18 and the pre-existing debt
items) must be resolved during later Production Readiness phases under change
control; AR-15 must be closed and re-verified **before any production authorization**.

## 20. Phase 2 entry recommendation

**Proceed to Phase 2** with these entry conditions carried as a tracked backlog,
**AR-15 first and release-blocking:** (0) **[CRITICAL] close AR-15/TB-02** — require
webhook signing secrets at startup (fail-closed), reject unsigned payloads, and stop
trusting `X-Tenant-Id` for tenant authority; (1) enforce High-priority governance
gates in code (B-02/AR-03) and the code-confirmed MAJOR gaps AR-16 (audit atomicity),
AR-17 (dataset-freeze enforcement), AR-18 (dedup uniqueness); (2) author the missing
ADRs (ADR-01); (3) activate CI enforcement for dependency scan, import-cycle,
OpenAPI-diff, and dead-code detection (AR-05); (4) migrate the deprecated audit shim
and resolve the duplicate billing webhook (B-01/DUP-02); (5) plan HA + scale
characterization (AR-06/AR-08). Phase 2 must not add product features, AI
specialists, or scope, and must preserve the frozen architecture.

## Acceptance criteria status

All Phase 1 acceptance criteria met: architecture frozen; every material module
inventoried; every critical module owned; every major data object has one SoR;
every interface inventoried; trust boundaries documented; responsibilities/
non-responsibilities explicit; circular/hidden dependencies assessed; duplicates
identified; placeholder isolated; failure/recovery documented; ADRs registered;
risks classified/assigned; readiness scored on evidence; **no Critical finding
hidden or downgraded**; Phase 2 recommendation produced.
