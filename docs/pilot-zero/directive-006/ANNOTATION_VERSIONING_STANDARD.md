# LPZ-DIR-006 — Annotation Versioning Standard

**Purpose:** define how every annotation change is versioned so the process is
reproducible and auditable. The core rule: **history is never overwritten.**
Every change creates a new immutable version; the prior version is retained.

## Required version fields

| Field | Meaning | System mapping |
|---|---|---|
| **Immutable UUID** | Permanent annotation identity | `Annotation.ann_id` (`ANN-YYYY-NNNNNNNNN`) |
| **Version Number** | Monotonic per annotation | `AnnotationVersion.version_number` / `Annotation.current_version` |
| **Parent Version** | The version this one supersedes | `AnnotationVersion.previous_version_id` |
| **Reviewer / Editor** | Who made the change (attributable) | `AnnotationVersion.editor` |
| **Timestamp** | When | `AnnotationVersion.created_at` |
| **Reason for Change** | Why (required) | `AnnotationVersion.reason` |
| **Evidence Reference** | Region/baseline evidence for the change | snapshot fields |
| **Audit Trail** | Linked audit event(s) | audit log |
| **Ground Truth Link** | GT status/version this change affects | `ground_truth_status` / `ground_truth_version` |
| **Dataset Link** | Dataset(s) the annotation is selected into | `dataset_version_id` |

*System:* `AnnotationVersion.snapshot_json` stores the full immutable snapshot of
the annotation state at each version.

## Rules

1. **Immutable identity, versioned content.** The UUID never changes; content
   changes create new versions beneath it.
2. **Append-only.** A new version is inserted; no prior version row is updated or
   deleted.
3. **Every change is a version.** Observation, region, severity, confidence,
   review outcome, and Ground Truth transitions each create a version.
4. **Reason required.** No version is created without an attributable reason.
5. **Monotonic numbering.** Version numbers increase by one; gaps are not
   allowed.
6. **Parent linkage.** Each version (after v1) references its parent, forming an
   unbroken lineage.
7. **Ground Truth immutability.** A Ground Truth correction is a **new**
   superseding version; the approved prior version remains in history
   (`GROUND_TRUTH_GOVERNANCE.md`).

## Lineage example

```
ANN-2026-000012345
  v1  created   editor=annotatorA  reason="primary annotation"
  v2  reviewed  editor=reviewerB   reason="secondary agreement"      parent=v1
  v3  adjudicated editor=clinicalC reason="resolved disagreement"    parent=v2
  v4  GT ACTIVE editor=approverD   reason="ground truth approval"    parent=v3
  v5  superseded editor=approverE  reason="evidence correction"      parent=v4
       (v4 retained, marked superseded — never deleted)
```

## Audit linkage

Each version links to its audit event(s) so that "who changed what, when, and
why" is answerable for every annotation and Ground Truth record. Version history
plus the audit trail together must reconstruct the complete lifecycle.

## Governance note (existing system)

`AnnotationVersion` is append-only today, capturing `version_number`, `editor`,
`reason`, `previous_version_id`, and a full `snapshot_json`; `annotation_service`
writes a version on create and on each update. Governance additions recorded for
a future authorized change: make **reason mandatory** at the API boundary for
every mutating call, and surface the dataset-link and GT-link fields in the
version snapshot so lineage-to-dataset is explicit in history.
