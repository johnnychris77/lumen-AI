# LPR-DIR-029 — Pilot Evidence Collection (Workstream 6)

Objective evidence for each capability that was actually **executed** in this environment.
Reproduce with:

```bash
.venv/bin/python scripts/pilot-verification/verify_capabilities.py
```

Source of the harness: `scripts/pilot-verification/verify_capabilities.py` (committed).
Result: **exit 0, 6/6 checks passed** (dev/sandbox scope). `ruff check` on the harness:
**All checks passed**.

## Verification output (verbatim, real run)

```
1. SECRET GENERATION + SHA-256 HASH-ONLY STORAGE + ROTATION
issued secret #1 length=54 chars; stored sha256=a586d6f0e9a7…01be4d
rotated secret #2 length=54 chars; stored sha256=930f0d96cc5b…17cc0e
[PASS] secret is token_urlsafe(40)
[PASS] rotation produces a different secret+hash
[PASS] only sha256 hash would be persisted (64 hex chars)

2. TLS CERTIFICATE GENERATION + VALIDATION (openssl)
subject=CN = pilot.lumenai.local
notBefore=Jul 20 00:15:36 2026 GMT   notAfter=Jul 20 00:15:36 2027 GMT
sha256 Fingerprint=E8:79:92:BB:1D:8D:24:0F:C9:32:E7:D2:18:F0:1B:39:29:99:A2:39:0E:F1:D4:EF:B4:1E:53:13:68:44:04:E4
openssl verify (self-signed as its own CA): /tmp/…/tls.crt: OK
[PASS] generated + inspected a valid X.509 cert

3. APPLICATION HEALTH PROBE (real app code via TestClient)
GET /health -> 200 {'status': 'ok', 'version': 'P11', 'environment': 'development'}
[PASS] /health returns 200 ok

4. FAIL-CLOSED WEBHOOK SECURITY (real route code)
no signing secret configured        -> 503 (expect 503, fail-closed)
secret set, bad signature           -> 401 (expect 401, reject)
secret+tenant set, valid signature  -> signature accepted; DB write needs a migrated DB; happy-path proven in CI test_p17
[PASS] webhook fail-closed demonstrated (503 no-secret / 401 bad-sig)

5. BACKUP + RESTORE DRILL (SQLite analog — NOT the managed pilot DB)
rows before=1000; backup=8.4 ms; rows in restored backup=1000; restore-open=0.7 ms
[PASS] backup captured and restored all rows (analog)

6. SCHEMA MIGRATION CHAIN INTEGRITY
migration files: 13 revisions; head(s): ['e7b2f4a86c31']
[PASS] exactly one alembic head

SUMMARY: 6/6 capability checks passed (dev/sandbox scope only).
```

## Evidence index (type → reference)

| Capability | Evidence type | Reference |
|---|---|---|
| Deploy workflow (real, fail-closed) | configuration / code diff | `.github/workflows/deploy.yml` (this PR) + YAML-valid + placeholder-removed checks |
| Secret gen/rotation/hash | verification output | harness §1 (above) |
| TLS cert gen/validation | verification output (openssl) | harness §2 (above) |
| App health/readiness | verification output | harness §3 + `backend/app/main.py:294,304` |
| Fail-closed webhook | verification output | harness §4 + CI `backend/tests/test_p17_recommendations.py` |
| Backup + restore (analog) | verification output + timing | harness §5 |
| Schema head integrity | verification output | harness §6 |
| Structured logging | run logs | harness stderr (JSON log lines) |

## Evidence that DOES NOT exist (honest — not fabricated)

- **Screenshots / dashboards** of metrics/alerting — none; no monitoring stack exists here.
- **Deployment records** from a real cluster — none; deploy workflow not executed against a cluster.
- **Managed-DB backup snapshots / restore transcripts** — none; no managed Postgres.
- **Container image digests / registry push records** — none; no image built/pushed.
- **On-call / incident-response drill logs** — none; no alerting/on-call backend.

These are marked **NOT STARTED** in `PILOT_ENTRY_EVIDENCE_STATUS.md`; they require a managed
environment this sandbox does not provide.
