# ADR-0005: Evidence Governance Ownership (Veritas)

## Status
Accepted.

## Context
Baseline resolution, evidence provenance, and training-data quality all needed a governing layer, but the platform already had baseline data (`BaselineLibraryEntry`), image data (`RetainedImage`/`ImageLabel`), and model data (`ModelRegistryEntry`) — a new evidence system risked either duplicating these stores or fragmenting evidence quality judgments across every specialist that touches evidence.

## Decision
Project Veritas owns evidence integrity and baseline governance exclusively. It composes existing stores (`resolve_baseline`, `BaselineLibraryEntry`, `RetainedImage`/`ImageLabel`, `ModelRegistryEntry`) rather than duplicating them, and other specialists that reference evidence (Aegis, Vulcan, Sage) are read-only consumers of Veritas's judgment, never overriding it. Veritas is explicitly distinguished from GuardianX's `EvidenceLedgerEntry` — a different concept (AI-assurance provenance for model governance) that happens to share the word "evidence."

## Consequences
- **Positive**: one clear owner for "is this evidence trustworthy," rather than each specialist making its own ad hoc judgment.
- **Positive**: the Veritas/GuardianX naming overlap was caught and documented at design time rather than discovered later as a collision.
- **Consideration for Phase 2**: Veritas's boundary with GuardianX's evidence ledger should be re-verified periodically as GuardianX's compliance-mapping scope grows, to ensure the "different evidence, different purpose" boundary doesn't blur.
