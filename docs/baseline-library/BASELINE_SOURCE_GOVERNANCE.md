# Baseline Source Governance — Project Atlas Sprint 1

Implements mission Sections 2 and 3: what a baseline image's *source*
claims, what *type* of baseline image it is, and the non-negotiable rule
that a manufacturer-provenance claim requires real evidence.

## Source types (`BASELINE_SOURCE_TYPES`)

| Source type | Meaning |
|---|---|
| `manufacturer_reference` | Supplied by or verifiably traceable to the instrument manufacturer |
| `organization_known_good` | This organization's own verified known-good instrument |
| `new_instrument_reference` | Captured from a newly received, unused instrument |
| `post_repair_reference` | Captured after a documented repair, representing the post-repair known state |
| `digital_twin_initial_reference` | The first image captured for a specific physical instrument's Digital Twin |
| `governed_consensus_reference` | An organization-authorized consensus reference, not tied to one manufacturer/model |
| `research_reference` | Research-only; explicitly never presented as a manufacturer or clinical baseline |

`research_reference` and any other unapproved source must never be
displayed or reported as a manufacturer baseline — the `image_type` field
(below) and `source_type` are always shown together in the viewer and
audit trail, and `link_lcid_image_to_baseline()` stores them independently
so one can never silently stand in for the other.

## Image types (`BASELINE_IMAGE_TYPES`)

| Image type | Meaning |
|---|---|
| `manufacturer_baseline` | This image documents the manufacturer-reference condition |
| `organization_baseline` | This image documents this organization's known-good condition |
| `digital_twin_baseline` | This image documents one physical instrument's own baseline |
| `anatomy_zone_reference` | This image documents one specific anatomy zone/view, not the whole instrument |
| `post_repair_reference` | This image documents the post-repair condition |
| `candidate_baseline` | Proposed but not yet governed as any of the above |

A `BaselineLibraryEntry` may have any number of `BaselineImageLink` rows
across these types and zones simultaneously — the mission's explicit
instruction "do not assume one image represents the entire instrument" is
enforced by there being no field anywhere that treats a single link as
comprehensive; the entry-level view in the frontend always lists every
linked image rather than picking one as "the" image.

## The provenance requirement (Section 5's manufacturer-approval rule)

`SOURCE_TYPES_REQUIRING_PROVENANCE = {manufacturer_reference}`.

`link_lcid_image_to_baseline()`
(`app/services/baseline_image_library_service.py`) raises
`ProvenanceRequiredError` — a 422 at the route layer — if `source_type ==
"manufacturer_reference"` and either `source_organization` or
`source_reference` is blank. There is no code path, dropdown default, or
review shortcut that can set `source_type` to `manufacturer_reference`
without both fields populated with non-empty, real values (a document ID,
purchase order or correspondence reference, or vendor-portal submission
ID) at the moment the link is created.

This is a **creation-time** gate, not merely a review-time warning: a
manufacturer-reference link cannot exist in the database at all — not even
in `DRAFT` — without that evidence, which is stronger than the mission's
literal wording ("do not permit a user to mark an image
manufacturer-approved merely by selecting a dropdown value") since it
closes the gap even before any human review occurs.

## Review still required regardless of source type

Provenance at creation time is necessary but not sufficient. Every
baseline image — regardless of `source_type` — must still pass through
`PENDING_REVIEW` → an authorized `BaselineImageReview` with
`decision="approve"` before activation (`BASELINE_REVIEW_WORKFLOW.md`,
Section 4's activation gate). A manufacturer-reference image with real
provenance still requires a real clinical/administrative review before it
can influence any comparison.
