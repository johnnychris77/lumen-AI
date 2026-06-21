# Multi-Region Architecture — LumenAI Global Infrastructure

**Document ID:** LUM-GLOBAL-005  
**Version:** 1.0  
**Status:** Planning  
**Milestone:** P20 — International Expansion & Global Regulatory Readiness  
**Classification:** Architecture Confidential  

---

## 1. Overview

This document defines the multi-region cloud architecture for LumenAI's global expansion. The architecture enforces data sovereignty, maintains tenant isolation across regions, and provides regional disaster recovery capabilities while prohibiting cross-region transfer of Protected Health Information (PHI) and personal data.

**Core Design Principles:**
1. **PHI Never Crosses Regional Boundaries** — Regional data planes are air-gapped for PHI
2. **Tenant Region Immutability** — Tenant's data region is set at onboarding and cannot migrate without documented process
3. **Regional Independence** — Each region operates as a fully functional LumenAI deployment; global control plane handles routing only (no PHI)
4. **Compliance by Architecture** — Data sovereignty enforced at infrastructure level, not solely by policy

---

## 2. Regional Deployment Map

### 2.1 Primary Regions

| Region Name | AWS Region | Role | Compliance Framework |
|-------------|-----------|------|---------------------|
| North America Primary | us-east-1 (N. Virginia) | Primary — US + Canada | HIPAA, PIPEDA |
| North America DR | us-west-2 (Oregon) | Disaster Recovery for NA | HIPAA, PIPEDA |
| Canada Primary | ca-central-1 (Montreal) | Canada-specific tenants | PIPEDA, Quebec Law 25 |
| Canada DR | ca-west-1 (Calgary) | DR for Canada | PIPEDA |
| Europe Primary | eu-west-1 (Ireland) | EU/EEA tenants | GDPR |
| Europe DR | eu-central-1 (Frankfurt) | DR for EU (within EEA) | GDPR |
| United Kingdom | eu-west-2 (London) | UK tenants | UK GDPR |
| UK DR | eu-west-2 (multi-AZ) | Multi-AZ within eu-west-2 | UK GDPR |
| Asia Pacific Primary | ap-southeast-1 (Singapore) | Singapore + ASEAN | PDPA |
| Australia Primary | ap-southeast-2 (Sydney) | Australia + NZ | Australian Privacy Act |
| Japan Primary | ap-northeast-1 (Tokyo) | Japan (future) | APPI |

### 2.2 Regional Architecture Diagram

```
╔══════════════════════════════════════════════════════════════════╗
║              GLOBAL CONTROL PLANE (us-east-1)                   ║
║  ┌─────────────────────────────────────────────────────────┐    ║
║  │  Route 53 (Global DNS)                                  │    ║
║  │  CloudFront (Static assets ONLY — no PHI)               │    ║
║  │  Global Auth Service (JWT issuance — no PHI payload)    │    ║
║  │  Product Analytics (de-identified telemetry)            │    ║
║  │  Billing Service (non-PHI commercial data)              │    ║
║  └─────────────────────────────────────────────────────────┘    ║
╚══════════════╦═══════════════════╦══════════════════════════════╝
               ║ (routing/auth)    ║ (routing/auth)
               ▼                   ▼
╔══════════════════╗  ╔═══════════════════╗  ╔════════════════════╗
║  NORTH AMERICA   ║  ║  EUROPE (GDPR)    ║  ║  ASIA PACIFIC      ║
║  us-east-1       ║  ║  eu-west-1        ║  ║  ap-southeast-1    ║
║  ┌────────────┐  ║  ║  ┌─────────────┐  ║  ║  ap-southeast-2    ║
║  │ API GW     │  ║  ║  │ API GW      │  ║  ║  ap-northeast-1    ║
║  │ ECS/Fargate│  ║  ║  │ ECS/Fargate │  ║  ║                    ║
║  │ RDS Multi-Z│  ║  ║  │ RDS Multi-Z │  ║  ║  [same stack per   ║
║  │ S3 (PHI)   │  ║  ║  │ S3 (PHI)    │  ║  ║   sub-region]      ║
║  │ KMS keys   │  ║  ║  │ KMS keys    │  ║  ║                    ║
║  │ CloudWatch │  ║  ║  │ CloudWatch  │  ║  ║                    ║
║  └────────────┘  ║  ║  └─────────────┘  ║  ║                    ║
║  DR: us-west-2   ║  ║  DR: eu-central-1 ║  ║  DR: multi-AZ      ║
╚══════════════════╝  ╚═══════════════════╝  ╚════════════════════╝
         UK: eu-west-2 (London) — separate stack per UK GDPR
```

