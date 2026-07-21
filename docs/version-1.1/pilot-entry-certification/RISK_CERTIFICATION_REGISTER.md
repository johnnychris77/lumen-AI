# RISK CERTIFICATION REGISTER — LPR-DIR-033 / Workstream 8

Residual risks categorized **LOW / MEDIUM / HIGH / CRITICAL** at the certification point.

## 1. Register
| ID | Domain | Risk | Category |
|---|---|---|---|
| CR-01 | Operational | No executed deploy/rollback → release + recovery path unproven | **CRITICAL** |
| CR-02 | Operational | No managed DB + backup/DR → data-loss with no proven recovery (RTO/RPO unknown) | **CRITICAL** |
| CR-03 | Operational | No alerting/on-call → pilot failures unnoticed | **HIGH** |
| CR-04 | Clinical | No pilot protocol / sponsor / quality / IP / privacy review | **CRITICAL** |
| CR-05 | Governance | No signed executive/infrastructure/budget authorization (EXEC-001 asserted, unconfirmed) | **HIGH** |
| CR-06 | Security (ops) | Managed secrets/TLS lifecycle unproven on ingress | **MEDIUM** |
| CR-07 | Security (prod) | SEC-H-01/02 partial | **MEDIUM** (non-pilot-gating) |
| CR-08 | Business | Certifying without evidence would create false assurance for a clinical pilot | **CRITICAL** |
| CR-09 | Process | Repository/roadmap divergence: DIR-032 marked complete but no evidence exists | **HIGH** |

## 2. Aggregate posture
**Four CRITICAL, three HIGH, two MEDIUM.** No risk was retired since DIR-030/031 because no new
operational or clinical evidence was produced. CR-08/CR-09 specifically caution against
certifying on assertion rather than evidence.

## 3. Determination — WS8
The risk posture is **incompatible with Pilot Entry Certification.** Multiple CRITICAL
operational and clinical risks are unmitigated, and a process risk (CR-09) flags the
evidence/assertion gap the board must not paper over.
