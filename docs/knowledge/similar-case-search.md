# Smart Knowledge Search & Competency Knowledge Library

## Smart Knowledge Search (Deliverable 4)

`POST /api/knowledge/search`

A deterministic, keyword-matched search — the same "explainable, not a
black box" approach already used by the disposition/priority/risk engines,
rather than a call to an external LLM. The query is matched against real,
already-known vocabulary:

- **Findings** — every key in `clinical_mentor.FINDING_EDUCATION` (blood,
  bone, corrosion, crack, ...).
- **Anatomy zones** — every key in `instrument_zones.ZONE_INFO`.
- **Instrument families** — every family in `instrument_anatomy.py`,
  matched either by family name or by any of that family's own match
  keywords (so "Kerrison" resolves to the `kerrison_rongeur` family).

A recognized finding keyword filters both `KnowledgeArticle` (approved
only) and `ClinicalCase` to that finding; a recognized instrument family
additionally filters cases to that family. With no recognized finding
keyword, the search falls back to a free-text substring match over
approved article title/body. Every query is logged (`KnowledgeQueryLog`)
for the "most common questions" analytic.

Example: *"show all blood findings in Kerrisons"* → `matched_findings:
["blood"]`, `matched_instrument_families: ["kerrison_rongeur"]` → real
articles and cases tagged to blood, further narrowed to the Kerrison
family.

## Competency Knowledge Library (Deliverable 7)

`GET /api/knowledge/competency-topics[/{finding_type}]`

Organizes competency knowledge by instrument family / anatomy / finding /
risk / inspection technique / cleaning consideration / corrective action —
merging the existing static `education_library.py` reference (definition,
clinical importance, inspection tips, cleaning considerations, corrective
actions) with any **approved** institutional `KnowledgeArticle` entries
tagged to the same finding type. Supervisor-contributed guidance sits
alongside the baseline reference rather than living in a second,
disconnected list — a technician looking up "blood" sees both the
standard reference and anything the department has since added.
