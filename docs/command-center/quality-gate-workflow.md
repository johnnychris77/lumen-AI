# Quality Gate Workflow

How an instrument actually moves through the pre-sterilization command
center, end to end — the operational story behind the ten modules.

## The gate, in sequence

```
1. Technician captures inspection image + tags inspected zones
        ↓
2. AI scoring engine runs (baseline comparison, zone-aware findings)
        ↓
3. Command center classifies readiness (classify_readiness)
        ↓
4a. READY_FOR_PACKAGING           → proceeds toward packaging
4b. REQUIRES_RECLEANING           → Supervisor Review Queue / Reclean and re-inspect
4c. REQUIRES_SUPERVISOR_REVIEW    → Supervisor Review Queue
4d. REQUIRES_REPAIR               → Repair / Remove From Service Queue (repair path)
4e. REMOVED_FROM_SERVICE          → Repair / Remove From Service Queue (retired)
4f. PENDING_ANALYSIS              → held until scoring completes
        ↓
5. Supervisor confirms or overrides (creates ground truth — Phase 18)
        ↓
6. Confirmed inspections exit the queues; instrument/tray/facility
   readiness scores update
```

## Step-by-step

### 1. Capture
A technician runs an inspection (`POST /api/inspections`), optionally
tagging `inspected_zones` — the checklist of anatomy zones they actually
photographed/examined. This is what Module 7 (Missing Anatomy Zone
Coverage) checks against the instrument family's required zones later.

### 2. Scoring
If an image was captured, `analyze_inspection`
(`app/services/baseline_comparison_scoring_service.py`) compares it
against the instrument's approved baseline (if one exists) and produces a
`recommended_action` sentence, a `risk_score`, and a `detected_issue`.
If no approved baseline exists, the inspection is held at
`REQUIRES_SUPERVISOR_REVIEW` regardless of what the image shows — no
score is fabricated without a baseline to compare against.

### 3. Readiness classification
The command center's `classify_readiness` (see
`docs/command-center/readiness-score-model.md`) turns that scoring output
into one of the six readiness states, and flags whether the finding is
critical (blood, tissue, bone, crack, insulation damage).

### 4. Routing
- **Ready** instruments simply roll up into the readiness rate — no queue
  action needed.
- **Requires recleaning / supervisor review** instruments appear in
  Module 5 (if critical) and/or Module 6 until a human confirms them.
- **Requires repair / removed from service** instruments appear in Module
  9, split so a repair coordinator and a disposal/replacement coordinator
  aren't working from the same undifferentiated list.

### 5. Human confirmation
A supervisor reviews the case — through the existing supervisor-review
form (`POST /inspections/{id}/supervisor-review`,
`app/routes/ai_clinical_review.py`) or the separate QA review flow
(`POST /api/qa-review/{id}`). Either one marks the inspection "confirmed"
for command-center purposes. Per Phase 18, the supervisor-review
submission *also* creates a `PilotValidationCase` ground-truth record in
the same transaction — the quality gate and the model's training-label
pipeline share the same human decision, not two separate ones.

### 6. Queues clear, scores update
Once confirmed, an inspection drops out of Modules 5 and 6 even if its
readiness state is still blocking (e.g. still `REQUIRES_RECLEANING`) — the
queues track *unresolved, unconfirmed* work, not the disposition itself.
Instrument (Module 3), tray (Module 2), and facility (Module 4) readiness
always reflect the *latest* inspection per instrument, so a re-inspection
after reprocessing immediately updates the instrument's and its tray's
readiness.

## Why the tray is weakest-link

A tray cannot go to packaging with one contaminated or unrepaired
instrument in it, no matter how clean the other nine are. Module 2
enforces this by reporting the tray's state as the single most-blocking
state among its instruments — there is no "average" or "mostly ready"
tray state, because that isn't how a physical instrument tray actually
works in SPD.

## Why "confirmed" matters more than "resolved"

The gate distinguishes *readiness state* (what the AI/rules concluded)
from *confirmation* (whether a human has actually looked at it). An
instrument can be `REQUIRES_RECLEANING` and confirmed (a supervisor
already sent it back for reprocessing — action is underway, no longer a
queue item) or unconfirmed (nobody has acted on it yet — it's the exact
item that should be at the top of someone's queue right now). Reporting
readiness state alone, without confirmation, would either flood every
dashboard with already-actioned items or hide the fact that action was
taken — both wrong for an operational quality gate.

## Escalation path for critical findings

A critical finding (blood, tissue, bone, crack, insulation damage) that is
also unconfirmed appears in the High-Risk Findings Queue (Module 5)
regardless of how it's routed elsewhere — this is deliberately redundant
with Modules 6 and 9 so Infection Prevention and Executive Leadership
personas, who may not watch the day-to-day supervisor queue, still see
every open critical item in one place.
