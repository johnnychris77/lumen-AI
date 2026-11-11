# Inspection #17 — "No visual (pixel) comparison was performed" diagnosis

PR #155 (merge commit `677d7d54`) is in `main`, yet production Inspection #17 still
shows *"Baseline reference image: No visual (pixel) comparison was performed."*
This is a diagnosis of the **deployed** workflow — not a new comparison engine.

## Sandbox limitation (stated up front)

This CI/sandbox cannot reach `*.onrender.com` (outbound proxy 403), so I could not
read Inspection #17's live record, the production upload response, or the backend
logs directly. The diagnosis below is established from the code paths and the
exact production message, and the fixes are verified locally end-to-end. Two
production checks only the operator can run are listed at the end.

## What the message tells us (primary signal)

The exact string *"No visual (pixel) comparison was performed."* is produced by
**one** place in the current frontend — `baselineImageStatusText()` in
`NewInspectionPage.tsx` — and **only** on its `if (!ev)` branch, i.e. when the
inspection's API response contains **no `baseline_evidence` object at all**:

```ts
function baselineImageStatusText(ev, reason) {
  if (!ev) return reason || "No visual (pixel) comparison was performed.";   // ← this
  if (ev.real_image_comparison_completed) return "Baseline visual comparison available.";
  … specific messages for metadata / registered / active / compatible / bytes …
}
```

Every merged backend path (#153–#155) **always** returns `baseline_evidence` —
including the AI-unavailable, no-baseline, and "bytes unavailable" cases, each of
which would yield a *specific* message ("…awaiting activation", "…bytes are
unavailable", etc.). The only ways to get the generic `!ev` message are:

1. **The deployed backend is not running the merged code** (it predates
   `baseline_evidence`, added in #153) — a deployment/restart gap; **or**
2. The backend has the code but `analyze_inspection` **raised**, so the route
   fell to its `analysis_failed` fallback (which omitted `baseline_evidence`).

Either way the primary blocker is **the backend, not the comparison logic** — and
most likely that **the Render backend has not been redeployed/restarted onto
`677d7d54`**. (Note: the backend bootstraps its schema with `create_all` +
`ensure_all_columns` at **startup**, so the new `inspection_processing_images`
table and the new `inspections.baseline_comparison_*` columns only appear after a
restart onto the merged code.)

## Secondary blocker found in code (fixed here)

Independently, there is a real **tenant-resolution mismatch** between the two
endpoints that cooperate on the comparison — it would silently break the
comparison for a logged-in (JWT) user *even once the backend is deployed*:

| Endpoint | Tenant resolution (before) |
|---|---|
| `POST /api/inspections` (create) | `current_user.tenant_id or request header` |
| `POST /api/inspections/upload-images` (stores the processing image) | **request header only** |

For a real JWT user whose membership tenant is resolved server-side and whose
client sends no `X-Tenant-Id` header, the upload stored the temporary processing
image under `default-tenant` while the inspection looked it up under the user's
real tenant → `load_processing_bytes` returns `None` → pixels unavailable → no
comparison. The existing tests masked it by sending an explicit `X-Tenant-Id` on
both calls. **Fix:** the upload endpoint now resolves tenant identically to
create (`current_user.tenant_id or header`). Regression test:
`test_upload_and_create_resolve_same_tenant_for_jwt_user` (no header, JWT tenant
set → comparison succeeds).

## Making production diagnosable (so the real cause is confirmable)

- `/health` now returns `git_commit` (from `RENDER_GIT_COMMIT`), so the operator
  can confirm whether the backend is actually running `677d7d54`.
- `POST /api/inspections/upload-images` now returns `processing_error` (not just a
  log line) when the temporary-processing store fails — e.g. if the
  `inspection_processing_images` table/migration is missing on an un-restarted
  backend, the API response names it directly.
- The create route no longer 500s if the processing table is missing; it degrades
  to "pixels unavailable" and logs, so a partial deploy fails safe.

## Correct the confirmed blocker + evidence

Local end-to-end (real HTTP), JWT user, **no** tenant header — the exact
production auth shape — now produces a real comparison:

```
UPLOAD (no X-Tenant-Id):  processing_available: true
RAW API baseline_evidence:
  manufacturer_baseline_metadata_found: true   baseline_image_registered: true
  baseline_image_active: true   baseline_image_compatible: true
  inspection_image_bytes_available: true        real_image_comparison_completed: true
  trained_vision_model_available: false
  baseline_image_similarity: {similarity, method: average_hash_hamming,
                              comparator_version: lens-average-hash-v1, baseline_id}
  ai_analysis.status: AI_UNAVAILABLE   authorizes_release: false   human_review_required: true
processing image: consumed (bytes nulled)   not enrolled in training
```

Full backend suite **3825 passed, 2 skipped**; `ruff` + frontend `vite build` clean.

## Two checks only the operator can run (to confirm #1)

1. `GET https://<backend>.onrender.com/health` → confirm `git_commit` is
   `677d7d54…`. If it is **not**, the backend is not deployed — redeploy/restart
   it; that alone should resolve #17 (plus this PR for the tenant case).
2. Re-run Inspection #17's upload and inspect the raw API responses:
   - upload response `processing_available` (and `processing_error` if false), and
   - inspection response — does `analysis.baseline_evidence` exist? If it is
     **absent**, the backend is old (see #1). If present with
     `inspection_image_bytes_available: false`, it is the tenant case this PR
     fixes (confirm the baseline link is ACTIVE for the user's tenant).
