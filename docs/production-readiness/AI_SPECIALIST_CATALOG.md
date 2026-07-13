# LumenAI — AI Specialist Catalog

Objective 7 review: purpose, inputs, outputs, and duplicated-responsibility check for every AI specialist. The brief named 10 specialists (Vision, Anatomy, Veritas, Aegis, Vulcan, Sage, Sentinel-X, Maestro, Council, Oracle) — those are reviewed first, in depth, including two real findings (Vision and Anatomy have no dedicated specialist module; Aegis has no model file). The remaining 15 specialists that exist in the codebase are cataloged afterward for completeness, since Objective 2 requires a full system inventory of "AI Specialists."

## Reuse discipline (how duplication is actually prevented here)

Every specialist model file below composes other specialists' already-computed outputs instead of re-deriving them, and ~20 of them carry an explicit "naming disambiguation" docstring section identifying prior systems they must not collide with. This is a working control, not aspirational — it's visible in the code today. The one place it did not fully succeed is Aegis (see below) and the two duplicate-class situations noted in the Architecture Inventory.

---

## The 10 Named Specialists

### Vision — **finding: no dedicated specialist module**
- **Purpose (as it exists today)**: CV/ML inference over inspection images.
- **Inputs**: image bytes, via `app/ai/inference.py`'s `LumenAIModel.predict`.
- **Outputs**: confidence scores, model name/version — persisted in `app/models/cv_inference.py` (`CVInferenceRecord`) and fields on `app/models/inspection.py`.
- **Duplication check**: N/A — no specialist exists to duplicate against. Nova's agent registry lists a `vision_agent` key but its own service marks it `reference_only`, i.e. Nova doesn't implement Vision, it just points at the inference file.
- **Recommendation**: either formally scope a Vision specialist (with its own naming-disambiguation docstring, service group, and route) or explicitly document — as this catalog now does — that Vision is intentionally infrastructure, not a specialist, so future work doesn't accidentally build a second one.

