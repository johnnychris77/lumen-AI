# AI/ML Change Control Plan
LumenAI Surgical Instrument Inspection Software | Version 1.0
**Subject to regulatory counsel review. Aligned with FDA AI/ML Action Plan (2021) and Predetermined Change Control Plan (PCCP) guidance.**

---

## 1. Overview

This document defines the change control process for LumenAI's AI/ML components, with particular focus on the Computer Vision (CV) Detection model. It addresses model versioning, performance monitoring, drift detection, retraining triggers, validation requirements, and the human approval chain required before any model update reaches production.

This plan is aligned with:
- FDA "Artificial Intelligence/Machine Learning (AI/ML)-Based Software as a Medical Device (SaMD) Action Plan" (January 2021)
- FDA "Marketing Submission Recommendations for a Predetermined Change Control Plan for Artificial Intelligence-Enabled Device Software Functions" (April 2023 draft guidance)
- ISO 14971:2019 Risk Management
- IEC 62304:2006+AMD1:2015 Software Lifecycle

---

## 2. Current Model State: Locked Model Assumption

**At Version 1.0, LumenAI's CV Detection model is a LOCKED model.**

Characteristics of the locked model state:
- Model weights are frozen at deployment; no automatic updates occur in production
- No online learning from production inspection data
- No federated learning across customer sites
- Model parameters cannot change without formal change control approval
- Production data is collected for monitoring and future retraining only; it does NOT automatically feed back into the deployed model

This locked model posture is intentional for Version 1.0 to simplify the regulatory pathway and ensure that model behavior is fully characterized by the pre-deployment validation evidence.

---

## 3. Model Versioning Scheme

### 3.1 CV Model Version Format
```
{major}.{minor}.{patch}-{sha8}
```

Example: `1.0.0-a1b2c3d4`

| Component | Meaning | When Incremented |
|-----------|---------|-----------------|
| major | Breaking architecture change | New model family, architecture redesign |
| minor | Significant retraining (new categories, major data expansion) | Requires full revalidation |
| patch | Bug fix or minor recalibration | Requires regression testing + clinical substudy |
| sha8 | First 8 characters of model artifact SHA-256 | Always present; uniquely identifies the model binary |

### 3.2 Dataset Versioning
- Training datasets versioned with SHA-256 manifest
- Version tag stored in S3 alongside model artifact
- Dataset manifest includes: source hospitals, collection dates, instrument categories, image counts, annotator identities, annotation protocol version

### 3.3 Model Registry Entry (Required for Each Version)
```
model_version: 1.0.0-a1b2c3d4
training_data_manifest_sha256: [SHA-256 of dataset manifest]
training_data_version_tag: train-v1.0-2025Q4
architecture: CNN-ResNet50-custom
training_completed: [ISO 8601 datetime]
validation_report: docs/clinical/clinical-performance-report.md
validation_kappa: 0.79
validation_sensitivity: 0.89
validation_critical_fn_rate: 0.018
deployment_date: [ISO 8601 datetime]
deployed_by: [name]
approved_by: [regulatory affairs sign-off name]
status: ACTIVE
```

---

## 4. Performance Thresholds — Mandatory Retraining Triggers

The following thresholds, if breached in quarterly RWE review, trigger mandatory model review. Retraining and redeployment are required unless the performance decline can be attributed to a transient, non-model cause (e.g., temporary camera hardware issue at one site) with documented justification.

| Metric | Threshold | Action on Breach |
|--------|-----------|-----------------|
| Sensitivity (overall) | < 85% | Mandatory retraining review |
| Cohen's Kappa | < 0.75 | Mandatory retraining review |
| False positive rate | > 20% | Mandatory retraining review |
| Critical false negative rate | > 2% | Immediate escalation; potential deployment pause |
| Per-category sensitivity (critical: crack/corrosion/insulation) | < 88% | Mandatory retraining review for affected categories |
| Population stability index (PSI) | > 0.2 | Drift alert; human review required |
| Characteristic stability index (CSI) | > 0.15 | Drift alert; human review required |

**Critical FN rate breach (>2%):** This triggers immediate escalation to the Chief Medical Officer, Regulatory Affairs, and Customer Success. A deployment pause may be initiated pending investigation. All affected customer sites are notified within 24 hours.

---

## 5. Drift Detection Protocol

