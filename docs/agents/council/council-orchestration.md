# Project Council — Council Orchestration Engine

LumenAI AI Leadership Platform, Mission & Section 1.

## Naming disambiguation

**"Council" already exists** in one unrelated context: Olympus's Network
Governance Council (`olympus_governance_council_service.py`,
`NetworkGovernanceCase` in `app/models/olympus_network.py`) -- a
cross-hospital, network-level governance body for intelligence-sharing
disputes between member sites. Project Council is a different,
single-tenant concept: structured AI leadership *teams* composed of
already-built LumenAI specialists, convened to review one operational or
clinical issue and produce a transparent, dissent-preserving
recommendation for human leadership. `council_` is used as a distinct
prefix throughout; nothing here touches `NetworkGovernanceCase` or any
Olympus table. `/council` and `/api/council` were unclaimed before this
sprint.

## Mission

Council synthesizes evidence from specialist agents, identifies agreement
and disagreement, evaluates tradeoffs, and gives human leaders a
transparent recommendation. Council does not replace leadership. It
answers: which specialists reviewed this issue, where do they agree,
where do they disagree, what evidence supports each position, what are
the tradeoffs, what action is recommended, and who must approve it. **No
recommendation may hide specialist disagreement.**

## Architecture

```
Inspection/Enterprise Data -> Specialist Agents -> Council Leadership Teams
  -> Consensus and Dissent Analysis -> Human Leadership Review
  -> Approved Action -> Outcome Measurement -> Institutional Learning
```

## What Council composes rather than duplicates

Council is a pure read-and-synthesize layer -- each specialist's
Council assessment is derived from that specialist's own, already-built
real service (`council_specialist_assessment_service.py`):

| Specialist | Reused from |
|---|---|
| Veritas | `veritas_evidence_agent_service.run_evidence_assessment` |
| Aegis | `vulcan_aegis_integration_service.compute_process_variation_signal` |
| Vulcan | `vulcan_reliability_agent_service.run_reliability_assessment` |
| Sage | `sage_knowledge_gap_service.list_gaps` |
| Sentinel-X | `sentinelx_risk_agent_service.run_risk_assessment` |
| Apollo | `apollo_capa_engine_service.capa_engine_summary` |
| Athena | `athena_search_service.organizational_search` |
| Pulse | `pulse_command_center_service.pulse_command_center` |
| Phoenix | `phoenix_maturity_index_service.compute_platform_maturity_index` |
| Maestro | `maestro_priority_engine_service.latest_priorities` |
| Research Agent | `horizon_research_portal_service.research_portal_summary` (read-only network reference) |

Reports reuse Veritas's generic `veritas_reports_service.
build_report_pdf_bytes`/`build_report_csv_bytes`/`build_report_xlsx_bytes`.
Decision Journal integration reuses Maestro's own
`maestro_decision_journal_service.record_decision` directly (see
`decision-journal-integration` in `docs/agents/council/consensus-engine.md`
-- Council never builds a second, parallel journal schema).

## The Orchestration Engine (`council_orchestration_service.py`)

1. **`select_specialists_for_case`** -- picks the appropriate leadership
   team (from `CASE_TYPE_DEFAULT_TEAM`) and its required specialists for
   a case type.
2. **`open_case`** -- creates the typed `CouncilCase` and assigns its
   team. No specialist has assessed anything yet.
3. **`convene`** -- runs every required specialist's independent
   assessment (`council_specialist_assessment_service.
   run_independent_assessments`), classifies consensus
   (`council_consensus_service`), records dissent
   (`council_dissent_service`), generates decision options
   (`council_decision_options_service`), and routes the case to the
   correct human authority tier.

Agents assess independently before seeing each other's conclusions --
this is structural, not a runtime lock: every resolver in
`council_specialist_assessment_service.py` reads only the case's own
evidence package and that one specialist's real store, never another
specialist's `CouncilSpecialistAssessment` row.
