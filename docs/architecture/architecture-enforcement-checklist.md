# Architecture Enforcement Checklist

Every future feature — a new finding type, a new dashboard, a new model, a
new report, a new API endpoint — must be able to answer **yes** to each of
these before it ships. This is the operational gate behind the design
principles in `docs/architecture/design-principles.md` and the layered
architecture in
`docs/architecture/lumenai-clinical-intelligence-architecture.md`.

## The checklist

1. **Does it identify the instrument?**
   The feature knows which instrument family (and manufacturer/model,
   where available) it's operating on — it does not reason about a bare
   image. *(Architecture Layer 3, Ontology: Instrument → Instrument
   Family)*

2. **Does it use anatomy or zone context?**
   Any finding, score, or recommendation is attributed to a resolved
   anatomy zone, not a generic "somewhere on the instrument." *(Layer 4,
   Ontology: Anatomy → Inspection Zone)*

3. **Does it map findings to SPD risk?**
   The feature knows whether the zone/finding combination is high-risk /
   high-retention, and that classification is visible in the output, not
   buried. *(Layer 6, Ontology: SPD Risk)*

4. **Does it generate clinical reasoning?**
   The output explains *why* something matters (zone risk, baseline
   deviation, severity) rather than presenting a bare score or label.
   *(Layer 6, Design Principle 3)*

5. **Does it support human validation?**
   A supervisor can see the feature's output, agree, disagree, correct it,
   and have that correction persisted as labeled data. *(Layer 8, Design
   Principle 4)*

6. **Does it preserve auditability?**
   Every consequential action (a submission, an override, a data export,
   an intelligence-sharing event) creates an audit event
   (`app/audit.py::log_audit_event`) with `compliance_flag` set where
   appropriate. *(Ontology: Audit Event)*

7. **Does it avoid making post-sterilization claims?**
   No output implies LumenAI monitors, measures, or validates the
   sterilization cycle itself — see
   `docs/architecture/pre-sterilization-boundary.md` for the banned
   phrases and preferred terminology.

8. **Does it contribute to continuous learning?**
   Where the feature produces or touches a supervisor decision, that
   decision becomes a Training Label (or is deliberately excluded, with a
   documented reason) rather than being discarded. *(Layer 9, Ontology:
   Learning Signal)*

## How to apply it

- **Code review:** reviewers should be able to point to where in the diff
  each "yes" is satisfied. A feature that can't answer one of these isn't
  necessarily wrong, but it needs a written exception in its PR
  description explaining why — not silence.
- **New AI capability:** before adding a new model or finding type, walk
  it through the full ontology chain
  (`docs/architecture/lumenai-clinical-ontology.md`) and confirm each link
  is populated, not just the new one being added.
- **New dashboard/report:** confirm every metric it surfaces is traceable
  to real rows in the domain model
  (`docs/architecture/domain-model.md`) — no fabricated or simulated
  numbers presented as real, consistent with existing platform practice
  (Phase 12/15/17/18 all compute from live data and return `null` rather
  than a fabricated zero when data doesn't exist yet).
- **Terminology:** any new user-facing or generated string should be
  checked against the pre-sterilization boundary's do/don't list before
  merge.