---

## 3. Tenant Region Assignment

### 3.1 Tenant Configuration Schema

Each tenant is assigned a region at onboarding. This is enforced throughout the application stack.

```json
{
  "tenant_id": "hosp-a1b2c3d4",
  "tenant_name": "Royal Melbourne Hospital",
  "tenant_region": "ap-southeast-2",
  "data_residency_country": "AU",
  "privacy_frameworks": ["Australian Privacy Act 1988"],
  "region_config": {
    "api_endpoint": "https://ap-southeast-2.api.lumenai.health",
    "kms_key_arn": "arn:aws:kms:ap-southeast-2:123456789:key/abcd-1234",
    "s3_data_bucket": "lumenai-phi-ap-southeast-2-a1b2c3d4",
    "rds_cluster_endpoint": "lumenai-prod.cluster-xyz.ap-southeast-2.rds.amazonaws.com",
    "cross_region_replication_enabled": false,
    "phi_cross_border_permitted": false
  },
  "created_at": "2026-06-21T00:00:00Z",
  "region_locked_at": "2026-06-21T00:00:00Z"
}
```

### 3.2 API Gateway Enforcement

Regional API Gateway instances enforce tenant-region binding:

```python
# backend/app/middleware/region_enforcement.py

import boto3
import os
from fastapi import HTTPException, Request
from app.core.auth import decode_jwt_token

CURRENT_REGION = os.environ.get("AWS_REGION", "us-east-1")

async def enforce_tenant_region(request: Request):
    """
    Middleware: Reject requests where tenant's assigned region
    does not match the regional API endpoint receiving the request.
    Prevents PHI from being processed in wrong region.
    """
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return  # Auth middleware handles missing tokens

    claims = decode_jwt_token(token)
    tenant_region = claims.get("tenant_region")

    if tenant_region and tenant_region != CURRENT_REGION:
        # Log sovereignty violation attempt
        logger.warning(
            "data_sovereignty_violation_attempt",
            tenant_id=claims.get("tenant_id"),
            assigned_region=tenant_region,
            request_region=CURRENT_REGION,
            path=request.url.path,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "DATA_SOVEREIGNTY_VIOLATION",
                "message": "Request routed to incorrect regional endpoint",
                "assigned_region": tenant_region,
                "request_region": CURRENT_REGION,
            }
        )
```

### 3.3 DNS-Level Region Routing

```
# Route 53 Geolocation + Latency-based routing (for login/auth only)
# After authentication, JWT contains tenant_region; client uses regional endpoint

lumenai.health          → CloudFront (static site, no PHI)
app.lumenai.health      → Global login → JWT with regional endpoint
api.lumenai.health      → Regional selector (by tenant_region in JWT)

# Regional API endpoints
us-east-1.api.lumenai.health     → AWS us-east-1 ALB
ca-central-1.api.lumenai.health  → AWS ca-central-1 ALB
eu-west-1.api.lumenai.health     → AWS eu-west-1 ALB
eu-west-2.api.lumenai.health     → AWS eu-west-2 ALB (UK)
ap-southeast-1.api.lumenai.health → AWS ap-southeast-1 ALB
ap-southeast-2.api.lumenai.health → AWS ap-southeast-2 ALB
```

---

## 4. Regional Object Storage (S3)

### 4.1 S3 Bucket Architecture

```
# PHI Buckets — one per tenant per region (or per-region shared with tenant prefix)
lumenai-phi-{region}-{tenant_id}/           # Instrument images, inspection data
  inspection-images/
    {year}/{month}/{day}/{inspection_id}.jpg
  reports/
    {year}/{month}/{report_id}.pdf
  audit-logs/
    {year}/{month}/{day}/{audit_id}.jsonl

# Non-PHI Operational Buckets
lumenai-ops-{region}/
  ml-models/                                # Model artifacts (no patient data)
  static-assets/                            # Served via CloudFront
  backups/                                  # Encrypted backups within region
```

