# Clinical Safety Framework

## Human-in-the-Loop

Every AI recommendation is advisory. Structural enforcement, not just
policy:

- The model deployment gate blocks any model from driving or advising a
  decision until it reaches `validated` status via human-approved
  promotion (`app/services/ml/deployment_gates.py`)
- The Supervisor Agent (Phase 22) is read-only by design — it reports
  whether a human has reviewed a case, it never fabricates a review
  (`docs/agents/multi-agent-architecture.md`)
- Every readiness state carries `human_review_required: true` through to
  the final API response

## Override Requirements

- A supervisor can agree, partially agree, disagree, or override any AI
  recommendation via `POST /inspections/{id}/supervisor-review`
- A rationale is **required** for partial agreement, disagreement, or any
  override (`app/routes/ai_clinical_review.py`) — not optional metadata
- Every override is captured as a `ClinicalDecisionLedgerEntry` of type
  `supervisor_override`, permanently

## Known Limitations

Stated plainly, not buried:

- No pixel-level CV localization yet (zone assignment is deterministic,
  instrument-type-derived — `docs/knowledge-graph/reasoning-engine.md`)
- Contamination/Damage agents currently read one persisted finding per
  inspection, not multiple simultaneous findings
  (`docs/agents/multi-agent-architecture.md`)
- Three instrument family profiles (cannulated, orthopedic, micro
  instruments) borrow the closest existing anatomy family pending a
  dedicated taxonomy split (`docs/knowledge-graph/instrument-intelligence.md`)
- No live multi-site clinical validation completed yet
  (`docs/evidence/validation-reports.md`)
- Full list: `VERSION_1_0.md` §Known Limitations

## Appropriate Use

- Pre-sterilization clinical inspection support for SPD professionals
- Decision support that must be reviewed by a qualified supervisor before
  any instrument disposition is finalized
- Quality-indicator trend analysis for SPD department management

## Inappropriate Use

- Autonomous instrument disposition without human review
- Sterilization cycle monitoring, biological indicator interpretation, or
  sterilizer performance validation (`docs/architecture/pre-sterilization-boundary.md`)
- Any use implying FDA clearance or regulatory approval (none claimed —
  CLAUDE.md constraint)
- Diagnosis or treatment of a patient — LumenAI inspects instruments, not
  patients

## Clinical Workflow Boundary

```
Point of Use → Transportation → Decontamination → Assembly/Inspection
    → LumenAI Clinical Inspection → Supervisor Review → Packaging
    → Sterilization → Sterile Storage → Operating Room
```

LumenAI's responsibility ends at Supervisor Review, before Packaging.
Full detail: `docs/architecture/pre-sterilization-boundary.md`.

## Decision Traceability

Every decision is recorded in the Clinical Decision Ledger
(`docs/cios/clinical-decision-ledger.md`) with who made it, why, what
evidence supported it, and which governance versions were active — an
immutable, append-only record.

## Explainability

Every recommendation traces through the full reasoning chain — Instrument
→ Manufacturer → Family → Anatomy → Zone → Retention Risk → Cleaning
Method → Clinical Meaning → Recommendation
(`docs/knowledge-graph/reasoning-engine.md`) — never a bare probability
with no explanation.

## Patient Safety Principles

1. Prevent harm before sterilization — catch problems while they're still
   correctable, not after.
2. Never claim causation — findings are potential associations requiring
   quality review, always.
3. Critical findings (blood, tissue, organic residue, crack, missing
   component) carry the highest safety weight and the tightest false-
   negative thresholds (`docs/validation/pilot-go-no-go-criteria.md`).
4. Human expertise is the final authority, always
   (`docs/architecture/design-principles.md`, Principle 4).
