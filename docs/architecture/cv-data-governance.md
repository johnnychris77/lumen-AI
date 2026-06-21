# CV Data Governance — Milestone P4

## Purpose

This document defines policies for image data handling, retention, privacy, audit trail, model versioning, and provider swap governance within the LumenAI Computer Vision subsystem.

---

## Data Classification

| Data Type | Classification | PHI Risk |
|---|---|---|
| Instrument inspection images | Internal — Confidential | Low (no patient identifiers if URL policy enforced) |
| Baseline reference images | Internal — Confidential | None |
| Borescope images | Internal — Confidential | Low |
| Barcode / UDI values | Internal — Sensitive | Low (instrument serial; no direct patient link) |
| `CVInferenceResult` JSON | Internal — Sensitive | Low |
| `result_json` column (DB) | Internal — Sensitive | Low |

**PHI in image URLs is strictly prohibited.** Image filenames and paths must use instrument model codes and anonymized lot identifiers only. Patient identifiers, procedure codes, and case numbers must never appear in image URLs.

---

## Image Retention Policy

| Image Type | Retention Period | Storage Location | Deletion Method |
|---|---|---|---|
| Inspection images | 7 years (regulatory) | Object storage (tenant-namespaced bucket) | Secure delete + tombstone record |
| Baseline reference images | Permanent (until superseded) | Object storage (read-only baseline bucket) | Version-preserved; old versions archived |
| Training images | Indefinite (model IP) | Separate training data store | Access-controlled; separate from production |
| Rejected / failed images | 90 days | Quarantine bucket | Auto-purged by lifecycle rule |

`cv_inference_records.image_url` and `baseline_image_url` columns store URLs, not image bytes. Raw image bytes are never written to the relational database.

---

## Audit Trail

Every CV inference is persisted to `cv_inference_records` by `pipeline._persist()` when a `db` session is provided. The record is immutable after creation.

### What is logged per inference

- Full `CVInferenceResult` as JSON (`result_json` column)
- Provider name and model version strings
- Processing duration (`processing_ms`)
- Tenant ID
- All scores and finding counts (denormalized for KPI queries)
- Baseline comparison result and verdict

### What is NOT logged

- Raw image bytes
- Base64 image payloads (`image_data_b64` field)
- Provider API credentials or internal model weights

### Tamper Detection

`cv_inference_records` rows must not be updated after insert. DB-level policy:

```sql
-- Revoke UPDATE privilege on cv_inference_records for application role
REVOKE UPDATE ON cv_inference_records FROM lumenai_app;
```

For cloud deployments, enable object-storage versioning on the audit export bucket so that log exports are cryptographically verifiable.

---

## Provider Swap Policy

The active CV provider is selected via the `CV_PROVIDER` environment variable. Provider swaps follow a promotion process:

### Promotion Gates

1. **Offline evaluation:** New provider must achieve ≥ 90% precision and ≥ 85% recall on the held-out test set for each finding category before promotion.
2. **Shadow mode:** New provider runs in parallel with the current provider for ≥ 500 inferences; outputs are compared but not served to end users.
3. **Staged rollout:** New provider serves 10% of traffic for 48 hours; alert thresholds set on `recognition_rate_pct` and `avg_baseline_match_pct` from `/kpi-summary`.
4. **Full promotion:** `CV_PROVIDER` updated in secrets manager; old provider deregistered.

### Rollback

`CVRegistry.reset()` combined with changing `CV_PROVIDER` triggers re-instantiation on next request. No restart required. Rollback SLA: < 5 minutes.

---

## Model Versioning

`CVInferenceResult.model_versions` is a `dict[str, str]` recording the version of each model component used for the inference:

```json
{
  "instrument_recognizer": "v2.1.0",
  "contamination_detector": "v1.4.2",
  "damage_detector": "v1.3.0",
  "baseline_comparator": "ssim-v1"
}
```

Rules:
- Model versions are immutable once deployed; a new training run produces a new version string.
- `result_json` stores `model_versions` verbatim, enabling retrospective audits of which model produced a given finding.
- Model version strings follow semver: `MAJOR.MINOR.PATCH`. Breaking schema changes increment MAJOR.

---

## Inter-Annotator Agreement

Training labels must achieve Cohen's κ ≥ 0.80 before acceptance. Annotation workflow:

1. Two independent annotators label each image.
2. Agreement is computed per finding category.
3. Disagreements go to a clinical expert adjudicator.
4. Adjudicated labels are gold-standard; used for test set construction.

Annotator IDs are stored in annotation metadata (not in `CVInferenceRecord`) so that annotator performance can be tracked over time.

---

## Access Control

| Role | Permissions |
|---|---|
| `operator` | Run inference, view history, view KPI summary |
| `admin` | All operator permissions + view `result_json`, trigger baseline comparisons |
| `superadmin` | All admin permissions + manage providers, access training data |

Provider configuration (`CV_PROVIDER`, API keys) is accessible only to deployment infrastructure roles, not application-layer roles.

---

## Tenant Isolation

- `tenant_id` is stored on every `CVInferenceRecord`.
- `/history` and `/kpi-summary` endpoints filter by `tenant_id` from the auth token; cross-tenant queries are blocked at the route layer.
- Baseline images are stored in tenant-namespaced paths: `baselines/{tenant_id}/{instrument_model}/{version}.jpg`.
- The mock provider returns the same deterministic output regardless of tenant (safe for demo; real providers must enforce tenant-level model isolation if fine-tuned).

---

## Incident Response

| Event | Response |
|---|---|
| PHI discovered in image URL | Immediately revoke URL; purge `image_url` column value; notify DPO within 24h |
| Model produces systematically wrong findings | Activate rollback; set `CV_PROVIDER=mock` as safe fallback; initiate shadow evaluation |
| Provider API key leaked | Rotate key immediately; audit `cv_inference_records` for affected time window |
| `cv_inference_records` tampered | Restore from immutable audit export; file integrity incident report |

---

## Regulatory Alignment

| Standard | Relevance | CV Subsystem Controls |
|---|---|---|
| FDA 21 CFR Part 820 (QSR) | Instrument inspection software is a quality system record | Immutable inference records; model version tracking |
| EU MDR Annex I | Software as a medical device safety requirements | Provider swap gating; recall thresholds |
| HIPAA | PHI must not appear in instrument images | URL policy; EXIF stripping before storage |
| ISO 13485 | Medical device quality management | Annotator agreement standards; training data traceability |
