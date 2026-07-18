# LPZ-DIR-010 — Data Governance Review (DGR)

**Purpose:** assess the data-governance frameworks and their implementation status.
Evidence-based.

## Review items

| Item | Framework | Implementation | Status |
|---|---|---|---|
| **Metadata integrity** | Directive 005 standard | Registry capture fields + `phi_verification`; **005 doc set not consolidated on main** | ⚠️ Doc gap (SRR-1) |
| **Ground Truth governance** | Directive 006 | `Annotation`/`AnnotationVersion` (append-only), GT service, ACTIVE gate | ✅ Framework + code |
| **Annotation governance** | Directive 006 | Annotation DB, review/blind-review services, `ANNOTATION_STATES` machine | ✅ Framework + code |
| **Digital Twin governance** | Directive 007 | `digital_twin_id` identity (LCID); twin services | ✅ Framework; aggregate record is a gap |
| **Baseline governance** | Directive 007 | `BaselineLibraryEntry`/`BaselineImageLink`, `BASELINE_IMAGE_STATES` lifecycle, review | ✅ Framework + code |
| **Dataset governance** | Directive 008 | `DatasetVersion`/`DatasetRegistryEntry`, builder, leakage-safe split, integrity, validation | ✅ Framework + code |
| **Version control** | 006/007/008 | Append-only versioning across annotation/baseline/dataset | ✅ Complete |
| **Lineage** | 008 lineage standard | `image_sha256`, `lcid`, `digital_twin_id`, `baseline_id`, `annotation_version` on entries | ✅ Framework + code |
| **Audit trails** | Foundation audit arch | Lifecycle audit events across modules | ✅ Complete |

## Findings

* **DGR-1 (doc gap):** Directive 005 (Image Acquisition & Metadata Standard)
  deliverables are not consolidated under `docs/pilot-zero/directive-005/`
  (mirrors SRR-1). Metadata governance is partly covered in the registry schema and
  Directive 004 workstation doc, but the dedicated standard set should be located or
  restated. **Condition.**
* **DGR-2 (enforcement gap):** Governance **preconditions** (ACTIVE-GT gating,
  separation of duties, dataset immutability, pinned versions) are **documented**
  across Directives 006–008 but not all **enforced in code**. **Condition** (shared
  with ERR-2).
* **DGR-3 (no data yet):** All governance is validated on schema/logic; with **no
  acquired governed images**, there is no end-to-end governed dataset instance to
  audit. This is a consequence of LRR-1, not a governance defect.
* **DGR-4 (strength):** The governance frameworks (006/007/008) are comprehensive,
  internally consistent, append-only, and largely backed by existing models and
  services with audit coverage.

## DGR determination

**CONDITIONAL PASS.** Data-governance frameworks are strong and substantially
implemented in code. Conditions: consolidate Directive 005 (DGR-1), enforce the
High-priority governance gates in code (DGR-2), and — post-LRR — validate one
end-to-end governed dataset instance (DGR-3).
