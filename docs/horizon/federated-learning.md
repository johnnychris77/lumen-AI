# Project Horizon — Federated Learning

LumenAI v3.4

## Mission

Create the world's first Federated Clinical Intelligence Network for
Sterile Processing. Hospitals remain completely isolated. Patient
information never leaves the organization. Institution-specific
workflows remain local. Only validated, de-identified, governance-
approved clinical inspection intelligence may contribute to global
learning.

## The fourth cross-tenant intelligence system — consolidate, don't duplicate

Before this sprint, three parallel cross-tenant/network intelligence
systems already existed in this codebase:

| System | Files | k-anonymity floor |
|---|---|---|
| P15 — National SPD Intelligence Network | `network_benchmark_service.py`, `network_benchmark.py` | `MIN_FACILITIES = 5` |
| P20 — Network Intelligence Platform | `p20_network_intelligence.py` | k=5 (route-enforced), IRB-gated Research Data Exchange already includes `ResearchDataset`/`ResearchStudy`/`ResearchPublication` |
| P23 — Global Surgical Intelligence Network (GSIN) | `global_intelligence.py`, `global_aggregation_job.py` | `GLOBAL_K_THRESHOLD = 10`, `EARLY_WARNING_K = 5` |

Project Horizon does not add a fifth. Every new k-anonymity gate in this
module imports `GLOBAL_K_THRESHOLD`/`EARLY_WARNING_K` directly from
`global_aggregation_job.py` — never a new threshold constant. Section 1's
"organization participation" composes GSIN's `GSINParticipant` (technical
enrollment: participant type, region, BAA/DPA, contribution categories)
together with P20's `IntelligenceSharingAgreement` (opt-in, reversible,
sharing-scope agreement) into one enrollment action
(`horizon_participation_service.enroll_organization`) — a federated
participant genuinely needs both, and neither table alone was sufficient.

## Section 1 deliverables, mapped to what already exists vs. what's new

| Requirement | Implementation |
|---|---|
| Organization participation | `GSINParticipant` + `IntelligenceSharingAgreement`, composed |
| Opt-in governance | `IntelligenceSharingAgreement.status`, reversible via `withdraw_organization` |
| De-identification | `KnowledgeContribution.source_tenant_id` never exposed cross-org; `GLOBAL_K_THRESHOLD`/Laplace noise on every numeric aggregate |
| Knowledge validation | `KnowledgeContribution.approval_status` (draft/pending_review/approved/rejected/archived) |
| Contribution tracking | `submitted_by`/`approved_by`/`approved_at`/`rejection_reason` |
| Version control | `version`, `supersedes_ref`/`superseded_by_ref` chain |
| Provenance | `source_tenant_id` retained for audit, never published |

## No PHI or customer-identifiable information is shared

Every aggregation in this module (`horizon_federated_signal_service.py`,
`horizon_benchmark_service.py`, `horizon_knowledge_graph_service.py`,
`horizon_trend_detection_service.py`) reads counts and rates only — never
raw inspection records, patient data, or facility identity — and only
from organizations with an active federated sharing agreement
(`horizon_participation_service.list_enrolled_tenant_ids`). Opt-in
governance is enforced as an actual data-scope filter on every
aggregation query, not merely a checkbox an organization ticks.

## Never fabricated

Every signal, benchmark, and trend in this module is computed from real
per-tenant rows (`InspectionFinding`, `Inspection`, `SupervisorReview`,
`RepairRequest`, `KnowledgeArticle`) — never a seeded-random mock, unlike
some of the systems it composes (`network_benchmark_service.py` still
falls back to a seeded mock when no `IndustryBenchmark` rows exist yet).
When fewer than `MIN_FACILITIES`/`GLOBAL_K_THRESHOLD` organizations
contribute to a given metric, the result is suppressed (`suppressed:
true`, value `null`) rather than published with an artificially small
sample.
