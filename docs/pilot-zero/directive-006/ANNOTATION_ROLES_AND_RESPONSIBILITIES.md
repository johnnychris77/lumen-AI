# LPZ-DIR-006 — Annotation Roles & Responsibilities

**Purpose:** define the governance roles in the annotation and Ground Truth
process, their authority, and the **separation-of-duties** rules that keep
Ground Truth trustworthy. Roles are *functions*, not necessarily distinct
people — but the separation rules below constrain which functions one person may
hold for the **same** annotation.

This document is governance only. It maps each governance role to the role
strings already present in the system (`app.models.annotation_database`,
`app.db.models.TenantMembership`, `app.models.user.User`) so it is auditable;
it does not create new product functionality or change auth infrastructure.

## Role summary

| Governance role | Implemented role string (nearest) | Approval authority |
|---|---|---|
| Image Acquisition Operator | `operator` | None over annotations |
| Primary Annotator | `operator` / `spd_manager` | Creates annotations |
| Secondary Reviewer | `spd_manager` | Confirms/flags annotations |
| Clinical Reviewer | `clinical_reviewer` | Adjudicates disagreements |
| Engineering Reviewer | `spd_manager` (engineering context) | Adjudicates technical/artifact disputes |
| Ground Truth Approver | `clinical_reviewer` / `admin` | **Finalizes Ground Truth** |
| Dataset Curator | `ai_researcher` | Selects GT into datasets (no GT edit) |
| Quality Auditor | `admin` / `viewer` (read) | Audits; cannot alter records |
| Program Administrator | `admin` | Governance config; not exempt from SoD |

`ROLES_MAY_ANNOTATE`, `ROLES_MAY_REVIEW`, `ROLES_MAY_FINALIZE_GROUND_TRUTH`,
`ROLES_MAY_EXPORT`, and `ROLES_MAY_VIEW` in `annotation_database.py` are the
enforcement sets that back this table today.

## Roles in detail

### Image Acquisition Operator
* **Responsibilities:** capture governed images per Directive 005; register
  instrument identity; record capture metadata. Does **not** annotate findings
  for Ground Truth.
* **Permissions:** create images/sessions; read own captures.
* **Approval authority:** none over annotation or Ground Truth.
* **Training:** acquisition SOPs, metadata standard, no-PHI guardrail.
* **Separation of duties:** may not be the sole reviewer of an annotation on an
  image they captured where capture judgment is itself in question.

### Primary Annotator
* **Responsibilities:** record observations using the controlled taxonomy,
  region, severity, location, evidence, and **reviewer confidence**; mark
  **Unknown** when uncertain (never forced to guess).
* **Permissions:** create/edit annotations they own (each edit = new version).
* **Approval authority:** proposes; does not approve.
* **Training:** taxonomy, guidelines, confidence standard, versioning.
* **Separation of duties:** cannot be the Secondary Reviewer or the Ground Truth
  Approver of the **same** annotation.

### Secondary Reviewer
* **Responsibilities:** independent review under blind-review rules; agree or
  raise a documented disagreement.
* **Permissions:** submit secondary review; view blind-review-permitted context.
* **Approval authority:** confirms annotations; can send to resolution.
* **Training:** guidelines, blind-review discipline, disagreement standard.
* **Separation of duties:** must differ from the Primary Annotator of the same
  annotation.

### Clinical Reviewer
* **Responsibilities:** adjudicate disagreements requiring domain judgment;
  decide Consensus / Third-Reviewer outcomes; may sit on an Expert Panel.
* **Permissions:** adjudicate; record resolution + reason.
* **Approval authority:** disagreement resolution; may act as GT Approver where
  authorized.
* **Training:** guidelines, disagreement standard, evidence preservation.
* **Separation of duties:** may not adjudicate a disagreement they were the
  primary/secondary party to.

### Engineering Reviewer
* **Responsibilities:** adjudicate disputes that are technical/optical in nature
  (image artifact vs. true finding, coverage, focus, lighting).
* **Permissions / authority / training / SoD:** as Clinical Reviewer, scoped to
  engineering/imaging questions.

### Ground Truth Approver
* **Responsibilities:** verify a candidate against evidence and guidelines;
  approve to create the immutable Ground Truth version, or reject with reason.
* **Permissions:** finalize Ground Truth (`ROLES_MAY_FINALIZE_GROUND_TRUTH`).
* **Approval authority:** **highest** — the only role that creates Ground Truth.
* **Training:** full framework, versioning, audit.
* **Separation of duties:** may not approve an annotation they authored or
  reviewed.

### Dataset Curator
* **Responsibilities:** select `ACTIVE` Ground Truth into datasets; record
  eligibility. Never edits Ground Truth.
* **Permissions:** export/select (`ROLES_MAY_EXPORT`); read Ground Truth.
* **Approval authority:** dataset composition only — not Ground Truth content.
* **Training:** export governance, dataset eligibility, leakage-safety awareness.
* **Separation of duties:** curation is read-only w.r.t. Ground Truth records.

### Quality Auditor
* **Responsibilities:** verify attribution, versioning, evidence linkage, and
  audit completeness; report metric outliers (`ANNOTATION_QUALITY_METRICS.md`).
* **Permissions:** read-only across the pipeline and audit trail.
* **Approval authority:** none — auditors observe, they do not alter.
* **Training:** metrics, audit standard, versioning.
* **Separation of duties:** independent of annotation/approval for items audited.

### Program Administrator
* **Responsibilities:** manage governance configuration, role assignment, and
  standards versions.
* **Permissions:** administrative (`admin`).
* **Approval authority:** governance configuration; **not** exempt from
  annotation/approval separation of duties — an admin who annotates an item is,
  for that item, an annotator and may not also approve it.
* **Training:** entire framework.
* **Separation of duties:** administrative power does not override SoD on
  individual records.

## Separation-of-duties matrix (same annotation)

| Held role → also allowed as ↓ | Primary Annotator | Secondary Reviewer | Adjudicator | GT Approver |
|---|---|---|---|---|
| **Primary Annotator** | — | ✗ | ✗ | ✗ |
| **Secondary Reviewer** | ✗ | — | ✗ (if a party) | ✗ |
| **Adjudicator** | ✗ | ✗ (if a party) | — | may, if not a prior party |
| **GT Approver** | ✗ | ✗ | may, if not a prior party | — |

Rule of thumb: **no one approves their own work.** At least two distinct people
stand between a raw annotation and an approved Ground Truth record.
