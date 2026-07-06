# Knowledge Governance & Organization Standards

## Knowledge Governance (Deliverable 9)

`POST /api/knowledge/articles/{id}/{submit-for-review,approve,reject,archive}`,
`GET /api/knowledge/governance-summary` (admin/spd_manager only for
approve/reject/archive/summary)

Every `KnowledgeArticle` tracks:

| Field | Meaning |
|---|---|
| `author` | who wrote it (the actor at creation time) |
| `reviewer` | who approved/rejected/archived it |
| `approval_status` | `draft` → `pending_review` → `approved` / `rejected` / `archived` |
| `version` | incremented on every substantive edit |
| `last_reviewed_at` | set on approve/reject/archive |
| `applicable_instruments` / `applicable_findings` | the search facets governance and search both use |

Archiving never deletes an article — it drops out of default
list/search results (`include_archived=False` unless explicitly
requested) but remains available for audit. This is the mechanism for
retiring outdated knowledge without losing the record of what the
organization used to believe and why it changed.

## Organization Standards (Deliverable 6)

`GET/POST /api/knowledge/standards`, `POST /api/knowledge/standards/{id}/deactivate`
(admin/spd_manager only for create/deactivate)

Per-tenant local policy in five categories: `inspection_standard`,
`photography_standard`, `coverage_requirement`,
`supervisor_approval_threshold`, `competency_requirement`. These
**supplement, never replace**, manufacturer IFUs — nothing in this module
overrides the AI's readiness/disposition/risk engines; a standard is
documentation and policy, not a code path the scoring engine reads.
Deactivated standards are excluded from the default list (`active_only=True`)
but not deleted, mirroring the same archive-not-delete governance
principle as knowledge articles.
