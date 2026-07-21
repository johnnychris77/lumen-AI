# ENGINEERING CAPABILITY CERTIFICATION — LPR-DIR-033 / Workstream 2

Each capability classified **CERTIFIED / PARTIALLY CERTIFIED / NOT CERTIFIED** against current
repository evidence. A capability is **CERTIFIED only with reproducible execution evidence on
the managed pilot environment.** Dev-technique demonstrations and code artifacts do not certify
an operational capability.

## 1. Classification
| Capability | Evidence in repo | Classification | Basis |
|---|---|---|---|
| Deployment | `deploy.yml` artifact; **no executed run** | **NOT CERTIFIED** | no cluster deploy; DIR-031 probe = not provisionable |
| Rollback | `rollout undo` in `deploy.yml`; **no drill** | **NOT CERTIFIED** | no executed rollback, no MTTR |
| Backup | SQLite analog only (harness §5) | **NOT CERTIFIED** | no managed-DB backup |
| Restore | SQLite analog only | **NOT CERTIFIED** | no managed-DB restore, no RTO/RPO |
| PostgreSQL | PG16 **CI service container**; migration head verified | **PARTIALLY CERTIFIED** | code Postgres-compatible; **no managed instance** |
| Monitoring | `/health` + structured logging (harness §3) | **PARTIALLY CERTIFIED** | primitives only; no monitoring stack |
| Alerting | none | **NOT CERTIFIED** | no alert generated/delivered/acked |
| Logging | structured JSON logs (harness) | **PARTIALLY CERTIFIED** | emitted; no aggregation |
| Secrets | gen/rotation/hash technique (harness §1); repo hygiene clean | **PARTIALLY CERTIFIED** | technique only; no managed injection/rotation |
| TLS | cert gen/validate technique (harness §2) | **PARTIALLY CERTIFIED** | technique only; no ingress-served cert / HTTPS enforcement |

## 2. Roll-up
- **CERTIFIED: 0**
- **PARTIALLY CERTIFIED: 5** (PostgreSQL, Monitoring, Logging, Secrets, TLS — all as *technique/
  code*, none as managed-environment operation)
- **NOT CERTIFIED: 5** (Deployment, Rollback, Backup, Restore, Alerting)

## 3. Note on the DIR-032 claim
The program context states LPR-DIR-032 ("Operational evidence execution") is *Completed*. **No
operational execution evidence exists in the repository** (see WS7 `OPERATIONAL_EVIDENCE_AUDIT.md`
and `pilot-operational-capability/DIR_032_READINESS_REPORT.md`, which records DIR-032 as
**NO-GO / not executed**). Per the certification principle *"only current evidence shall be
evaluated"* and WS7 *"reject documentation presented as deployment,"* the *Completed* assertion
is **not supported by evidence** and cannot upgrade any classification above.

## 4. Determination — WS2
**No engineering capability is CERTIFIED for pilot operation.** Five are PARTIALLY CERTIFIED as
techniques/code; five are NOT CERTIFIED. Operational certification requires the DIR-032 evidence
that does not yet exist.
