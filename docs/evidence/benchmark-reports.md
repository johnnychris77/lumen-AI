# Benchmark Reports

## Status: infrastructure ready, publishable benchmarks pending sufficient contributing facilities

LumenAI's network benchmarking infrastructure (Phase 15) is built and
tested:

- `app/models/network_benchmark.py` — benchmark computation and storage
- `app/models/instrument_registry.py` — network-wide instrument
  aggregates (`network_inspection_count`, `network_defect_rate`,
  `network_pass_rate`), gated by `contributing_facilities` — the registry
  deliberately withholds publishing an aggregate until enough facilities
  have contributed to make anonymization meaningful (a benchmark from
  one or two facilities is not really anonymous)
- `app/models/global_intelligence.py` — cross-hospital signal
  aggregation, anonymized at the point of aggregation per the CLAUDE.md
  constraint that hospital identities are never exposed in cross-hospital
  intelligence

## What's required before a benchmark is publishable here

1. A minimum number of contributing facilities per instrument
   category/finding type (the exact threshold is set per
   `contributing_facilities` — publish only once this crosses the
   platform's minimum anonymization threshold).
2. Every contributing facility's identity anonymized in the published
   output — no hospital name, tenant ID, or facility-identifying detail
   in a published benchmark report.
3. An audit trail of the aggregation itself
   (`app/audit.py::log_audit_event`, `compliance_flag=True` for any
   intelligence-sharing action, per CLAUDE.md).

## What a benchmark report entry looks like once published

```markdown
### [Instrument category] — [Finding type] Benchmark

**Contributing facilities:** N (minimum threshold met)
**Period:** [date range]
**Network defect rate:** X% (anonymized aggregate)
**Network pass rate:** Y%
**Percentile context:** how an individual facility's own rate compares
(via the facility's own dashboard — the published report itself never
identifies which facility is where in the distribution)
```

## Current state

As of this document's creation, no benchmark report meets the
contributing-facility threshold for publication — this is expected at
this stage of platform adoption, not a defect. As more tenants onboard
(see `docs/customer/implementation-timeline.md`) and opt into network
intelligence sharing (`app/models/global_intelligence.py::GSINParticipant`
consent), this section will be populated with real, anonymized benchmark
reports.
