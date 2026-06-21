# Autonomous Healthcare Quality Intelligence Network
## Architecture Document — P21

**Status:** Active  
**Governance Level:** Human-Supervised — All outputs require human review before action  
**Association Policy:** All intelligence outputs use association-not-causation language  

---

## Overview

The Autonomous Healthcare Quality Intelligence Network (P21) provides multi-tenant signal
ingestion, risk scoring, investigation coordination, preventive action recommendations, and
executive intelligence dashboards for SPD quality management.

All outputs are advisory only. No autonomous clinical or operational decisions are made.
Every signal, recommendation, and dashboard metric requires human quality review.

---

## Data Flow Diagram (ASCII)

```
External Data Sources
┌─────────────────────────────────────────────────────────────────┐
│  Inspection Events │ CAPA Records │ Recall Signals │ Vendor Data │
└─────────┬──────────┴──────┬───────┴───────┬────────┴──────┬─────┘
          │                 │               │               │
          ▼                 ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│              Signal Ingestion Pipeline                          │
│   • Tenant-scoped ingestion (all data filtered by tenant_id)   │
│   • Event normalization and deduplication                       │
│   • Source tagging (inspection/capa/recall/vendor/manufacturer) │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Risk Scoring Algorithm                             │
│   • Confidence score: 0.0 – 1.0 (statistical estimate only)   │
│   • Tier: low (<0.4) / medium (0.4–0.7) / high (>0.7)         │
│   • All tiers require human review — no autonomous action       │
│   • Trend direction: increasing / stable / decreasing           │
│   • association_reason field required on every signal           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Enterprise Risk Graph                              │
│   EnterpriseRiskNode: instrument/tray/vendor/manufacturer/      │
│                       capa/recall/safety_event/facility         │
│   EnterpriseRiskEdge: linked_to/reported_in/associated_with/   │
│                       escalated_by/investigated_by              │
│   • Graph traversal surfaces cross-entity risk patterns         │
│   • All graph relationships tagged as "potential association"   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Emerging Risk Signal Detection                     │
│   EmergingRiskSignal:                                           │
│   • signal_type: recurring_contamination / baseline_deviation   │
│                  / capa / safety_event / vendor / manufacturer  │
│   • confidence_score with disclaimer                            │
│   • association_reason (required, non-null)                     │
│   • human_review_required: True (always)                        │
│   • status: open → under_review → resolved / dismissed          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Investigation Coordination                         │
│   QualityInvestigationP21:                                      │
│   • Linked to EmergingRiskSignal (signal_id FK)                 │
│   • Links to CAPA IDs and Recall IDs (JSON lists)              │
│   • Priority: low / medium / high / critical                    │
│   • Status: open → in_progress → resolved → closed             │
│   • assigned_to: human quality team member                      │
│   • human_review_required: True (always)                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Recommendation Engine                              │
│   PreventiveActionRecommendation:                               │
│   • Types: inspection_frequency / vendor_review /               │
│            instrument_retirement / training_intervention /      │
│            capa_review                                          │
│   • status: pending_review → accepted / rejected / implemented  │
│   • All recommendations: pending_review until human approves    │
│   • reviewed_by + reviewed_at required for status change        │
│   • effectiveness_score tracked post-implementation             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Executive Intelligence Layer                       │
│   • Executive summary by role (quality_director / CNO / CEO)   │
│   • KPI dashboard: total_signals / open_investigations /        │
│                    pending_recommendations / high_confidence     │
│   • human_review_required_count always equal to total_signals   │
│   • Disclaimer on every response                                │
│   • No autonomous reporting — human sign-off required           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Descriptions

### Signal Ingestion Pipeline

Ingests quality events from inspection records, CAPA workflow, recall signals, vendor
scorecards, and external safety event integrations. All events are scoped to a single
tenant (tenant_id filter enforced at every query layer). Events are normalized into
EmergingRiskSignal records with mandatory association_reason and human_review_required
fields.

### Risk Scoring Algorithm

Assigns a confidence_score (0.0–1.0) to each signal using deterministic seeded logic
or DB-driven pattern analysis. Scores are presented with a disclaimer: they are statistical
estimates, not clinical determinations. All confidence tiers (low < 0.4, medium 0.4–0.7,
high > 0.7) require human review. Trend direction (increasing/stable/decreasing) is
tracked across signal types.

### Enterprise Risk Graph

Nodes represent entities (instruments, trays, vendors, manufacturers, recalls, safety
events, facilities, service lines). Edges represent relationships with typed labels
(linked_to, reported_in, associated_with, escalated_by, investigated_by) and a weight
field for relationship strength. Graph is tenant-scoped. Risk scores on nodes represent
potential association strength — not confirmed risk.

### Investigation Coordination

QualityInvestigationP21 records coordinate human-led quality investigations. Each
investigation links to an EmergingRiskSignal and optionally to CAPA and recall records.
Assignment, priority, evidence notes, and resolution notes are tracked. Status lifecycle
is managed through the PATCH /investigations/{id} endpoint with full audit logging.

### Recommendation Engine

Generates preventive action recommendations from signal patterns. All recommendations
are in pending_review status until a human quality reviewer accepts or rejects them via
the POST /recommendations/{id}/review endpoint. Recommendations include rationale and
confidence_score with disclaimer. Implementation effectiveness is tracked via
effectiveness_score after human-approved implementation.

### Executive Intelligence Layer

Role-scoped executive summaries aggregate KPIs for quality directors, CNOs, and CEOs.
Every summary response includes disclaimer, human_review_required, and governance_note
fields. The dashboard endpoint provides consolidated KPIs:
total_signals, open_investigations, pending_recommendations, high_confidence_signals,
human_review_required_count.

---

## Governance Constraints

1. **No autonomous decisions.** The system never takes clinical or operational action.
   All outputs are advisory and require human approval.

2. **Association-not-causation language.** All signal descriptions, recommendations, and
   summaries use: "elevated risk", "emerging signal", "review recommended",
   "potential association", "investigation candidate". Words like "caused", "led to",
   "resulted in" are prohibited.

3. **human_review_required = True always.** This field is hardcoded True on all model
   fields and all API responses. It cannot be set to False by any API call.

4. **Tenant isolation.** Every query filters by tenant_id. Cross-tenant data access is
   architecturally prevented at the service and route layer.

5. **Audit logging.** Every API call generates an audit log entry via log_audit_event().
   Signal creation, investigation updates, and recommendation reviews are all logged.

6. **association_reason required.** Every EmergingRiskSignal must have a non-null
   association_reason field explaining the statistical basis for the signal.

7. **No patient identifiers.** Intelligence outputs do not include patient_id, mrn, dob,
   ssn, or patient_name fields. Governance tests enforce this at the response level.
