# LumenAI — Module Catalog

Per-module ownership review. "Owner" reflects the team role that would own this module in production (this codebase has no per-file `CODEOWNERS`; roles are inferred from module purpose) — assigning real named owners is a Phase 2 action item, not done by this document. "Status" is `Active` (in active use, wired into `main.py`/frontend), `Orphaned` (built but not linked into navigation or never registered), or `Legacy` (superseded by a newer module but still present).

Modules are grouped by the specialist/subsystem pattern used throughout the codebase: one model file + a group of `<prefix>_*` services + one route file + one frontend workspace.

## AI Specialist Modules

| Module | Purpose | Responsibilities | Inputs | Outputs | Dependencies | Consumers | Owner | Status |
|---|---|---|---|---|---|---|---|---|
| **Council** | Multi-agent leadership decision support | Convene specialist assessments, preserve dissent, record human decisions | Veritas, Aegis, Vulcan, Sage, Sentinel-X, Apollo, Athena, Pulse, Phoenix, Maestro assessments | `CouncilCase`, human decision record, outcome review | 10 specialist services | Steward (creates actions from decisions), leadership UI | AI Platform Lead | Active |
| **Maestro** | Executive priority synthesis | Rank operational priorities, daily briefs, decision journal | Every specialist's live output + Phase 22 pipeline | Priority items, recommendations, daily brief | ~10 specialist services + `knowledge_graph_service` | Council (priorities feed), leadership UI | AI Platform Lead | Active |
| **Oracle** | Discovery engine / research hypotheses | Observe data, propose hypotheses, gate through 8-stage validation | Sentinel-X AI health, Apollo twin history, Vulcan progression | Hypotheses, trend/twin/model observations, knowledge suggestions | Sentinel-X, Apollo, Vulcan, GovernanceApproval | Knowledge governance workflow | AI Platform Lead | Active |
| **Steward** | Governed execution of approved decisions | Implementation planning, rollout, verification, benefits realization, closure | Council decisions, CAPAs, Sentinel-X alerts, Maestro/Aegis/Vulcan/Sage/Veritas/Phoenix recommendations | Governed actions, audit trail, outcome reviews | Council, Veritas, Sentinel-X, Vulcan, Sage | Leadership boards | AI Platform Lead | Active |
| **Vulcan** | Instrument reliability & repair intelligence | Failure analysis, repair effectiveness, owns Aegis sub-capability | `InspectionFinding`, `RepairRequest` history | Reliability/repair assessments | Core inspection data | Council, Steward, Sentinel-X, Sage, Veritas, Oracle | Reliability Eng Lead | Active |
| **Sage** | SPD education & competency intelligence | Knowledge-gap detection, learning plans, effectiveness assessment | `CompetencyEvent`, `SupervisorReview`, Vulcan/Aegis signals | Learning plans, microlearning, assessments | Vulcan, Aegis | Council, Steward, Sentinel-X | Education Lead | Active |
| **Veritas** | Evidence integrity & baseline governance | Baseline resolution, evidence provenance/readiness, training data curation | `resolve_baseline`, `BaselineLibraryEntry`, image labels | Governance actions, readiness assessments | Aegis, Vulcan, Sage (read-only refs) | Council, Steward, Sentinel-X | Quality/Compliance Lead | Active |
| **Sentinel-X** | Composite clinical risk & patient safety | Risk scoring, patient-safety alerting, supervisor override tracking | Vulcan, Aegis, Veritas, Sage, knowledge confidence | Risk assessments, safety alerts | Vulcan, Aegis, Veritas, Sage | Council, Steward, Oracle | Patient Safety Lead | Active |
| **Apollo** | Autonomous clinical quality management | Unify CAPA/root-cause/accreditation/competency/complaint surfaces | Pre-existing CAPA, RCA, accreditation, competency services | Quality policy, complaints, quality twin | 5+ pre-existing quality services | Council, Oracle, Sage | Quality Lead | Active |
| **Athena** | Institutional knowledge & memory | Knowledge-experience graph, media curation, preservation sessions | `KnowledgeArticle`, `ClinicalCase`, knowledge-graph reasoning | Experience graph, knowledge memory | `knowledge_graph_service`, Apollo | Council | Knowledge Lead | Active |
| **Phoenix** | Self-improving platform intelligence | Improvement recommendations, innovation pipeline, platform maturity | Pilot metrics, Sentinel-X AI health, Apollo twin score | Recommendations, maturity snapshots | Sentinel-X, Apollo, Forge (approval chain) | Council, GuardianX | Platform Health Lead | Active |
| **GuardianX** | Cross-cutting AI assurance | Model risk, compliance mapping, evidence ledger, explainability | Olympus model registry, Phoenix health scores, audit service | Trust snapshots, explainability records | Olympus, Phoenix, Forge, audit service | Compliance Lead | Active |
| **Genesis AI** | Global sterile-processing intelligence cloud | Anatomy taxonomy, manufacturer knowledge updates, cross-org sharing | P15 registry, Horizon evidence, Beacon portal | `AnatomyProfile`, manufacturer updates | P15, Horizon, Beacon, Olympus | Every specialist referencing anatomy | Network Intelligence Lead | Active |
| **Nova** | Governed AI agent platform | Agent registry, comms bus, task orchestration, memory | Phase 22 agent pipeline trace, GuardianX explainability | Agent definitions, messages, task runs | Phase 22 `app/agents/*`, GuardianX, Infinity | Platform team | Active |
| **Olympus** | Autonomous healthcare intelligence network | Trust network, cross-org exchange packages, network governance | P24, Athena trust, Infinity certification, Horizon | Trust snapshots, exchange packages, governance cases | P24, Athena, Infinity, Horizon | GuardianX, Genesis AI | Network Lead | Active |
| **Infinity** | Developer ecosystem & marketplace | Developer accounts/keys, marketplace listings, billing, sandbox | Genesis (v4.0) plugins, Nexus credential pattern | Marketplace listings/installs/revenue | Genesis v4.0, Nexus, Forge | Olympus, GuardianX | Platform/Commercial Lead | Active |
| **Beacon** | Industry collaboration ecosystem | Repair intelligence, advisory board management | P24 consortium members, Horizon evidence | Advisory meetings/action items | P24, Horizon | Olympus | Partnerships Lead | Active |
| **Forge** | No-code clinical rules/workflow engine | Nested-boolean workflow definitions, approval chains, execution | User-authored rules | Workflow executions, approval instances | none (foundational) | Athena, Phoenix, GuardianX, Olympus, Infinity (approval chain reused 5x) | Workflow Lead | Active |
| **Pulse** | Real-time operations command center | Live alerts, dashboard widgets/layouts | Sentinel health-score service, AI-ops monitor | Alerts, widgets | Sentinel (legacy) | Operations leadership UI | Operations Lead | Active |
| **Catalyst** | Conversational AI copilot | NL conversation, skills framework, pending actions | User NL input | Conversation/message records | none (foundational); distinct from legacy P9 Copilot | Technician/supervisor/executive copilot UI | Copilot Lead | Active |
| **Orbit** | Perioperative & surgical readiness | Case cart, implant, loaner, staff/environment readiness | Scheduling, case data | Readiness snapshots, simulation runs | none (foundational, distinct from P25 instrument readiness) | Surgical readiness dashboard | Perioperative Lead | Active |
| **Vanguard** | Executive intelligence & strategy | Scorecards, board reports, strategic initiatives, benchmarks | Enterprise-wide metrics | Scorecard snapshots, board packets | none (foundational; explicitly notes some pre-existing "executive dashboard" surfaces are mock data) | Executive UI | Executive Lead | Active |

