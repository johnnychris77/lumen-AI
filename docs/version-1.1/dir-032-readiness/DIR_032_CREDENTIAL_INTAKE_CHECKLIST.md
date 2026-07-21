# DIR-032 CREDENTIAL INTAKE CHECKLIST — (prep, post-EXEC-001)

**Context:** EXEC-001 (Executive Environment Authorization) is asserted GRANTED by the
governance authority; environment provisioning + credential delivery are **PENDING OBJECTIVE
CONFIRMATION**. This checklist defines exactly what must be delivered, where, and how presence
is verified. **No secret value appears here or is committed to the repo — names + delivery
location only.**

## 1. Intake matrix
| Ref | Secret / access | Delivered to (location) | Consumed by | Presence check (no value) | Status |
|---|---|---|---|---|---|
| K1 | `KUBE_CONFIG` (staging cluster) | GitHub Actions **repo/environment secret** | `deploy.yml` staging job | Actions run reaches `kubectl` auth step | ☐ PENDING |
| D1 | `DATABASE_URL` (managed Postgres) | cluster **secrets store** → app env | app runtime + migrations | pod boots; `alembic current` succeeds | ☐ PENDING |
| D2 | Restore-target DB URL | secrets store (DR job / operator) | backup/restore drill | isolated instance reachable | ☐ PENDING |
| W1 | `WEBHOOK_SECRET_<SYS>` | secrets store → app env | webhook verification | `/webhook` returns 401 (bad sig), not 503 | ☐ PENDING |
| W2 | `WEBHOOK_TENANT_<SYS>` | secrets store → app env | webhook tenant binding | signed webhook accepted | ☐ PENDING |
| W3 | `STRIPE_WEBHOOK_SECRET` | secrets store → app env | billing webhook (if exercised) | presence-only | ☐ PENDING |
| S1 | App signing/JWT keys | secrets store → app env | auth | auth path functional | ☐ PENDING |
| O1 | Alert channel token | alert-manager config / secrets store | alert delivery | test alert delivered | ☐ PENDING |
| R1 | Container registry creds | GitHub Actions secret + cluster pull secret | image publish + pull | image push/pull succeeds | ☐ PENDING |

> `KUBE_CONFIG_PROD` is intentionally **NOT** part of DIR-032 (pilot-grade, non-production). Do
> not deliver production cluster access for this phase.

## 2. Delivery rules (non-negotiable)
- Values set **only** in GitHub Actions secrets and/or the cluster secrets store — **never** in
  the repo, `.env`, manifests, code, logs, PR text, or commit messages.
- Repo continues to track only `*.env.example` placeholders (verified clean, DIR-030).
- CI/operator logs assert **presence/behavior**, never echo secret values.
- Each credential least-privilege and independently revocable (see DIR-031A
  `CREDENTIAL_AND_ACCESS_REQUIREMENTS.md`).

## 3. Intake completion gate
DIR-032 does not begin until **every row above is ☐→☑ confirmed** by the credential owner AND
the pre-flight checks in `DIR_032_EXECUTION_RUNBOOK.md` §0 pass. Marking a row complete requires
an objective presence/behavior check, not an assertion.

## 4. Honesty note
As of this document, **no credential has been received by any executing context** and no row is
confirmed. This checklist is the intake instrument; it is not evidence that access exists.
