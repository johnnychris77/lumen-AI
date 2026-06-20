# Predetermined Change Control Plan (PCCP)
LumenAI Surgical Instrument Inspection Software | Version 1.0
**Prepared per FDA "Artificial Intelligence/Machine Learning (AI/ML)-Based Software as a
Medical Device (SaMD) Action Plan" (January 2021) and draft guidance.**
**Subject to regulatory counsel review and FDA feedback before finalization.**

## 1. Purpose
This PCCP describes how LumenAI plans to make modifications to its AI/ML models
post-clearance without requiring a new 510(k) submission for each change, provided
the modifications fall within the pre-specified boundaries defined herein.

## 2. Device Modification Types Covered

### Type 1 — Minor Model Update (No Submission Required)
**Definition**: Bug fixes, calibration adjustments, data preprocessing updates that do not
change model architecture, training data sources, or intended use.
**Performance boundary**: Overall kappa must remain ≥ 0.80 and critical FN rate ≤ 2%.
**Verification required**: Full automated test suite (1,163+ tests) passes; regression on
validation dataset shows ≤ 2% degradation in any per-category metric.
**Reporting**: Document in Software Version History; include in next annual report.

### Type 2 — Moderate Model Update (Real-World Performance Report Required)
**Definition**: Retraining on new data (same distribution), threshold adjustments, feature
additions that do not change intended use or finding categories.
**Performance boundary**: Kappa ≥ 0.80, critical sensitivity ≥ 95%, FN ≤ 2%.
**Verification required**: Full test suite + validation on held-out dataset (≥ 500 cases) +
comparison report showing non-inferiority to cleared version.
**Reporting**: File 30-day report to FDA with performance data.

### Type 3 — Major Model Update (New Submission Required)
**Definition**: New finding categories, new intended use, new patient populations, change
in human-in-the-loop requirements, architecture change (CNN → transformer), new modality.
**Required action**: New 510(k) or De Novo submission before deployment.

## 3. Pre-Specified Performance Objectives

| Metric | Cleared Baseline | Minimum Acceptable | Maximum Acceptable |
|--------|-----------------|-------------------|-------------------|
| Overall Cohen's kappa | ≥ 0.80 | 0.80 | — |
| Critical finding sensitivity | ≥ 95% | 95% | — |
| Critical FN rate | ≤ 2% | — | 2% |
| Overall precision | ≥ 85% | 85% | — |
| False positive rate | ≤ 15% | — | 15% |
| PSI (distribution drift) | < 0.20 | — | 0.20 |

## 4. Pre-Specified Methodology

### Performance Measurement
- Dataset: Held-out validation set (15% split, sealed, independent evaluation)
- Minimum case count: 500 cases (stratified by finding category)
- Ground truth: Consensus of ≥ 3 SPD educators
- Statistical method: Wilson 95% CI; one-sided non-inferiority test

### Drift Detection (Post-Market)
- Weekly RWE metric snapshots via P12 RWE scheduler
- PSI computed on finding_category distribution vs. cleared version baseline
- Alert threshold: PSI > 0.20 triggers Type 2 review process
- CSI threshold: > 0.15 triggers human review

### Update Evaluation Timeline
| Step | Type 1 | Type 2 | Type 3 |
|------|--------|--------|--------|
| Internal regression | 3 days | 5 days | 10 days |
| Validation dataset eval | N/A | 10 days | 30 days |
| Clinical committee review | 1 day | 5 days | 30 days |
| Regulatory approval | N/A | 30-day report | 510(k) |
| Total elapsed | ~1 week | ~3 weeks | 3–6 months |

## 5. Human Approval Chain (All Update Types)
1. **Data Science Lead**: Certifies model meets performance thresholds
2. **Clinical Validation Committee**: Reviews clinical evidence
3. **Regulatory Affairs**: Confirms change category, files required reports
4. **VP Engineering**: Signs deployment authorization
5. **CISO**: Confirms no new cybersecurity risks

## 6. Rollback Plan
- All deployed model versions are tagged in Docker registry (`lumenai/backend:{version}`)
- `kubectl rollout undo deployment/lumenai-backend` restores previous version in < 15 minutes
- Alembic downgrade available for schema changes (tested in staging)
- Rollback trigger: any post-deployment performance metric falls below PCCP minimum threshold

## 7. Post-Market Reporting
- Monthly: RWE dashboard reviewed by Clinical Validation Committee
- Quarterly: Formal RWE report submitted to Regulatory Affairs
- Annual: FDA annual report (post-clearance, 510(k) requirement)
- Adverse events: FDA MDR within 30 days of awareness (21 CFR Part 803)

## 8. Limitations of This PCCP
- This PCCP covers locked model updates only (no online/continuous learning)
- Does not cover changes to non-AI modules (P8–P10 administrative modules)
- Subject to FDA review — modifications to this plan require FDA notification
