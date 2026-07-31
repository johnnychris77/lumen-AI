# LumenAI Marketing — Product Claims Review

Every public statement on the `/site` marketing pages is classified below.
Source of truth for capability status is the repository's
`docs/product-truth-reset/PRODUCT_CAPABILITY_MATRIX.md` and
`docs/production-readiness/AI_SPECIALIST_CATALOG.md`. This review must be
re-checked whenever site copy changes.

## Classification key

- **A — Supported by current product:** implemented and running today.
- **B — Demonstrated with simulated data:** shown on the site using synthetic
  data, clearly labeled; not a claim of production accuracy.
- **C — Planned / concept-stage:** described as concept; not implied to exist.
- **D — Requires legal / regulatory / security / clinical review before use.**
- **E — Must NOT be published:** not present on the site by design.

## A — Supported by current product

| Claim on site | Where | Basis |
|---|---|---|
| Structured inspection records with instrument/tray/location/technician/time metadata | Platform, Workflow | Core inspection workflow |
| Baseline-aware comparison when an approved baseline exists | Platform, Workflow, Home | Baseline resolution + comparison service |
| Evidence recorded to a hash-chained, tamper-evident audit trail | Security, Evidence path, Platform | Enterprise audit service (hash-chained) |
| Risk/uncertain findings route to human review | Everywhere | Supervisor review + gating |
| Role-based access; tenant isolation enforced at the API layer | Security, Platform | RBAC + Atlas scope enforcement |
| Versioned APIs | Security | `/api/v1` surface |
| Instrument history / digital-twin record | Platform | Digital-twin/instrument condition records |
| Quality / exportable reports | Platform, Workflow | Report generation |

## B — Demonstrated with simulated data (labeled on the site)

| Item | Where | Label shown |
|---|---|---|
| Interactive workflow demo (instrument, image, finding, baseline, ranking, report) | Workflow | "Demonstration Data — Not for Clinical Use" persistent banner |
| Concept quality dashboard (volumes, categories, trend) | Platform | Same banner; figures synthetic |
| Vendor / instrument trend intelligence | Platform capability card | Tagged "Demonstrated with simulated data" |
| Knowledge-graph relationships | Platform capability card | Tagged "Demonstrated with simulated data" |

## C — Planned / concept-stage (labeled "Concept stage")

| Item | Where | Note |
|---|---|---|
| AI-assisted finding **suggestions** as a product feature | Platform capability card | Current build runs a **documented placeholder scorer**, not a validated CV model. Presented as assistive only. |
| Trained, validated computer-vision model | Architecture ("Honest about the model"), Platform | Explicitly stated as not yet existing; requires formal validation. |

## D — Requires review before any stronger claim is made

- Any statement that the AI **detects**, **classifies**, or **measures**
  findings with an accuracy figure → requires a completed clinical validation
  study (blinded multi-reader). **Not made anywhere on the site.**
- Any pilot outcome, throughput, or quality-improvement number → requires real
  pilot data. **Not made.**
- Security control language beyond "designed with … principles in mind" →
  requires security review before claiming certification-grade assurance.

## E — Claims deliberately NOT published (must not appear)

The site contains **none** of the following, by design:

- Infection-rate reduction or any patient-safety outcome claim.
- Regulatory or accreditation **compliance** guarantees.
- FDA clearance / FDA status.
- HIPAA compliance.
- SOC 2 or any cybersecurity certification.
- Diagnostic accuracy or AI accuracy percentages.
- Cost-savings or labor-reduction figures.
- Any statement that LumenAI replaces technicians, infection preventionists,
  surgeons, manufacturers, or regulatory authorities.
- Causation language (uses "possible association" / "quality review
  recommended" framing instead).

The Security page includes an explicit "What we do not claim" panel restating
the FDA/HIPAA/SOC 2 exclusions for the reader.

## Reviewer sign-off (to complete before public launch)

- [ ] Regulatory/legal review of all A/B/C copy
- [ ] Security review of the Security page control descriptions
- [ ] Clinical review of the AI-architecture and workflow framing
- [ ] Confirm no production secret, internal URL, or PHI in the built bundle
      (see DEPLOYMENT_GUIDE "Pre-publish security checklist")
