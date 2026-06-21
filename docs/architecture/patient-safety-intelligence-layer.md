# Patient Safety Intelligence Layer — Architecture

> **DISCLAIMER**: LumenAI's Patient Safety Intelligence Layer identifies *potential associations* between instrument quality signals and patient safety events for human review purposes. It does **not** establish, imply, or claim causation. All outputs require human clinical and quality review before any action is taken.

---

## 1. Position in the LumenAI Stack

The Patient Safety Intelligence Layer sits above all existing intelligence modules as an aggregation and correlation layer:

```
┌──────────────────────────────────────────────────────────────────┐
│               Patient Safety Intelligence Layer (P16)            │
│  Correlation Engine · Risk Tier · Human Review Queue · CAPA      │
└────────────┬──────────┬──────────┬───────────┬───────────────────┘
             │          │          │           │
     ┌───────┴──┐ ┌─────┴────┐ ┌──┴──────┐ ┌─┴────────────────┐
     │Inspection│ │Baseline  │ │Vendor   │ │Predictive Failure│
     │Intell.   │ │Intell.   │ │Intell.  │ │Analytics (P6)    │
     └──────────┘ └──────────┘ └─────────┘ └──────────────────┘
     ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌──────────────────┐
     │Regulatory│ │Copilot   │ │Digital  │ │National Network  │
     │Automation│ │(P9)      │ │Twin(P10)│ │Benchmarking(P15) │
     └──────────┘ └──────────┘ └─────────┘ └──────────────────┘
```

### Upstream data sources consumed by this layer

| Source Module | Signal type |
|---|---|
| Inspection Intelligence | Contamination findings, override events, repeat failures |
| Baseline Intelligence | Baseline deviations, cycle parameter drift |
| Vendor Intelligence | Vendor scorecard declines, procurement risk |
| Predictive Failure Analytics | Instrument failure predictions |
| Regulatory Automation | Unresolved CAPAs, accreditation gaps |
| National Network | Cross-facility recall signals, industry benchmarks |
| External Connectors | SafeCare, RLDatix, MIDAS, VigiLanz, ICNet, CensiTrac |

---

## 2. Data Flow

```
Inspection Findings
        │
        ▼
  Quality Signal                   External Events
  (InstrumentQualitySignal)  ◄──── (ExternalEventImport)
        │
        ▼
  Correlation Engine
  (patient_safety_engine.py)
   - Group by (instrument_id, event_type)
   - Recurrence detection → NearMissCorrelation
   - Risk tier assignment
        │
        ├──► Risk Tier: critical/high
        │         │
        │         ▼
        │    ExecutiveRiskSignal
        │    (Executive Review Queue)
        │
        ├──► Recurrence count ≥ 2
        │         │
        │         ▼
        │    NearMissCorrelation
        │    (Near Miss Review Queue)
        │
        ├──► Infection Prevention feed
        │         │
        │         ▼
        │    InfectionPreventionSignal
        │    (IP Team Review Queue)
        │
        └──► CAPA tracking
                  │
                  ▼
             CAPAEffectivenessSignal
             (Quality Team Review)
                  │
                  ▼
           Human Review Queue
           (pending → under_review → reviewed → closed)
```

---

## 3. External System Integration Points

| System | Category | Integration Method |
|---|---|---|
| CensiTrac, SPM, ReadySet, Abacus | SPD Tracking | REST API / CSV import |
| SafeCare, RLDatix, MIDAS, Verge Health | Quality/Event Reporting | REST API / webhook |
| ICNet, VigiLanz, Theradoc | Infection Prevention | HL7 FHIR / REST API |
| VendorMade | Vendor/Manufacturer | REST API |
| Epic, Cerner (future) | EHR | HL7 FHIR (de-identified only) |

All external events are de-identified before storage. Raw payload SHA-256 hash is stored for audit; raw payload is discarded.

---

## 4. Privacy and De-identification Model

- **No patient identifiers** are stored in any signal model. Fields `patient_id`, `mrn`, `dob`, `patient_name`, `ssn` are explicitly prohibited.
- External events containing patient identifiers must be de-identified at the connector layer before `ExternalEventImport` is created.
- Instrument, procedure type, and pathogen context are retained as quality markers only.
- All `ExternalEventImport` records carry `de_identified=True` flag; connector must set `False` if de-identification failed and event must not be processed.

---

## 5. Governance: Association-not-Causation Principle

LumenAI **never** claims that an instrument caused a patient harm event. All signals use qualified language:

- **Required**: "potential association", "flagged for review", "review candidate", "may be associated", "linked for investigation"
- **Prohibited**: "caused", "resulted in", "responsible for", "proven link"

Every API response and dashboard includes the disclaimer:
> *"These signals represent potential associations for human review. They do not establish causation."*

All signals carry `human_review_required: true`.

---

## 6. Human Review Requirement

Every signal created by this layer:
1. Has `human_review_required = True` (immutable at creation)
2. Enters the queue with `human_review_status = "pending"`
3. Must be reviewed by a qualified clinical or quality professional before action
4. Review workflow: `pending → under_review → reviewed → closed`
5. Reviewer identity and timestamp are recorded in `reviewed_by` / `reviewed_at`

---

## 7. Audit Trail Architecture

Every action in the Patient Safety Intelligence Layer creates an audit event via `log_audit_event()`:

| Action | `action_type` |
|---|---|
| View signal list | `patient_safety.signals.list` |
| View signal detail | `patient_safety.signals.detail` |
| Run correlation engine | `patient_safety.correlate` |
| View near misses | `patient_safety.near_misses.list` |
| View executive risks | `patient_safety.executive_risk.list` |
| Import external events | `patient_safety.events.import` |
| View dashboard | `patient_safety.dashboard.view` |
| View infection prevention | `patient_safety.infection_prevention.list` |
| View CAPA effectiveness | `patient_safety.capa_effectiveness.list` |

Audit events include: `tenant_id`, `actor_email`, `action_type`, `resource_type`, `resource_id`, `details`, `timestamp`.

---

## 8. Tenant Isolation

All signal models include `tenant_id` (indexed). Every query is filtered by the authenticated tenant's ID derived from `get_request_tenant_id(request)`. Cross-tenant signal visibility is architecturally impossible via the API layer.