### 4.2 S3 Bucket Policies — GDPR Example (EU)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyNonEUAccess",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::lumenai-phi-eu-west-1-*",
        "arn:aws:s3:::lumenai-phi-eu-west-1-*/*"
      ],
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": ["eu-west-1", "eu-central-1"]
        }
      }
    },
    {
      "Sid": "DenyCrossRegionReplication",
      "Effect": "Deny",
      "Principal": {"Service": "s3.amazonaws.com"},
      "Action": "s3:ReplicateObject",
      "Resource": "arn:aws:s3:::lumenai-phi-eu-west-1-*/*",
      "Condition": {
        "StringNotEquals": {
          "s3:prefix": ["backups/"]
        }
      }
    },
    {
      "Sid": "RequireSSLOnly",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": "arn:aws:s3:::lumenai-phi-eu-west-1-*",
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    }
  ]
}
```

### 4.3 S3 Encryption Configuration

- **SSE-KMS**: All PHI buckets use AWS KMS Customer Managed Keys (CMK)
- **CMK per region**: Regional KMS keys; key material never exported cross-region
- **Key rotation**: Automatic annual key rotation enabled
- **Bucket-level encryption**: Default encryption enforced; unencrypted uploads rejected

### 4.4 S3 Cross-Region Replication Rules

| Bucket Type | Cross-Region Replication | Justification |
|-------------|--------------------------|---------------|
| PHI data buckets | DISABLED | Data sovereignty; GDPR/HIPAA prohibition on PHI cross-border |
| Backup buckets (within region) | ENABLED — same region only | DR within EEA for GDPR; within AU for Privacy Act |
| ML model artifacts (no PHI) | ENABLED — global | Model updates deployed globally; no patient data |
| Static asset buckets | ENABLED — global | CloudFront origin; no PHI |

---

## 5. Regional Database Architecture

### 5.1 RDS Configuration

Each region deploys an independent RDS PostgreSQL cluster:

```
# Per-region RDS configuration
Engine: PostgreSQL 15.x
Instance: db.r6g.xlarge (production); db.t3.medium (staging)
Storage: gp3 encrypted; 1 TB initial; auto-scaling enabled
Multi-AZ: ENABLED (synchronous standby in second AZ within region)
Encryption: AWS KMS CMK (regional key)
Backup: Automated daily backups; 35-day retention; within region ONLY
Parameter Group: Custom — enforce SSL, disable pg_stat_statements logging of PHI queries
```

### 5.2 PHI Cross-Region Replication Policy

**STRICTLY PROHIBITED:**
- RDS cross-region read replicas for PHI databases
- Database snapshot copies to other regions
- Logical replication of PHI to cross-region targets

**PERMITTED:**
- RDS Multi-AZ within the same AWS region (synchronous replication — same country/region)
- Schema/migration scripts replicated across regions (no data)
- De-identified schema statistics for capacity planning

### 5.3 Database Schema — tenant_region Enforcement

```sql
-- Row-Level Security enforcement (in addition to application-layer tenant_id checks)
-- Ensures PHI data cannot be accessed across tenant boundaries
CREATE POLICY tenant_isolation_policy ON inspections
  USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Tenant configuration table — region enforcement