### Anatomy — **finding: no dedicated specialist module, split across two systems**
- **Purpose**: standardized anatomy taxonomy + per-inspection zone resolution.
- **Inputs**: instrument type, free-text zone strings from older code.
- **Outputs**: `AnatomyProfile` (the taxonomy, defined inside Genesis AI's model file, `genesis_ai_intelligence_cloud.py`); live zone resolution via Phase 22's `app/agents/anatomy_agent.py` wrapping `app/services/instrument_zones.py`.
- **Duplication check**: 21 model files reference "anatomy" in some field, but only these two systems actually own anatomy data — everyone else reads a zone string by field name. Not duplicated, but not owned by one clear module either.
- **Recommendation**: same as Vision — formally scope or formally document as cross-cutting infrastructure, not a specialist.

### Veritas
- **Purpose**: evidence integrity and baseline governance — the platform's data-quality assurance layer.
- **Inputs**: `baseline_comparison_scoring_service.resolve_baseline`, `BaselineLibraryEntry`, `EnterpriseVendorBaselineSubscription`, `RetainedImage`/`ImageLabel`, `ModelRegistryEntry`.
- **Outputs**: 7 tables — baseline resolutions, governance actions, evidence provenance, readiness assessments, evidence conflicts, training-dataset entries, feedback.
- **Duplication check**: clean. Reads Aegis/Vulcan/Sage output by reference only, never overwrites another specialist's conclusion. Explicitly distinguishes its own per-inspection-image evidence provenance from GuardianX's AI-assurance evidence ledger (different concept, same word "evidence").

### Aegis — **finding: no model file, not a full specialist**
- **Purpose**: process-variation signal (technician/vendor concentration patterns behind a recurring finding).
- **Inputs**: `Inspection.technician`, `Inspection.vendor_name` concentration patterns.
- **Outputs**: a JSON conclusion (`aegis_conclusion_json`) stored as **a column on Vulcan's own table** (`VulcanReliabilityAssessment`), not a separate table.
- **Duplication check**: `grep -l aegis app/models/*.py` returns zero files. The only implementation is `app/services/vulcan_aegis_integration_service.py::compute_process_variation_signal`, authored by Vulcan with an explicit docstring stating no Aegis agent existed before this and the signal is deliberately minimal rather than fabricated. Council, Steward, Maestro, and Sentinel-X all reference it as `SOURCE_AEGIS_PROCESS_RECOMMENDATION`/`SPECIALIST_AEGIS` — treating it as a first-class specialist in vocabulary even though it has no independent data store.
- **Recommendation**: formal architecture decision needed — either promote Aegis to a real specialist with its own model file (if its scope is expected to grow), or explicitly ratify that it is permanently a Vulcan sub-capability (Technical Debt Register TD-08 / ADR-0008).

### Vulcan
- **Purpose**: instrument reliability, failure analysis, repair intelligence.
- **Inputs**: `InspectionFinding` history, `RepairRequest` (`or_connect.py`), `instrument_knowledge.py`, digital-twin state, `SupervisorReview`.
- **Outputs**: 3 tables — reliability assessment, repair-effectiveness assessment, feedback.
- **Duplication check**: clean for its named scope; the one blur is that it also authors Aegis (see above).

### Sage
- **Purpose**: SPD education, competency, and workforce intelligence.
- **Inputs**: `CompetencyEvent` log, `SupervisorReview` ground truth, `Inspection.coverage_pct`/`ai_confidence`, Aegis/Vulcan signals.
- **Outputs**: 7 tables — knowledge gaps, learning plans, microlearning modules, assessments, education images, effectiveness assessments, feedback.
- **Duplication check**: clean — references `RetainedImage`/`ImageLabel` by ID rather than duplicating them.

### Sentinel-X — **naming collision explicitly resolved**
- **Purpose**: composite clinical risk intelligence and proactive patient-safety alerting.
- **Inputs**: Vulcan reliability, Aegis process-variation, Veritas evidence readiness, Sage gap detection, knowledge confidence.
- **Outputs**: 3 tables — risk assessment, patient-safety alert, supervisor override.
- **Duplication check**: a real prior collision exists and is deliberately avoided — the older "Project Sentinel" (`sentinel_orchestration.py`, v3.0, `SentinelRiskSignal`/`SentinelAlert`) is a separate, still-active advisory monitoring system. Sentinel-X uses a distinct `sentinelx_` file/table prefix, `/api/sentinelx` mount, and frontend route `/risk` (not `/sentinel`) to avoid collision. Both systems remain active — this is a candidate for a future consolidation decision, not a bug (Technical Debt Register TD-07).

### Maestro
- **Purpose**: executive-layer synthesis reading every specialist's output to rank operational priorities.
- **Inputs**: Phase 22 pipeline, `knowledge_graph_service`, `instrument_condition_service`, Veritas/Aegis/Vulcan/Sage/Sentinel-X/Pulse/Phoenix, Forge's approval/CAPA-suggestion services (read-only), Catalyst (read-only reference).
- **Outputs**: 5 tables — priority items, recommendations, daily briefs, operational health snapshots, decision journal.
- **Duplication check**: clean. Explicitly distinguishes itself from the pre-existing Phase 22 `app/agents/orchestrator.py` and Nova's `nova_orchestration_service.py` — different orchestration layers, never touching each other's tables.

### Council
- **Purpose**: convenes cross-specialist "AI leadership teams" for transparent, dissent-preserving human recommendations.
- **Inputs**: Veritas, Aegis, Vulcan, Sage, Sentinel-X, Apollo, Athena, Pulse, Phoenix, Maestro, Research Agent — 11 specialist services, read-only.
- **Outputs**: 8 tables — case, specialist assessment, dissent record, decision option, human decision, meeting notes, outcome review.
- **Duplication check**: clean. Explicitly distinguishes itself from Olympus's `NetworkGovernanceCase` (a cross-hospital governance body, unrelated concept sharing the word "council").

### Oracle
- **Purpose**: clinical intelligence scientist / discovery engine proposing human-gated research hypotheses.
- **Inputs**: Sentinel-X `compute_ai_health`, Apollo `twin_history`, Vulcan `compute_progression`/`findings_timeline`.
- **Outputs**: 6 tables — hypothesis, stage transition, trend observation, digital-twin insight, model observation, knowledge suggestion.
- **Duplication check**: clean. Stores Sentinel-X's health snapshot verbatim rather than recomputing it; cites (never merges with) Horizon's network-wide `EmergingTrendAlert`; promotion writes a shared `GovernanceApproval` row rather than a `KnowledgeArticle` directly.

---

## The Other 15 Specialists (full-system completeness)

| Specialist | One-line purpose | Duplication check |
|---|---|---|
| **Steward** | Governed execution layer for already-approved decisions | Clean — never re-decides; links to CAPA via `source_id` rather than duplicating the CAPA lifecycle |
| **Apollo** | Autonomous clinical quality management, unifying 5 pre-existing quality surfaces | Clean — extends CAPA/RCA/accreditation/competency services rather than replacing them |
| **Athena** | Institutional knowledge & experience graph | Clean — composes `knowledge_graph_service.reasoning_chain()` rather than reimplementing traversal |
| **Phoenix** | Self-improving platform intelligence (maturity, improvement pipeline) | Clean — explicitly distinguishes its Platform Maturity Index from GuardianX's Platform Trust Score |
| **GuardianX** | Cross-cutting AI assurance (trust/compliance/explainability) | Clean — extends `AIModelRegistryEntry` directly rather than a second registry |
| **Genesis AI** | Global sterile-processing intelligence cloud (v5.3) | Clean — explicitly not the same as "Project Genesis" v4.0 (`platform_core.py`), same name by sprint-numbering coincidence only |
| **Nova** | Governed AI agent platform around the static Phase 22 pipeline | Clean — several "Core Agent" registry entries are explicitly `reference_only` stubs, not reimplementations |
| **Olympus** | Autonomous healthcare intelligence network | Clean — distinguishes its Trust Network from Athena's per-article Knowledge Trust Score |
| **Infinity** | Developer ecosystem & marketplace | Clean — extends `PlatformPlugin` rather than a second plugin table; reuses Nexus's key-issuance pattern byte-for-byte |
| **Beacon** | Industry collaboration ecosystem | Clean — reuses P24's consortium members rather than a parallel membership table |
| **Forge** | No-code clinical rules/workflow engine | Clean — its approval chain is reused (not copied) by 5 other specialists |
| **Pulse** | Real-time operations command center | Clean — composes the legacy Sentinel health-score service |
| **Catalyst** | Conversational AI copilot | Clean — explicitly distinct from the older P9 guided-checklist "Copilot" (`copilot.py`) |
| **Orbit** | Perioperative & surgical readiness | Clean — explicitly distinct from P25's instrument-quality readiness score (different axis: per-case vs. per-instrument) |
| **Vanguard** | Executive intelligence & strategy | Notable, not a duplication issue: explicitly documents that some pre-existing "executive dashboard" endpoints it doesn't touch return mock/fabricated data — flagged for Technical Debt Register (TD-09) |

## Verdict

No specialist duplicates another specialist's core reasoning. The two real gaps are **ownership gaps, not duplication**: Vision and Anatomy lack a single owning module, and Aegis lacks independent specialist status despite specialist-level treatment in vocabulary. Both are documented as findings above and carried into the Technical Debt Register.