### 5.1 Drift Metrics
| Metric | Definition | Calculation | Frequency |
|--------|-----------|------------|----------|
| Population Stability Index (PSI) | Shift in finding type distribution | PSI = sum((actual% - expected%) * ln(actual%/expected%)) across finding categories | Monthly |
| Characteristic Stability Index (CSI) | Shift in baseline confidence score distribution | CSI = sum((actual% - expected%) * ln(actual%/expected%)) across score deciles | Monthly |
| Performance Stability | Rolling sensitivity/kappa against labeled production cases | Requires human-labeled production subset (RWE module) | Quarterly |

### 5.2 Drift Response Protocol
```
PSI or CSI exceeds threshold
          |
          v
Automated alert generated in P12 drift dashboard
          |
          v
Data Science Team reviews within 5 business days
          |
    /----------\
   /            \
Transient?    Persistent?
   |                |
Document &    Root cause analysis
No action       (7 days max)
                    |
             /------------\
            /              \
    Data shift?        Model decay?
         |                  |
  Site-level       Formal retraining
  investigation     process initiated
```

### 5.3 Drift Investigation Documentation
All drift investigations must produce:
- Investigation ID and date
- PSI/CSI values and trend chart
- Root cause determination
- Corrective action (or documented justification for no action)
- Sign-off by Data Science Lead and Regulatory Affairs

---

## 6. Change Impact Categories

### 6.1 Minor Change
**Definition**: No change to model weights, architecture, training data, or clinical claims.
**Examples**: Bug fix in confidence score display; performance optimization that does not change model output; UI change.
**Required**: Full automated test suite (1,163+); ruff; frontend build.
**Not Required**: Clinical revalidation; regulatory notification.

### 6.2 Moderate Change
**Definition**: Changes that may affect model output distribution but do not change the fundamental model architecture or intended use.
**Examples**: Model patch update (recalibration); addition of new instrument types with limited scope expansion; hyperparameter tuning without architecture change.
**Required**: Full automated test suite; regression testing on validation dataset; clinical substudy (n=200 minimum from sealed test set); Regulatory Affairs review.
**Not Required**: Full revalidation study; new 510(k) (subject to counsel review).

### 6.3 Major Change
**Definition**: Changes that materially affect model performance, architecture, training data composition, or intended use.
**Examples**: New model architecture (e.g., switch to transformer-based CV); new contamination categories added; training data expanded with new hospital populations; intended use statement updated; performance claims changed.
**Required**: Full revalidation study (per clinical-validation-plan.md); updated risk management file; Regulatory Affairs review; potential regulatory submission (510(k) supplement or new submission); FDA notification per PCCP (once PCCP is approved).

---

## 7. Predetermined Change Control Plan (PCCP)

Per FDA "Marketing Submission Recommendations for a Predetermined Change Control Plan" (2023 draft guidance), this section defines the pre-specified framework for managing anticipated future changes.

**Note: This PCCP section is preparatory. It will be refined and formalized as part of the 510(k) submission, subject to FDA review and regulatory counsel guidance.**

### 7.1 Pre-Specified Performance Objectives
The following performance objectives are pre-specified as targets for any retrained model version to meet or exceed before deployment:

| Metric | Minimum Acceptable Level | Target Level |
|--------|------------------------|-------------|
| Overall sensitivity | 85% | 90% |
| Overall specificity | 80% | 90% |
| Cohen's Kappa | 0.75 | 0.80 |
| Critical FN rate (crack/corrosion/insulation) | < 2% | < 1% |
| AUC (ROC) | 0.88 | 0.93 |
| 95% CI lower bound on kappa | 0.72 | 0.77 |

### 7.2 Pre-Specified Methodology for Measuring Performance
Performance will be measured using:
1. **Sealed test set evaluation**: Randomly withheld 20% of total dataset; never used in training; SHA-256 locked. Protocol: `docs/clinical/sealed-test-set-protocol.md`
2. **MRMC reader study**: Multi-reader multi-case study with minimum 5 reader roles, 35 readers, 500 cases. Protocol: `docs/clinical/human-vs-ai-study-protocol.md`
3. **Subgroup analysis**: Performance reported by instrument category, contamination type, facility type, and image acquisition protocol
4. **Statistical methods**: Wilson score 95% CIs; Cohen's kappa with bootstrap CI; sensitivity/specificity with Clopper-Pearson CI

