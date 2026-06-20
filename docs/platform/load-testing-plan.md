# LumenAI Load Testing Plan

## Overview

Load and performance testing plan for LumenAI to validate production readiness before go-live with hospital customers.

---

## Tooling

**Primary**: [k6](https://k6.io/) — JavaScript-based, cloud-native, Prometheus integration
**Alternative**: [Locust](https://locust.io/) — Python-based, good for complex scenarios

---

## Baseline Performance Targets

### API (Non-Inference)
| Percentile | Target  |
|------------|---------|
| p50        | < 100ms |
| p95        | < 300ms |
| p99        | < 500ms |

### Inference Endpoints
| Percentile | Target  |
|------------|---------|
| p50        | < 500ms |
| p99        | < 2s    |

### Frontend (Core Web Vitals)
| Metric | Target    |
|--------|-----------|
| LCP    | < 2.5s    |
| FID    | < 100ms   |
| CLS    | < 0.1     |
| TTFB   | < 600ms   |

### Database
- Query plan analysis: no sequential scans on tables > 10k rows
- Index coverage: all foreign keys indexed, all WHERE clause columns indexed
- p99 query time: < 100ms

---

## Test Scenarios

### Scenario 1: Inspection Ranking Burst
**Description**: Simulate 50 concurrent inspectors submitting CV analysis requests
**Endpoint**: `POST /api/cv/analyze`
**Load profile**:
- Ramp up: 0 → 50 VUs over 30s
- Sustained: 50 VUs for 5 minutes (50 RPS)
- Ramp down: 50 → 0 over 30s

**Pass criteria**: p99 < 2s, error rate < 1%

### Scenario 2: Executive Dashboard Load
**Description**: Multiple dashboard users loading the executive view simultaneously
**Endpoints**: `GET /api/executive-dashboard`, `GET /api/predictions/dashboard`, `GET /api/vendor-intelligence/vendors`
**Load profile**:
- 20 VUs constant for 10 minutes
- Mixed read pattern (20 RPS total)

**Pass criteria**: p99 < 500ms, error rate < 0.1%

### Scenario 3: Inference Sustained Load
**Description**: Sustained AI inference requests
**Endpoint**: `POST /api/cv/analyze`, `GET /api/predictions/dashboard`
**Load profile**:
- 10 VUs constant for 15 minutes
- Think time: 2s between requests (realistic pacing)

**Pass criteria**: p99 < 2s, no OOM errors, CPU < 80%

### Scenario 4: Vendor Intake Spike
**Description**: End-of-quarter vendor intake surge
**Endpoints**: `GET /api/vendor-intelligence/vendors`, `POST /api/vendor-intelligence/vendors`
**Load profile**:
- Ramp up: 0 → 100 VUs over 60s
- Peak: 100 VUs for 2 minutes
- Return to baseline: 100 → 10 VUs

**Pass criteria**: HPA scales out within 2 minutes, p99 < 500ms after scale-out

### Scenario 5: Audit Package Export
**Description**: Compliance team generating audit packages at end of audit cycle
**Endpoint**: `POST /api/regulatory/audit-package`, `POST /api/regulatory/audit-package/pdf`
**Load profile**:
- 5 concurrent users
- Duration: 5 minutes

**Pass criteria**: PDF export p99 < 5s, no timeout errors

---

## k6 Load Test Script

```javascript
// k6/inspection-ranking-burst.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const inferenceLatency = new Trend('inference_latency');

export const options = {
  stages: [
    { duration: '30s', target: 50 },  // ramp up
    { duration: '5m', target: 50 },   // sustained
    { duration: '30s', target: 0 },   // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(99)<2000'],  // p99 < 2s
    errors: ['rate<0.01'],              // error rate < 1%
    inference_latency: ['p(99)<2000'],
  },
};

const BASE_URL = __ENV.API_BASE_URL || 'http://localhost:8000';

// Login once per VU and cache token
export function setup() {
  const loginRes = http.post(`${BASE_URL}/api/auth/login`, JSON.stringify({
    username: 'loadtest@lumenai.health',
    password: __ENV.LOAD_TEST_PASSWORD,
  }), { headers: { 'Content-Type': 'application/json' } });

  check(loginRes, { 'login 200': (r) => r.status === 200 });
  return { token: loginRes.json('access_token') };
}

export default function (data) {
  const headers = {
    'Authorization': `Bearer ${data.token}`,
    'Content-Type': 'application/json',
    'X-LumenAI-Tenant-Id': 'loadtest-tenant',
  };

  const start = Date.now();
  const res = http.post(`${BASE_URL}/api/cv/analyze`, JSON.stringify({
    image_url: 'https://example.com/sample-device.jpg',
    device_type: 'infusion_pump',
  }), { headers });

  inferenceLatency.add(Date.now() - start);
  errorRate.add(res.status >= 500);

  check(res, {
    'status 200': (r) => r.status === 200,
    'has ai_findings': (r) => r.json('ai_findings') !== undefined,
  });

  sleep(1); // 1s think time between requests
}
```

```javascript
// k6/dashboard-load.js
import http from 'k6/http';
import { check, group, sleep } from 'k6';

export const options = {
  vus: 20,
  duration: '10m',
  thresholds: {
    http_req_duration: ['p(99)<500'],
    http_req_failed: ['rate<0.001'],
  },
};

const BASE_URL = __ENV.API_BASE_URL || 'http://localhost:8000';

export default function () {
  const headers = {
    'Authorization': `Bearer ${__ENV.LOAD_TEST_TOKEN}`,
    'X-LumenAI-Tenant-Id': 'loadtest-tenant',
  };

  group('executive dashboard', () => {
    const res = http.get(`${BASE_URL}/api/executive-dashboard`, { headers });
    check(res, { 'dashboard 200': (r) => r.status === 200 });
  });

  group('predictions', () => {
    const res = http.get(`${BASE_URL}/api/predictions/dashboard`, { headers });
    check(res, { 'predictions 200': (r) => r.status === 200 });
  });

  group('vendors', () => {
    const res = http.get(`${BASE_URL}/api/vendor-intelligence/vendors`, { headers });
    check(res, { 'vendors 200': (r) => r.status === 200 });
  });

  sleep(3); // think time between page loads
}
```

---

## Running Load Tests

### Prerequisites
```bash
brew install k6   # macOS
# or
sudo apt install k6  # Ubuntu

export API_BASE_URL=https://api.staging.lumenai.health
export LOAD_TEST_TOKEN=<staging-token>
```

### Run inspection burst test
```bash
k6 run --env API_BASE_URL=$API_BASE_URL k6/inspection-ranking-burst.js
```

### Run dashboard load test
```bash
k6 run --env API_BASE_URL=$API_BASE_URL --env LOAD_TEST_TOKEN=$LOAD_TEST_TOKEN k6/dashboard-load.js
```

### Output to Prometheus + Grafana
```bash
K6_PROMETHEUS_RW_SERVER_URL=http://prometheus:9090/api/v1/write \
k6 run --out experimental-prometheus-rw k6/inspection-ranking-burst.js
```

---

## Database Query Analysis

### Check missing indexes
```sql
-- Tables with sequential scans
SELECT schemaname, tablename, seq_scan, idx_scan
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan
ORDER BY seq_scan DESC;

-- Identify slow queries
SELECT query, calls, total_exec_time/calls AS avg_ms
FROM pg_stat_statements
WHERE calls > 100
ORDER BY avg_ms DESC
LIMIT 20;
```

### Run EXPLAIN ANALYZE on key queries
```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM inspections
WHERE tenant_id = 'abc' AND created_at > NOW() - INTERVAL '30 days'
ORDER BY created_at DESC LIMIT 50;
```

### Required indexes (verify before go-live)
```sql
-- Verify these exist
\d inspections
\d audit_logs
\d vendor_intelligence_vendors

-- Critical indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_tenant_created
  ON inspections(tenant_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_tenant_timestamp
  ON audit_logs(tenant_id, timestamp DESC);
```

---

## Frontend Performance

### Lighthouse CI
```bash
npm install -g @lhci/cli
lhci autorun --collect.url=https://staging.lumenai.health
```

### WebPageTest / Chrome DevTools
- Profile: 4G mobile + desktop
- Target: LCP < 2.5s, FID < 100ms, CLS < 0.1
- Check: bundle size (JS < 500KB gzipped), image optimization, code splitting

### Bundle Size Analysis
```bash
cd frontend
npm run build -- --report
# Or use vite-bundle-visualizer
npx vite-bundle-visualizer
```

---

## Performance Testing Schedule

| Phase          | When                        | Tests Run                              |
|----------------|-----------------------------|----------------------------------------|
| Pre-staging    | Before staging deploy       | Unit + integration tests               |
| Staging        | After staging deploy        | All k6 scenarios (reduced load)        |
| Pre-production | Before production deploy    | Full load test suite                   |
| Post-release   | 30 days after go-live       | Production traffic analysis            |
| Quarterly      | Every 3 months              | Regression load test                   |
