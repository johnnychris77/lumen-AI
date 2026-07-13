# LumenAI — AI Limitations

Objective 8's explainability requirement asks every AI recommendation to disclose: evidence used, confidence, limitations, alternative explanations, recommended next step, and required reviewer. This document catalogs where that disclosure is real today and where it is partial, consolidated from the per-table audit below plus every limitation surfaced elsewhere in this review.

## Explainability field audit — 4 representative AI-output tables

| Table | Evidence used | Confidence | Limitations | Alternative explanations | Next step | Required reviewer |
|---|---|---|---|---|---|---|
| `SupervisorReview` (a human-feedback snapshot of an AI output, not itself AI-generated) | No dedicated field | Yes (`ai_confidence`, numeric) | No | No | Partial (`ai_recommendation` captures what was recommended, no distinct next-step field) | Yes (`reviewer_role`, but records who *did* review, not who is *required* to) |
| `SentinelXRiskAssessment` | Yes (`evidence_json`) | Partial (`confidence`, categorical string) | **No explicit field** | No | No explicit field (`reasoning_narrative` is free-text rationale) | Partial (`human_review_required` bool; no specific required role on this table) |
| `VeritasEvidenceReadinessAssessment` | Yes (`missing_zones_json` + provenance linkage) | Partial (`confidence`, categorical) | **Yes** (`limitations_json`) | No explicit field | **Yes** (`next_action`, `recommended_gate`) | Partial (`human_review_required` bool; role lives on a related table) |
| `OracleHypothesis` | Yes (`evidence_json`, `statistical_summary_json`, `sample_size`) | Partial (`confidence_level`, categorical) | **No explicit field** | No explicit field (enforced by phrasing convention instead) | Partial (`current_stage` implies the next gate, no free-text next-step field) | Partial (`human_review_required` bool; `research_owner` names an owner, not a required role) |

**No table has all six fields.** Veritas comes closest (evidence, limitations, and next-step are explicit fields). Across all four, "required reviewer" is consistently a boolean gate (`human_review_required`) rather than a named required role on the AI-output row itself — the actual reviewing role is captured on a separate feedback/override/transition table (`SentinelXSupervisorOverride.submitted_role`, `VeritasFeedback.submitted_role`, `OracleStageTransition.changed_by_role`), not co-located with the AI's own conclusion. **Recommendation**: add `limitations` fields to `SentinelXRiskAssessment` and `OracleHypothesis` as a Phase 4 improvement — Veritas's pattern is the one to replicate.

## The single most important limitation: no trained model ships in this repository

`app/ai/inference.py` runs a deterministic fallback (`_deterministic_fallback()`) unless a real YOLO model file is present. That fallback emits only `debris`, `corrosion`, `stain`, `clean` — a small fraction of the 12-13-category taxonomy the scoring/education layer is designed around. See [FINDING_TAXONOMY.md](./FINDING_TAXONOMY.md) for the full accounting. **This is the limitation that should be stated first, before any other, in any clinical-facing description of the platform.**

## Anatomy/zone resolution is a heuristic, not true localization

`instrument_zones.py`'s own docstring: instrument→zone mapping is "the same placeholder-grade heuristic... NOT pixel-level localization," with confidence explicitly capped at 0.70. See [ANATOMY_REFERENCE.md](./ANATOMY_REFERENCE.md).

## Finding taxonomy is not uniform across the codebase

Five different, overlapping finding-type vocabularies coexist (scoring engine, trend service, education content, two agent-level subsets, and the frontend dashboard), differing in which of rust/discoloration/pitting/missing_component/wear/other_organic_residue they include. `wear` in particular is taxonomized in three vocabularies but explicitly documented as functionally unscored ("will always report 0"). See [FINDING_TAXONOMY.md](./FINDING_TAXONOMY.md) for the full comparison table.

## No per-finding-type documented visual evidence or false-positive/negative criteria

