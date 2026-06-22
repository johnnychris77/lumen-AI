# LumenAI Instrument Lifecycle Intelligence

> **Audience:** SPD leadership, supply chain, and clinical engineering. Defines how LumenAI tracks the full instrument lifecycle — acquisition through retirement — and how anonymized lifecycle benchmarks are published to the network. No FDA/regulatory/causation claims.

---

## 1. Purpose

Give every SPD department a complete, structured view of each instrument's journey — from acquisition to retirement — and benchmark that journey against anonymized network intelligence to identify replacement patterns, repair costs, and failure trends before they become clinical or compliance risks.

---

## 2. Lifecycle Stages

```
acquired → [inspected] → [repaired] → replacement_recommended → retired
                                                                     ↑
                                            recalled ────────────────┘
```

Each stage transition is an **immutable lifecycle event** — events are never edited or deleted, creating a complete, auditable instrument history.

| Event Type | Description |
|------------|-------------|
| `acquired` | Instrument enters inventory |
| `inspected` | Inspection performed; outcome: pass / fail |
| `repaired` | Repair performed; type and cost captured |
| `replacement_recommended` | Reviewer recommends replacement |
| `retired` | Instrument permanently removed from service |
| `recalled` | Instrument status set to recalled |

---

## 3. Lifecycle Analytics

Each lifecycle record tracks:

| Field | Meaning |
|-------|---------|
| `total_inspections` | Cumulative inspection count |
| `total_defects_found` | Inspections with fail outcome |
| `defect_rate` | `total_defects / total_inspections` (rolling) |
| `total_repairs` | Cumulative repair count |
| `estimated_remaining_cycles` | Human-entered estimate for planning |
| `lifecycle_status` | Current stage |

These are **tenant-scoped** — no cross-tenant raw data is accessible.

---

## 4. Network Lifecycle Benchmarks

Anonymized cross-network benchmarks are published at the **instrument category level** (e.g., laparoscopes, trocars, forceps). k-anonymity floor of 5 enforced; Laplace noise applied.

Representative benchmark metrics:

| Metric Name | Definition |
|-------------|------------|
| `median_lifespan_cycles` | p50 of total inspections at retirement |
| `repair_rate` | Network median repairs per inspection cycle |
| `defect_rate` | Network median fail rate per inspection |
| `time_to_replacement_days` | Median days from first inspection to retirement |

---

## 5. Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/network-intelligence/lifecycle/instruments` | Create lifecycle record |
| `GET /api/network-intelligence/lifecycle/instruments?tenant_id=` | List instruments (tenant-scoped) |
| `POST /api/network-intelligence/lifecycle/events` | Log lifecycle event |
| `GET /api/network-intelligence/lifecycle/events?tenant_id=&instrument_uid=` | Full event history |
| `POST /api/network-intelligence/lifecycle/benchmarks` | Publish a pre-computed anonymized benchmark (k-floor enforced) |
| `POST /api/network-intelligence/lifecycle/benchmarks/compute` | **Derive** a benchmark from contributed lifecycle records (opt-in + k-floor + Laplace noise enforced in code) |
| `GET /api/network-intelligence/lifecycle/benchmarks` | List published benchmarks |

### Computed Benchmarks (opt-in enforced)

`POST /lifecycle/benchmarks/compute?instrument_category=&metric_name=` is the link between contributed data and published intelligence:

- Aggregates `InstrumentLifecycleRecord` rows **only from tenants with an active benchmark-scoped sharing agreement** — opt-in is enforced, not decorative
- k-anonymity floor of 5 is measured on **distinct contributing facilities**, not row count
- **Laplace noise is applied in code** (`noise_applied` is truthful, not a hardcoded flag)
- Supported metrics: `defect_rate`, `repair_rate`, `median_lifespan_cycles`

---

## 6. Governance

| Principle | Enforcement |
|-----------|-------------|
| Tenant isolation | Lifecycle records and events are tenant-scoped; no cross-tenant reads |
| Immutability | Events are append-only; no edits or deletes |
| Anonymization | Network benchmarks use k-anonymity floor of 5 + Laplace noise |
| Human review | Replacement recommendations require human sign-off before action |
| Audit trail | Every event creation is compliance-flagged in the audit log |
| No causation | Benchmark deviations are candidate signals — not causation findings |

---

## 7. Roadmap

| Horizon | Milestone |
|---------|-----------|
| Q1–Q2 | Lifecycle record + event log live at pilot sites |
| Q3–Q4 | Network benchmarks published (≥5 facilities contributing) |
| Year 2 | Predictive replacement signals (human-reviewed candidate alerts) |

---

*LumenAI does not claim FDA clearance or regulatory approval. All lifecycle analytics and network benchmarks are decision-support indicators requiring human review.*
