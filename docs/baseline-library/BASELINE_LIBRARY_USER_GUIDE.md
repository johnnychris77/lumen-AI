# Baseline Image Library — User Guide

Covers the workspace at `/baseline-library` (also reachable at
`/baselines/library`) and its child routes, built in Project Atlas
Sprint 1. This is the governed workspace for linking, reviewing,
activating, and viewing image evidence behind existing baseline entries —
it is **not** the Manufacturer Baselines vendor-upload flow
(`/manufacturer-baselines`) or the Vendor Baseline Portal
(`/vendor-baseline-portal`), which remain separate, unmodified legacy
workflows for a different purpose (see
`BASELINE_CURRENT_STATE_TRACE.md` Section 6 for how these differ).

## Routes

| Route | Purpose |
|---|---|
| `/baselines/library` | Browse all baseline image links for your tenant, filterable by lifecycle status |
| `/baselines/library/new` | Link an existing LCID-registered image to an existing baseline entry |
| `/baselines/library/:baselineId` | Full viewer + lifecycle actions for one baseline image link |
| `/baselines/sets/:baselineSetId` | View a governed multi-image baseline set and its members |
| `/baselines/review` | Queue of baseline images currently `PENDING_REVIEW` |

## Linking a new baseline image (`/baselines/library/new`)

Requires `admin`, `spd_manager`, `clinical_reviewer`, or `operator`. You
will need:

1. **The baseline library entry ID** this image documents — the existing
   metadata-only baseline entry (from Manufacturer Baselines, the network
   baseline registry, or elsewhere).
2. **An existing LCID-registered image** — selected from a dropdown of
   images already registered through the dataset registry (`/dataset-registry/images`).
   You cannot upload a new image file here; this workspace only links
   evidence that has already gone through image ingestion and LCID
   registration. If the image you need isn't registered yet, register it
   through the image ingestion workflow first.
3. **Anatomy zone and inspection view** — required; a baseline image
   without these cannot later be activated.
4. **Image type** — which of the six governed types (manufacturer
   baseline, organization baseline, Digital Twin baseline, anatomy-zone
   reference, post-repair reference, candidate baseline) this image
   represents.
5. **Source type and provenance** — if you select "manufacturer
   reference," you must also provide a source organization and a real
   source reference (document ID, PO, vendor-portal submission ID). The
   form will not submit without both.

The new link starts in **DRAFT**.

## Submitting for review and reviewing (`/baselines/library/:baselineId`)

- Anyone who can create a link can submit it for review
  (DRAFT → PENDING_REVIEW).
- Reviewers (`admin`, `spd_manager`, `clinical_reviewer`) see a review form
  requiring a rationale, with optional limitations, source-verification
  notes, an anatomy-compatibility confirmation checkbox, and an image
  quality assessment. Approve moves the link to APPROVED; reject moves it
  to REJECTED.
- The review queue at `/baselines/review` lists everything currently
  awaiting a decision, flagging manufacturer-reference-sourced images for
  extra scrutiny.

## Activating, suspending, archiving, superseding

- **Activate** (APPROVED → ACTIVE): only available if every activation
  gate condition is met (see `BASELINE_REVIEW_WORKFLOW.md`). If any
  condition is missing, the API returns exactly which ones — the frontend
  surfaces that list as an error rather than a generic failure.
- **Suspend** (ACTIVE → SUSPENDED): temporarily removes an image from
  comparison eligibility without losing its history; can be reactivated.
- **Archive**: available from most states; marks an image as no longer
  relevant.
- **Supersede**: replace an ACTIVE image with a new APPROVED one — the old
  image is marked SUPERSEDED (never deleted) and remains visible via its
  detail page.

## Viewing a baseline image (Section 11)

The detail page shows: the image itself (loaded through the same
authenticated-image path used elsewhere in the platform, never a public
URL), its ID and SHA-256 hash, source type, manufacturer/model, anatomy
zone, inspection view, version, current lifecycle status, the latest
review decision (reviewer, rationale, limitations), effective date, linked
Digital Twin identity, and — when applicable — the link it supersedes.
**No similarity score is shown or computed here** — this sprint does not
implement image-based comparison; only compatibility/resolution decisions
and image evidence management.

## Roles at a glance

| Role | Can do |
|---|---|
| Technician / Operator | View ACTIVE baseline images within scope; create DRAFT links; cannot review or activate |
| Reviewer | Review within scope |
| Clinical Reviewer / SPD Manager | Approve/reject, activate/suspend/archive/supersede within scope |
| Administrator | Manage lifecycle, view the legacy migration report; cannot bypass any evidence requirement |
| AI Researcher | View baseline images for use in governed datasets; cannot review, approve, or activate |
| Viewer | Read-only |

## Legacy migration report

Administrators and SPD managers can view `/baselines/library?report=1` for
a summary of every pre-existing metadata-only `BaselineLibraryEntry`: how
many now have an ACTIVE image, how many are missing image evidence
(marked `IMAGE_EVIDENCE_MISSING`), missing anatomy zone, missing usage
rights, or awaiting review. See `BASELINE_LIBRARY_MANUAL_ACCEPTANCE.md`
Scenario 9 for the expected behavior of a metadata-only entry.
