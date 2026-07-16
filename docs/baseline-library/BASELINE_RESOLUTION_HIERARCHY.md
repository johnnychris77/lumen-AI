# Baseline Resolution Hierarchy — Project Atlas Sprint 1

Implements mission Section 8. `resolve_baseline_image()`
(`app/services/baseline_compatibility_service.py`) picks the single best
`ACTIVE`, approved baseline image for one candidate instrument context,
following a fixed, most-specific-first hierarchy — never silently falling
back to a broader baseline unless the caller allows it.

## The hierarchy, in order

1. **`digital_twin_exact`** — an `ACTIVE` baseline image whose
   `digital_twin_id` exactly matches the candidate's, and that identity is
   *tracked* (`not is_untracked_twin(...)`). This is the exact
   physical-instrument baseline: the strongest possible match, because it
   is keyed to one specific real instrument rather than a model or family.
2. **`manufacturer_model_zone`** — an `ACTIVE` baseline image with matching
   `manufacturer`, `model_name`, and `anatomy_zone` (requires all three to
   be present on the candidate).
3. **`organization_family_zone`** — an `ACTIVE` baseline image with matching
   `instrument_family` and `anatomy_zone`, restricted to organization
   source types (`organization_known_good`, `new_instrument_reference`,
   `post_repair_reference`) — an organization-approved reference, broader
   than manufacturer/model-specific.
4. **`governed_consensus`** — an `ACTIVE` baseline image with matching
   `instrument_family` and `source_type == governed_consensus_reference` —
   an authorized cross-organization consensus reference, broader still.
5. **`none`** — nothing approved resolves; returned with an honest reason,
   never a fabricated fallback.

Each level is tried in order; the **first** level that produces a match
wins — the function does not compare across levels or pick "the best
score," matching the mission's requirement that an exact match always
resolves before a broader one, never the reverse.

## `require_exact`

Some organization policies forbid comparison against anything looser than
the exact Digital Twin baseline. Passing `require_exact=True` makes the
function attempt only level 1; a miss returns `resolution_scope="none"`
with the reason "Organization policy requires an exact Digital Twin
baseline and none is approved — not falling back to a broader baseline,"
and a `limitations` entry making the same point explicit to the caller.
This is the mechanism satisfying "do not silently use a broader baseline
when an exact baseline is required by organization policy" (Section 8).

## `ResolutionResult`

Every resolution call returns:

- `baseline_image_link_id` (or `None`)
- `baseline_set_id` (reserved; always `None` today — set-level resolution
  is not yet wired, only individual-link resolution)
- `resolution_scope` — one of the five hierarchy levels above
- `resolution_reason` — a human-readable sentence explaining why this
  particular result was chosen
- `version` — the resolved link's `baseline_version`
- `limitations` — a list of caveats (e.g. "Consensus reference — not
  manufacturer, model, or anatomy-zone specific")

This full record — not just an image ID — is what callers and the audit
trail persist, so a later reviewer can see *why* a given baseline was
selected, not just *that* one was.

## Tenant isolation

Every level filters `BaselineImageLink.tenant_id == candidate.tenant_id`
first. A baseline image belonging to a different tenant is never resolved,
matched, or hinted at — it is invisible to resolution exactly as if it did
not exist, consistent with `check_compatibility()`'s cross-tenant handling
in `BASELINE_COMPATIBILITY_CONTRACT.md`.

## API

`POST /api/baseline-library/resolve` (optional `require_exact` query
param) accepts the same `CandidateContext` body shape as
compatibility-check and returns the full `ResolutionResult` as JSON.