### 7.3 Pre-Specified Update Procedure
Updates within PCCP scope will follow:
1. Data Science team completes retraining per standard protocol
2. Internal validation on sealed test set (performance objectives must be met)
3. Clinical Validation Committee review
4. Regulatory Affairs review and sign-off
5. Engineering review and deployment approval
6. Phased deployment: 1 site (2 weeks) → 5 sites (4 weeks) → full rollout
7. Post-deployment monitoring: daily PSI/CSI for 30 days

### 7.4 Pre-Specified Reporting Mechanism
- Minor changes: Documented in change log; no regulatory reporting required
- Moderate changes within PCCP: Annual report to FDA (per approved PCCP)
- Major changes outside PCCP: 510(k) supplement required before deployment
- Adverse events or significant performance degradation: MDR reporting per 21 CFR Part 803

---

## 8. Regression Testing Protocol

Every model update (Minor, Moderate, or Major) must pass:

1. **Full automated test suite**: All 1,163+ pytest tests must pass with zero failures
2. **ruff static analysis**: Zero violations
3. **Frontend build**: Must succeed
4. **P12 validation report**: Accuracy, precision, recall, F1, kappa metrics must meet or exceed thresholds in Section 7.1
5. **Sealed test set evaluation** (Moderate and Major only): Performance on sealed test set documented
6. **Security scan** (all changes): SBOM generated; known vulnerabilities addressed

Regression testing is executed in CI (GitHub Actions) for automated checks; human review required for validation report sign-off.

---

## 9. Human Approval Chain

No model update may be deployed to production without completion of the following approval chain:

```
[Data Science Team]
  Trains and validates model on sealed test set
  Documents performance metrics and regression test results
          |
          v
[Clinical Validation Committee]
  Reviews clinical performance data
  Confirms performance thresholds met
  Approves clinical adequacy
          |
          v
[Regulatory Affairs Lead]
  Reviews against PCCP scope
  Confirms no new 510(k) submission required (or initiates one)
  Signs off on regulatory compliance
          |
          v
[VP Engineering]
  Reviews deployment plan
  Confirms infrastructure readiness
  Approves production deployment
          |
          v
[Production Deployment]
  Phased rollout per PCCP update procedure
  Monitoring activated for 30 days post-deployment
```

All approvals must be documented with name, date, and signature before deployment proceeds. No step may be skipped. Emergency exceptions require CEO or CMO written authorization with documented justification.

---

## 10. Rollback Procedure

In the event of a post-deployment model failure or unexpected performance degradation:

### 10.1 Rollback Steps
1. **Incident declared** by on-call engineer or monitoring alert
2. **Assessment** (15 minutes): Confirm model-related vs. infrastructure issue
3. **Rollback decision** by Engineering Lead + Regulatory Affairs (or on-call VP)
4. **Execute rollback**:
   - `kubectl rollout undo deployment/lumenai-api` (reverts to previous pod image)
   - Alembic downgrade if database schema changed (requires tested downgrade script)
   - Docker image tag reverted to previous SHA in K8s manifest
   - Model registry entry updated: status → ROLLED_BACK
5. **Verify rollback**: Automated health checks; manual validation spot check
6. **Notify affected sites**: Within 30 minutes of rollback completion
7. **Root cause investigation**: Complete within 5 business days
8. **Post-incident review**: Document findings; update risk management file if new hazard identified

### 10.2 RTO Target
- **15 minutes** from rollback decision to restored service (K8s rollback is near-instantaneous; database downgrade adds time if needed)
- RTO exceeding 60 minutes triggers DR escalation protocol

---

## 11. Post-Market Performance Monitoring

Ongoing monitoring conducted via P12 RWE module:

| Activity | Frequency | Responsible | Output |
|---------|----------|------------|--------|
| PSI/CSI calculation | Monthly (automated) | Data Science | Drift dashboard update |
| Performance metrics review (labeled subset) | Quarterly | Clinical Validation Committee | Quarterly performance report |
| Full model performance audit | Annual | Data Science + Clinical | Annual model audit report |
| Retraining trigger assessment | Quarterly | Data Science + Regulatory Affairs | Go/No-Go decision documented |
| Post-market surveillance summary | Annual | Regulatory Affairs | Annual report (FDA post-market) |
| RWE enrollment review | Quarterly | Clinical Validation Committee | Enrollment status report |

All monitoring outputs archived in regulatory evidence repository with 7-year retention.
