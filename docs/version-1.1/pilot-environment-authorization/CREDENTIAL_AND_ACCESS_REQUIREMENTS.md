# CREDENTIAL & ACCESS REQUIREMENTS — LPR-DIR-031A

Exactly what the DIR-032 executing context needs, how it must be delivered, and the
least-privilege posture. **This document lists credential *names* and *delivery methods* only
— never values. No secret is or will be committed to the repository.**

## 1. Credentials/access required by DIR-032 (by Work Package)
| Ref | Name | Delivered as | Consumed by | Least-privilege scope |
|---|---|---|---|---|
| K1 | `KUBE_CONFIG` (staging) | CI secret (GitHub Actions) | `deploy.yml` staging job | deploy/rollout on the pilot namespace only |
| K2 | `KUBE_CONFIG_PROD` | CI secret | `deploy.yml` prod job | **not used in DIR-032** (pilot-grade only); reserved |
| D1 | `DATABASE_URL` (managed Postgres) | secrets store → app env | app runtime, migrations, backup | pilot DB only; no cross-env access |
| D2 | Restore-target DB URL | secrets store (DR job) | backup/restore drill | isolated restore instance |
| W1 | `WEBHOOK_SECRET_<SYS>` | secrets store → app env | webhook verification | per-integration; rotatable |
| W2 | `WEBHOOK_TENANT_<SYS>` | secrets store → app env | webhook tenant binding | per-integration |
| W3 | `STRIPE_WEBHOOK_SECRET` | secrets store → app env | billing webhook (if exercised) | single purpose |
| S1 | App signing/JWT keys | secrets store → app env | auth | issue once; rotatable; hash-verified |
| O1 | Alerting channel token (email/Slack/PagerDuty) | secrets store / alert-manager config | alert delivery | send-to-one-channel only |
| R1 | Container registry pull/push creds | CI secret | image build/publish + cluster pull | pilot repo only |

## 2. Delivery rules (non-negotiable)
- Secrets are set in the **managed secrets store** and/or **CI secret settings** — **never** in
  the repo, `.env`, manifests, code, logs, PR text, or commit messages.
- The repo continues to track only `*.env.example` placeholders (verified clean in DIR-030).
- Secret **values** are never echoed to CI logs; only presence/absence is asserted.
- Rotation is supported: rotating a value in the store must let the app pick up the new value
  and reject the old — this is itself DIR-032 WP-6 evidence.

## 3. Least-privilege principles
- Each credential scoped to the **single** resource + action it needs (deploy to one
  namespace; read/write one DB; publish to one registry repo; send to one alert channel).
- No shared "god" credential. No production access in the pilot-grade path (K2 reserved,
  unused in DIR-032).
- Service accounts auditable; revocable independently.

## 4. What the executing context must confirm before DIR-032
- [ ] K1, D1, W1–W3, S1, O1, R1 present in the store/CI (presence check, not value dump).
- [ ] `GET /health` over HTTPS returns 200 at the ingress.
- [ ] A no-op `deploy.yml` dry-run authenticates to the cluster (auth reachability).

## 5. Security-constraint compliance
This document reintroduces **no** hardcoded credentials and **no** `Bearer dev-token`; it does
not weaken auth. All values live in a managed store, hash-only where applicable, consistent
with the program's non-negotiable security constraints.
