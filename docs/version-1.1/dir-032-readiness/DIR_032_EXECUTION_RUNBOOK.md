# DIR-032 EXECUTION RUNBOOK — (prep, post-EXEC-001)

Ordered run plan for producing DIR-032 operational evidence, to be executed by the contexts in
`DIR_032_EXECUTING_CONTEXT_REQUIREMENTS.md` once EXEC-001 provisioning + credential intake
complete. Each step lists the command(s) and the **evidence artifact** to capture (logs ·
timestamps · env id · commit SHA · operator · verification step). Maps to
`../pilot-operational-capability/DIR_032_ACCEPTANCE_CHECKLIST.md`.

## §0 Pre-flight (gate — all must pass before §1)
```
# credential intake confirmed (see DIR_032_CREDENTIAL_INTAKE_CHECKLIST.md)
curl -fsS https://<endpoint>/health            # expect 200 over HTTPS  → env reachable
# GitHub Actions auth reachability (dry): deploy.yml first job authenticates to cluster
```
Evidence: health 200 transcript + Actions auth-step log. **If §0 fails, STOP — do not proceed.**

## §1 WP-2 Deployment
```
gh workflow run deploy.yml -f environment=staging     # or Actions → Run workflow
kubectl -n lumenai get deploy lumenai -o jsonpath='{.metadata.uid} {.spec.template.spec.containers[0].image}'
kubectl -n lumenai rollout status deploy/lumenai --timeout=300s
curl -fsS https://<endpoint>/health                   # smoke → 200
alembic -c backend/alembic.ini current                # single head e7b2f4a86c31
```
Evidence: run URL, deployment UID, image/version, rollout log w/ timestamps, smoke 200, alembic head.

## §2 WP-3 Rollback
```
# deploy A, deploy B, force B unhealthy, then:
t0=$(date +%s); kubectl -n lumenai rollout undo deploy/lumenai
kubectl -n lumenai rollout status deploy/lumenai --timeout=300s; t1=$(date +%s); echo "MTTR=$((t1-t0))s"
curl -fsS https://<endpoint>/health                   # post-rollback smoke
```
Evidence: A→B→A transcript, MTTR, post-rollback 200. Repeat ≥2×.

## §3 WP-4 Backup & DR
```
pg_dump "$DATABASE_URL" -Fc -f backup_$(date -u +%Y%m%dT%H%M%SZ).dump
t0=$(date +%s); pg_restore -d "$RESTORE_URL" --clean --if-exists backup_*.dump; t1=$(date +%s); echo "RTO=$((t1-t0))s"
psql "$RESTORE_URL" -c "select count(*) from <critical_tables>;"   # parity
```
Evidence: backup artifact + timestamp, restore transcript, RTO, RPO statement, row parity.

## §4 WP-5 Observability & Alerting
```
# confirm metrics on dashboard; then induce controlled failure:
kubectl -n lumenai scale deploy/postgres --replicas=0
#   assert: alert FIRES → delivered → operator ACK → restore → RESOLVES
kubectl -n lumenai scale deploy/postgres --replicas=1
```
Evidence: dashboard screenshot, alert payload, delivery receipt+ts, ack ts, resolve ts.

## §5 WP-6 Secrets & TLS
```
openssl s_client -connect <endpoint>:443 -servername <host> </dev/null   # served cert
curl -I http://<endpoint>/                                               # HTTPS enforced
# rotate one secret in the store → app accepts new, rejects old
```
Evidence: cert inspection, HTTP→HTTPS enforcement, rotation transcript (no values).

## §6 WP-7 Incident Response drill
```
# ≥1 controlled scenario (DB down / app restart / deploy failure) with timeline:
kubectl -n lumenai rollout restart deploy/lumenai
```
Evidence: timestamped timeline detect→act→recover→verify.

## §7 Evidence handoff
Collect all artifacts (run URLs, transcripts, screenshots, receipts) and provide them back to
the program, which will index them under `../pilot-operational-capability/evidence/` with a row
per WP in `OPERATIONAL_EVIDENCE_INDEX.md`, then drive **DIR-033** re-certification.

## Guardrails
- Synthetic/non-PHI data only. No secret values in logs/repo. No `Bearer dev-token`.
- No pilot/production/clinical/regulatory claim. Pilot Entry remains DENIED until DIR-033.
