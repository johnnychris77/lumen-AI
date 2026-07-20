# LPR-DIR-030 — Evidence Audit (Workstream 5)

Every DIR-029 evidence item audited against the standard. **Accept** = objective evidence
supports the specific claim. **Reject** = unsupported, mis-scoped, provenance-less, or
"documentation/config presented as operational capability."

| # | Evidence item (DIR-029) | Audit result | Reason |
|---|---|---|---|
| 1 | Harness §1 secret gen/rotation/hash | ✅ **ACCEPT (dev technique)** | Independently re-run; deterministic, reproducible output |
| 2 | Harness §2 TLS cert gen + `openssl verify OK` | ✅ **ACCEPT (dev technique)** | Independently re-run; verifiable fingerprint |
| 3 | Harness §3 `/health` 200 | ✅ **ACCEPT (app primitive)** | Independently re-run against real app code |
| 4 | Harness §4 fail-closed webhook 503/401 | ✅ **ACCEPT (behavior)** | Independently re-run on the real route |
| 5 | Harness §5 backup/restore 1000 rows | ⚠️ **ACCEPT as ANALOG ONLY** | Real mechanic, but SQLite — **REJECT** as evidence for the managed-DB backup gate |
| 6 | Harness §6 single alembic head | ✅ **ACCEPT** | Independently re-derived (`e7b2f4a86c31`) |
| 7 | `deploy.yml` real workflow (placeholder removed) | ✅ **ACCEPT as ARTIFACT** | Re-inspected: 0 echo-stubs, 8 real verbs, valid YAML — **REJECT** as evidence of a *performed* deployment |
| 8 | Managed DB / cloud secrets / TLS ingress / cluster | ❌ **REJECT (absent)** | No artifacts exist; correctly not claimed COMPLETE by DIR-029 |
| 9 | Screenshots / dashboards / deployment records / container digests | ❌ **REJECT (absent)** | None produced; **none fabricated** — nothing to accept |
| 10 | Alerting / on-call / incident-response drill logs | ❌ **REJECT (absent)** | No backends; no drill evidence |

## Provenance + integrity checks
- **Reproducibility:** the accepted items (1–7) are re-runnable from committed artifacts
  (`scripts/pilot-verification/verify_capabilities.py`, `.github/workflows/deploy.yml`) — I
  reproduced them independently on head `66c2e0d`.
- **No provenance-less screenshots:** none were submitted; the audit did not accept any
  image evidence (there is none).
- **No undocumented completion:** every "COMPLETE"-looking claim was cross-checked; DIR-029
  honestly marked managed items NOT COMPLETE, so no false completion was found to reject.

## Determination
DIR-029's evidence is **honest and internally consistent**: it claims only dev-sandbox
techniques + a workflow artifact, and does **not** overclaim managed-environment capability.
**Accepted:** 6 dev-technique items + 1 workflow artifact. **Rejected/absent:** all
managed-environment operational evidence (it does not exist). No fabricated or
provenance-less evidence was found.
