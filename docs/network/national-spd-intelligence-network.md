# National SPD Intelligence Network

## Overview

The National SPD Intelligence Network is a voluntary, opt-in data-sharing consortium for sterile processing departments (SPDs) across hospitals, health systems, and ambulatory surgery centers (ASCs). LumenAI operates as the anonymization broker — raw facility data never leaves the tenant boundary; only aggregated, de-identified metrics flow across participants.

---

## Network Topology: Hub-and-Spoke with LumenAI as Anonymization Broker

```
[Facility A] ──┐
[Facility B] ──┤──► [LumenAI Anonymization Broker] ──► [Aggregated Network Intelligence]
[Facility C] ──┤                                              │
[Facility N] ──┘                                    ┌─────────┴──────────┐
                                                     │                    │
                                             Industry Benchmarks    Recall Signals
                                             Instrument Registry    Baseline Library
```

- **Hub**: LumenAI platform — enforces anonymization, k-anonymity, differential privacy
- **Spokes**: Individual tenant facilities — contribute only aggregated, pre-processed metrics
- **Raw data never transits the hub** — tenant data stays within tenant boundaries at all times

---

## Data Sharing Model

### What Flows Across Tenants
- Aggregated metric percentiles (P25/P50/P75/P90) with Laplace noise applied
- Recall signal patterns (instrument category + finding type only, no facility info)
- Instrument registry statistics (network-level pass/defect rates per UDI)
- Approved baseline configurations (manufacturer-verified, no PII)

### What Never Flows
- Raw inspection records
- Patient identifiers or case information
- Facility names, addresses, or identifiers
- Individual staff performance data
- Exact instrument counts (only ranges)

---

## Anonymization Model

### K-Anonymity (k ≥ 5)
- No aggregate metric is published unless at least 5 distinct facilities contributed
- Cohorts with N < 5 are entirely suppressed (null returned, not suppressed value)
- Applied to: all benchmark distributions, instrument registry stats, regional cohorts

### Facility Pseudonymization
- Facility IDs replaced with rotating pseudonyms: `SHA-256(facility_id + monthly_salt)[:12]`
- Monthly salt rotated on the first of each month
- Pseudonyms are one-way — cannot be reversed without the original facility ID and salt
- Salt is stored only within LumenAI's secure key management system

### Differential Privacy
- Laplace noise added to all published rates: ε = 0.1, sensitivity = 0.01
- Applied after k-anonymity check, before serving any API response
- Noise prevents inference attacks even when N is at the minimum threshold

### Suppression Rules
- Any cell where count < 3 contributing facilities: suppressed entirely
- Any cohort where N < 5: entire distribution suppressed
- Recall signals: suppressed unless N ≥ 3 facilities reporting AND signal_strength > 0.3

---

## Governance Framework

### Network Participation Agreement (NPA)
- All participants sign the NPA before data flows
- NPA covers: data use limitations, anonymization requirements, exit rights, liability
- NPA reviewed annually by the data stewardship council

### Data Stewardship Council
- Composed of: 3 member facility representatives (rotating), 2 LumenAI data scientists, 1 independent privacy counsel
- Meets quarterly to review: anonymization effectiveness, signal quality, new metric proposals
- Approves all changes to anonymization parameters (k, ε, suppression thresholds)
- Has authority to suspend network access for policy violations

### Quarterly Audits
- External privacy audit of anonymization controls
- Statistical audit of differential privacy noise calibration
- Review of any de-anonymization requests (FDA escalation pathway)
- Published audit summary shared with all network members

---

## Participation Model

### Opt-In Only
- Facilities must explicitly opt in via `POST /api/network/opt-in`
- Default state: not participating; no data contributed or received
- Opt-in confirms acceptance of the Network Participation Agreement

### Participation Tiers

| Tier | Description | Access |
|------|-------------|--------|
| **Observer** | Read-only access to benchmarks | Can view industry benchmarks, recall signals |
| **Contributor** | Full bidirectional participation | All Observer access + contributes metrics to network |
| **Full Member** | Governance participation | All Contributor access + vote on stewardship council |

### Exit Rights
- Facilities may opt out at any time via `POST /api/network/opt-out`
- Upon opt-out: contributions removed from future aggregations within 24 hours
- Historical aggregated data (published before opt-out): cannot be retroactively removed from past benchmarks
- Facility-specific data: deleted within 30 days of opt-out per data retention policy
- Exit does not affect access to LumenAI's core SPD platform features
