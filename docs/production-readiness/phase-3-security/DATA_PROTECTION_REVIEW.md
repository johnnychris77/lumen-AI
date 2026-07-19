# LPR-DIR-014 — Data Protection Review (Phase 3)

**Basis:** code + config inspection at `f889d95`.

## Protection controls

| Control | Status | Evidence / note |
|---|---|---|
| Transport encryption | Deploy-time | TLS terminated at ingress (Helm/K8s/Render); app assumes HTTPS; CORS credentialed |
| Database encryption at rest | **Infra-dependent** | Provided by managed Postgres (RDS/Render); not app-enforced — document as deployment control (SEC-DP-01) |
| Secrets storage | **Strong** | Secret API keys → `secrets.token_urlsafe(40)`, stored **SHA-256 hash only**, never retrievable; passwords PBKDF2/bcrypt |
| Secrets in config | **Conditions** | Insecure fallback defaults for `SECRET_KEY` (SEC-AUTH-01); no startup validation (SEC-AUTH-02) |
| Key management | Basic | Env-injected secrets; no KMS/rotation abstraction (SEC-DP-02, future) |
| Backups / DR | **Verified** | Backup/restore + DR executed with measured RTO/RPO (foundation) |
| Retention / deletion | **Retention-first** | Soft-deactivate/retain across governed objects; preserves evidence lineage |
| Immutable objects | **Verified** | Image bytes, annotation, GT, baseline, model, audit immutable/append-only |

## Per-governed-object protection

| Object | SoR | Immutability | Tenant | Notes |
|---|---|---|---|---|
| Inspection | inspection models | state-machine | ✅ | no false closure |
| Image | `RetainedImage` | **immutable bytes**, `image_sha256`, hash-verified | ✅ | sole byte owner |
| Metadata | capture fields | pinned to image | ✅ | validation only |
| Annotation | `AnnotationVersion` | **append-only** | ✅ | new version only |
| Ground Truth | `Annotation` GT (ACTIVE) | **immutable, superseded not overwritten** | ✅ | |
| Baseline | `BaselineLibraryEntry` | append-only lifecycle | ✅ | hash-verified access |
| Digital Twin | `digital_twin_id` (LCID) | identity immutable | ✅ | composed history |
| Evidence | evidence bundle | checksummed, audit-immutable | ✅ | authz-gated |
| Dataset | `DatasetVersion` | **NOT lock-enforced when frozen (SEC-DP-03/AR-17)** | ✅ | integrity gap |
| Audit | `enterprise_audit_service` | **hash-chained, append-only** | ✅ | single writer |
| Reports | reporting release | from governed records | ✅ | not editable in place |

## Findings
| ID | Sev | Finding |
|---|---|---|
| SEC-DP-03 | MEDIUM | Frozen `DatasetVersion` not lock-enforced (`dataset_builder` writes split/quality without checking `frozen`) — dataset integrity/reproducibility (=AR-17) |
| SEC-DP-01 | LOW | DB encryption-at-rest is an infra control; document/enforce per deployment |
| SEC-DP-02 | LOW/FUTURE | No KMS/secret-rotation abstraction; env-injected secrets only |

**Positive:** SHA-256-only secret storage, strong password KDFs, immutable governed
objects (image/annotation/GT/baseline/model/audit), retention-first deletion, DR
with measured RTO/RPO. No PHI in demo data/image metadata (policy-aligned). The
material data-protection gaps are dataset-freeze enforcement (SEC-DP-03) and the
secret-default theme (SEC-AUTH-01/02).
