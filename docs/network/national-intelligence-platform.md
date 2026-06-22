# LumenAI National Intelligence Platform

> **Audience:** Product, clinical informatics, and strategic leadership. Defines how LumenAI builds and governs a national SPD intelligence network — under strict k-anonymity, opt-in participation, and no-causation discipline. No FDA/regulatory/causation claims.

---

## 1. Purpose

Transform LumenAI into the leading intelligence platform for sterile processing quality, instrument lifecycle management, and surgical readiness — by aggregating anonymized signals from hundreds of facilities into a national intelligence commons that benefits every participant.

---

## 2. National SPD Registry (Phase 1)

Every participating facility is represented by a **rotating pseudonym** — never by name, tenant ID, or exact address. Coarse attributes only:

| Attribute | Granularity |
|-----------|-------------|
| Facility type | hospital / health_system / asc / ltac |
| Bed count | Banded ranges ("300–499", "500+") |
| Region | Northeast / Southeast / Midwest / West / Mountain |
| Case volume | Banded ranges ("<5000", "5000–15000", ">15000") |

Participation is **opt-in, reversible, and audit-logged** via the Intelligence Sharing Agreement (`POST /api/network-intelligence/sharing-agreements`). Withdrawal removes the facility's contribution from future aggregates; it cannot retroactively alter published snapshots (immutability principle).

### Participation Tiers

| Tier | Access |
|------|--------|
| `observer` | Read-only network benchmarks |
| `contributor` | Contributes data; receives enhanced benchmarks |
| `full_member` | Contributes + receives recall early warnings + research invitations |

### Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/network-intelligence/registry` | Register facility (opt-in) |
| `GET /api/network-intelligence/registry?tenant_id=` | Own registry record |
| `GET /api/network-intelligence/registry/network-summary` | Anonymized composition (k-anonymity enforced) |
| `POST /api/network-intelligence/sharing-agreements` | Create participation agreement |
| `DELETE /api/network-intelligence/sharing-agreements/{id}` | Withdraw (reversible) |
| `POST /api/network-intelligence/aggregate-snapshots` | Capture network aggregate (k-floor enforced) |
| `GET /api/network-intelligence/aggregate-snapshots` | List aggregate history |

---

## 3. Intelligence Sharing Framework

All published intelligence outputs enforce:

- **k-anonymity floor of 5** — any aggregate below 5 active participants is suppressed
- **Laplace noise** — applied to all numeric aggregates before publication
- **Pseudonym rotation** — facility pseudonyms rotate periodically; historical mapping is governance-controlled, never published
- **No raw cross-tenant data** — participants never see each other's records; only anonymized aggregates
- **Opt-in, opt-out** — withdrawal honored in all future publications

---

## 4. Governance

| Principle | Enforcement |
|-----------|-------------|
| Opt-in only | Sharing agreement required before any data contributes to the network |
| Reversibility | Withdrawal endpoint; audit-logged |
| k-anonymity | Hard 5-participant floor on all published aggregates |
| Anonymization | Pseudonyms + coarse attributes + Laplace noise |
| Human review | Network steward approves all escalated signals |
| No causation | "Candidate signal", "investigation indicator" only — never causation |
| No regulatory claims | No FDA clearance or regulatory-approval language |
| Audit trail | Every mutation compliance-flagged in the platform audit log |

---

## 5. Success Metrics

| Metric | Target (Year 1) |
|--------|----------------|
| Registered facilities | 50+ active contributors |
| Aggregate snapshot cadence | Monthly minimum |
| Sharing agreement withdrawal rate | <5% annually |
| k-floor suppression rate | <10% of regional cuts |

---

*LumenAI does not claim FDA clearance or regulatory approval. All network intelligence outputs are anonymized aggregates requiring human review.*
