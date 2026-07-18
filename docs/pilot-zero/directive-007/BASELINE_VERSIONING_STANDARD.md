# LPZ-DIR-007 — Baseline Versioning Standard

**Purpose:** define how baselines are versioned. Core rule: **no baseline is
overwritten**, and **historical versions remain retrievable**. A baseline's
identity is permanent; its content evolves through immutable versions.

## Required version fields

| Field | Meaning | System mapping |
|---|---|---|
| **Immutable UUID** | Permanent baseline identity | `BaselineImageLink` / `BaselineLibraryEntry` id |
| **Major Version** | Substantive change (new reference image, changed decision) | `baseline_version` (major.minor) |
| **Minor Version** | Non-substantive refinement (metadata, rationale) | `baseline_version` |
| **Parent Version** | The version this supersedes | supersede linkage |
| **Effective Date** | When this version became active | activation timestamp |
| **Superseded Date** | When replaced by a newer version | supersede timestamp |
| **Reason for Revision** | Why the version was created (required) | `governance_notes` / review reason |
| **Evidence References** | Source images / GT / provenance | link + review records |
| **Approval History** | Approver(s) and timestamps across versions | approval records |
| **Retirement Status** | Retired/archived flag | lifecycle state |

## Versioning rules

1. **Major vs. minor.** A **major** bump is required when the reference image(s),
   the Ground Truth beneath the baseline, or the baseline's decision meaning
   changes. A **minor** bump covers metadata/rationale refinements that do not
   change what the baseline asserts.
2. **Append-only.** A new version is created; the prior version is never edited or
   deleted. It is marked **Superseded** with a superseded date.
3. **Parent linkage.** Each version (after the first) references its parent,
   forming an unbroken lineage.
4. **Reason required.** No version is created without an attributable reason.
5. **Retrievable history.** Every historical version remains retrievable for
   audit and to reproduce a past comparison.
6. **Re-approval on major change.** A major version requires a fresh approval per
   `BASELINE_APPROVAL_STANDARD.md`; a minor change may follow a lighter governed
   path but is still attributable.

## Lineage example

```
BASELINE 2026-000042
  v1.0  effective 2026-02-01  approver=D  reason="initial approved reference"
  v1.1  effective 2026-03-10  approver=D  reason="rationale/metadata refinement"  parent=v1.0
  v2.0  effective 2026-05-20  approver=E  reason="new reference image; GT v3"      parent=v1.1
         (v1.0, v1.1 retained, marked Superseded — never deleted)
```

## Interaction with Digital Twin and inspections

* A Digital Twin references the **current ACTIVE** baseline version, but the twin's
  history retains which baseline version was active at any past time.
* An inspection comparison records the exact **baseline version** it compared
  against, so results are reproducible even after the baseline is superseded.

## Governance note (existing system)

`BaselineLibraryEntry.baseline_version` and the baseline image library's lifecycle
(`SUPERSEDED` state + transition map) provide append-only supersession today, and
`BaselineComparisonAccessLog` records access. Governance additions recorded for a
future authorized change: formalize major/minor semantics, require a revision
reason on every version, and pin the compared baseline **version** (not just id)
into each inspection comparison record. No code is changed under this directive.