Nothing in the codebase documents what specific visual evidence distinguishes, e.g., corrosion from pitting, or documents finding-type-specific false-positive/false-negative risk. `docs/clinical/clinical-performance-report.md` names this exact discrimination problem as a known, currently-unresolved weakness pending the (not-yet-conducted) multi-site study. This review does not invent that missing detail — it states its absence plainly, per [FINDING_TAXONOMY.md](./FINDING_TAXONOMY.md).

## Digital twin confidence disclosure is inconsistent across twin systems

`digital_quality_twin.py`'s forecast/simulation/intervention/executive-brief models are **consistently** paired with a `confidence_score` field, `human_review_required=True`, and an explicit disclaimer stating no causation is established. Apollo's governance-health twin (`apollo_quality_twin_service.py::compute_quality_twin`), by contrast, has **no numeric confidence field at all** — only a `factors` dict of hand-written scope-limitation strings (e.g., "tenant-wide, not department-scoped"). Its `twin_history` view is hedged even less (no `factors`, no `disclaimer`, no `human_review_required` in the history rows at all). See [DIGITAL_TWIN_CLINICAL_MODEL.md](./DIGITAL_TWIN_CLINICAL_MODEL.md) — recommend adding a numeric confidence field to Apollo's twin as a Phase 4 item.

## Knowledge governance has no review-schedule enforcement

`KnowledgeArticle` has `version`, `author`, `reviewer`, `approval_status`, and `last_reviewed_at` — but **no review-schedule field** (no `next_review_due`, `review_interval_days`, or expiration date). An article can go stale indefinitely with no automated flag that it's overdue for re-review. `references`, `ifu_reference` (appearing on 6 different model files), and Oracle's `supporting_literature_json` are all unstructured free-text/JSON fields with no citation-validation logic anywhere in the codebase.

## Knowledge Graph governance review (Objective 6)

`KnowledgeArticle` (`app/models/knowledge.py`) carries real governance scaffolding: `category` (classifies article *type* — best_practice, clinical_pearl, manufacturer_clarification, etc.), `author`, `reviewer`, `version` (integer counter), `approval_status` (`draft → pending_review → approved/rejected → archived`, enforced by `knowledge_governance_service.py`), and `last_reviewed_at`. The approval workflow is real and role-gated: any authenticated role can submit for review, but only `admin`/`spd_manager` can approve, reject, or archive (`app/routes/knowledge.py`'s `_LEADERSHIP_ROLES` gate) — though this role check lives at the route layer, not inside `knowledge_governance_service.py` itself, so a direct service call from another module would bypass it.

**Two real gaps, not aspirational claims:**
- **No source/provenance-type field.** Nothing distinguishes a manufacturer-IFU-derived article from an internally-authored playbook from a clinical-literature-derived one — `category` classifies the article's *kind*, not where its content came from.
- **No review-schedule field.** `last_reviewed_at` records that a review happened once; there is no `next_review_due`/`review_interval_days`/expiration field, so an article can go stale indefinitely with no automated staleness flag.

**Manufacturer and clinical-literature references are universally unstructured free text.** `ifu_reference` appears on 6 different model files (`enterprise_quality.py`, `instrument_knowledge.py`, `instrument_registry.py`, `integrations.py`, plus label constants in `guardianx_assurance.py`/`veritas_evidence.py`) — every instance is a bare `String`/`Text` column with no foreign key and no format validation. `KnowledgeArticle.references` is free `Text`. Oracle's `supporting_literature_json` is a JSON-encoded list with no citation-validation logic. **None of these fields are checked for existence, format, or validity anywhere in the codebase** — this review found no citation-validation service of any kind.

## Root-cause and Oracle-hypothesis scope boundaries (verified, not a gap)

Root-cause categorization is deliberately human-only (`root_cause.py`), and Oracle hypotheses require passing through all 8 stages of a human-gated validation pipeline — including tier-2-or-above authorization plus recorded gate-check notes to reach the terminal `PRODUCTION_KNOWLEDGE` stage — before they can be described as anything beyond a research hypothesis. Neither of these is a limitation to fix; both are working, verified safeguards.
