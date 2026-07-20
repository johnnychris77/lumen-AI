# DIR-032 EXECUTING CONTEXT REQUIREMENTS — (prep, post-EXEC-001)

**Purpose:** state precisely **where DIR-032 must run**, because operational evidence can only
be produced by a context that can *reach the provisioned environment*. This repository sandbox
**cannot** — objectively re-confirmed below — so DIR-032 must execute elsewhere.

## 1. This sandbox cannot execute DIR-032 (re-confirmed, timestamped)
Probe at **2026-07-20T18:52:53Z**, commit `a738bf9`:
| Check | Result |
|---|---|
| docker daemon | **UNREACHABLE** |
| kubectl | **ABSENT** |
| cloud CLI (aws/gcloud/az) | **ABSENT** |
| managed Postgres on :5432 | **no response** |

**Conclusion:** DIR-032 evidence will **not** be produced from this Claude Code sandbox. Any
attempt to do so from here would be fabrication. DIR-032 runs in the contexts below.

## 2. Approved executing contexts (by Work Package)
| WP | Executing context | Why it can reach the env | Evidence lands in |
|---|---|---|---|
| WP-2 Deploy | **GitHub Actions runner** via `deploy.yml` (`workflow_dispatch`) | runner authenticates with `KUBE_CONFIG` secret → reaches cluster | Actions run logs + URL |
| WP-3 Rollback | **GitHub Actions runner** (`deploy.yml` `rollout undo` path) | same | Actions run logs |
| WP-4 Backup/DR | **Operator context** (bastion / CI job) with `DATABASE_URL` + restore target | direct managed-DB access | operator transcript + timestamps |
| WP-5 Observability/Alerting | **Cluster + alerting backend**; operator induces controlled failure | in-cluster + alert channel | dashboard screenshots + alert receipts |
| WP-6 Secrets/TLS | **Cluster/ingress** + operator | in-cluster secret store + served cert | `openssl s_client` output + rotation transcript |
| WP-7 Incident drill | **Cluster** + operator | in-cluster perturbation | timeline log |

## 3. Recommended primary path: GitHub Actions for deploy/rollback
`deploy.yml` already exists, is fail-closed, and runs on GitHub's runners — which **can** reach
a real cluster once `KUBE_CONFIG` is set as a repo/environment secret. This is the cleanest,
auditable path for WP-2/WP-3 evidence (the run URL + logs are the evidence, tied to a commit
SHA). WP-4..WP-7 need an operator/bastion context with DB + cluster + alerting access.

## 4. Who runs what
- **Release Engineering / DevSecOps:** set CI secrets; trigger `deploy.yml`; capture run URLs.
- **Infrastructure operator:** run backup/DR, observability, secrets/TLS, incident drills from
  a context with cluster + managed-DB + alerting access; capture transcripts.
- **This program (Claude Code):** prepares the runbook + intake + acceptance criteria, and —
  once evidence artifacts (run URLs, transcripts, receipts) are provided back — will **index +
  verify** them under `pilot-operational-capability/evidence/` and drive DIR-033. It will not,
  and cannot, manufacture the evidence itself.

## 5. Honesty statement
DIR-032 has **not** executed. No environment is confirmed reachable from any context yet. This
document defines the required executing contexts so that, when EXEC-001 provisioning completes,
the evidence is produced where it legitimately can be — and never fabricated here.
