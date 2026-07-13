# ADR-0008: Aegis's Specialist Status (Proposed — needs a decision)

## Status
**Proposed.** This ADR documents a gap surfaced during the Phase 1 architecture review; it is not yet a ratified decision. Raised as Technical Debt Register TD-08.

## Context
"Aegis" (process-variation signal detection from technician/vendor concentration patterns) is referenced as a first-class specialist name throughout Council's, Steward's, Maestro's, and Sentinel-X's vocabularies (`SOURCE_AEGIS_PROCESS_RECOMMENDATION`, `SPECIALIST_AEGIS`, etc.). In reality, it has no model file, no independent table, and no independent service directory — its one implementation is `vulcan_aegis_integration_service.compute_process_variation_signal`, and its one persisted artifact is a JSON column on Vulcan's own `VulcanReliabilityAssessment` table. Vulcan's own docstring is explicit that this was a deliberate choice: no Aegis agent existed before this file, and rather than fabricate a fuller one, Vulcan built a real, minimal signal from actual data.

## Decision needed
Two options, requiring a real architecture-review decision (per this document's own freeze policy) rather than default drift:
1. **Ratify Aegis as a permanent Vulcan sub-capability** — update the vocabulary in Council/Steward/Maestro/Sentinel-X to reflect this explicitly (e.g. rename `SPECIALIST_AEGIS` references to make the Vulcan relationship clear) rather than implying independent specialist status it doesn't have.
2. **Promote Aegis to a full specialist** — give it its own model file, naming-disambiguation docstring, and service group, migrating the `aegis_conclusion_json` column's data into a real `AegisProcessVariationSignal` table, if its scope is expected to grow beyond what a column on Vulcan's table can reasonably hold.

## Consequences (either direction)
- Doing nothing (the status quo) means new code will keep treating Aegis as specialist-equivalent in naming while its actual data model doesn't support that — the ambiguity compounds with every future specialist that references it.
- This is exactly the kind of decision the Phase 1 architecture freeze exists to force before further growth, rather than letting it resolve itself by accretion.
