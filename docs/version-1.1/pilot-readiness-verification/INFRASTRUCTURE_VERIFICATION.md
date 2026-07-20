# LPR-DIR-030 — Infrastructure Verification (Workstream 1)

**Independent Verification Authority.** Verification standard (non-negotiable):
*implementation ≠ verification; documentation ≠ evidence; configuration ≠ operational
capability.* Two columns are kept distinct: **Technique verified** (re-run independently in
the dev sandbox) vs **Pilot-Entry Gate satisfied** (requires the managed environment).

**Independent action performed:** I re-ran `scripts/pilot-verification/verify_capabilities.py`
myself (not trusting the DIR-029 report). Result: **exit 0, 6/6 checks pass** (fresh run).

| Capability | Technique verified (dev)? | Evidence I re-observed | Managed-env / Pilot-Gate satisfied? |
|---|---|---|---|
| **Managed database** | — | none exists (no Postgres server in this environment) | ❌ **FAIL** — no managed DB, no connection proof, no snapshot |
| **Automated backups** | ⚠️ mechanic only | harness §5: 1000 rows backed up + restored — **SQLite analog**, explicitly not managed Postgres | ❌ **FAIL** — no managed-DB backup artifact |
| **Secrets management** | ✅ | harness §1: `token_urlsafe(40)` + SHA-256 + rotation → PASS | ❌ **NOT VERIFIED** — no managed secrets store/injection evidence |
| **TLS** | ✅ | harness §2: X.509 issued for `pilot.lumenai.local`, `openssl verify … OK` | ❌ **NOT VERIFIED** — no ingress/domain serving a cert |
| **Environment provisioning** | — | no kubectl/helm/cluster in this environment | ❌ **FAIL** — no cluster/namespace stood up |

## Rejected claims (evidence audit tie-in)
- **Backup as managed-DB backup:** REJECTED — the demonstrated backup is a SQLite analog;
  it does not verify the managed-Postgres backup gate.
- **TLS/secrets as "provisioned":** REJECTED as gate-satisfying — cert *generation* and
  secret *generation* are techniques, not a provisioned managed ingress/secrets store.
- **Screenshots / deployment records / managed-DB snapshots:** none were produced by
  DIR-029 (honestly), so there is nothing to accept — and nothing is fabricated here.

## Determination
**Infrastructure techniques are independently verified in the sandbox** (secrets, TLS,
backup mechanic). **No managed-environment infrastructure gate is satisfied** — managed DB,
managed backups, managed secrets/TLS, and cluster provisioning are **FAIL / NOT VERIFIED**
because no managed environment exists to produce operational evidence.
