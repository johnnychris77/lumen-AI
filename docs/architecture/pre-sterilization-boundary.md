# Pre-Sterilization Boundary

## The workflow LumenAI operates within

```
Point of Use
    ↓
Transportation
    ↓
Decontamination
    ↓
Assembly / Inspection
    ↓
LumenAI Clinical Inspection   ← LumenAI operates here
    ↓
Supervisor Review
    ↓
Packaging
    ↓
Sterilization
```

**LumenAI operates before sterilization.** It sits at the
Assembly/Inspection step, between decontamination and packaging. It never
observes, measures, or reports on what happens inside the sterilizer, and
it makes no claim about the outcome of a sterilization cycle.

## Why this boundary matters

Sterile Processing has well-established, separately regulated systems for
verifying sterilization itself: biological indicators, chemical
indicators, and sterilizer load/cycle monitoring. LumenAI is not one of
those systems and must never be described as if it were — doing so would
misrepresent both what LumenAI does and what those systems are responsible
for. Conflating the two would:

- overstate LumenAI's regulatory posture (implying sterilization-assurance
  claims it hasn't made or been cleared for),
- confuse hospital risk/quality teams about which system is responsible
  for which compliance record, and
- understate the actual value LumenAI provides — catching problems
  *before* an instrument reaches the sterilizer, when they're still cheap
  and safe to fix.

## Terminology

### Do not use

These phrases incorrectly imply LumenAI validates or monitors the
sterilization process itself:

- "sterilization cycle count" (as a LumenAI capability claim)
- "sterilization assurance" (as something LumenAI provides)
- "biological indicator monitoring"
- "sterilizer performance validation"
- "sterilization readiness" / "sterilization validation" / "sterilization
  cycle intelligence" as platform-level claims

### Use instead

| Instead of | Use |
|---|---|
| sterilization readiness | pre-sterilization readiness |
| sterilization assurance | inspection assurance / pre-sterilization cleaning assurance |
| sterilization validation | clinical inspection readiness |
| sterilization cycle intelligence | pre-sterilization quality gate |
| (general) | inspection history, cleaning assessment, contamination trend, damage trend, repair history, baseline match, inspection coverage, clinical readiness, pre-sterilization decision |

### Correctly bounding scope is fine

Documentation that explicitly states LumenAI does **not** replace
sterilization validation/assurance protocols is the correct pattern, not a
violation — e.g. "The SRI does not replace clinical sterilization
validation protocols" (`docs/infrastructure/surgical-readiness-index.md`)
and "Sterilization assurance is a separate function"
(`docs/clinical/clinical-performance-report.md`). These disclaimers should
stay; only language that implies LumenAI *performs* that function needs to
change.

## Phase 19.5 terminology audit result

A repository-wide search for the banned phrases found one violation in
generated clinical-mentor text
(`app/services/clinical_mentor.py`): the `other_organic_residue` finding's
`clinical_significance` read *"Any retained organic soil reduces
sterilization assurance"* — corrected to *"Any retained organic soil
compromises pre-sterilization cleaning assurance."* No other code or
frontend strings used the banned phrases; the remaining matches
(`docs/infrastructure/surgical-readiness-index.md`,
`docs/regulatory/submission-strategy.md`,
`docs/clinical/clinical-performance-report.md`) were already correctly
worded as boundary disclaimers and required no change.
