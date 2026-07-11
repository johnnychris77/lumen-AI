# Project GuardianX — Explainability Dashboard & Audit Replay

LumenAI Network v5.2, Sections 3 & 4.

## Explainability Dashboard (Section 3) — genuinely new, reference-only

Nothing before GuardianX captured a structured explanation for an AI
output. `AIExplainabilityRecord` is referenced by `source_type`/
`source_id`, the same pointer-only pattern already used by
`HIXExchangePackage` (Olympus) — it never copies the underlying
recommendation. Every field Section 3 names is a real column: input
summary, evidence used, knowledge sources, Digital Twin context,
clinical rules applied, confidence, alternative explanations, and human
overrides (appendable after the fact via a dedicated endpoint).

Digital Twin Context reuses Phoenix's `compute_digital_twin_health_score`
(`phoenix_platform_health_service.py`, v4.9) directly — never a second
Digital Twin summarizer.

```
POST /api/guardianx/explainability
GET  /api/guardianx/explainability/{id}
POST /api/guardianx/explainability/{id}/human-override
GET  /api/guardianx/explainability?source_type=...&source_id=...
```

## Audit Replay (Section 4) — no new table, pure composition + verification

A replay composes what already exists:

* `WorkflowExecution`'s already-captured `decision_path_json`/
  `execution_log_json` (Forge, v4.1) for the exact nodes visited and the
  timeline (`started_at`/`completed_at`).
* The linked `WorkflowDefinition`/`WorkflowRule` rows at the exact
  version referenced ("Model version, Rules").
* GuardianX's own Evidence Ledger and Explainability Record entries for
  the same `source_type`/`source_id` ("Knowledge, Evidence").
* `audit_chain_verification_service.verify_audit_chain` for a real,
  hash-chained, tamper-evident timeline of every recorded action against
  the resource — never a fabricated "audit trail".

```
GET /api/guardianx/audit-replay/inspections/{id}
GET /api/guardianx/audit-replay/workflow-executions/{id}
GET /api/guardianx/audit-replay/rules/{id}
GET /api/guardianx/audit-replay/recommendations?source_type=...&source_id=...
```

`replay_recommendation` is the generic form: "Entire recommendation" or
"Entire AI reasoning chain" both replay through the same
`source_type`/`source_id` reference the Evidence Ledger and
Explainability Record already use.
