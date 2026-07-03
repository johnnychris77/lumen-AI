"""Phase 23 §10 — Platform Governance.

Tracks the versions every inspection is governed by. These are code-level
constants, not per-tenant mutable state — bump them here when the
underlying artifact actually changes (a new architecture doc revision, a
new ontology chain, a newly promoted model, etc.), and every inspection
processed after that point references the new value. Past Decision Ledger
entries keep the version snapshot that was active *when they were
created* (see app/models/clinical_decision_ledger.py) — they are never
retroactively rewritten.
"""
from __future__ import annotations

ARCHITECTURE_VERSION = "19.5"          # docs/architecture/ — frozen reference architecture
ONTOLOGY_VERSION = "1.0"               # docs/architecture/lumenai-clinical-ontology.md chain
KNOWLEDGE_GRAPH_VERSION = "21.0"       # docs/knowledge-graph/ — node/relationship taxonomy
MODEL_VERSION = "baseline-comparison-scoring-pilot-1"  # active scoring engine, see app/services/baseline_comparison_scoring_service.py
DATASET_VERSION = "pilot-v1"           # default Phase 18 ground-truth dataset version
CLINICAL_RULE_VERSION = "1.0"          # see app/cios/rule_registry.py
INSPECTION_PIPELINE_VERSION = "22.0"   # Phase 22 multi-agent pipeline, see app/agents/registry.py


def governance_snapshot() -> dict:
    """The full version snapshot every inspection/ledger entry references."""
    return {
        "architecture_version": ARCHITECTURE_VERSION,
        "ontology_version": ONTOLOGY_VERSION,
        "knowledge_graph_version": KNOWLEDGE_GRAPH_VERSION,
        "model_version": MODEL_VERSION,
        "dataset_version": DATASET_VERSION,
        "clinical_rule_version": CLINICAL_RULE_VERSION,
        "inspection_pipeline_version": INSPECTION_PIPELINE_VERSION,
    }
