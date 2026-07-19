# LPR-DIR-012 — Failure & Recovery Architecture

The core doctrine (verified by tests + foundation DR work): **the architecture must
never treat an absence as a success.**

## Non-negotiable failure invariants

| Must NOT treat… | …as | Enforced by |
|---|---|---|
| missing evidence | successful evidence | fail-closed evidence engine (`test_evidence_authorization_baseline`) |
| missing baseline | normal comparison | compatibility contract; escalation |
| missing model | successful inference | safe unavailable-model states |
| absent finding | clean | contamination-safety invariant (false-PASS remediation) |
| failed audit write | auditable success | hash-chained writer; write failure surfaces |
| unknown state | approved state | Unknown is a governed, non-approving outcome |

## Per-subsystem failure & recovery

| Subsystem | Failure | Behavior | Recovery |
|---|---|---|---|
| Startup | missing config/DB | Startup fails; `/ready` not green | Fix config; container restart |
| Database | unavailable | `/ready` DB hard-gate fails; requests 503 | Backup/restore; DR (measured RTO/RPO) |
| Storage | unavailable/corrupt | Integrity-hash mismatch → fail-closed read | Restore from backup |
| Authentication | invalid/unverifiable token | 401 | Re-authenticate |
| Authorization | insufficient role/tenant | 403 (no side effect) | Grant/deny by policy |
| Tenant resolution | no membership | 403 fail-closed | Provision membership |
| Audit write | chain write fails | Operation not reported as auditable success | Retry; investigate integrity |
| Evidence generation | incomplete bundle | Not promoted; quarantined | Re-assemble from governed records |
| Corrupted image | hash mismatch | Rejected; not annotated | Re-acquire |
| Missing metadata | required field absent | Excluded; validation error | Supply metadata |
| Unavailable baseline | no approved baseline | Comparison inconclusive → escalate | Approve/activate baseline |
| Missing Digital Twin | identity unresolved | Fail-closed; no promotion | Register identity |
| Unresolved Ground Truth | GT not ACTIVE | Blocks dataset/baseline use | Complete review/approval |
| Unavailable candidate model | model absent | Safe unavailable state; human review | Register/certify model (future) |
| Report generation | source incomplete | Report not produced from partial data | Complete governed records |
| Partial workflow | interrupted | State machine holds; no false closure | Resume from last valid state |
| Duplicate request | repeated write | Idempotency/uniqueness (e.g. `image_sha256`) | Dedup |
| Timeout | slow dependency | Bounded; fail-closed | Retry per policy |
| Retry | transient error | Bounded retries | Backoff |
| Rollback | bad model version | Restore prior version (checksum-verified) | Rollback standard (Directive 009) |
| Restart recovery | process restart | Stateless request handling; DB is SoR | Resume; no in-process state loss |

## Recovery evidence

* **Backup / restore / disaster recovery** executed with **measured RTO/RPO**
  (foundation).
* **`/ready`** per-dependency probe hard-gates the database.
* **Append-only history** guarantees historical records survive working-copy loss.

## Findings

* **No CRITICAL failure-architecture defect.** The "absence ≠ success" invariants
  are implemented and test-backed.
* **MAJOR (recovery):** production-scale HA (multi-instance DB/runtime) is not yet
  proven; current mitigations are DR + `/ready` gating + container scaling — a later
  Production Readiness phase item.
