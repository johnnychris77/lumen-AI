# LPR-DIR-018 — Operations KPI Report (Phase 7)

## ⚠️ Status: NO PRODUCTION KPIs — PLATFORM NOT LAUNCHED

Operational KPIs require a **running production system with live traffic**. None
exists (Phase 6 withheld authorization). **All production KPI values below are NOT
AVAILABLE and are not fabricated.** What is provided instead: (a) the **KPI/SLI
definitions and proposed SLO targets** to instrument, and (b) the **only real
measurements** taken during the program (non-production, clearly labeled).

## Production KPIs (measured) — NONE

| KPI | Production value | Note |
|---|---|---|
| Availability / uptime | **NOT AVAILABLE** | no production deployment |
| API latency (p50/p95/p99) | **NOT AVAILABLE (prod)** | see non-prod note below |
| Inspection throughput | **NOT AVAILABLE** | no live tenants/inspections |
| Report generation time | **NOT AVAILABLE** | no production report runs |
| Audit integrity (prod) | **NOT AVAILABLE** | design-verified only (see below) |
| Tenant health | **NOT AVAILABLE** | no production tenants |
| Error rate (5xx) | **NOT AVAILABLE** | no production traffic |

## Non-production measurements (real, from Phases 3–4; NOT production KPIs)
- Latency (in-process TestClient, SQLite): `/health` p99 8.93 ms, `/ready` p99 15.82
  ms — **harness measurement, not production capacity** (Phase 4).
- Security/governance test subset: **50 passed, 0 failed**; audit chain + evidence
  integrity **verified by test** (Phase 3) — design-verified, not a production uptime
  figure.
- DR restore drill: **measured RTO 10.4 s** (foundation) — a recovery-time
  measurement, not an availability KPI.
- No production load test has been run (PERF-07, HIGH, open).

## KPI/SLO framework to instrument before launch (none defined today, MON-01)

| SLI | Proposed SLO (set with business) | Instrumentation needed |
|---|---|---|
| Availability | 99.x% | `/ready` uptime + Alertmanager |
| API p95 latency | < X ms per endpoint class | request-latency histograms (to add — OPS-OBS-01) |
| Error rate | < 0.1% | status-code counters by class |
| Inspection throughput | ≥ N/shift | app metric (to add) |
| Report gen time | < Y s p95 | app timer (to add) |
| Audit integrity | 100% chain-valid | scheduled chain-verification + alert |
| DB pool saturation | < 80% | pool gauge (to add) |
| Error budget burn | within budget | SLO tooling (to add) |

## Determination
**No operational KPIs can be reported** because the platform is not in production and
the metrics infrastructure to measure them (latency histograms, error/pool gauges,
SLOs, alerting) **has not been built** (Phase 5 OPS-OBS-01/02, MON-01/02). Building
that instrumentation + defining SLOs is a **pre-launch prerequisite**, tracked in the
CI backlog.
