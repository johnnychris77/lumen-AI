# Baseline Compatibility Contract — Project Atlas Sprint 1

Implements mission Section 7. `app/services/baseline_compatibility_service.py`
decides **whether** a candidate inspection image and a baseline image are
comparable at all — it never computes or returns a numeric similarity
itself. The actual pixel comparison, once compatibility is established, is
`app.services.ml.image_similarity_service` (Project Lens) — unchanged,
reused as-is, never reimplemented here.

## `check_compatibility(candidate, baseline_link)`

Evaluated in this order (first match wins):

1. `baseline_link is None` → `NO_APPROVED_BASELINE`
2. `candidate.tenant_id != baseline_link.tenant_id` → `NO_APPROVED_BASELINE`
   (cross-tenant baselines are never distinguished from "nothing approved"
   — tenant isolation must never leak a "this exists but isn't yours"
   signal, per the project's non-negotiable security constraints)
3. `baseline_link.lifecycle_status != ACTIVE` → `BASELINE_NOT_ACTIVE`
4. Manufacturer mismatch (when both sides specify one) → `INCOMPATIBLE_INSTRUMENT`
5. Instrument family mismatch → `INCOMPATIBLE_INSTRUMENT`
6. Anatomy zone mismatch → `INCOMPATIBLE_ANATOMY_ZONE`
7. Inspection view mismatch → `INCOMPATIBLE_VIEW`
8. Orientation mismatch → `INCOMPATIBLE_ORIENTATION`
9. Candidate image quality is `Reject` or `Poor` → `INSUFFICIENT_IMAGE_QUALITY`
10. Otherwise → `COMPATIBLE`

Every non-`COMPATIBLE` outcome is a distinct, named reason — never a
generic false or a fabricated partial score. **No numeric similarity is
generated when compatibility fails** (mission Section 7's explicit
constraint): `check_compatibility()`'s return type is a plain status
string, with no similarity field at all, so there is no code path that
could accidentally attach a number to an incompatible pairing.

## Outcome vocabulary

`COMPATIBLE`, `INCOMPATIBLE_INSTRUMENT`, `INCOMPATIBLE_ANATOMY_ZONE`,
`INCOMPATIBLE_VIEW`, `INCOMPATIBLE_ORIENTATION`,
`INSUFFICIENT_IMAGE_QUALITY`, `BASELINE_NOT_ACTIVE`, `NO_APPROVED_BASELINE`
— exactly the eight values the mission specifies, defined as module-level
constants in `app/models/baseline_image_library.py` and reused (not
re-declared) by the route layer and tests.

## API

`POST /api/baseline-library/compatibility-check` accepts a
`CandidateContext`-shaped body (instrument family, manufacturer, model,
anatomy zone, view, orientation, image quality status, Digital Twin ID)
plus an optional `baseline_image_link_id` query parameter identifying
which specific baseline image to check against. Returns `{"status":
"<one of the eight values>"}`.

## Relationship to resolution

Compatibility checking is deliberately a separate function from
resolution (`BASELINE_RESOLUTION_HIERARCHY.md`). Resolution picks *which*
baseline image should be used for a given context; compatibility checking
answers whether a *specific* candidate/baseline pairing may be compared at
all. The resolution hierarchy calls the same tenant/lifecycle-status
filters internally so a resolved baseline is always `ACTIVE` and
tenant-scoped, but a caller with a specific baseline image in hand (e.g.
from a `BaselineSet`) can call `check_compatibility()` directly without
going through resolution.

## What this sprint does not do

Per the mission's non-negotiable constraint ("do not implement a trained
vision model in this sprint" / "do not fabricate baseline similarity"),
this module does not call, wrap, or modify `image_similarity_service.py`.
It only decides whether that comparator would be an honest thing to run at
all for a given pairing. Wiring an actual numeric comparison into this
contract (once compatible) is future work, not part of this sprint's
scope.
