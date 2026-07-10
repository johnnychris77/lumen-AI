# Project Beacon — Clinical Evidence Exchange

LumenAI v3.5 — Section 5

## Extends Horizon's evidence store — does not build a second one

Horizon's `ClinicalEvidenceReference` / `RecommendationEvidenceLink`
(`app/models/federated_horizon.py`, `app/services/horizon_evidence_
service.py`) is already the first general-purpose clinical evidence
store in this codebase, covering peer-reviewed literature, manufacturer
guidance, AAMI/AORN standards, an organization's own SOPs, and internal
validation studies — with public (`tenant_id == ""`) vs. private
(tenant-scoped) visibility already enforced, and a generic
`source_type`/`source_id` link so any recommendation-producing engine
(Sentinel, Atlas, Insight, Quality Guardian's CAPA/RCA) can cite it.

This sprint's Section 5 asks for three more evidence types — validation
studies (already covered by `internal_validation_study`), case reports,
quality improvement initiatives, best practices — so `EVIDENCE_TYPES`
was extended with `case_report`, `quality_improvement_initiative`, and
`best_practice` rather than a second evidence table.
`beacon_evidence_exchange_service.py` adds no new persistence: it is a
presentation layer over `horizon_evidence_service`, exactly like
`horizon_research_portal_service.py` composed Horizon's own signals over
P20's research exchange.

## "Every AI recommendation links to available evidence"

This guarantee was already implemented by Horizon's `GET /api/horizon/
evidence/for/{source_type}/{source_id}`; Beacon exposes the identical
read path at `GET /api/beacon/evidence-exchange/for/{source_type}/
{source_id}` (`beacon_evidence_exchange_service.evidence_for_
recommendation`, a direct passthrough).

## Endpoints

```
GET  /api/beacon/evidence-exchange                                     — summary across all evidence types
POST /api/beacon/evidence-exchange/case-reports
POST /api/beacon/evidence-exchange/quality-improvement-initiatives
POST /api/beacon/evidence-exchange/best-practices
GET  /api/beacon/evidence-exchange/for/{source_type}/{source_id}
```