## Legacy Platform Sprints (P-number)

| Module | Purpose | Status |
|---|---|---|
| P20 (`p20_network_intelligence.py`) | National registry, instrument lifecycle, recall early warning, research data exchange, executive intelligence (14 tables) | Active — heavily composed by newer specialists |
| P21 (`quality_intelligence.py`) | Enterprise risk graph | Active |
| P22 (`p22_operations.py`) | Autonomous operations: workflow, work queue, ops copilot | Active |
| P23 (`global_intelligence.py`) | Global surgical intelligence network, k-anonymity gated aggregates | Active |
| P24 (`p24_standards.py`) | Global standards/accreditation/consortium/API partner | Active — composed by Beacon, Olympus, GuardianX |
| P25 (`p25_infrastructure.py`) | Instrument digital identity, surgical readiness, quality registry | Active |

## Core Infrastructure & Platform Modules (not tied to one specialist)

| Module | Purpose | Owner | Status |
|---|---|---|---|
| Auth (`app/deps.py`, `app/tenant_authz.py`, `app/auth_simple.py`) | Identity resolution, tenant-role RBAC | Platform Security | Active |
| Audit (`enterprise_audit_service.py`, `audit_chain_verification_service.py`) | Hash-chained tamper-evident audit log | Platform Security | Active |
| Tenant management (`tenant_*.py` models, 12+ files) | Membership, plan, quota, entitlement, health, onboarding, SSO | Platform/Commercial | Active |
| Billing (`invoice_line_item.py`, `payment_event.py`, `subscription_change_event.py`) | Usage metering and billing events | Commercial | Active |
| Governance workflow (`governance_approval.py`, `governance_rollback.py`, `governance_sla_*.py`) | Generic approval/rollback/SLA framework reused across specialists | Platform | Active |
| Reporting/briefing (`leadership_packet*.py`, `generated_briefing.py`, `account_review_*.py`, `saved_report.py`) | Executive report generation and distribution | Reporting | Active — no single owning module (Technical Debt TD-06) |
| Nexus (`nexus_integration.py`) | Integration/connector API gateway, event bus, identity mapping | Integrations Lead | Active |
| Integrations (`integrations.py`, P17) | One-way CSV/API import from external quality systems | Integrations Lead | Active, distinct axis from Nexus |
| Digital Twin (x3: `digital_twin.py`, `digital_quality_twin.py`, Apollo's twin) | Simulation/forecasting twins, deliberately non-duplicative | Quality/Ops | Active |
| Knowledge Graph (`knowledge_graph_service.py`, `knowledge.py`) | Reasoning chain, learning confidence, article store | Knowledge Lead | Active |
| Predictive/Insight (`predictions.py` P7, `predictive_insight.py` v3.3) | Instrument failure prediction, quality forecasting | Analytics Lead | Active |
| Guardian/Symphony/Atlas/Horizon/Sentinel(legacy)/Simulation Engine | Earlier-generation quality/coordination/enterprise/cross-tenant/risk/scenario systems, composed by newer specialists rather than replaced | Various | Active, but candidates for consolidation review (Technical Debt TD-07) |
| Mobile (`mobile.py`, P18) | Offline inspection, scan capture, device sessions | Mobile Lead | Active |
| Retention/consent (`retained_image.py`, `retention_policy.py`, `consent_record.py`) | Opt-in image retention, GDPR/PIPEDA consent | Compliance | Active |

## Module Boundary Verification (Objective 5)

Spot-checked against the brief's examples:

- **Veritas — Evidence Integrity only.** Confirmed: Veritas never writes a conclusion for Aegis/Vulcan/Sage, only references their output by ID.
- **Vulcan — Instrument Reliability only.** Confirmed, with one caveat: Vulcan also *authors* the Aegis process-variation signal (`vulcan_aegis_integration_service.py`) since no Aegis specialist exists. This is a boundary blur worth a formal decision (promote Aegis to its own specialist, or document Vulcan's authorship of it as permanent) — see Technical Debt Register TD-08.
- **Council — Decision Support only.** Confirmed: Council performs no independent analysis; every conclusion is sourced from a named specialist call.
- **Execution Engine (Steward) — Task execution only.** Confirmed: Steward's own docstring is explicit that it "never re-decides anything."
