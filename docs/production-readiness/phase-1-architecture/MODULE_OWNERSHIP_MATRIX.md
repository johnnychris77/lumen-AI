# LPR-DIR-012 — Module Ownership Matrix

Ownership is assigned by **role**, not individual. Every critical module has an
accountable owner. Roles: Accountable Owner (A), Technical Maintainer (M), Data
Steward (D), Security Approver (S), Quality Approver (Q), Business Owner (B).

| Module / domain | Accountable Owner | Tech Maintainer | Data Steward | Security Approver | Quality Approver | Business Owner |
|---|---|---|---|---|---|---|
| Frontend SPA | Frontend Engineering | Frontend Eng | — | Security Eng | Quality Eng | Product Ops |
| Backend API runtime / gateway | Backend Engineering | Backend Eng | — | Security Eng | Quality Eng | Product Ops |
| Authentication / Authorization | Security Engineering | Backend Eng | — | Security Eng | Quality Eng | Compliance |
| Authenticated Principal / Tenant Context | Security Engineering | Backend Eng | Data Eng | Security Eng | Quality Eng | Compliance |
| Tenant Isolation | Security Engineering | Backend Eng | Data Eng | Security Eng | Quality Eng | Compliance |
| Secrets Management | Security Engineering | Infra Eng | — | Security Eng | Quality Eng | Compliance |
| Audit (hash chain) | Security Engineering | Backend Eng | Data Eng | Security Eng | Quality Eng | Compliance |
| Database / persistence | Data Engineering | Data Eng | Data Eng | Security Eng | Quality Eng | Platform |
| Object/file storage | Infrastructure Engineering | Infra Eng | Data Eng | Security Eng | Quality Eng | Platform |
| Inspection Engine | Backend Engineering | Backend Eng | Data Eng | Security Eng | Clinical Governance | Product Ops |
| Image Service / Quality | Backend Engineering | Backend Eng | Data Eng | Security Eng | Quality Eng | Product Ops |
| Vision Engine / Candidate models | Machine Learning Engineering | ML Eng | Data Eng | Security Eng | Clinical Governance | Product Ops |
| Baseline Engine / Governance | Data Engineering | Backend Eng | Data Eng | Security Eng | Clinical Governance | Product Ops |
| Digital Twin Engine | Data Engineering | Backend Eng | Data Eng | Security Eng | Quality Eng | Product Ops |
| Evidence Engine | Backend Engineering | Backend Eng | Data Eng | Security Eng | Compliance | Compliance |
| Reporting Engine | Backend Engineering | Backend Eng | — | Security Eng | Quality Eng | Product Ops |
| Annotation / Ground Truth | Data Engineering | Backend Eng | Data Eng | Security Eng | Clinical Governance | Product Ops |
| Dataset Registry / Eligibility / Lineage | Data Engineering | ML Eng | Data Eng | Security Eng | Quality Eng | Product Ops |
| Candidate Model Registry / Promotion | Machine Learning Engineering | ML Eng | Data Eng | Security Eng | Clinical Governance | Product Ops |
| Experiment Tracking | Machine Learning Engineering | ML Eng | Data Eng | Security Eng | Quality Eng | Product Ops |
| Knowledge Graph | Data Engineering | Backend Eng | Data Eng | Security Eng | Quality Eng | Product Ops |
| Human Review / Safety Escalation | Clinical Governance | Backend Eng | — | Security Eng | Clinical Governance | Compliance |
| Workflow / Analytics / Marketplace / Subscription / SLA / Vendor Scorecard | Product Operations | Backend Eng | Data Eng | Security Eng | Quality Eng | Product Ops |
| PDF / Notification / Integration Adapters | Backend Engineering | Backend Eng | — | Security Eng | Quality Eng | Product Ops |
| Deployment / Monitoring / Logging | Infrastructure Engineering | Infra Eng | — | Security Eng | Quality Eng | Platform |
| CI/CD | Quality Engineering | Infra Eng | — | Security Eng | Quality Eng | Platform |
| Architecture freeze / change control | Program Architecture | — | — | Security Eng | Quality Eng | Program |

## Ownership findings

* **No critical module is ownerless.** Every module in `SYSTEM_INVENTORY.md` maps
  to an accountable owner role above.
* **Knowledge-concentration risk (MAJOR):** the large single-runtime backend
  concentrates many domains under Backend Engineering; distribute technical
  maintainership by domain (tracked as an architecture risk).
* **Cross-approval discipline:** Security Approver and Quality Approver are
  distinct roles from the Accountable Owner for every governed module — preserving
  separation of duties.
