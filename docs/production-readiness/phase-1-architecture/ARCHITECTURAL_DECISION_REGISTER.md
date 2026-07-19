# LPR-DIR-012 — Architectural Decision Register

Inventory of architectural decisions, each classified: **Documented & Implemented /
Documented, Not Implemented / Implemented, Undocumented / Obsolete / Conflicting /
Superseded / Missing**. Existing ADRs live in `docs/adr/` (0001–0009). No
speculative ADRs are created here.

## Existing ADRs

| ADR | Topic | Status |
|---|---|---|
| 0001 | Multi-agent architecture | Documented & Implemented |
| 0002 | Digital Twin systems | Documented & Implemented (identity; aggregate record = Future) |
| 0003 | Knowledge graph | Documented & Implemented |
| 0004 | Council decision support | Documented & Implemented (human-authoritative) |
| 0005 | Evidence governance | Documented & Implemented |
| 0006 | Baseline hierarchy | Documented & Implemented |
| 0007 | Tenant isolation | Documented & Implemented (tests pass) |
| 0008 | Aegis specialist status | Documented & Implemented |
| 0009 | Risk-monitoring system consolidation | Documented & Implemented |

## Required decision coverage (this review)

| Decision | Reality | Classification | ADR reference / gap |
|---|---|---|---|
| Modular monolith vs. services | Single FastAPI runtime + one DB | **Implemented, Undocumented** | **Missing ADR** — record "modular monolith for v1.0" |
| Database strategy | PostgreSQL authoritative (SQLite tests) | Implemented, Undocumented | Missing ADR — record DB strategy |
| Tenant-isolation strategy | `TenantMembership` authoritative; fail-closed | Documented & Implemented | ADR 0007 |
| Authentication model | Typed principal; OIDC/JWT; prod dev-token rejected | Implemented, partially documented | Update/confirm ADR |
| Authorization model | `require_*` role/tenant guards | Implemented, partially documented | Update/confirm ADR |
| Audit-chain model | Hash-chained, append-only | Implemented, Undocumented | **Missing ADR** — record audit-chain design |
| Evidence immutability | Checksums + append-only + audit chain | Documented & Implemented | ADR 0005 |
| Digital Twin identity | LCID identity anchor | Documented & Implemented | ADR 0002 |
| Baseline governance | Approved-only lifecycle | Documented & Implemented | ADR 0006 |
| Ground Truth authority | Human-approved, immutable | Implemented, partially documented | Confirm/record ADR |
| Dataset immutability | Version-frozen after approval | Implemented, Undocumented | Missing ADR — record dataset immutability |
| Candidate-model role | Decision-support-only; no deployment | Documented & Implemented (Directive 009) | Directive 009 (link as ADR) |
| Human-review authority | Human finalizes; AI advisory | Documented & Implemented | ADR 0004 + Directive 009 |
| Placeholder isolation | Safe unavailable-model states | Implemented, Undocumented | Missing ADR — record placeholder isolation |
| Reporting architecture | Governed report/evidence release | Implemented, partially documented | Confirm ADR |
| Deployment topology | Container monolith + DB + storage | Implemented, Undocumented | Missing ADR — record deployment topology |

## Findings

| ID | Sev | Finding | Action |
|---|---|---|---|
| ADR-01 | MAJOR | Core decisions **Implemented but Undocumented** (monolith, DB strategy, audit-chain, dataset immutability, placeholder isolation, deployment topology) | Author the missing ADRs (documentation correction — permitted under freeze) |
| ADR-02 | MINOR | Some auth/authz/GT/reporting ADRs are partial | Update to reflect implemented reality |
| ADR-03 | OBSERVATION | No obsolete/conflicting ADRs detected | None |

No speculative ADRs were created. The gap is **documentation of existing
decisions**, which the freeze explicitly permits.
