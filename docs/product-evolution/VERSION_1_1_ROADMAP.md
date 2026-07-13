# LumenAI — Version 1.1 Roadmap

Built exclusively from the Approved and Planned items in `docs/product-evolution/PRODUCT_BACKLOG.md`. Honestly framed: this is a **pre-pilot hardening roadmap**, not yet a customer-driven roadmap in the fullest sense this program's mission describes — because no real customer has used the product yet. It becomes genuinely customer-driven the moment the "Pilot Requested" backlog category receives its first real entry.

## Roadmap sequencing

### Stage 1 — Clinical-safety and explainability completeness (highest priority)
- FR-001: Reachable Supervisor Approve/Return Action
- FR-007: Mount Orphaned Veritas Panel / Wire GuardianX Tab
- FR-008: Bind Human-Review-Required Disclaimer to Real Flag

**Rationale**: these three items directly close the gap between the platform's stated patient-safety/explainability governance principles and what a real user can actually observe and act on in the UI. Per this program's Definition of Done ("every enhancement is evidence-driven, customer-validated, clinically reviewed"), these are the items with the clearest clinical review already on record (`docs/clinical-validation/`) and should ship first, before any real pilot begins, so the pilot itself starts from a platform that matches its own safety narrative.

### Stage 2 — Navigation and workflow consolidation
- FR-003: Wire Orphaned Routes into Primary Navigation
- FR-002: Consolidate the Three Inspection-Creation Flows

**Rationale**: these reduce onboarding friction and the risk of contradictory training material — directly relevant before any pilot's technician-training phase begins (see `docs/demo-program/TRAINING_GUIDE.md`'s dependency on a single, unambiguous inspection flow).

### Stage 3 — Performance hardening
- FR-005: Fix Atlas Enterprise Dashboard N+1 Query Pattern
- FR-006: Consistent AI Inference Queuing

**Rationale**: lowest clinical risk, real and verified findings, but only performance-relevant at real usage scale — appropriately sequenced after the clinical/workflow items above.

### Stage 4 — Data model and reporting (Planned/Research)
- FR-009: Add Missing `Inspection` Model Fields
- FR-004: Consolidate Duplicated Dashboard KPIs
- FR-010: Add Missing Aggregate Reports (pending sub-item scoping)

**Rationale**: real, valuable, but requires more design work (a real Alembic migration for FR-009, a KPI-source-of-truth design for FR-004, individual scoping for FR-010's 7 sub-reports) before implementation should begin.

## What this roadmap explicitly does not include

Per this program's architecture-preservation mandate, this roadmap contains **zero new AI specialists, zero new modules, and zero changes to the frozen Version 1.0 architecture** — every item is a fix, a consolidation, or a UI-wiring change to already-existing backend capability. This is a deliberate, evidence-driven constraint, not an oversight: this program's own review discipline (Phases "Foundation" through "Sustain") repeatedly found that the platform's real problem is fragmentation and incompleteness, not a shortage of capability — so Version 1.1's roadmap correctly emphasizes completion and consolidation over addition.

## The one item this roadmap cannot yet plan

A genuinely customer-driven Version 1.1 feature set — the kind this program's mission statement describes — cannot be roadmapped today because the evidence for it doesn't exist yet. This roadmap should be revisited and re-prioritized against real "Pilot Requested" backlog entries as soon as the first real customer pilot produces them, per `docs/product-evolution/CUSTOMER_FEEDBACK_REPORT.md`'s recommendation.
