# LumenAI Observability Plan

## Overview

This document defines the logging, metrics, tracing, and alerting strategy for LumenAI in production.

---

## 1. Logging

### Format
All backend logs are emitted as structured JSON (see `JSONFormatter` in `app/main.py`):
```json
{
  "timestamp": "2026-01-15 10:30:45,123",
  "level": "INFO",
  "logger": "app.routes.predictions",
  "message": "Prediction job completed for tenant abc123"
}
```

### Log Levels by Environment

| Environment | Log Level | Notes                                    |
|-------------|-----------|------------------------------------------|
| local       | DEBUG     | All queries, request details             |
| development | DEBUG     | Full verbosity                           |
| staging     | INFO      | Request logs, warnings, errors           |
| production  | WARNING   | Errors and warnings only (performance)   |

**Audit events** are always logged at INFO regardless of `LOG_LEVEL` — HIPAA requires audit trail.

### Log Shipping

| Environment | Destination                | Tool                    |
|-------------|----------------------------|-------------------------|
| Kubernetes  | stdout/stderr              | Fluentd/Fluent Bit → S3 / CloudWatch |
| AWS         | CloudWatch Logs            | CloudWatch agent or Fluent Bit        |
| Self-hosted | ELK Stack (Elasticsearch)  | Logstash / Filebeat     |

### Correlation IDs
Every HTTP request receives an `X-Correlation-ID` header (generated if not provided). This ID should be propagated to:
- All downstream service calls
- Database audit log entries
- Background job logs

### Log Retention
- Application logs: 90 days in CloudWatch / ELK
- Audit logs (HIPAA): 7 years in immutable S3 bucket

---

## 2. Metrics

### Endpoints
- **`/metrics`** — Prometheus-compatible plaintext format (currently: request count, uptime)
- **`/health`** — Liveness: `{"status": "ok", "version": "P11", "environment": "production"}`
- **`/ready`** — Readiness: DB connectivity check, returns 200 or 503

### Prometheus Scrape Config
```yaml
scrape_configs:
  - job_name: lumenai-backend
    static_configs:
      - targets: ['lumenai-backend:8000']
    metrics_path: /metrics
    scrape_interval: 30s
```

### Key Metrics to Track

| Metric                       | Type    | SLO Target                     |
|------------------------------|---------|--------------------------------|
| HTTP request latency (p99)   | Histogram | < 500ms for API endpoints    |
| Inference latency (p99)      | Histogram | < 2s for ML inference        |
| HTTP error rate (5xx)        | Counter | < 0.1% of total requests       |
| DB query latency (p99)       | Histogram | < 100ms                      |
| Pod CPU utilization          | Gauge   | < 70% (triggers HPA)          |
| Pod memory utilization       | Gauge   | < 80%                         |
| DB connection pool saturation| Gauge   | < 80% pool in use             |

### Grafana Dashboards
1. **API Overview**: request rate, error rate, latency percentiles
2. **Infrastructure**: pod count, CPU/memory, HPA events
3. **Database**: query latency, connection pool, replication lag
4. **Business**: tenant count, inference jobs completed, audit packages generated

---

## 3. Distributed Tracing

### Current State
Basic correlation ID propagation via `X-Correlation-ID` header.

### Future: OpenTelemetry
```python
# Add to requirements.txt:
# opentelemetry-sdk
# opentelemetry-instrumentation-fastapi
# opentelemetry-exporter-otlp

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint="http://otel-collector:4317")))
trace.set_tracer_provider(provider)
FastAPIInstrumentor.instrument_app(app)
```

**Trace backends**: Jaeger, Tempo (Grafana), AWS X-Ray

---

## 4. Alerting

### Alert Rules (Prometheus AlertManager / CloudWatch Alarms)

```yaml
# prometheus-alerts.yaml
groups:
  - name: lumenai-api
    rules:
      - alert: HighErrorRate
        expr: rate(lumenai_requests_total{status=~"5.."}[5m]) / rate(lumenai_requests_total[5m]) > 0.001
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "LumenAI API error rate > 0.1%"

      - alert: APILatencyHigh
        expr: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API p99 latency > 500ms"

      - alert: PodDown
        expr: up{job="lumenai-backend"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "LumenAI backend pod is down"

      - alert: DatabaseConnectionFailed
        expr: lumenai_db_ready == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "LumenAI database unreachable"

      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes{container="backend"} / container_spec_memory_limit_bytes > 0.85
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Backend memory > 85% of limit"
```

### Alert Notification Channels
- **SEV1 (critical)**: PagerDuty → on-call engineer (immediate)
- **SEV2 (warning)**: Slack `#lumenai-alerts` channel
- **SEV3 (info)**: Weekly digest email

### Uptime Monitoring
- External: UptimeRobot or AWS Route 53 Health Checks → `https://api.lumenai.health/health`
- Check interval: 60 seconds
- Alert if 3 consecutive failures
