# LPR-DIR-028 — Managed Environment Implementation Plan (Workstream 2)

Implementation plan for the managed pilot environment. **Plan only — nothing here is
provisioned or demonstrated.** Existing repo assets (`helm/lumenai/*`, `k8s/*`, Dockerfiles,
`docs/foundation/*`) are reused where noted.

| Capability | Current state (IRC-1) | Implementation | Verification (objective evidence) |
|---|---|---|---|
| **Managed database** | single-container Postgres (SPOF) | Provision managed Postgres (or HA pair); apply `alembic upgrade head` (`e7b2f4a86c31`) | `SELECT version()` from managed host; migration transcript; WP-05 restore drill |
| **Secrets management** | env vars / dev fallbacks | Secrets store (k8s Secrets via `helm/lumenai/templates/secret.yaml` or external manager); inject `SECRET_KEY`, `WEBHOOK_SECRET_*`, `WEBHOOK_TENANT_*`, `STRIPE_WEBHOOK_SECRET`, DB URL | No literal secrets in manifests; app boots without dev fallbacks; `main.py` prod guard passes |
| **Environment provisioning** | none (no cluster) | Provision cluster/namespace (`k8s/namespace.yaml`); apply manifests/Helm chart; single replica for pilot | `kubectl get pods` healthy; readiness probe 200 |
| **TLS** | none | Ingress TLS (`k8s/ingress.yaml`) + managed cert | `curl -v https://…` shows valid cert; HTTP→HTTPS redirect |
| **Monitoring** | health/monitoring service in code | Deploy metrics/health scrape; dashboards for latency/error/DB/safety-fail-closed | Dashboard shows live metrics; health endpoint scraped |
| **Logging** | structured app logging | Central log aggregation; retention policy | Query a known request across aggregated logs |
| **Alerting** | none | Alert rules → routing → on-call (WP-02) | Synthetic alert delivered + acknowledged |
| **Backups** | documented + dev exercise | Automated managed snapshots + schedule | Snapshot listing; scheduled job config |
| **Disaster recovery** | runbook + prior dev RTO/RPO | Restore-to-clean-instance drill on pilot-class env | Restore transcript + measured RTO/RPO |
| **Rollback** | schema-compatible by construction (no migration) | Real deploy A→B→A on the env (WP-03/WP-04) | Rollback transcript + post-rollback smoke test green |

## Sequencing
1. Environment + secrets + TLS (WP-06) → 2. Managed DB + migrations (WP-01) →
3. Real deploy path (WP-03) → 4. Monitoring/logging/alerting (WP-02/03) →
5. Backup + DR drill (WP-05) → 6. Rollback drill (WP-04).

## Honest caveat
This plan describes **how** to build the managed environment. **No capability is
demonstrated by this document.** Each row's "Verification" column must produce recorded
evidence in `PILOT_ENTRY_EVIDENCE_TRACKER.md` before the corresponding gate can be
considered for closure. Container image build/publish + a fresh SBOM (LPR-DIR-026 integrity
gaps) are prerequisites for WP-03 and are included in the deploy work package.
