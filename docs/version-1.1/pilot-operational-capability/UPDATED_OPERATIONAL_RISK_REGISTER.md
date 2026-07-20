# UPDATED OPERATIONAL RISK REGISTER — LPR-DIR-031 / WP-10

Updates the DIR-030 Residual Risk Register with the LPR-DIR-031 execution outcome. The
material change this directive adds is the **objectively confirmed root cause**: the execution
context cannot provision a managed environment (`evidence/PROVISIONING_PROBE.log`), so the
operational gaps persist and are now tied to a single explicit unblocking dependency.

## 1. Risk register
| ID | Risk | Sev | Status after DIR-031 | Closure precondition (unblock) |
|---|---|---|---|---|
| RR-01 | No managed DB / backup → data loss, no recovery | **High** | OPEN | Managed Postgres + backup + restore transcript + RTO/RPO |
| RR-02 | No executed deploy/rollback → unproven release/recovery | **High** | OPEN | Cluster + `KUBE_CONFIG` → executed deploy + timed rollback |
| RR-03 | No alerting/on-call → failures unnoticed | **High** | OPEN | Monitoring/alerting stack + on-call routing + delivered alert |
| RR-04 | No managed secrets/TLS lifecycle | **Medium** | OPEN | Secrets store + managed cert on ingress |
| RR-05 | SEC-H-01/02 partial (prod hardening) | **Medium** | OPEN | Full fallback elimination + `Settings.validate()` coverage |
| RR-06 | PERF-07 / RES-01 unproven at scale / multi-replica | **Medium** | OPEN | Representative load test; leader-election failover test |
| RR-07 | Clinical prerequisites not started | **High** | OPEN (external) | WP-07 clinical package (out of scope here) |
| RR-08 | Executive approvals pending | **High** | OPEN (external) | WP-08 approvals against operational evidence |
| RR-09 | Harness result environment-sensitive (needs backend deps) | **Low** | MITIGATED | Deps installed + 6/6 re-run captured; pin deps in runner |
| **RR-10 (new)** | **Execution context cannot provision managed infra** → operational evidence cannot be generated regardless of engineering readiness | **High (process)** | **OPEN** | A managed environment + credentials must be supplied to any future execution directive (LPR-DIR-032 precondition) |

## 2. Remaining operational gaps
Managed DB + backup/DR · executed deploy + rollback · monitoring + alerting + on-call ·
managed secrets/TLS lifecycle · operational incident drill. **All OPEN.**

## 3. Remaining pilot gaps
0/23 Pilot-Entry gates VERIFIED (unchanged). All 5 pilot blockers OPEN. Pilot Entry DENIED.

## 4. Future dependencies (single critical path)
Every remaining operational gap collapses to **one external dependency: a provisioned managed
environment with credentials**. Until that is supplied, no execution directive can generate
the operational evidence — this is the governing precondition for **LPR-DIR-032 (Pilot Entry
Gate Re-Certification)**, which cannot succeed on engineering-blocker closure until RR-10 is
resolved.

## 5. Determination
Risk posture is **unchanged in substance** from DIR-030 and now carries an explicit root-cause
risk (RR-10). No operational risk was retired by execution because execution was not possible.
