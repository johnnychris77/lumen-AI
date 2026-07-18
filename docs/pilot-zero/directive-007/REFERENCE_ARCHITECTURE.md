# LPZ-DIR-007 — Reference Architecture

**Purpose:** show how the governed artifacts connect end-to-end, from a physical
instrument to future decision support, so every baseline and Digital Twin used in
future computer-vision workflows has documented provenance and lifecycle. This is
a **provenance architecture**, not a deployment or AI-training architecture.

## End-to-end chain

```
Instrument                     physical reusable surgical instrument (identity: UDI/barcode)
   │
   ▼
Inspection                     a governed inspection event referencing the instrument
   │
   ▼
Image                          governed capture (Directive 005): identity-bound, hashed, no PHI
   │
   ▼
Metadata                       acquisition provenance (Directive 005): device, operator, time, calibration
   │
   ▼
Annotation                     controlled-taxonomy findings + evidence (Directive 006)
   │
   ▼
Ground Truth                   human-approved, immutable, ACTIVE label (Directive 006)
   │
   ▼
Baseline                       approved reference built ONLY on ACTIVE Ground Truth (this directive)
   │
   ▼
Digital Twin                   governed anchor tying identity → images → annotations → GT → baselines
   │
   ▼
Evidence Library               assembled, auditable evidence packages per instrument / point in time
   │
   ▼
Future AI Models               (reserved) trained later, under a separate authorized directive
   │
   ▼
Future Clinical Decision Support (reserved) advisory only, human-in-the-loop, never autonomous
```

## Layer responsibilities & provenance guarantees

| Layer | Owns | Provenance guarantee |
|---|---|---|
| Instrument | Identity (UDI/barcode) | Never fabricated |
| Inspection | Inspection event | Attributable, referenced (not rewritten) |
| Image | Pixels (`RetainedImage`) | Integrity-hashed, no PHI |
| Metadata | Acquisition context | Complete per Directive 005 |
| Annotation | Findings (`Annotation`/`AnnotationVersion`) | Controlled taxonomy, versioned, evidence-linked |
| Ground Truth | Approved labels | Human-approved, immutable, never overwritten |
| Baseline | Approved references | GT-gated, versioned, lifecycle-governed |
| Digital Twin | Instrument anchor | Immutable identity, composed history |
| Evidence Library | Evidence packages | Reconstructable, auditable |
| Future AI | Model outputs | Reserved; advisory; separate directive |
| Future CDS | Decision support | Reserved; human-in-the-loop; no autonomous disposition |

## Cross-cutting governance

* **Fail-closed everywhere:** missing identity, evidence, coverage, or quality
  blocks promotion at every layer.
* **Immutability & versioning:** Ground Truth and baselines are append-only;
  history is retrievable.
* **Separation of duties:** authors, reviewers, and approvers are distinct for the
  same evidence.
* **Audit:** every transition emits an attributable event; the whole chain is
  reconstructable.
* **Tenant isolation & no PHI:** enforced across the chain.
* **AI is advisory:** the two bottom layers are reserved and out of scope here;
  when built later they support, never replace, expert judgment.

## Boundary of this directive

Directive 007 governs the **Baseline** and **Digital Twin** layers (and their
dependence on the layers above). The **Future AI Models** and **Future Clinical
Decision Support** layers are shown for architectural completeness but are
explicitly **reserved** — no AI is created or trained, and no clinical decision
support is built, under this directive.

## Mapping to the existing system

Instrument/identity via `ml.lcid_service`; images in `RetainedImage` / LCID
`DatasetRegistryEntry`; metadata per Directive 005; annotations & GT in
`Annotation`/`AnnotationVersion` + annotation services; baselines in
`BaselineLibraryEntry` + `BaselineImageLink`/`BaselineSet` with a governed
lifecycle; Digital Twin as the reused `digital_twin_id` identity plus specialist
twin services; evidence assembly via existing audit/evidence facilities. This
architecture documents and governs those existing pieces as one chain; it adds no
code under this directive.
