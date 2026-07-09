# Project Atlas — Enterprise Knowledge Sharing

LumenAI v3.1 — Section 6

## Endpoints

```
POST /api/atlas/knowledge/share
GET  /api/atlas/knowledge/{system_id}
GET  /api/atlas/knowledge/{system_id}/{article_id}
POST /api/atlas/knowledge/{system_id}/{article_id}/retract
```

## Architecture

```
backend/app/services/atlas_knowledge_sharing_service.py
frontend/src/components/AtlasDashboard.tsx  — "Knowledge Sharing" tab
```

## A publish-a-copy pattern

The source `KnowledgeArticle` (tenant-scoped, `app/models/knowledge.py`) is
never mutated or exposed cross-tenant directly. Sharing an article creates
a `SharedKnowledgeArticle` row — a snapshot copy carrying its own
`system_id`, `source_tenant_id`, and `source_article_id` back-reference —
so a later edit at the source facility never silently changes what's
already been shared enterprise-wide, and retracting a shared copy never
touches the source.

## Approval gate

Only articles with `approval_status == APPROVED` (from
`app/models/knowledge.py`) can be shared. Sharing a `draft`,
`pending_review`, `rejected`, or `archived` article raises
`ArticleNotApprovedError` (surfaced as HTTP 422) — an article an
individual facility hasn't finished its own governance review on can never
leak to the rest of the enterprise.

## Sharing scope

Every shared article declares a `sharing_scope`: `facility`, `market`, or
`system_wide` (`SHARE_SCOPES` in `app/models/atlas_enterprise.py`). This is
new governance metadata `KnowledgeArticle` doesn't carry today — an
enterprise share needs to know *how far* it should propagate, which a
purely local article never needed.

## Why no k-anonymity here

Unlike the k-anonymity/differential-privacy machinery
`global_intelligence.py`/`instrument_registry.py` apply to aggregated
clinical *metrics* — where re-identifying a facility could expose
competitively sensitive performance data — shared knowledge content (best
practices, anatomy guidance, educational material) is authored text, not a
facility's clinical performance. No suppression applies. What does still
apply, per this platform's audit rule, is that every share and every
retraction is its own audited event
(`atlas.knowledge_article_shared` / `atlas.knowledge_article_retracted`).

## Governance fields carried on the shared copy

`owner`, `approver`, `version` (copied from the source at share time),
and `effective_date` — fields the sprint asks for that the source
`KnowledgeArticle` doesn't fully carry today (no `effective_date`, no
`sharing_scope`), which is exactly why `SharedKnowledgeArticle` is its own
table rather than a view over `KnowledgeArticle`.
