# DIR-032 ACCEPTANCE CHECKLIST — LPR-DIR-031A

The objective evidence each DIR-032 Work Package MUST produce once the authorized environment
exists. DIR-032 is COMPLETE only when every row is satisfied with captured, reproducible
evidence (logs · timestamps · environment id · commit SHA · operator · verification steps).
Rows map to the ready-to-run procedures already written in
`../pilot-operational-capability/*_EXECUTION_REPORT.md`.

## WP-2 Deployment
- [ ] `deploy.yml` run URL + deployment ID + deployed image/version.
- [ ] `kubectl rollout status` success transcript with timestamps.
- [ ] `GET /health` → 200 over HTTPS at the ingress (smoke).
- [ ] Migrations applied on managed Postgres (`alembic current` = single head `e7b2f4a86c31`).

## WP-3 Rollback
- [ ] Deploy A → B → forced-fail → `rollout undo` transcript.
- [ ] **MTTR** measured (timestamped) + post-rollback `/health` 200.
- [ ] Repeated ≥2× (repeatability).

## WP-4 Backup & DR
- [ ] `pg_dump` backup of managed DB (artifact + timestamp).
- [ ] Restore to a **clean** target; row-count + schema-head parity.
- [ ] **RTO** measured; **RPO** stated.

## WP-5 Monitoring & Alerting
- [ ] Metrics visible on a dashboard from the running instance.
- [ ] Controlled failure induced → alert **fires**.
- [ ] Alert **delivered** to channel (receipt + timestamp).
- [ ] Alert **acknowledged** + **resolved** (timestamps).

## WP-6 Secrets & TLS
- [ ] Secret injected from the store into the running app (no plaintext in manifest/image).
- [ ] Secret **rotated**: app accepts new, rejects old.
- [ ] Served certificate inspected (`openssl s_client`); HTTPS enforced (HTTP refused/redirected).

## WP-7 Incident Response
- [ ] ≥1 controlled operational exercise (DB down / app restart / deploy failure) with a
      timestamped timeline: detect → act → recover → verify.

## Engineering blocker closure (WP-9, reassessed in DIR-033)
Only when the above evidence exists can these move toward VERIFIED (DIR-033 decides):
- [ ] SCAL-01 (managed DB + backup) · OPS-DEP-01 (deploy) · OPS-DEP-02 (rollback+MTTR) ·
      OPS-INC-01 (alerting+IR) · DR · E-02 (secrets/TLS on env).

## Out of scope (remain external, unchanged)
Clinical prerequisites (E-09..E-17) and executive approvals (E-18..E-23) are **not** closed by
DIR-032; they belong to DIR-034 (Controlled Pilot Authorization) and the clinical work packages.

## Completion rule
DIR-032 exits COMPLETE only if all WP-2..WP-7 rows are evidenced. Any missing row →
COMPLETE-WITH-GAPS or INCOMPLETE, per the same honesty standard used throughout the program.
