# Project Atlas — Multi-Site Governance: Watchlists, Alerts & RBAC

LumenAI v3.1 — Sections 4, 8 & 10

## Enterprise Watchlists (Section 4)

### Endpoints

```
GET  /api/atlas/watchlist/{system_id}
POST /api/atlas/watchlist/{system_id}/refresh
POST /api/atlas/watchlist/{system_id}/{entry_id}/resolve
```

### Architecture

`backend/app/services/atlas_watchlist_service.py`

`EnterpriseWatchlistEntry` is system_id-scoped (spans tenant_ids), distinct
from Sentinel's tenant-scoped `ClinicalWatchlistEntry`. It carries an
explicit `direction` field (`risk` or `improvement`) because two of the
eight watchlist types this sprint asks for — Highest Knowledge Growth and
Fastest Improvement — are positive-trend signals, not risk flags, and
conflating them into a single risk score would misrepresent them.

Eight watchlist types, refreshed idempotently (`_upsert` keyed on
`entity_type` + `entity_value`, so re-running `refresh` updates existing
entries rather than duplicating them):

| Entity type | Direction | Basis |
|---|---|---|
| `hospital` | risk | Latest `FacilityIntelligenceSnapshot.risk_score` ≥ 60 |
| `instrument_family` | risk | ≥3 condition findings on a resolved instrument family, system-wide, in 90 days |
| `manufacturer` | risk | Deprecated `BaselineLibraryEntry` rows for that manufacturer |
| `facility_repair` | risk | ≥3 `RepairRequest`s at a facility in 90 days |
| `facility_reclean` | risk | ≥3 `REPROCESS` dispositions at a facility in 90 days |
| `knowledge_growth` | improvement | ≥1 new `KnowledgeArticle` authored at a facility in 90 days |
| `fastest_improvement` | improvement | Quality score improved ≥5 points between the two most recent snapshots |
| `emerging_trend` | risk | A Sentinel risk signal type (`sentinel_risk_monitor_service.list_open_signals`) recurring across ≥2 facilities |

## Enterprise Alerts (Section 8)

### Endpoints

```
GET  /api/atlas/alerts/{system_id}
POST /api/atlas/alerts/{system_id}/generate
POST /api/atlas/alerts/{system_id}/{alert_id}/acknowledge
POST /api/atlas/alerts/{system_id}/{alert_id}/resolve
```

### Architecture

`backend/app/services/atlas_alert_service.py`

Every alert is explainable — never a bare severity number. Each `Enterprise
Alert` carries a `narrative` (what was observed), a `recommendation` (what
to do), and a `reasoning` field (why this is enterprise-relevant, not just
facility-level noise). Three alert sources, generated from what
`atlas_watchlist_service`/`atlas_analytics_service` already found (never
re-derived):

- **Emerging trend** watchlist entries → "a market-wide or system-wide
  cause is more likely than N unrelated local causes."
- **Highest-risk hospital** entries (score ≥ 0.8) → critical-severity
  escalation recommendation.
- A ≥5-point drop in the system-wide `supervisor_agreement_rate` trend
  (from `atlas_analytics_service.enterprise_trend`) between the two most
  recent periods → flags a possible model- or process-level cause.

Idempotent via `_already_alerted`: re-running `generate` never creates a
second open alert with the same title while one is still unresolved.

## Governance / RBAC (Section 10)

### Endpoints

```
POST /api/atlas/roles/grant
GET  /api/atlas/roles/{user_email}
POST /api/atlas/roles/{assignment_id}/revoke
GET  /api/atlas/roles/access-check
```

### Architecture

`backend/app/services/atlas_rbac_service.py`

There is no central role registry anywhere else in this codebase — four
independent auth modules (`authz.py`, `enterprise_auth.py`,
`tenant_authz.py`, `portfolio_authz.py`) each declare their own ad hoc role
strings, checked per-route with no shared enum. Atlas doesn't replace that
(out of scope for this sprint); every Atlas route still gates on the same
base four roles (`admin`, `spd_manager`, `operator`, `viewer`) via
`require_roles`, exactly like every prior sprint's routes.

What Atlas adds is a second, additive layer: `EnterpriseRoleAssignment`
scopes one of the seven Atlas-specific roles (Regional Administrator,
Market Director, Facility Director, SPD Manager, Supervisor, Technician,
Viewer) to a specific node in the existing organization hierarchy — system,
market, or facility. `user_has_scope_access` implements hierarchical
inheritance: a role granted at the system level implies access to every
market and facility under that system; a market-level grant implies access
to every facility in that market. This makes "Market Director for market
X" a real, checkable fact rather than a flat role string with no notion of
which market.

Granting a role is audit-logged (`atlas.role_granted`), consistent with
this platform's rule that every governance action creates an audit event.
