# Security & Governance — National SPD Intelligence Network

## 1. Anonymization Controls

### Pseudonym Rotation
- Facility IDs replaced with `SHA-256(facility_id + monthly_salt)[:12]` before any cross-tenant storage
- Salt rotated monthly; pseudonyms from prior months cannot be linked to current pseudonyms without the historical salt
- See `anonymization-specification.md` for full technical details

### K-Anonymity (k ≥ 5)
- No metric published unless ≥ 5 facilities contributed
- Enforced at the service layer before API response construction
- Suppressed values return `null`; boolean `suppressed: true` flag included

### Differential Privacy
- Laplace noise (ε = 0.1) applied to all published rates
- Applied after k-anonymity check, before serialization
- Noise makes individual facility contribution mathematically undetectable

---

## 2. Tenant Isolation

### Architecture Guarantee
- Network intelligence queries operate exclusively on pre-aggregated, anonymized tables (`industry_benchmarks`, `recall_signals`, `registry_instruments`)
- Network queries **never** join across tenant raw data tables (`inspections`, `audit_logs`, tenant-scoped tables)
- SQLAlchemy ORM models for network tables contain no foreign keys to tenant-scoped tables

### Enforcement Points
1. **Route layer**: `_require_participant()` checks opt-in status before granting access
2. **Service layer**: aggregate functions query only anonymized aggregate tables
3. **DB layer**: network tables have no referential integrity to tenant tables (by design)

### What Is Permissible
- Tenant sees their own raw data (full access within their tenant boundary)
- Tenant sees anonymized network aggregates (benchmarks, recall signals, registry stats)
- Tenant sees their own percentile rank (computed without revealing peer values)

### What Is Prohibited
- Tenant A querying Tenant B's inspections — blocked by tenant_id scoping on all raw tables
- Cross-tenant joins at the DB level — no foreign keys exist between network and tenant tables
- Deriving peer identities from aggregate data — prevented by k-anonymity + Laplace noise

---

## 3. Audit Logging

### Every Network Data Access Is Logged
All network route handlers call `log_audit_event()` with:
- `tenant_id`: the requesting tenant (stored in audit log, never in network response)
- `action_type`: namespaced as `network.<action>` (e.g., `network.benchmarks_viewed`)
- `resource_type`: the network resource accessed
- `timestamp`: UTC timestamp of access
- `compliance_flag`: set to `True` for FDA escalation actions

### Logged Events

| Action | audit action_type | compliance_flag |
|--------|-------------------|-----------------|
| Opt in to network | `network.opt_in` | false |
| Opt out of network | `network.opt_out` | false |
| View benchmarks | `network.benchmarks_viewed` | false |
| View my percentile | `network.my_percentile_viewed` | false |
| View recall signals | `network.recall_signals_viewed` | false |
| View signal detail | `network.recall_signal_detail_viewed` | false |
| Escalate signal to FDA | `network.recall_signal_escalated_to_fda` | **true** |
| Lookup instrument | `network.registry_lookup` | false |
| Register instrument | `network.registry_register` | false |
| View defect history | `network.defect_history_viewed` | false |
| Submit baseline | `network.baseline_submitted` | false |
| Approve baseline | `network.baseline_approved` | **true** |

### Log Retention
- Network audit logs retained for 7 years (same as core audit trail)
- Logs are immutable per existing audit chain design

---

## 4. Access Controls

### Network Endpoints Require Enterprise Tier
All `/api/network/*` endpoints call `require_enterprise_auth(request)` — enforced via Bearer token validation. The dev-token bypass is intentional for non-production environments only.

### Manufacturer/Vendor Dashboards
- `GET /api/network/dashboard/manufacturer` — requires auth; manufacturer identity from `X-Manufacturer-ID` header in production
- `GET /api/network/dashboard/vendor` — requires auth; vendor identity scoped to tenant

### Network Participation Gating
- Benchmark and recall signal endpoints require active participation (`is_active = True` in `network_participants`)
- Participants who opt out immediately lose access to benchmark and recall signal data
- Public endpoint: `GET /api/network/participants/count` — no auth required; reveals only count, not identities

---

## 5. Opt-In Governance

### Participation Agreement Terms
By opting in, facilities agree to:
1. Contribute anonymized aggregate metrics to the network
2. Not attempt to re-identify peer facilities from network data
3. Accept monthly pseudonym rotation (breaking continuity of cross-facility tracking)
4. Network Participation Agreement (NPA) reviewed annually

### Exit Rights
- Facilities may opt out at any time with immediate effect
- Contributions removed from future aggregations within 24 hours
- Historical published benchmarks (computed before opt-out) cannot be retroactively removed
- All facility-specific data (pseudonyms, participation records) deleted within 30 days

### Data Retention on Exit
| Data Type | Retention After Exit |
|-----------|---------------------|
| Network pseudonym | Deleted within 30 days |
| Contribution records | Deleted within 30 days |
| Historical aggregates (published) | Retained (anonymized, cannot be attributed) |
| Audit logs of participation | Retained 7 years (compliance) |

---

## 6. Incident Response

### De-Anonymization for FDA Recall Escalation

In extreme cases (confirmed instrument safety recall), LumenAI may provide facility-specific data to FDA with dual approval:

**Process**:
1. FDA formal written request citing regulatory authority (21 CFR Part 806 or equivalent)
2. LumenAI General Counsel review and approval
3. Chief Privacy Officer review and approval
4. De-anonymization executed by two senior engineers with access logging
5. Only the specific facility records relevant to the recall are disclosed
6. All disclosed facilities notified within 24 hours of disclosure
7. Audit trail created with `compliance_flag = True`

**Safeguards**:
- Dual approval (no single-person de-anonymization)
- Scope-limited (only records relevant to specific recall, not all network data)
- Notified disclosure (facilities informed)
- Time-limited (de-anonymized data not retained beyond regulatory need)

### Security Incident (Data Breach)
1. Immediate isolation of affected network aggregation pipeline
2. Assessment: was any raw facility data exposed? (Should be impossible by architecture)
3. Notification: affected facilities within 72 hours if pseudonym-to-identity mapping compromised
4. Remediation: salt rotation to invalidate compromised pseudonyms
5. Post-incident review by data stewardship council within 30 days
