# Project Phoenix — Innovation Pipeline

LumenAI OS v4.9, Section 8.

No Idea/Evidence/ROI/Clinical-Impact/Roadmap backlog concept existed
anywhere in this codebase before Phoenix (confirmed by grep — the word
"backlog" was already used elsewhere only for unrelated operational queue
counts, e.g. `supervisor_backlog`/`repair_backlog`). `InnovationIdea` is a
genuinely new table.

## Fields

Every idea tracks exactly what the brief names:

* **Ideas** — `title`/`description`.
* **Evidence** — free-text supporting evidence.
* **Estimated ROI** — `estimated_roi_usd`, nullable (never a fabricated dollar figure when no estimate exists).
* **Clinical Impact** — `low | medium | high | critical`.
* **Technical Complexity** — `low | medium | high`.
* **Priority** — `low | medium | high | critical`.
* **Approval Status** — `draft | approved | rejected | in_progress | completed`.
* **Roadmap Assignment** — free text (e.g. "Q3 2026", "backlog").

An idea never auto-advances between approval statuses — every transition
in `update_idea_status` is an explicit call, intended to be driven by a
human decision in the UI.

```
POST  /api/phoenix/innovation/ideas
GET   /api/phoenix/innovation/ideas?approval_status=draft
GET   /api/phoenix/innovation/ideas/{id}
PATCH /api/phoenix/innovation/ideas/{id}/status
GET   /api/phoenix/innovation/summary
```

`innovation/summary` rolls up counts by status/priority and total
(human-entered) estimated ROI across the backlog — the same "never
fabricate a total from partial data" convention used throughout this
codebase: ideas with no ROI estimate simply don't contribute to the sum.
