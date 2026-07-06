# AI Knowledge Assistant & Knowledge Analytics

## AI Knowledge Assistant (Deliverable 8)

`POST /api/knowledge/assistant`

Answers contextual technician questions ("Why is this finding important?",
"Where does blood commonly hide on this instrument?", "Why is this anatomy
considered high risk?") using the same deterministic, source-grounded
pattern already used by `knowledge_graph_service.reasoning_chain()` —
never a call to an external LLM. The question is parsed for the same
finding/zone/instrument-family vocabulary as Smart Knowledge Search, and
the answer is composed from:

1. **Finding education** (`clinical_mentor.FINDING_EDUCATION`) — clinical
   significance for any matched finding.
2. **Approved institutional knowledge** — up to 3 approved
   `KnowledgeArticle` entries tagged to the matched finding. Unapproved
   (draft/pending_review) articles are never surfaced here — the
   assistant only cites guidance the organization has actually signed off
   on.
3. **Instrument anatomy profile** — for a matched or supplied instrument
   family, the zones classified `high`/`critical` risk, answering "why is
   this anatomy considered high risk" with the same data
   `instrument_anatomy.py` already maintains.

Every response includes `sources` — exactly which of the above contributed
— so nothing is presented as authoritative without a traceable origin. If
nothing matches, the assistant says so explicitly rather than fabricating
an answer, and suggests the gap be filled via the Knowledge Repository.

Every question (both from Search and the Assistant) is logged to
`KnowledgeQueryLog` for analytics.

## Knowledge Analytics (Deliverable 10)

`GET /api/knowledge/analytics` (admin/spd_manager only)

All six rollups are computed from real, already-recorded data:

| Metric | Source |
|---|---|
| Most viewed articles | `KnowledgeArticle.view_count`, incremented on every `GET /api/knowledge/articles/{id}` |
| Most common questions | `KnowledgeQueryLog`, grouped by exact query text |
| Most frequent teaching points | `KnowledgeArticle` where `category=teaching_point`, grouped by tagged finding |
| Common supervisor comments | `DispositionOverride.reason` (v1.6), grouped by exact text |
| Knowledge gaps | Finding types with a real `ClinicalCase` but no approved article tagged to that finding |
| Training opportunities | Technicians with a `repeated_error` competency event (v1.4) for a finding type with no approved article |

Knowledge gaps and training opportunities are the two forward-looking
metrics — both point at real, unaddressed needs rather than a general
"engagement" score.
