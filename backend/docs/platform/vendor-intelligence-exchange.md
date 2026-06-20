# Vendor Intelligence Exchange & Manufacturer Collaboration Network (P6)

## Overview

The Vendor Intelligence Exchange (P6) extends LumenAI's enterprise platform with a
cross-hospital intelligence layer that enables healthcare networks to benchmark vendor
and manufacturer performance without exposing protected health information or raw
tenant data. It builds on the P5 benchmarking engine to provide:

- Per-vendor scorecards with composite quality scores (0–100)
- Manufacturer baseline quality tracking and defect trend analytics
- Anonymized shared defect signals aggregated across all contributing hospitals
- Cross-hospital instrument risk patterns with recommended corrective actions
- Real-time recall management (FDA, manufacturer, and internal sources)
- CAPA effectiveness measurement per tenant
- Executive intelligence dashboard combining all P6 signals

---

## Data Ownership Model

Each piece of data belongs to exactly one tenant. Vendor scorecards, manufacturer
scorecards, defect trends, response metrics, and recall impact assessments are all
scoped to `tenant_id`. No tenant can read another tenant's scoped rows.

The only data that crosses tenant boundaries are **anonymized aggregate signals**:

| Table | Tenant-scoped? | Contains hospital IDs? |
|---|---|---|
| vendor_scorecards | Yes | No |
| vendor_defect_trends | Yes | No |
| manufacturer_scorecards | Yes | No |
| shared_defect_signals | No (global) | Never |
| cross_hospital_trends | No (global) | Never |
| instrument_risk_patterns | No (global) | Never |
| recall_events | Yes (or global advisory) | No |

---

## Tenant Isolation Boundaries

1. Every DB query that touches a tenant-scoped table MUST filter by `tenant_id`.
2. Service functions that operate on global aggregates (`get_shared_defect_signals`,
   `get_instrument_risk_patterns`, `get_cross_hospital_trends`) do NOT accept a
   `tenant_id` parameter and MUST NOT join against tenant-scoped tables.
3. API routes validate `tenant_id` from the authenticated request context — not from
   caller-supplied query params directly (the auth middleware resolves the tenant).
4. No route response may include a raw `hospital_id` or another tenant's `tenant_id`.

---

## Data-Sharing Permission Model (Opt-In)

Hospitals contribute to the shared defect signal pool only through an explicit
opt-in flag on their `EnterpriseFacility` record (`share_signals = True`). The
default is **off**. Only aggregate counts are written to `shared_defect_signals`;
the contributing facility is never stored.

---

## Cross-Hospital Anonymization Rules

1. `SharedDefectSignal.occurrence_count` stores the aggregate count of events; no
   per-hospital breakdown is ever persisted.
2. `CrossHospitalTrend.hospital_count_contributing` stores the *number* of
   contributing facilities, never their identifiers.
3. `InstrumentRiskPattern.hospital_count_affected` is likewise an anonymized count.
4. `RecallImpactAssessment.affected_hospitals_count` is anonymized.
5. Any analytics function that would reduce a cross-hospital aggregate to fewer than
   3 hospitals MUST suppress the result (k-anonymity floor = 3).

---

## Audit Requirements

Every intelligence-sharing action MUST write a record to the `audit_logs` table:

| Action | audit `action_type` | audit `resource_type` |
|---|---|---|
| Vendor scorecard computed | `vendor_scorecard_computed` | `vendor_scorecard` |
| Manufacturer scorecard computed | `manufacturer_scorecard_computed` | `manufacturer_scorecard` |
| Shared defect signals read | `shared_defect_signals_read` | `intelligence_signal` |
| Recall list retrieved | `recall_list_read` | `recall_event` |
| Intelligence dashboard generated | `intelligence_dashboard_generated` | `intelligence_dashboard` |
| CAPA effectiveness computed | `capa_effectiveness_computed` | `capa_effectiveness` |

---

## Compliance Considerations

### HIPAA
- No PHI (patient identifiers, dates of service, diagnosis codes) is stored in any
  P6 model. Instrument serial numbers are stored only within tenant-scoped rows and
  are never included in cross-hospital aggregates.
- Role-based access enforced via `require_enterprise_auth` on every endpoint.

### Joint Commission
- Vendor performance scorecards support documentation required for the Joint
  Commission's supply chain management standards (LD.04.01.05, EC.02.02.01).
- Recall tracking supports the environment-of-care recall response requirements.

### FDA 21 CFR Part 11
- All intelligence-sharing actions are audit-logged with timestamp, actor, and
  resource (immutable audit trail).
- Recall events carry a `source` field and `source_url` to maintain traceability
  back to the original FDA MedWatch or manufacturer notice.
- CAPA effectiveness metrics feed back into the existing P2/P3 CAPA workflow audit
  trail.

---

## P6 Component Map

```
backend/
  app/
    models/
      vendor_intelligence.py       # All P6 SQLAlchemy ORM models
    schemas/
      vendor_intelligence.py       # Pydantic request/response schemas
    services/
      vendor_intelligence_engine.py  # Computation engine (DB + mock fallback)
    routes/
      vendor_intelligence.py       # GET /api/vendor-intelligence/...
      manufacturer_intelligence.py # GET /api/manufacturer-intelligence/...
      intelligence.py              # GET /api/intelligence/...
  docs/
    platform/
      vendor-intelligence-exchange.md  # This file

frontend/
  src/
    components/
      VendorIntelligenceDashboard.tsx  # 3-tab executive intelligence UI

backend/
  tests/
    test_p6_intelligence.py        # 60+ comprehensive tests
```
