# Monitoring

## Probe surface

| Endpoint | Auth | Checks |
|---|---|---|
| `GET /health` (pre-existing) | none | process liveness |
| `GET /ready` (pre-existing) | none | database `SELECT 1` |
| `GET /metrics` (pre-existing) | token / localhost | request count, uptime (Prometheus text) |
| `GET /api/gpae/health/deep` (NEW) | admin / spd_manager | database, alembic revision, object storage read/write round-trip, audit-log readability, model registry, baseline-resolution tables, governed-object registry — each with per-component status + latency |
| `POST /api/gpae/monitoring/sweep` (NEW) | admin / spd_manager | deep check + raises one audited platform alert per failed component |

Implementation: `app/services/gpae_monitoring_service.py`. The deep
check never raises — failures are reported per component and roll up
into `overall_status: degraded`, so a broken subsystem cannot hide by
crashing the probe.

## Alerting — what is true today

`dispatch_platform_alert`:

1. logs the alert at ERROR level (visible to any log shipper),
2. writes a hash-chained audit event (`platform_alert_raised`,
   `compliance_flag=true`) recording the severity, message, and the
   **actual delivery outcome**,
3. emails the alert **only when a destination is configured**
   (`SMTP_HOST` + `ALERT_EMAIL_TO`).

When no destination is configured — true of every current development
environment — the outcome is recorded as `no_destination_configured`.
The service never claims delivery that did not happen, and a failed send
is recorded as `delivery_failed` with the error. Verified by
`tests/test_gpae_foundation.py::TestGpaeMonitoring`.

## Honest gaps

* No external alert destination (Slack/Teams/pager/email) is configured
  anywhere in this repository's environments — configuring one is a
  deployment task, deliberately not faked here. This remains a
  NOT MET item in the controlled-production entry criteria.
* Uploads/inference/authentication monitoring beyond the deep check
  remains the existing per-request logging + `/metrics` counters; a
  full metrics pipeline (histograms, dashboards) is future managed-
  deployment work.
* No scheduler invokes the sweep automatically in this container; a
  managed deployment runs it on a timer (same mechanism as backups).
