# ADR-0003: Knowledge Graph as a Shared Reasoning Layer

## Status
Accepted.

## Context
Multiple specialists (Maestro, Athena, Oracle, Sentinel-X) each needed a way to traverse relationships between findings, instruments, anatomy, and recommendations, and to derive a confidence-in-learning signal from historical supervisor review data.

## Decision
A single `knowledge_graph_service.py` (`explore()`, `reasoning_chain()`, `learning_confidence()`) is the one shared reasoning layer; `app/models/knowledge.py` (`KnowledgeArticle`, `ClinicalCase`, `OrganizationStandard`, `KnowledgeQueryLog`) is the one persisted knowledge store. Athena's `ExperienceGraphNode`/`ExperienceGraphEdge` extend the graph for institutional-memory traversal without a second article store; every consuming specialist calls into this one service rather than building its own graph traversal.

## Consequences
- **Positive**: no duplicated graph-traversal logic anywhere in the codebase — confirmed during this review.
- **Positive**: `learning_confidence()` in particular is reused as a trust signal by both Maestro and Oracle without either recomputing it.
- **Risk to monitor**: as more specialists depend on this one service, it becomes a shared-fate dependency (similar to Forge's approval chain) — any change to its output shape has a wide blast radius. Not currently a problem, but worth the same "treat as a stable internal contract" discipline recommended for Forge (Technical Debt Register TD-10).
