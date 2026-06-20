# LumenAI Reliability

## SLA / SLO / SLI Definitions

### Uptime Target
**99.9%** — 8.7 hours of allowable downtime per year (43.8 minutes per month)

### Service Level Objectives (SLOs)

| SLO                              | Target       | Measurement Window |
|----------------------------------|--------------|-------------------|
| API availability                 | 99.9%        | Rolling 30 days   |
| API p99 latency (non-inference)  | < 500ms      | Rolling 5 minutes |
| Inference p99 latency            | < 2s         | Rolling 5 minutes |
| API error rate (5xx)             | < 0.1%       | Rolling 5 minutes |
| DB query p99 latency             | < 100ms      | Rolling 5 minutes |
| PDF export p99 latency           | < 5s         | Rolling 5 minutes |

### Service Level Indicators (SLIs)
Measured via Prometheus metrics scraped from `/metrics` and Kubernetes node metrics.

```promql
# API availability (1 - error_rate)
1 - (
  sum(rate(http_requests_total{status=~"5.."}[5m]))
  /
  sum(rate(http_requests_total[5m]))
)

# API p99 latency
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

# Error rate
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))
```

---

## Alerting Rules

### Prometheus AlertManager Rules
```yaml
groups:
  - name: lumenai-slo
    rules:
      # Burn rate alert: consuming error budget 6x faster than allowed
      - alert: SLOErrorBudgetBurnRateFast
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[1h])) /
          sum(rate(http_requests_total[1h])) > 0.006
        for: 5m
        labels:
          severity: critical
          slo: error_rate
        annotations:
          summary: "Fast error budget burn rate (>6x)"

      - alert: APILatencyP99High
        expr: histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API p99 latency > 500ms SLO"

      - alert: InferenceLatencyHigh
        expr: histogram_quantile(0.99, sum(rate(inference_duration_seconds_bucket[5m])) by (le)) > 2.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Inference p99 latency > 2s SLO"

      - alert: BackendPodsDown
        expr: kube_deployment_status_replicas_available{deployment="lumenai-backend"} < 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "All LumenAI backend pods are down"

      - alert: DatabaseUnreachable
        expr: probe_success{job="blackbox-lumenai-ready"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "LumenAI /ready endpoint returning non-200 (DB unreachable)"
```

---

## Incident Response Workflow

### Severity Definitions

| Severity | Definition                                         | Response Time | Escalation         |
|----------|---------------------------------------------------|---------------|--------------------|
| SEV1     | Production down, data loss risk, HIPAA breach     | 15 minutes    | CTO + On-call SRE  |
| SEV2     | Degraded performance, partial outage (< 50% users)| 30 minutes    | On-call SRE        |
| SEV3     | Non-critical feature broken, no data impact       | 4 hours       | Engineering team   |

### Response Workflow

#### SEV1 (Critical)
1. **Detect** — PagerDuty alert fires, on-call SRE paged
2. **Acknowledge** — Acknowledge in PagerDuty within 15 minutes
3. **Communicate** — Post in `#incident-response` Slack: "SEV1 declared: [description]. IC: [name]"
4. **Mitigate** — Apply immediate mitigation (rollback, scale-out, circuit break)
5. **Resolve** — Confirm SLO metrics recovering
6. **Post-mortem** — Blameless post-mortem within 48 hours

#### SEV2 (Warning)
1. **Detect** — Prometheus alert → Slack `#lumenai-alerts`
2. **Triage** — On-call engineer triages within 30 minutes
3. **Mitigate** — Apply fix or workaround
4. **Resolve** — Close alert, add incident to tracking system

---

## Rollback Strategy

### Kubernetes Rolling Update → Rollback
```bash
# Check rollout history
kubectl rollout history deployment/lumenai-backend -n lumenai

# Rollback to previous version
kubectl rollout undo deployment/lumenai-backend -n lumenai

# Rollback to specific revision
kubectl rollout undo deployment/lumenai-backend --to-revision=3 -n lumenai

# Verify rollback
kubectl rollout status deployment/lumenai-backend -n lumenai
```

### Database Rollback (Alembic)
```bash
# Rollback last migration
DATABASE_URL=$DATABASE_URL alembic downgrade -1

# Rollback to specific revision
DATABASE_URL=$DATABASE_URL alembic downgrade <revision_id>
```

**Note**: Always test database downgrade migrations in staging before deploying schema-breaking changes to production.

### Image Tagging Strategy
```
lumenai/backend:latest        ← current production
lumenai/backend:<git-sha>     ← immutable, per-commit
lumenai/backend:stable        ← last known-good release
```

Before each production deployment, tag current image as `stable`:
```bash
docker tag lumenai/backend:latest lumenai/backend:stable
docker push lumenai/backend:stable
```

---

## Deployment Strategy

All production deployments use **Rolling Update**:
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1         # Add 1 new pod before removing old
    maxUnavailable: 0   # Never reduce below replica count (zero-downtime)
```

**Pre-deployment checklist**:
- [ ] `alembic upgrade head` in init container
- [ ] Smoke test on staging passes
- [ ] Manual approval in GitHub Actions `production` environment
- [ ] Rollback procedure reviewed

**Post-deployment verification**:
```bash
# Check all pods healthy
kubectl get pods -n lumenai

# Verify health endpoint
curl https://api.lumenai.health/health

# Check error rate for 5 minutes post-deploy
# (watch Grafana dashboard)
```