CREATE TABLE tenant_configurations (
    tenant_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_name         TEXT NOT NULL,
    tenant_region       TEXT NOT NULL CHECK (tenant_region IN (
                            'us-east-1', 'ca-central-1', 'eu-west-1',
                            'eu-west-2', 'ap-southeast-1', 'ap-southeast-2',
                            'ap-northeast-1'
                        )),
    data_residency      TEXT NOT NULL,
    phi_cross_border    BOOLEAN NOT NULL DEFAULT FALSE,
    region_locked_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- region cannot be changed after lock
    CONSTRAINT region_immutable CHECK (region_locked_at IS NOT NULL)
);
```

### 5.4 Regional Database Endpoints

| Region | Primary Endpoint | Standby | Backup Region | DR Strategy |
|--------|-----------------|---------|---------------|-------------|
| us-east-1 | lumenai-na.cluster.us-east-1.rds.amazonaws.com | AZ-b (us-east-1b) | us-west-2 (schema only) | Multi-AZ failover |
| ca-central-1 | lumenai-ca.cluster.ca-central-1.rds.amazonaws.com | AZ-b | ca-west-1 (schema only) | Multi-AZ failover |
| eu-west-1 | lumenai-eu.cluster.eu-west-1.rds.amazonaws.com | AZ-b (eu-west-1b) | eu-central-1 (EEA backup) | Multi-AZ; EEA snapshot |
| eu-west-2 | lumenai-uk.cluster.eu-west-2.rds.amazonaws.com | AZ-b (eu-west-2b) | eu-west-2 AZ-c | Multi-AZ only |
| ap-southeast-1 | lumenai-sg.cluster.ap-southeast-1.rds.amazonaws.com | AZ-b | AZ-c | Multi-AZ |
| ap-southeast-2 | lumenai-au.cluster.ap-southeast-2.rds.amazonaws.com | AZ-b | AZ-c | Multi-AZ |
| ap-northeast-1 | lumenai-jp.cluster.ap-northeast-1.rds.amazonaws.com | AZ-b | AZ-c | Multi-AZ |

---

## 6. Disaster Recovery

### 6.1 DR Objectives

| Metric | Target | Applies To |
|--------|--------|-----------|
| RPO (Recovery Point Objective) | ≤ 4 hours | All PHI data |
| RTO (Recovery Time Objective) | ≤ 8 hours | Full regional service restoration |
| MTTR (Mean Time to Recover) | ≤ 4 hours | Application layer (ECS/Fargate) |
| Data loss window | < 5 minutes | RDS Multi-AZ synchronous replication |
| Backup frequency | Daily automated + continuous WAL archiving | RDS |
| Backup retention | 35 days (production) | RDS automated backups |

### 6.2 DR Strategy by Region

**North America (US)**
- Primary: us-east-1 (Multi-AZ RDS, ECS across 3 AZs)
- DR: us-west-2 (warm standby — RDS read replica for schema; ECS capacity reserved)
- PHI replication: Within us-east-1 via Multi-AZ ONLY
- DR activation: Manual failover trigger; RDS promotion of standby; DNS failover via Route 53 health checks
- RTO target: ≤ 8 hours (ECS scaling + RDS failover)

**Europe (EU/GDPR)**
- Primary: eu-west-1 (Ireland) — Multi-AZ across eu-west-1a, eu-west-1b, eu-west-1c
- DR: eu-central-1 (Frankfurt) — RDS backup snapshots within EEA
- GDPR compliance: Both regions within EEA; no adequacy decision needed for snapshot transfer
- DR activation: Restore from eu-west-1 encrypted snapshot to eu-central-1 RDS; ECS stack pre-deployed
- RTO target: ≤ 8 hours (snapshot restore ~2–4 hours + ECS warmup)

**United Kingdom**
- Primary: eu-west-2 (London) — Multi-AZ
- DR: eu-west-2 (AZ failover within London region)
- No cross-border DR: UK data stays in UK (post-Brexit data sovereignty)
- DR activation: RDS Multi-AZ automatic failover (< 60 seconds for AZ failure)
- Extended DR: Restore from eu-west-2 encrypted daily backup to new eu-west-2 cluster

**Canada**
- Primary: ca-central-1 (Montreal) — Multi-AZ
- DR: ca-west-1 (Calgary) — schema-only; PHI backup snapshots
- PIPEDA compliance: Both regions within Canada
- DR activation: Schema restore + application deployment; snapshot restore for PHI
- RTO target: ≤ 8 hours

**Asia Pacific (Singapore/Australia)**
- Singapore: ap-southeast-1 Multi-AZ (self-contained DR within region)
- Australia: ap-southeast-2 Multi-AZ (self-contained; AU Privacy Act requires AU data stay in AU)
- Japan (future): ap-northeast-1 Multi-AZ

### 6.3 DR Runbooks

Each region maintains documented DR runbook including:
1. Failure detection and alert thresholds (CloudWatch alarms)
2. Incident classification (AZ failure vs. region failure)
3. Escalation procedure (on-call rotation; regional ops contact)
4. Failover execution steps (automated vs. manual triggers)
5. Post-failover validation checklist
6. Customer communication templates (per data residency SLA)
7. Return-to-primary procedure

**DR Testing Schedule:**
- Annual full DR failover test per region (scheduled maintenance window)
- Semi-annual tabletop exercise per region
- Quarterly backup restoration test (verify backup integrity)

---

## 7. Global CDN — CloudFront

### 7.1 CDN Scope

**CloudFront ONLY serves:**
- Static web application bundle (HTML, CSS, JavaScript)
- Public marketing/documentation assets
- Product icons and images (non-PHI)

**CloudFront NEVER serves:**
- PHI (inspection images, patient/instrument data)
- Authenticated API responses
- Tenant-specific data

### 7.2 CloudFront Configuration

```
Origins:
  - S3 bucket (us-east-1): lumenai-static-assets
    - Access: CloudFront OAC (Origin Access Control)
    - Cache behavior: 1 year (hashed filenames)

