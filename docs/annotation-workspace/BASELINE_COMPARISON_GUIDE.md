# Baseline Comparison Guide

Source: `app/services/baseline_comparison_service.py`
(`compare_to_baselines()`),
`GET /api/dataset-registry/images/{entry_id}/baseline-comparison`, and
`lcid_service.digital_twin_history()`'s `timeline` field (extended,
additive, this sprint) surfaced by `DatasetImageDetailPage.tsx`
(`/dataset/images/:imageId`).

## Four baseline buckets, each independently resolved

| Bucket | Resolved from |
|---|---|
| Manufacturer | `entry.baseline_id` → `BaselineLibraryEntry` |
| Organization | Sibling entry with `baseline_type == "network_contributed"` |
| Digital Twin | Sibling entry sharing the same `digital_twin_id` with `image_type == "baseline_reference"` |
| Research | Sibling entry with `image_type == "research_reference"`, `review_status == APPROVED`, matching instrument family/manufacturer |

Each bucket independently returns `{"available": false, "reason": "..."}`
when nothing resolves — never a fabricated comparison. A bucket is only
`"available": true` when a real row was found and its `source` is named.

## Never presenting an unapproved baseline as authoritative

An unreviewed (`review_status != APPROVED`) sibling entry is never
returned as a Research baseline; an unresolved manufacturer/organization/
Digital-Twin bucket is reported unavailable rather than falling back to
an unrelated entry.

## Digital Twin timeline

`digital_twin_history()`'s `timeline` field lists every
`DatasetRegistryEntry` sharing the same `digital_twin_id`
(`{id, lcid, image_type, capture_date, review_status, baseline_id,
created_at}`), ordered chronologically — rendered inline as an ordered
list in the image detail page's instrument-context panel, not linked out
to the unrelated pre-existing `/digital-twin` knowledge-graph dashboard
(`DigitalTwinPage.tsx`, a different concept from LCID's barcode/UDI-based
identity).

## Tests

`backend/tests/test_review_workspace.py` (baseline-comparison resolves an
approved manufacturer baseline / reports unavailable when nothing
resolves; digital-twin timeline includes per-image detail).
