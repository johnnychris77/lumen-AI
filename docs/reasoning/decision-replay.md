# Decision Replay (Project Cortex, Section 9)

`app/services/decision_replay_service.py`, `GET /api/inspections/{id}/decision-replay`.

## Replay by reconstruction, not a frozen snapshot

`build_explainable_decision()` is a pure function of already-persisted data
(`Inspection`, `InspectionFinding`, `SupervisorReview`, Clinical Memory) —
the same "replay = re-derive from real rows" approach
`knowledge_graph_service.explain_inspection()` already uses for its own
explainability graph. Replaying an inspection's decision therefore
re-derives it live rather than reading back a separately persisted JSON
snapshot, which keeps replay always in sync with the current rule library:
if a rule was fixed or a new supervisor rule was added since the original
inspection, replay shows that — clearly labeled via the response's `note`
field — rather than silently disagreeing with what the rules say today.

## Response shape

```
input                — instrument_type, finding_type, zone, risk_score,
                        risk_level, created_at, as persisted at the time
reasoning_path        — same as the live decision endpoint
applied_rules         — same as the live decision endpoint
evidence              — same as the live decision endpoint
decision:
  clinical_rationale
  final_recommendation
  confidence           — vision / reasoning / overall clinical
  persisted_recommended_action  — what was actually shown/acted on then
  persisted_disposition
supervisor_outcome    — every SupervisorReview row for this inspection:
                        reviewer, agreement, override_action,
                        final_disposition, rationale
```

## Use cases

- **Audit**: confirm a past recommendation was reproducible from the
  evidence available at the time, and see exactly what a supervisor did
  with it.
- **Education**: walk a technician through why a past inspection was
  flagged, using the same reasoning path/rules a live inspection would show.