Cache Behaviors:
  - /api/*: Disallowed — API requests must go directly to regional endpoints
  - /*.js, /*.css: Cached at edge (1 year TTL)
  - /index.html: No cache (must-revalidate for app shell updates)

Security:
  - HTTPS only (HTTP redirect to HTTPS)
  - TLS 1.2+ minimum
  - Security headers: HSTS, CSP, X-Frame-Options, X-Content-Type-Options
  - Geo-restriction: None on static assets (global CDN)
  - WAF: AWS WAF on CloudFront for rate limiting and bot protection on static delivery

PHI Prohibition:
  - CloudFront behavioral policy: No PHI in response headers, body, or cache
  - Signed URL/cookies: Available if needed for authenticated asset delivery
    (but PHI assets served from regional S3 via pre-signed URLs, not CloudFront)
```

---

## 8. Inter-Region Communication

### 8.1 Non-PHI Operational Messages

Inter-region communication is permitted for non-PHI operational data only:

```
# SNS Topics (non-PHI operational events)
arn:aws:sns:us-east-1:...:lumenai-ops-global
  → System health events
  → ML model deployment notifications
  → Global incident alerts
  → Billing/subscription events (non-PHI)

# SQS Queues (per-region processing)
arn:aws:sqs:{region}:...:lumenai-ops-{region}
  → Regional operational tasks
  → Deployment pipeline triggers
  → Non-PHI data processing
```

### 8.2 PHI Cross-Region Communication

**STRICTLY PROHIBITED:**
- PHI in SNS/SQS messages between regions
- Lambda invocations that pass PHI across regions
- VPC peering for PHI traffic between regions
- API calls from one region's data plane to another that include PHI

**Enforcement:**
- Data Classification Tags on all resources: `DataSensitivity: PHI` resources have SCPs blocking cross-region data transfer
- AWS Service Control Policies (SCPs): Restrict PHI-tagged S3 bucket replication and RDS snapshot copy to approved same-region/same-country targets only

### 8.3 Global Model Deployment Pipeline

```
# ML Model artifacts (contain NO patient data)
Model Registry (us-east-1)
  → Model artifact S3 bucket (no PHI)
  → Cross-region copy: us-east-1 → eu-west-1, ap-southeast-1, ap-southeast-2
  → Each region downloads model artifact and loads into local ECS inference container
  → Inference runs entirely within regional data plane
  → No patient data or PHI in model artifacts or model deployment pipeline
```

---

## 9. Monitoring and Observability

### 9.1 Regional Monitoring Stack

Each region operates an independent monitoring stack:

```
CloudWatch (per-region):
  - Application metrics (API latency, error rates, inspection throughput)
  - RDS performance insights (de-identified query performance)
  - ECS resource utilization
  - Data sovereignty violation alerts

CloudWatch Alarms:
  - PHI cross-region access attempt → SNS → PagerDuty CRITICAL
  - RDS Multi-AZ failover triggered → SNS → PagerDuty HIGH
  - API error rate > 5% → SNS → PagerDuty HIGH
  - S3 bucket policy violation → SNS → PagerDuty CRITICAL
  - Encryption failure → SNS → PagerDuty CRITICAL
```

### 9.2 Cross-Region Operational Telemetry (Non-PHI)

Global operational dashboard aggregates de-identified metrics:
- Request counts (no PHI in metric labels)
- System health across regions
- Deployment status per region
- Capacity utilization trends

No PHI flows into global telemetry aggregation.

---

## 10. Infrastructure as Code

All regional deployments defined as Infrastructure as Code (IaC):

```
infrastructure/
├── terraform/
│   ├── modules/
│   │   ├── regional-data-plane/    # Reusable module for each region
│   │   │   ├── rds.tf
│   │   │   ├── s3.tf
│   │   │   ├── kms.tf
│   │   │   ├── ecs.tf
│   │   │   ├── api-gateway.tf
│   │   │   └── monitoring.tf
│   │   └── global-control-plane/  # One instance — us-east-1
│   │       ├── cloudfront.tf
│   │       ├── route53.tf
│   │       └── auth.tf
│   ├── environments/
│   │   ├── prod-us-east-1/
│   │   ├── prod-ca-central-1/
│   │   ├── prod-eu-west-1/
│   │   ├── prod-eu-west-2/
│   │   ├── prod-ap-southeast-1/
│   │   └── prod-ap-southeast-2/
│   └── scp/                       # AWS Service Control Policies
│       └── data-sovereignty-scp.json
```

---

## 11. Document Metadata

| Field | Value |
|-------|-------|
| Author | LumenAI Infrastructure & Security Team |
| Review Date | Quarterly |
| Next Review | 2026-09-21 |
| Approvers | CTO, VP Infrastructure, Chief Security Officer |
| Related Documents | LUM-GLOBAL-003 (Privacy & Data Residency), LUM-GLOBAL-008 (Security Readiness) |
