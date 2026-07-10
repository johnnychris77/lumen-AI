# Project Horizon — Knowledge Governance

LumenAI v3.4 — Sections 8, 9 & 10

## Governance Center (`/governance`, Section 9)

`horizon_governance_service.py` composes what already exists rather than
building a parallel governance store:

- **Participation agreements** — `horizon_participation_service`'s
  combined `GSINParticipant` + `IntelligenceSharingAgreement` view.
- **Contribution approval** — `horizon_contribution_service`'s pending
  queue (`list_all_pending_approvals` for a governance-board-wide view;
  `governance_overview`'s per-tenant view shows both what an org has
  submitted and, for reviewers, what's outstanding).
- **Knowledge review** — the approve/reject endpoints themselves
  (`POST /contributions/{id}/approve|reject`).
- **Version history** — `horizon_contribution_service.get_version_history`.
- **Audit trail** — queries this platform's existing `AuditLog` table for
  every `horizon.*` action type (`horizon.participation_enrolled`,
  `horizon.contribution_submitted`, `horizon.contribution_approved`, ...)
  via the same `app/audit.py::log_audit_event` mechanism every other
  sprint in this codebase already uses — no second audit store.
- **Data sharing preferences** — `GSINParticipant.contribution_categories`
  (already a JSON list field on the existing model), updated via
  `POST /participation/contribution-categories`. Reused rather than
  adding a new preferences table.

## Clinical Evidence Repository (`/research`, Section 8)

Before this sprint, the only existing evidence/citation structure was a
narrow finding-category-to-regulatory-clause mapping
(`app/models/regulatory.py::FindingRegulatoryMapping`, used for
accreditation packages). `ClinicalEvidenceReference` is the first
general-purpose evidence store, covering six types the sprint names:
peer-reviewed literature, manufacturer guidance, AAMI standards, AORN
standards, an organization's own approved SOPs, and internal validation
studies.

### Public vs. private evidence

`ClinicalEvidenceReference.tenant_id` is blank for globally-visible
evidence (peer-reviewed literature, AAMI/AORN standards, manufacturer
guidance that applies to every organization) and set to a specific tenant
only for that organization's own private SOPs and internal validation
studies. `list_evidence` never returns another organization's private
evidence — only global (`tenant_id == ""`) entries plus, when a
`tenant_id` is passed, that one organization's own private entries.

### Linking evidence to recommendations

`RecommendationEvidenceLink` is deliberately generic: `source_type` is a
free-form label (`"sentinel_recommendation"`, `"atlas_alert"`,
`"insight_recommendation"`, `"quality_capa"`, ...) and `source_id` a
string identifier — this link table never needs a schema change to cover
a new recommendation-producing engine. No existing recommendation engine
in this codebase (Sentinel, Atlas, Insight, Quality Guardian's CAPA/RCA)
linked to any citation before this sprint; each used only a free-text
`reasoning`/`association_reason` string. `GET /evidence/for/{source_type}/
{source_id}` is the read path any of those engines' UIs can call to show
"here's the evidence behind this recommendation."

## Global AI Improvement (Section 10)

`horizon_ai_improvement_service.py` reads only **published,
k-anonymity-verified** federated knowledge (`FederatedLearningSignal`,
`GlobalKnowledgeGraphEdge`, `EmergingTrendAlert`) and produces advisory
suggestions tagged to one of the five named local systems:

| Target system | Triggered by |
|---|---|
| Knowledge Graph | A published global knowledge-graph edge recurring across many organizations |
| Clinical Reasoning | Low global coverage effectiveness for an instrument type |
| Zone Intelligence | A recurring anatomy-trend signal for a zone |
| Digital Twins | An active emerging trend alert |
| Prediction Models | An elevated global instrument-failure-pattern rate |

Every suggestion is **advisory only** — this service never mutates any
local system's baselines, weights, or parameters. A human reviews and
applies (or dismisses) each suggestion locally; `human_review_required:
true` is set on every suggestion without exception, and every suggestion
carries the evidence and confidence that produced it.
