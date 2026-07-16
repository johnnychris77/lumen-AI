# LumenAI — Feature Governance

**Product Evolution Program · Version 1.1: Evolution · Customer-Driven Enhancements & Continuous Innovation**

This document defines the governance process itself — the one part of this program that can be fully specified today, independent of whether real pilot evidence yet exists. It draws on real, existing governance infrastructure rather than inventing a parallel process.

## The central constraint this entire program must operate under

This program's own stated philosophy is unambiguous: *"No feature is accepted because 'It would be nice.' Every enhancement requires evidence. Evidence comes from production."* This is a real, binding constraint, not rhetorical framing — and it must be applied to this document set itself. **As of this writing, no real customer has entered a disclosed pilot** (confirmed independently by `docs/commercial-readiness/FINAL_READINESS_REPORT.md`'s Conditional-Go verdict and `docs/release-management/CUSTOMER_FEEDBACK_LOG.md`'s explicit statement that zero real feedback exists). Every document in this set states plainly where a feature candidate is backed by genuine internal review evidence (usability studies, performance metrics, security reviews, clinical validation reviews — all explicitly acceptable input sources per this program's own list) versus where "Pilot Hospital" or "Customer Feedback" evidence — the program's primary intended source — is not yet available. See `docs/product-evolution/CUSTOMER_FEEDBACK_REPORT.md` for the full accounting.

## Feature Review Board — real roles, mapped to what exists

| Board role | Real backing today |
|---|---|
| Product Management | No dedicated product-management system exists in-code; this role is organizational, not platform-enforced |
| Engineering | Represented by the real severity/change-control process in `docs/commercial-readiness/PRODUCT_OPERATIONS_GUIDE.md` (defect classification, change-control gate) |
| Clinical Leadership | Represented by the real clinical-scope discipline established across `docs/clinical-validation/` — any AI/clinical-facing enhancement must be checked against `CLINICAL_SCOPE.md`'s stated limitations before approval |
| Quality | Represented by the real CAPA/root-cause governance infrastructure (`quality_guardian.py`'s lifecycle, confirmed real in this session's regression work) |
| Security | Represented by the real, CI-blocking `pip-audit`/`npm audit` gate and the security-risk-register process (`docs/security/security-risk-register.md`) |
| Customer Success | Represented by the real customer-success playbook and health-score framework (`docs/commercial-readiness/CUSTOMER_SUCCESS_PLAYBOOK.md`) — currently has no live customer to report on |
| Architecture | Represented by the real, frozen v1.0 architecture declared in `docs/production-readiness/ARCHITECTURE_INVENTORY.md` — this board seat's job is specifically to confirm a Version 1.1 proposal **extends** rather than **replaces** that frozen architecture, per this program's own mission statement |

**Council (`council_orchestration_service.py`) is the closest real, working analog to a multi-stakeholder review board already in this codebase** — it genuinely invokes multiple specialists and requires an explicit human decision to finalize a case (confirmed in `docs/demo-program/ROLE_BASED_DEMOS.md`'s AI-specialist-chain investigation). Steward's action-lifecycle state machine (`docs/agents/steward/action-lifecycle.md`) is the closest real analog to a governed-approval pipeline with role-authority-tier gating. Neither is a literal "Feature Review Board" — no code path exists today for routing a *feature proposal* (as opposed to a clinical/operational case) through this kind of review — but both demonstrate the pattern (multi-party review, explicit human sign-off, full audit trail) that a real Feature Review Board process should follow.

## Feature Governance template — the 18 required fields

Every entry in `docs/product-evolution/FEATURE_REQUEST_REGISTER.md` must include: Feature ID, Title, Description, Problem Statement, Business Value, Clinical Value, Evidence Source, Supporting Metrics, Affected Users, Affected Modules, Security Impact, Clinical Impact, Operational Impact, Estimated Effort, Priority, Product Owner, Approval Status, Target Version. **"Evidence Source" is the field this program's philosophy makes load-bearing** — every entry must cite a specific, real document or dataset, never an unattributed assertion.

## Feature classification taxonomy

User Experience, Workflow Improvement, Performance, Security, Clinical, AI, Reporting, Dashboard, Integration, Mobile, Analytics, Documentation, Infrastructure, Administration, Enterprise — used consistently in the Feature Request Register to classify each entry.

## Backlog states and traceability

Approved, Planned, Deferred, Rejected, Research, Pilot Requested, Future Release — per `docs/product-evolution/PRODUCT_BACKLOG.md`. Every item must remain traceable to its originating evidence document, its review-board disposition, and (once approved) its target release in `docs/product-evolution/VERSION_1_1_RELEASE_PLAN.md`.

## What "architecture review" means in this governance process

Per this program's Definition of Done ("Version 1.1 extends Version 1.0. It does not replace the Version 1.0 architecture"), the Architecture board seat's approval criterion is specific and checkable: does the proposal add new tables/services/routes following the existing specialist-pattern conventions (documented in `docs/architecture/design-principles.md` and the Phase 1 `MODULE_CATALOG.md`), or does it require modifying a frozen module's core contract? Only the former is in scope for a Version 1.1 minor release; the latter would require a major-version decision outside this program's mandate.
