# Interactive Workflow Demo — Status/Ranking Contract Mapping

**Scope:** the public `/workflow` interactive demo (`frontend/src/marketing/components/WorkflowDemo.tsx`,
`frontend/src/marketing/lib/workflowDemo.ts`). All values are **SYNTHETIC**; the demo
never calls the production API.

## Why presentation labels exist
The production backend does **not** expose a user-facing field called "ranking." Its
canonical decision output is a **disposition** plus `human_review_required`:

- `backend/app/services/disposition_engine.py` — seven standardized dispositions:
  `Proceed to packaging`, `Reclean`, `Repeat inspection`, `Repair evaluation`,
  `Manufacturer evaluation`, `Remove from service`, **`Supervisor Review Required`**.
- `backend/app/services/lumen_decision_engine.py` — statuses like
  `supervisor_review_required`, `unknown_review_required`, with an `escalation_condition`
  and `human_decision_required` (default `True`).

To avoid inventing user-facing ranking names, the demo maps its three synthetic states
through documented presentation labels:

| Demo enum (`workflowDemo.ts`) | Presentation label (UI) | Aligned backend concept |
|---|---|---|
| `provisional-pass` | "Provisional — no automated escalation" | disposition ~ *Proceed to packaging*, `human_review_required: true` |
| `provisional-attention` | "Provisional — flagged for reviewer attention" | reviewer-attention escalation |
| `hold-for-review` | "Held for Supervisor Review" | canonical **`Supervisor Review Required`** |

## Distinct states surfaced by the demo
- **Provisional result** vs **final result** — the demo result is always labeled
  *Provisional (not final)*; a qualified person owns the final decision.
- **Approved baseline** (consistent) / **deviation** / **no approved baseline**.
- **Human review required** vs **No automated review escalation triggered** — the latter
  replaced the earlier "No mandatory review triggered," which could be read as implying
  human review is unnecessary.

## Safety invariants preserved
- Persistent disclaimer "Demonstration Data — Not for Clinical Use" on every step.
- "A qualified person owns the final decision" shown on review + completion.
- "This synthetic result does not authorize instrument use" on completion.
- No production endpoints, no real inference, no PHI.
