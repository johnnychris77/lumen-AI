# Project Athena — Knowledge Trust Score

LumenAI OS v4.8, Section 8.

No trust/reputation/evidence-quality construct existed anywhere in this
codebase before Athena — `beacon_standards_service.py` and
`p24_standards_service.py` only carry `version`/`status` fields. Every
component below is computed **live** from real `KnowledgeArticle` fields
(never persisted as a fabricated number), and Contributor Reputation
reuses Apollo's existing `competency_service.record_knowledge_
contribution`/`CompetencyEvent` log rather than re-deriving a contribution
count.

## The seven components (equal-weighted average → overall score)

| Component | Real basis |
|---|---|
| Evidence Quality | Body length + linked-standards count (`linked_standards_json`, new column) + whether `references` is populated |
| Clinical Validation | `approval_status == approved` and whether a `reviewer` is on record |
| Usage | `view_count` |
| Review Date Recency | Days since `last_reviewed_at`, decaying over a 1-year window |
| Approval Status | Fixed score per `approval_status` value |
| Contributor Reputation | The author's `knowledge_contribution` event count (Apollo's `CompetencyEvent` log) |
| Reference Strength | Count of linked standard codes |

```
GET /api/athena/trust/articles?min_trust=70
GET /api/athena/trust/articles/{article_id}
```

"Organizations can filter by trust level" (the brief's own words) is
implemented via the `min_trust` query parameter — never a black-box
relevance score, every component is visible in the response.
